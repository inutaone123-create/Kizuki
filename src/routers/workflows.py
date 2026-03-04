"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Workflow, Issue
from src.schemas import WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowStepUpdate, IssueResponse

router = APIRouter(tags=["workflows"])


def _to_response(wf: Workflow) -> WorkflowResponse:
    """WorkflowモデルをWorkflowResponseに変換する.

    Args:
        wf: Workflowモデルインスタンス

    Returns:
        WorkflowResponse
    """
    steps = json.loads(wf.steps) if isinstance(wf.steps, str) else wf.steps
    return WorkflowResponse(
        id=wf.id,
        name=wf.name,
        steps=steps,
        created_at=wf.created_at,
    )


@router.get("/api/workflows", response_model=list[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db)):
    """ワークフロー一覧を取得する.

    Args:
        db: DBセッション

    Returns:
        ワークフローのリスト
    """
    return [_to_response(wf) for wf in db.query(Workflow).order_by(Workflow.name).all()]


@router.post("/api/workflows", response_model=WorkflowResponse, status_code=201)
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db)):
    """ワークフローを新規作成する.

    Args:
        body: 作成するワークフローのデータ
        db: DBセッション

    Returns:
        作成されたワークフロー
    """
    wf = Workflow(name=body.name, steps=json.dumps(body.steps, ensure_ascii=False))
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _to_response(wf)


@router.put("/api/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(workflow_id: int, body: WorkflowUpdate, db: Session = Depends(get_db)):
    """ワークフローを更新する.

    Args:
        workflow_id: ワークフローID
        body: 更新するフィールド
        db: DBセッション

    Returns:
        更新後のワークフロー

    Raises:
        HTTPException: ワークフローが存在しない場合
    """
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if body.name is not None:
        wf.name = body.name
    if body.steps is not None:
        wf.steps = json.dumps(body.steps, ensure_ascii=False)
    db.commit()
    db.refresh(wf)
    return _to_response(wf)


@router.delete("/api/workflows/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """ワークフローを削除する.

    Args:
        workflow_id: ワークフローID
        db: DBセッション

    Raises:
        HTTPException: ワークフローが存在しない場合
    """
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()


@router.patch("/api/issues/{issue_id}/workflow-step", response_model=IssueResponse)
def update_workflow_step(
    issue_id: int, body: WorkflowStepUpdate, db: Session = Depends(get_db)
):
    """イシューのワークフローステップを更新する.

    Args:
        issue_id: イシューID
        body: 新しいステップインデックス
        db: DBセッション

    Returns:
        更新後のイシュー

    Raises:
        HTTPException: イシューが存在しない場合、またはワークフロー未割り当ての場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not issue.workflow_id:
        raise HTTPException(status_code=400, detail="ワークフローが割り当てられていません")
    wf = db.query(Workflow).filter(Workflow.id == issue.workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    steps = json.loads(wf.steps)
    if body.step < 0 or body.step >= len(steps):
        raise HTTPException(
            status_code=400,
            detail=f"ステップインデックスは 0〜{len(steps) - 1} の範囲で指定してください",
        )
    issue.workflow_step = body.step
    db.commit()
    db.refresh(issue)
    return issue

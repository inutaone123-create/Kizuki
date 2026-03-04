"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Issue
from src.schemas import (
    IssueCreate,
    IssueUpdate,
    IssueStatusUpdate,
    IssueResponse,
    IssueListResponse,
    AssigneeInfo,
    WorkflowInfo,
)
import json

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("", response_model=list[IssueListResponse])
def list_issues(
    status: str | None = Query(None, description="ステータスフィルター"),
    priority: str | None = Query(None, description="優先度フィルター"),
    category: str | None = Query(None, description="カテゴリフィルター"),
    db: Session = Depends(get_db),
):
    """イシュー一覧を取得する.

    Args:
        status: ステータスで絞り込む（todo / in_progress / done）
        priority: 優先度で絞り込む（high / medium / low）
        category: カテゴリで絞り込む
        db: DBセッション

    Returns:
        イシューのリスト
    """
    query = db.query(Issue)
    if status:
        query = query.filter(Issue.status == status)
    if priority:
        query = query.filter(Issue.priority == priority)
    if category:
        query = query.filter(Issue.category == category)
    return query.order_by(Issue.updated_at.desc()).all()


@router.post("", response_model=IssueResponse, status_code=201)
def create_issue(body: IssueCreate, db: Session = Depends(get_db)):
    """イシューを新規作成する.

    Args:
        body: 作成するイシューのデータ
        db: DBセッション

    Returns:
        作成されたイシュー
    """
    issue = Issue(**body.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    """イシューの詳細を取得する.

    Args:
        issue_id: イシューID
        db: DBセッション

    Returns:
        イシュー詳細（作業ログ含む）

    Raises:
        HTTPException: イシューが存在しない場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.put("/{issue_id}", response_model=IssueResponse)
def update_issue(issue_id: int, body: IssueUpdate, db: Session = Depends(get_db)):
    """イシューを更新する.

    Args:
        issue_id: イシューID
        body: 更新するフィールド（指定したフィールドのみ更新）
        db: DBセッション

    Returns:
        更新後のイシュー

    Raises:
        HTTPException: イシューが存在しない場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)
    db.commit()
    db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=204)
def delete_issue(issue_id: int, db: Session = Depends(get_db)):
    """イシューを削除する.

    Args:
        issue_id: イシューID
        db: DBセッション

    Raises:
        HTTPException: イシューが存在しない場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    db.delete(issue)
    db.commit()


@router.patch("/{issue_id}/status", response_model=IssueResponse)
def update_issue_status(
    issue_id: int, body: IssueStatusUpdate, db: Session = Depends(get_db)
):
    """イシューのステータスのみを更新する（カンバン用）.

    Args:
        issue_id: イシューID
        body: 新しいステータス
        db: DBセッション

    Returns:
        更新後のイシュー

    Raises:
        HTTPException: イシューが存在しない場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = body.status
    db.commit()
    db.refresh(issue)
    return issue

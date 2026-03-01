"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Issue, WorkLog
from src.schemas import WorkLogCreate, WorkLogResponse

router = APIRouter(tags=["logs"])


@router.get("/api/issues/{issue_id}/logs", response_model=list[WorkLogResponse])
def list_logs(issue_id: int, db: Session = Depends(get_db)):
    """イシューに紐づく作業ログ一覧を取得する.

    Args:
        issue_id: イシューID
        db: DBセッション

    Returns:
        作業ログのリスト（新しい順）

    Raises:
        HTTPException: イシューが存在しない場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return (
        db.query(WorkLog)
        .filter(WorkLog.issue_id == issue_id)
        .order_by(WorkLog.logged_at.desc(), WorkLog.created_at.desc())
        .all()
    )


@router.post(
    "/api/issues/{issue_id}/logs", response_model=WorkLogResponse, status_code=201
)
def create_log(issue_id: int, body: WorkLogCreate, db: Session = Depends(get_db)):
    """イシューに作業ログを追加する.

    Args:
        issue_id: イシューID
        body: 作成するログのデータ
        db: DBセッション

    Returns:
        作成された作業ログ

    Raises:
        HTTPException: イシューが存在しない場合
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    log = WorkLog(issue_id=issue_id, **body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/api/logs/{log_id}", status_code=204)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    """作業ログを削除する.

    Args:
        log_id: 作業ログID
        db: DBセッション

    Raises:
        HTTPException: ログが存在しない場合
    """
    log = db.query(WorkLog).filter(WorkLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    db.delete(log)
    db.commit()

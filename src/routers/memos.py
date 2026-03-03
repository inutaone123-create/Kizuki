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
from src.schemas import MemoCreate, MemoIssueUpdate, MemoResponse, MemoUpdate

router = APIRouter(prefix="/api/memos", tags=["memos"])


def _to_memo_response(log: WorkLog) -> MemoResponse:
    """WorkLog を MemoResponse に変換する.

    Args:
        log: WorkLog ORM インスタンス

    Returns:
        MemoResponse（issue_title を含む）
    """
    issue_title = log.issue.title if log.issue else None
    return MemoResponse(
        id=log.id,
        issue_id=log.issue_id,
        content=log.content,
        logged_at=log.logged_at,
        created_at=log.created_at,
        issue_title=issue_title,
    )


@router.get("", response_model=list[MemoResponse])
def list_memos(db: Session = Depends(get_db)):
    """全メモ一覧を取得する（logged_at 降順）.

    Args:
        db: DBセッション

    Returns:
        メモのリスト（新しい日付順）
    """
    logs = (
        db.query(WorkLog)
        .order_by(WorkLog.logged_at.desc(), WorkLog.created_at.desc())
        .all()
    )
    return [_to_memo_response(log) for log in logs]


@router.post("", response_model=MemoResponse, status_code=201)
def create_memo(body: MemoCreate, db: Session = Depends(get_db)):
    """新規メモを作成する（タスク紐付けは任意）.

    Args:
        body: メモ作成データ
        db: DBセッション

    Returns:
        作成されたメモ

    Raises:
        HTTPException: 指定したタスクが存在しない場合
    """
    if body.issue_id is not None:
        issue = db.query(Issue).filter(Issue.id == body.issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
    log = WorkLog(**body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return _to_memo_response(log)


@router.put("/{memo_id}", response_model=MemoResponse)
def update_memo(memo_id: int, body: MemoUpdate, db: Session = Depends(get_db)):
    """メモを更新する（内容・日付・タスク紐付けを変更可能）.

    Args:
        memo_id: メモID
        body: 更新データ（変更しないフィールドは None）
        db: DBセッション

    Returns:
        更新されたメモ

    Raises:
        HTTPException: メモまたは指定タスクが存在しない場合
    """
    log = db.query(WorkLog).filter(WorkLog.id == memo_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Memo not found")

    data = body.model_dump(exclude_unset=True)

    if "issue_id" in data and data["issue_id"] is not None:
        issue = db.query(Issue).filter(Issue.id == data["issue_id"]).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

    for key, value in data.items():
        setattr(log, key, value)

    db.commit()
    db.refresh(log)
    return _to_memo_response(log)


@router.delete("/{memo_id}", status_code=204)
def delete_memo(memo_id: int, db: Session = Depends(get_db)):
    """メモを削除する.

    Args:
        memo_id: メモID
        db: DBセッション

    Raises:
        HTTPException: メモが存在しない場合
    """
    log = db.query(WorkLog).filter(WorkLog.id == memo_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Memo not found")
    db.delete(log)
    db.commit()


@router.patch("/{memo_id}/issue", response_model=MemoResponse)
def update_memo_issue(
    memo_id: int, body: MemoIssueUpdate, db: Session = Depends(get_db)
):
    """メモのタスク紐付けのみを変更する（issue_id: null で解除）.

    Args:
        memo_id: メモID
        body: issue_id（null で解除）
        db: DBセッション

    Returns:
        更新されたメモ

    Raises:
        HTTPException: メモまたは指定タスクが存在しない場合
    """
    log = db.query(WorkLog).filter(WorkLog.id == memo_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Memo not found")

    if body.issue_id is not None:
        issue = db.query(Issue).filter(Issue.id == body.issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

    log.issue_id = body.issue_id
    db.commit()
    db.refresh(log)
    return _to_memo_response(log)

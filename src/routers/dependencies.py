"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Issue, IssueDependency
from src.schemas import DependencyAdd

router = APIRouter(prefix="/api/issues", tags=["dependencies"])


@router.get("/{issue_id}/dependencies")
def get_dependencies(issue_id: int, db: Session = Depends(get_db)):
    """タスクの依存関係を取得する.

    Args:
        issue_id: イシューID
        db: DBセッション

    Returns:
        blocked_by: このタスクをブロックしているタスクのID・タイトル一覧
        blocking: このタスクがブロックしているタスクのID・タイトル一覧
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    blocked_by = (
        db.query(Issue)
        .join(IssueDependency, IssueDependency.blocked_by_id == Issue.id)
        .filter(IssueDependency.issue_id == issue_id)
        .all()
    )
    blocking = (
        db.query(Issue)
        .join(IssueDependency, IssueDependency.issue_id == Issue.id)
        .filter(IssueDependency.blocked_by_id == issue_id)
        .all()
    )

    return {
        "blocked_by": [{"id": i.id, "title": i.title, "status": i.status} for i in blocked_by],
        "blocking": [{"id": i.id, "title": i.title, "status": i.status} for i in blocking],
    }


@router.post("/{issue_id}/dependencies", status_code=201)
def add_dependency(issue_id: int, body: DependencyAdd, db: Session = Depends(get_db)):
    """依存関係を追加する（issue_id は blocked_by_id が完了するまでブロック）.

    Args:
        issue_id: ブロックされるタスクのID
        body: blocked_by_id（ブロックするタスクのID）
        db: DBセッション

    Returns:
        作成された依存関係

    Raises:
        HTTPException: タスクが存在しない、自己参照、既存の依存関係、循環依存の場合
    """
    if issue_id == body.blocked_by_id:
        raise HTTPException(status_code=400, detail="Self-dependency not allowed")

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    blocker = db.query(Issue).filter(Issue.id == body.blocked_by_id).first()
    if not blocker:
        raise HTTPException(status_code=404, detail="Blocker issue not found")

    existing = (
        db.query(IssueDependency)
        .filter(
            IssueDependency.issue_id == issue_id,
            IssueDependency.blocked_by_id == body.blocked_by_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Dependency already exists")

    # 循環依存チェック: body.blocked_by_id が issue_id に依存していないか
    reverse = (
        db.query(IssueDependency)
        .filter(
            IssueDependency.issue_id == body.blocked_by_id,
            IssueDependency.blocked_by_id == issue_id,
        )
        .first()
    )
    if reverse:
        raise HTTPException(status_code=400, detail="Circular dependency not allowed")

    dep = IssueDependency(issue_id=issue_id, blocked_by_id=body.blocked_by_id)
    db.add(dep)
    db.commit()
    return {"issue_id": issue_id, "blocked_by_id": body.blocked_by_id}


@router.delete("/{issue_id}/dependencies/{blocked_by_id}", status_code=204)
def remove_dependency(issue_id: int, blocked_by_id: int, db: Session = Depends(get_db)):
    """依存関係を削除する.

    Args:
        issue_id: ブロックされるタスクのID
        blocked_by_id: ブロックしているタスクのID
        db: DBセッション

    Raises:
        HTTPException: 依存関係が存在しない場合
    """
    dep = (
        db.query(IssueDependency)
        .filter(
            IssueDependency.issue_id == issue_id,
            IssueDependency.blocked_by_id == blocked_by_id,
        )
        .first()
    )
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    db.delete(dep)
    db.commit()

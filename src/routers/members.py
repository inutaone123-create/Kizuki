"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Member
from src.schemas import MemberCreate, MemberUpdate, MemberResponse

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("", response_model=list[MemberResponse])
def list_members(db: Session = Depends(get_db)):
    """メンバー一覧を取得する.

    Args:
        db: DBセッション

    Returns:
        メンバーのリスト
    """
    return db.query(Member).order_by(Member.name).all()


@router.post("", response_model=MemberResponse, status_code=201)
def create_member(body: MemberCreate, db: Session = Depends(get_db)):
    """メンバーを新規作成する.

    Args:
        body: 作成するメンバーのデータ
        db: DBセッション

    Returns:
        作成されたメンバー

    Raises:
        HTTPException: 同名メンバーが既に存在する場合
    """
    existing = db.query(Member).filter(Member.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="同名のメンバーが既に存在します")
    member = Member(**body.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, body: MemberUpdate, db: Session = Depends(get_db)):
    """メンバーを更新する.

    Args:
        member_id: メンバーID
        body: 更新するフィールド
        db: DBセッション

    Returns:
        更新後のメンバー

    Raises:
        HTTPException: メンバーが存在しない場合
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """メンバーを削除する.

    Args:
        member_id: メンバーID
        db: DBセッション

    Raises:
        HTTPException: メンバーが存在しない場合
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()

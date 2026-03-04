"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import AISettings
from src.schemas import AISettingsResponse, AISettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

_DEFAULT_UPDATED_AT = datetime(2026, 1, 1)


@router.get("/ai", response_model=AISettingsResponse)
def get_ai_settings(db: Session = Depends(get_db)):
    """AI設定を取得する（id=1 固定、なければデフォルト値を返す）.

    Args:
        db: DBセッション

    Returns:
        AI設定（api_key は返さず has_api_key: bool で代替）
    """
    cfg = db.query(AISettings).filter(AISettings.id == 1).first()
    if cfg is None:
        return AISettingsResponse(
            base_url=None,
            model=None,
            has_api_key=False,
            updated_at=_DEFAULT_UPDATED_AT,
        )
    return AISettingsResponse(
        base_url=cfg.base_url,
        model=cfg.model,
        has_api_key=bool(cfg.api_key),
        updated_at=cfg.updated_at,
    )


@router.put("/ai", response_model=AISettingsResponse)
def update_ai_settings(body: AISettingsUpdate, db: Session = Depends(get_db)):
    """AI設定を保存する（id=1 固定の upsert）.

    空文字の api_key は無視して既存キーを維持する。

    Args:
        body: AI設定更新データ
        db: DBセッション

    Returns:
        更新後のAI設定
    """
    cfg = db.query(AISettings).filter(AISettings.id == 1).first()
    if cfg is None:
        cfg = AISettings(id=1)
        db.add(cfg)

    if body.base_url is not None:
        cfg.base_url = body.base_url or None
    if body.model is not None:
        cfg.model = body.model or None
    # api_key: 空文字でなければ更新（空文字は「変更なし」として扱う）
    if body.api_key:
        cfg.api_key = body.api_key

    cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)

    return AISettingsResponse(
        base_url=cfg.base_url,
        model=cfg.model,
        has_api_key=bool(cfg.api_key),
        updated_at=cfg.updated_at,
    )

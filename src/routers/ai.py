"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.ai_service import suggest_workflow

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/suggest-workflow")
async def suggest_workflow_endpoint(
    category: str | None = Query(None, description="フィルタリングするカテゴリ（任意）"),
    db: Session = Depends(get_db),
):
    """既存タスクを分析してワークフローを提案する.

    Args:
        category: タスクをフィルタリングするカテゴリ（任意）
        db: DBセッション

    Returns:
        suggested_name: 提案ワークフロー名
        suggested_steps: 提案ステップリスト
        reason: 提案理由
        is_ai_generated: AI生成フラグ
    """
    return await suggest_workflow(db, category)

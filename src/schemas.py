"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, Field


# ---------- WorkLog スキーマ ----------

class WorkLogCreate(BaseModel):
    """作業ログ作成リクエスト."""

    content: str = Field(..., min_length=1, description="Markdown形式の作業内容")
    logged_at: date = Field(default_factory=date.today, description="作業日")


class WorkLogResponse(BaseModel):
    """作業ログレスポンス."""

    id: int
    issue_id: int
    content: str
    logged_at: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Issue スキーマ ----------

StatusType = Literal["todo", "in_progress", "done"]
PriorityType = Literal["high", "medium", "low"]


class IssueCreate(BaseModel):
    """イシュー作成リクエスト."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    status: StatusType = "todo"
    priority: PriorityType = "medium"
    category: str | None = None
    tags: str | None = Field(None, description="カンマ区切りタグ")


class IssueUpdate(BaseModel):
    """イシュー更新リクエスト（全フィールド任意）."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: StatusType | None = None
    priority: PriorityType | None = None
    category: str | None = None
    tags: str | None = None


class IssueStatusUpdate(BaseModel):
    """イシューステータス更新リクエスト（カンバン用）."""

    status: StatusType


class IssueResponse(BaseModel):
    """イシューレスポンス."""

    id: int
    title: str
    description: str | None
    status: str
    priority: str
    category: str | None
    tags: str | None
    created_at: datetime
    updated_at: datetime
    logs: list[WorkLogResponse] = []

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    """イシュー一覧レスポンス（ログなし）."""

    id: int
    title: str
    description: str | None
    status: str
    priority: str
    category: str | None
    tags: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

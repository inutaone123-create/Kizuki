"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import json
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, Field, field_validator

# ---------- WorkLog スキーマ ----------


class WorkLogCreate(BaseModel):
    """作業ログ作成リクエスト."""

    content: str = Field(..., min_length=1, description="Markdown形式の作業内容")
    logged_at: date = Field(default_factory=date.today, description="作業日")


class WorkLogResponse(BaseModel):
    """作業ログレスポンス."""

    id: int
    issue_id: int | None
    content: str
    logged_at: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Memo スキーマ ----------


class MemoCreate(BaseModel):
    """メモ作成リクエスト（issue_id 任意）."""

    content: str = Field(..., min_length=1, description="Markdown形式のメモ内容")
    logged_at: date = Field(default_factory=date.today, description="メモ日付")
    issue_id: int | None = Field(None, description="紐付けるタスクID（任意）")


class MemoUpdate(BaseModel):
    """メモ更新リクエスト（全フィールド任意）."""

    content: str | None = Field(None, min_length=1, description="Markdown形式のメモ内容")
    logged_at: date | None = Field(None, description="メモ日付")
    issue_id: int | None = Field(None, description="紐付けるタスクID（None で解除）")


class MemoIssueUpdate(BaseModel):
    """メモのタスク紐付けのみ更新するリクエスト."""

    issue_id: int | None = Field(None, description="紐付けるタスクID（None で解除）")


class MemoResponse(BaseModel):
    """メモレスポンス."""

    id: int
    issue_id: int | None
    content: str
    logged_at: date
    created_at: datetime
    issue_title: str | None = Field(None, description="紐付けタスクのタイトル（表示用）")

    model_config = {"from_attributes": True}


# ---------- Member スキーマ ----------


class MemberCreate(BaseModel):
    """メンバー作成リクエスト."""

    name: str = Field(..., min_length=1, max_length=100, description="メンバー名")
    color: str = Field("#6366f1", max_length=7, description="HEXカラーコード")


class MemberUpdate(BaseModel):
    """メンバー更新リクエスト（全フィールド任意）."""

    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=7)


class MemberResponse(BaseModel):
    """メンバーレスポンス."""

    id: int
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Workflow スキーマ ----------


class WorkflowCreate(BaseModel):
    """ワークフロー作成リクエスト."""

    name: str = Field(..., min_length=1, max_length=100, description="ワークフロー名")
    steps: list[str] = Field(..., min_length=1, description="ステップ名リスト")


class WorkflowUpdate(BaseModel):
    """ワークフロー更新リクエスト（全フィールド任意）."""

    name: str | None = Field(None, min_length=1, max_length=100)
    steps: list[str] | None = None


class WorkflowResponse(BaseModel):
    """ワークフローレスポンス."""

    id: int
    name: str
    steps: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("steps", mode="before")
    @classmethod
    def parse_steps(cls, v):
        """steps JSON文字列をリストに変換する."""
        if isinstance(v, str):
            return json.loads(v)
        return v


# ---------- WorkflowStep スキーマ ----------


class WorkflowStepUpdate(BaseModel):
    """ワークフローステップ更新リクエスト."""

    step: int = Field(..., ge=0, description="新しいステップインデックス（0始まり）")


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
    assignee_id: int | None = Field(None, description="担当者ID")
    workflow_id: int | None = Field(None, description="ワークフローID")
    workflow_step: int | None = Field(None, description="現在のステップインデックス")


class IssueUpdate(BaseModel):
    """イシュー更新リクエスト（全フィールド任意）."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: StatusType | None = None
    priority: PriorityType | None = None
    category: str | None = None
    tags: str | None = None
    assignee_id: int | None = None
    workflow_id: int | None = None
    workflow_step: int | None = None


class IssueStatusUpdate(BaseModel):
    """イシューステータス更新リクエスト（カンバン用）."""

    status: StatusType


class AssigneeInfo(BaseModel):
    """担当者情報（イシューレスポンス用）."""

    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}


class WorkflowInfo(BaseModel):
    """ワークフロー情報（イシューレスポンス用）."""

    id: int
    name: str
    steps: list[str]

    model_config = {"from_attributes": True}

    @field_validator("steps", mode="before")
    @classmethod
    def parse_steps(cls, v):
        """steps JSON文字列をリストに変換する."""
        if isinstance(v, str):
            return json.loads(v)
        return v


class IssueResponse(BaseModel):
    """イシューレスポンス."""

    id: int
    title: str
    description: str | None
    status: str
    priority: str
    category: str | None
    tags: str | None
    assignee_id: int | None
    workflow_id: int | None
    workflow_step: int | None
    assignee: AssigneeInfo | None = None
    workflow: WorkflowInfo | None = None
    created_at: datetime
    updated_at: datetime
    logs: list[WorkLogResponse] = []

    model_config = {"from_attributes": True}


# ---------- AI設定 スキーマ ----------


class AISettingsUpdate(BaseModel):
    """AI設定更新リクエスト."""

    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class AISettingsResponse(BaseModel):
    """AI設定レスポンス（api_key は返さない）."""

    base_url: str | None
    model: str | None
    has_api_key: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------- レポート スキーマ ----------

ReportType = Literal["daily", "weekly", "monthly"]


class ReportGenerateRequest(BaseModel):
    """レポート生成リクエスト."""

    report_type: ReportType
    target_date: date


class ReportListItem(BaseModel):
    """レポート一覧アイテム（content を含まない軽量版）."""

    id: int
    report_type: str
    period_start: date
    period_end: date
    title: str
    is_ai_generated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(ReportListItem):
    """レポート詳細レスポンス（content を含む）."""

    content: str


# ---------- Issue スキーマ ----------

class IssueListResponse(BaseModel):
    """イシュー一覧レスポンス（ログなし）."""

    id: int
    title: str
    description: str | None
    status: str
    priority: str
    category: str | None
    tags: str | None
    assignee_id: int | None
    workflow_id: int | None
    workflow_step: int | None
    assignee: AssigneeInfo | None = None
    workflow: WorkflowInfo | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

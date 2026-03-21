"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from datetime import datetime, date
from sqlalchemy import Integer, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class Member(Base):
    """メンバーモデル.

    担当者として登録するメンバーを表す（認証なし・名前ベース）。
    """

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="assignee",
        passive_deletes=True,
    )


class Workflow(Base):
    """ワークフローモデル.

    カスタムステップ（例：申請→承認→実行→完了）を定義するワークフロー。
    steps は JSON 配列文字列で格納する。
    """

    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    steps: Mapped[str] = mapped_column(Text, nullable=False, default='["開始","完了"]')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="workflow",
        passive_deletes=True,
    )


class Issue(Base):
    """イシューモデル.

    カンバンボードの各カードに対応するイシューを表す。
    """

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    workflow_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    workflow_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    logs: Mapped[list["WorkLog"]] = relationship(
        "WorkLog",
        back_populates="issue",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    assignee: Mapped["Member | None"] = relationship("Member", back_populates="issues")
    workflow: Mapped["Workflow | None"] = relationship("Workflow", back_populates="issues")
    blocked_by_deps: Mapped[list["IssueDependency"]] = relationship(
        "IssueDependency",
        foreign_keys="IssueDependency.issue_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    blocking_deps: Mapped[list["IssueDependency"]] = relationship(
        "IssueDependency",
        foreign_keys="IssueDependency.blocked_by_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class IssueDependency(Base):
    """タスク依存関係モデル.

    issue_id のタスクは blocked_by_id のタスクが完了するまでブロックされる。
    """

    __tablename__ = "issue_dependencies"

    issue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )


class WorkLog(Base):
    """作業メモモデル.

    イシューに紐づく（または独立した）日付付きの作業ログ（Markdown形式）を表す。
    issue_id は nullable であり、タスクに紐付けない独立メモとしても使用できる。
    """

    __tablename__ = "work_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    logged_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issue: Mapped["Issue | None"] = relationship("Issue", back_populates="logs")


class AISettings(Base):
    """AI設定モデル.

    OpenAI互換APIの接続情報を保存する（id=1固定の単一レコード）。
    """

    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Report(Base):
    """レポートモデル.

    日報・週報・月報を保存する。content は Markdown 形式。
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Integer, default=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="1970-01-01 00:00:00"
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

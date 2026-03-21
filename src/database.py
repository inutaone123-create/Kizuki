"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_db_path = os.environ.get("KIZUKI_DB_PATH", "./data/issuelog.db")
DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """SQLite 接続時に外部キー制約を有効化する.

    SQLite は PRAGMA foreign_keys = ON を明示的に設定しないと
    外部キー制約（ON DELETE SET NULL 等）が機能しない。
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy ORMの基底クラス."""

    pass


def get_db():
    """DBセッションを生成するジェネレーター.

    Yields:
        DBセッションオブジェクト
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """テーブルを初期化する.

    全テーブルをDBに作成する（既存テーブルはスキップ）。
    既存テーブルへのカラム追加も安全に行う。
    """
    from src import models  # noqa: F401 - モデルをインポートしてテーブル登録

    Base.metadata.create_all(bind=engine)
    _migrate_reports_table()


def _migrate_reports_table():
    """reports テーブルに新カラムを追加する（既存DBへの安全なマイグレーション）."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(
            __import__("sqlalchemy").text("PRAGMA table_info(reports)")
        )}
        migrations = [
            ("status",       "ALTER TABLE reports ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'"),
            ("updated_at",   "ALTER TABLE reports ADD COLUMN updated_at DATETIME DEFAULT '1970-01-01 00:00:00'"),
            ("submitted_at", "ALTER TABLE reports ADD COLUMN submitted_at DATETIME"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(__import__("sqlalchemy").text(sql))
        conn.commit()

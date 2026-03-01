"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./data/issuelog.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

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
    """
    from src import models  # noqa: F401 - モデルをインポートしてテーブル登録

    Base.metadata.create_all(bind=engine)

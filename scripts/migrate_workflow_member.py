"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

"""members/workflows テーブル追加・issues テーブル拡張マイグレーションスクリプト.

SQLite は ALTER COLUMN をサポートしないため、issues テーブルは再作成方式を採用する。

手順:
    1. members テーブルを新規作成
    2. workflows テーブルを新規作成
    3. issues テーブルを新スキーマで再作成し、データをコピー
    4. work_logs テーブルの外部キーを再設定

使い方:
    python3 scripts/migrate_workflow_member.py
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "issuelog.db"


def migrate(db_path: Path) -> None:
    """ワークフロー・メンバー機能向けのマイグレーションを実行する.

    Args:
        db_path: SQLite データベースファイルのパス
    """
    if not db_path.exists():
        print(f"データベースが見つかりません: {db_path}")
        print("サーバーを一度起動してDBを初期化してください。")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        cur = conn.cursor()

        # ── 1. members テーブルを作成（既存なら skip） ──────────────────
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='members'"
        )
        if not cur.fetchone():
            print("members テーブルを作成...")
            cur.execute(
                """
                CREATE TABLE members (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    color VARCHAR(7) NOT NULL DEFAULT '#6366f1',
                    created_at DATETIME
                )
                """
            )
            print("  members テーブル作成完了")
        else:
            print("members テーブルは既に存在します（スキップ）")

        # ── 2. workflows テーブルを作成（既存なら skip） ─────────────────
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'"
        )
        if not cur.fetchone():
            print("workflows テーブルを作成...")
            cur.execute(
                """
                CREATE TABLE workflows (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    steps TEXT NOT NULL DEFAULT '["開始","完了"]',
                    created_at DATETIME
                )
                """
            )
            print("  workflows テーブル作成完了")
        else:
            print("workflows テーブルは既に存在します（スキップ）")

        # ── 3. issues テーブルに新カラムが必要か確認 ────────────────────
        cur.execute("PRAGMA table_info(issues)")
        existing_cols = {row[1] for row in cur.fetchall()}
        needs_migration = not (
            "assignee_id" in existing_cols
            and "workflow_id" in existing_cols
            and "workflow_step" in existing_cols
        )

        if not needs_migration:
            print("issues テーブルは既にマイグレーション済みです（スキップ）")
        else:
            print("issues テーブルを新スキーマで再作成...")

            # 3a. issues_new テーブルを新スキーマで作成
            cur.execute(
                """
                CREATE TABLE issues_new (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'todo',
                    priority VARCHAR(10) DEFAULT 'medium',
                    category VARCHAR(100),
                    tags TEXT,
                    assignee_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
                    workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
                    workflow_step INTEGER,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )

            # 3b. 既存カラムを列挙して、存在するカラムのみコピー
            copy_cols = [
                c for c in ["id", "title", "description", "status", "priority",
                             "category", "tags", "created_at", "updated_at"]
                if c in existing_cols
            ]
            cols_str = ", ".join(copy_cols)
            cur.execute(
                f"""
                INSERT INTO issues_new ({cols_str}, assignee_id, workflow_id, workflow_step)
                SELECT {cols_str}, NULL, NULL, NULL
                FROM issues
                """
            )
            copied = cur.rowcount
            print(f"  {copied} 件のレコードをコピーしました")

            # 3c. 旧 issues テーブルを削除してリネーム
            cur.execute("DROP TABLE issues")
            cur.execute("ALTER TABLE issues_new RENAME TO issues")
            print("  issues テーブル再作成完了")

        conn.commit()
        print("マイグレーション完了！")

    except Exception as e:
        conn.rollback()
        print(f"マイグレーション失敗: {e}")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    migrate(DB_PATH)

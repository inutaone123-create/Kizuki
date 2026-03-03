"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

"""work_logs テーブルの issue_id を nullable に変更するマイグレーションスクリプト.

SQLite は ALTER COLUMN をサポートしないため、テーブル再作成方式を採用する。

手順:
    1. work_logs_new テーブルを nullable issue_id で作成
    2. 既存データをコピー
    3. work_logs を drop
    4. work_logs_new を work_logs にリネーム

使い方:
    python3 scripts/migrate_memo.py
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "issuelog.db"


def migrate(db_path: Path) -> None:
    """work_logs テーブルを nullable issue_id へマイグレーションする.

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

        # 現在のテーブル定義を確認
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='work_logs'"
        )
        row = cur.fetchone()
        if not row:
            print("work_logs テーブルが存在しません。マイグレーション不要です。")
            return

        current_ddl = row[0]
        if "nullable=True" in current_ddl or "issue_id INTEGER" in current_ddl.upper():
            # issue_id が NOT NULL かどうかを確認
            if "NOT NULL" not in current_ddl.upper().split("ISSUE_ID")[1][:30]:
                print("すでにマイグレーション済みです。")
                return

        print("マイグレーション開始...")

        # 1. 新テーブルを nullable issue_id で作成
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS work_logs_new (
                id INTEGER PRIMARY KEY,
                issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
                content TEXT NOT NULL,
                logged_at DATE,
                created_at DATETIME
            )
            """
        )

        # 2. 既存データをコピー
        cur.execute(
            """
            INSERT INTO work_logs_new (id, issue_id, content, logged_at, created_at)
            SELECT id, issue_id, content, logged_at, created_at
            FROM work_logs
            """
        )
        copied = cur.rowcount
        print(f"  {copied} 件のレコードをコピーしました")

        # 3. 旧テーブルを削除
        cur.execute("DROP TABLE work_logs")

        # 4. 新テーブルをリネーム
        cur.execute("ALTER TABLE work_logs_new RENAME TO work_logs")

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

"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

"""既存DBに ai_settings と reports テーブルを追加するマイグレーションスクリプト.

べき等に実行できる（IF NOT EXISTS を使用）。
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "issuelog.db"


def migrate(db_path: Path = DB_PATH) -> None:
    """マイグレーションを実行する.

    Args:
        db_path: SQLite DB ファイルのパス
    """
    if not db_path.exists():
        print(f"DB not found: {db_path} — スキップします")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS ai_settings (
            id          INTEGER PRIMARY KEY,
            base_url    TEXT,
            api_key     TEXT,
            model       TEXT,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type     TEXT    NOT NULL,
            period_start    DATE    NOT NULL,
            period_end      DATE    NOT NULL,
            title           TEXT    NOT NULL,
            content         TEXT    NOT NULL,
            is_ai_generated INTEGER DEFAULT 0,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_reports_id ON reports (id);
    """)

    conn.commit()
    conn.close()
    print("マイグレーション完了: ai_settings, reports テーブルを追加しました")


if __name__ == "__main__":
    migrate()

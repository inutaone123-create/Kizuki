"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

"""サンプルデータ投入スクリプト.

Usage:
    python3 scripts/seed.py
"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal, init_db
from src.models import Issue, WorkLog


def seed():
    """サンプルデータをDBに投入する."""
    init_db()
    db = SessionLocal()

    try:
        # サンプルイシュー
        issues = [
            Issue(
                title="FastAPI バックエンドのセットアップ",
                description="プロジェクトの初期構成を整備する",
                status="done",
                priority="high",
                category="インフラ",
                tags="fastapi,setup,backend",
            ),
            Issue(
                title="カンバンボードUIの実装",
                description="ドラッグ&ドロップ対応のカンバンUIを実装する",
                status="in_progress",
                priority="high",
                category="フロントエンド",
                tags="ui,kanban,javascript",
            ),
            Issue(
                title="作業メモのMarkdownプレビュー",
                description="marked.jsを使ってMarkdownをリアルタイムプレビューする",
                status="todo",
                priority="medium",
                category="フロントエンド",
                tags="markdown,preview",
            ),
            Issue(
                title="READMEの整備",
                description="起動手順・使い方を記述する",
                status="todo",
                priority="low",
                category="ドキュメント",
                tags="docs,readme",
            ),
        ]

        for issue in issues:
            db.add(issue)
        db.flush()

        # サンプル作業ログ
        logs = [
            WorkLog(
                issue_id=issues[0].id,
                content="## 完了内容\n- `requirements.txt` を作成\n- FastAPI の Hello World を確認",
                logged_at=date.today() - timedelta(days=2),
            ),
            WorkLog(
                issue_id=issues[1].id,
                content="## 進捗\n- 3カラムレイアウトを実装\n- SortableJS でD&Dを試験中",
                logged_at=date.today() - timedelta(days=1),
            ),
            WorkLog(
                issue_id=issues[1].id,
                content="## 本日の作業\n- ドロップ時にPATCH APIを呼ぶ実装を追加\n- カード色分けを実装",
                logged_at=date.today(),
            ),
        ]

        for log in logs:
            db.add(log)

        db.commit()
        print("✅ サンプルデータを投入しました")
        print(f"  - イシュー: {len(issues)}件")
        print(f"  - 作業ログ: {len(logs)}件")

    except Exception as e:
        db.rollback()
        print(f"❌ エラー: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

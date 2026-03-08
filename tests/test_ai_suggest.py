"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import pytest
from fastapi.testclient import TestClient


class TestSuggestWorkflow:
    def test_suggest_returns_valid_structure(self, client: TestClient):
        """AI未設定でもフォールバック提案が返ること."""
        r = client.post("/api/ai/suggest-workflow")
        assert r.status_code == 200
        data = r.json()
        assert "suggested_name" in data
        assert "suggested_steps" in data
        assert "reason" in data
        assert "is_ai_generated" in data
        assert isinstance(data["suggested_steps"], list)
        assert len(data["suggested_steps"]) >= 3

    def test_suggest_is_not_ai_without_settings(self, client: TestClient):
        """AI設定なしのとき is_ai_generated が False であること."""
        r = client.post("/api/ai/suggest-workflow")
        assert r.json()["is_ai_generated"] is False

    def test_suggest_with_category(self, client: TestClient):
        """カテゴリ指定でも正常に提案が返ること."""
        r = client.post("/api/ai/suggest-workflow?category=承認")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["suggested_steps"], list)

    def test_suggest_approval_flow_for_approval_category(self, client: TestClient):
        """「承認」カテゴリで承認フローが提案されること."""
        r = client.post("/api/ai/suggest-workflow?category=承認")
        data = r.json()
        # 承認フローのステップが含まれているか
        assert "承認" in data["suggested_steps"] or "審査" in data["suggested_steps"]

    def test_suggest_with_existing_issues(self, client: TestClient):
        """タスクが存在する状態でも正常に動作すること."""
        # タスクを作成
        for i in range(3):
            client.post("/api/issues", json={
                "title": f"テストタスク{i}",
                "category": "開発",
                "status": "done"
            })
        r = client.post("/api/ai/suggest-workflow?category=開発")
        assert r.status_code == 200
        assert len(r.json()["suggested_steps"]) >= 3

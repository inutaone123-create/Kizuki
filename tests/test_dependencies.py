"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import pytest
from fastapi.testclient import TestClient


def create_issue(client: TestClient, title="テストタスク", status="todo"):
    """テスト用イシューを作成するヘルパー."""
    r = client.post("/api/issues", json={"title": title, "status": status})
    assert r.status_code == 201
    return r.json()


class TestDependencies:
    def test_add_dependency(self, client: TestClient):
        """依存関係を追加できる."""
        issue_a = create_issue(client, "タスクA")
        issue_b = create_issue(client, "タスクB")
        r = client.post(f"/api/issues/{issue_b['id']}/dependencies",
                        json={"blocked_by_id": issue_a["id"]})
        assert r.status_code == 201

    def test_get_dependencies(self, client: TestClient):
        """依存関係を取得できる."""
        issue_a = create_issue(client, "タスクA")
        issue_b = create_issue(client, "タスクB")
        client.post(f"/api/issues/{issue_b['id']}/dependencies",
                    json={"blocked_by_id": issue_a["id"]})
        r = client.get(f"/api/issues/{issue_b['id']}/dependencies")
        assert r.status_code == 200
        data = r.json()
        assert len(data["blocked_by"]) == 1
        assert data["blocked_by"][0]["id"] == issue_a["id"]

    def test_is_blocked_in_list(self, client: TestClient):
        """未完了ブロッカーがある場合 is_blocked=True になる."""
        issue_a = create_issue(client, "タスクA", status="todo")
        issue_b = create_issue(client, "タスクB")
        client.post(f"/api/issues/{issue_b['id']}/dependencies",
                    json={"blocked_by_id": issue_a["id"]})
        r = client.get("/api/issues")
        issues = r.json()
        b = next(i for i in issues if i["id"] == issue_b["id"])
        assert b["is_blocked"] is True
        assert issue_a["id"] in b["blocked_by_ids"]

    def test_not_blocked_when_blocker_done(self, client: TestClient):
        """ブロッカーが完了済みの場合 is_blocked=False になる."""
        issue_a = create_issue(client, "タスクA", status="done")
        issue_b = create_issue(client, "タスクB")
        client.post(f"/api/issues/{issue_b['id']}/dependencies",
                    json={"blocked_by_id": issue_a["id"]})
        r = client.get("/api/issues")
        issues = r.json()
        b = next(i for i in issues if i["id"] == issue_b["id"])
        assert b["is_blocked"] is False

    def test_self_dependency_rejected(self, client: TestClient):
        """自己参照の依存関係は400エラーになる."""
        issue_a = create_issue(client, "タスクA")
        r = client.post(f"/api/issues/{issue_a['id']}/dependencies",
                        json={"blocked_by_id": issue_a["id"]})
        assert r.status_code == 400

    def test_circular_dependency_rejected(self, client: TestClient):
        """循環依存は400エラーになる."""
        issue_a = create_issue(client, "タスクA")
        issue_b = create_issue(client, "タスクB")
        client.post(f"/api/issues/{issue_b['id']}/dependencies",
                    json={"blocked_by_id": issue_a["id"]})
        r = client.post(f"/api/issues/{issue_a['id']}/dependencies",
                        json={"blocked_by_id": issue_b["id"]})
        assert r.status_code == 400

    def test_remove_dependency(self, client: TestClient):
        """依存関係を削除できる."""
        issue_a = create_issue(client, "タスクA")
        issue_b = create_issue(client, "タスクB")
        client.post(f"/api/issues/{issue_b['id']}/dependencies",
                    json={"blocked_by_id": issue_a["id"]})
        r = client.delete(f"/api/issues/{issue_b['id']}/dependencies/{issue_a['id']}")
        assert r.status_code == 204
        r2 = client.get(f"/api/issues/{issue_b['id']}/dependencies")
        assert len(r2.json()["blocked_by"]) == 0

    def test_duplicate_dependency_rejected(self, client: TestClient):
        """重複した依存関係は400エラーになる."""
        issue_a = create_issue(client, "タスクA")
        issue_b = create_issue(client, "タスクB")
        client.post(f"/api/issues/{issue_b['id']}/dependencies",
                    json={"blocked_by_id": issue_a["id"]})
        r = client.post(f"/api/issues/{issue_b['id']}/dependencies",
                        json={"blocked_by_id": issue_a["id"]})
        assert r.status_code == 400

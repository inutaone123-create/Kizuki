"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi.testclient import TestClient


def test_create_issue(client: TestClient):
    """イシューを作成できる."""
    resp = client.post("/api/issues", json={"title": "テストイシュー"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "テストイシュー"
    assert data["status"] == "todo"
    assert data["priority"] == "medium"


def test_list_issues(client: TestClient):
    """イシュー一覧を取得できる."""
    client.post("/api/issues", json={"title": "Issue A", "status": "todo"})
    client.post("/api/issues", json={"title": "Issue B", "status": "done"})
    resp = client.get("/api/issues")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_filter_issues_by_status(client: TestClient):
    """ステータスでイシューをフィルタリングできる."""
    client.post("/api/issues", json={"title": "Todo Issue", "status": "todo"})
    client.post("/api/issues", json={"title": "Done Issue", "status": "done"})
    resp = client.get("/api/issues?status=todo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Todo Issue"


def test_get_issue(client: TestClient):
    """イシュー詳細を取得できる."""
    created = client.post(
        "/api/issues",
        json={"title": "詳細テスト", "description": "説明文"},
    ).json()
    resp = client.get(f"/api/issues/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["description"] == "説明文"


def test_get_issue_not_found(client: TestClient):
    """存在しないイシューは404を返す."""
    resp = client.get("/api/issues/9999")
    assert resp.status_code == 404


def test_update_issue(client: TestClient):
    """イシューを更新できる."""
    created = client.post("/api/issues", json={"title": "更新前"}).json()
    resp = client.put(
        f"/api/issues/{created['id']}",
        json={"title": "更新後", "priority": "high"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "更新後"
    assert data["priority"] == "high"


def test_patch_issue_status(client: TestClient):
    """イシューのステータスをPATCHで更新できる."""
    created = client.post("/api/issues", json={"title": "カンバンテスト"}).json()
    resp = client.patch(
        f"/api/issues/{created['id']}/status",
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_delete_issue(client: TestClient):
    """イシューを削除できる."""
    created = client.post("/api/issues", json={"title": "削除テスト"}).json()
    resp = client.delete(f"/api/issues/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/issues/{created['id']}").status_code == 404

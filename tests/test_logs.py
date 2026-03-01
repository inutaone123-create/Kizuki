"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi.testclient import TestClient


def _create_issue(client: TestClient, title: str = "テストイシュー") -> dict:
    """テスト用イシューを作成するヘルパー."""
    return client.post("/api/issues", json={"title": title}).json()


def test_create_log(client: TestClient):
    """作業ログを作成できる."""
    issue = _create_issue(client)
    resp = client.post(
        f"/api/issues/{issue['id']}/logs",
        json={"content": "## 作業内容\n- タスクA完了", "logged_at": "2026-03-01"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "## 作業内容\n- タスクA完了"
    assert data["logged_at"] == "2026-03-01"


def test_list_logs(client: TestClient):
    """イシューに紐づくログ一覧を取得できる."""
    issue = _create_issue(client)
    client.post(
        f"/api/issues/{issue['id']}/logs",
        json={"content": "ログ1", "logged_at": "2026-03-01"},
    )
    client.post(
        f"/api/issues/{issue['id']}/logs",
        json={"content": "ログ2", "logged_at": "2026-03-02"},
    )
    resp = client.get(f"/api/issues/{issue['id']}/logs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_create_log_issue_not_found(client: TestClient):
    """存在しないイシューへのログ追加は404を返す."""
    resp = client.post(
        "/api/issues/9999/logs",
        json={"content": "エラーテスト", "logged_at": "2026-03-01"},
    )
    assert resp.status_code == 404


def test_delete_log(client: TestClient):
    """作業ログを削除できる."""
    issue = _create_issue(client)
    log = client.post(
        f"/api/issues/{issue['id']}/logs",
        json={"content": "削除テスト", "logged_at": "2026-03-01"},
    ).json()
    resp = client.delete(f"/api/logs/{log['id']}")
    assert resp.status_code == 204

    logs = client.get(f"/api/issues/{issue['id']}/logs").json()
    assert len(logs) == 0


def test_delete_log_not_found(client: TestClient):
    """存在しないログの削除は404を返す."""
    resp = client.delete("/api/logs/9999")
    assert resp.status_code == 404


def test_delete_issue_cascades_logs(client: TestClient):
    """イシュー削除時に関連ログも削除される."""
    issue = _create_issue(client)
    client.post(
        f"/api/issues/{issue['id']}/logs",
        json={"content": "カスケードテスト", "logged_at": "2026-03-01"},
    )
    client.delete(f"/api/issues/{issue['id']}")
    # イシュー削除後にログ一覧取得は404
    resp = client.get(f"/api/issues/{issue['id']}/logs")
    assert resp.status_code == 404

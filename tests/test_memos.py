"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import pytest
from fastapi.testclient import TestClient


# ─── ヘルパー ─────────────────────────────────────────────────────────────────


def create_issue(client: TestClient, title: str = "テストイシュー") -> dict:
    """テスト用イシューを作成して返す."""
    res = client.post("/api/issues", json={"title": title})
    assert res.status_code == 201
    return res.json()


# ─── テスト ───────────────────────────────────────────────────────────────────


def test_create_memo_standalone(client: TestClient):
    """タスク未紐付けのメモを単独で作成できる."""
    res = client.post(
        "/api/memos",
        json={"content": "## 独立メモ\n- メモ内容", "logged_at": "2026-03-03"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["content"] == "## 独立メモ\n- メモ内容"
    assert data["logged_at"] == "2026-03-03"
    assert data["issue_id"] is None
    assert data["issue_title"] is None


def test_create_memo_with_issue(client: TestClient):
    """タスクに紐付けてメモを作成できる."""
    issue = create_issue(client, "タスクA")
    res = client.post(
        "/api/memos",
        json={
            "content": "タスクAのメモ",
            "logged_at": "2026-03-03",
            "issue_id": issue["id"],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["issue_id"] == issue["id"]
    assert data["issue_title"] == "タスクA"


def test_create_memo_invalid_issue(client: TestClient):
    """存在しないタスクIDを指定すると 404 が返る."""
    res = client.post(
        "/api/memos",
        json={"content": "メモ", "issue_id": 9999},
    )
    assert res.status_code == 404


def test_list_memos(client: TestClient):
    """メモ一覧を取得できる（logged_at 降順）."""
    client.post("/api/memos", json={"content": "古いメモ", "logged_at": "2026-03-01"})
    client.post("/api/memos", json={"content": "新しいメモ", "logged_at": "2026-03-03"})

    res = client.get("/api/memos")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    # 新しい日付が先頭
    assert data[0]["logged_at"] == "2026-03-03"
    assert data[1]["logged_at"] == "2026-03-01"


def test_update_memo_content(client: TestClient):
    """メモの内容を更新できる."""
    create_res = client.post(
        "/api/memos",
        json={"content": "元の内容", "logged_at": "2026-03-03"},
    )
    memo_id = create_res.json()["id"]

    res = client.put(f"/api/memos/{memo_id}", json={"content": "更新後の内容"})
    assert res.status_code == 200
    assert res.json()["content"] == "更新後の内容"


def test_update_memo_not_found(client: TestClient):
    """存在しないメモを更新しようとすると 404 が返る."""
    res = client.put("/api/memos/9999", json={"content": "内容"})
    assert res.status_code == 404


def test_patch_memo_issue_attach(client: TestClient):
    """PATCH /api/memos/{id}/issue でタスクに紐付けられる."""
    issue = create_issue(client, "紐付けタスク")
    create_res = client.post(
        "/api/memos",
        json={"content": "タスク未紐付けメモ", "logged_at": "2026-03-03"},
    )
    memo_id = create_res.json()["id"]
    assert create_res.json()["issue_id"] is None

    res = client.patch(
        f"/api/memos/{memo_id}/issue", json={"issue_id": issue["id"]}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["issue_id"] == issue["id"]
    assert data["issue_title"] == "紐付けタスク"


def test_patch_memo_issue_detach(client: TestClient):
    """PATCH /api/memos/{id}/issue で issue_id: null を送るとタスク紐付けが解除される."""
    issue = create_issue(client, "解除テストタスク")
    create_res = client.post(
        "/api/memos",
        json={"content": "紐付きメモ", "issue_id": issue["id"]},
    )
    memo_id = create_res.json()["id"]
    assert create_res.json()["issue_id"] == issue["id"]

    res = client.patch(f"/api/memos/{memo_id}/issue", json={"issue_id": None})
    assert res.status_code == 200
    assert res.json()["issue_id"] is None
    assert res.json()["issue_title"] is None


def test_delete_memo(client: TestClient):
    """メモを削除できる."""
    create_res = client.post(
        "/api/memos",
        json={"content": "削除テストメモ"},
    )
    memo_id = create_res.json()["id"]

    res = client.delete(f"/api/memos/{memo_id}")
    assert res.status_code == 204

    # 削除後はリストから消えている
    list_res = client.get("/api/memos")
    assert all(m["id"] != memo_id for m in list_res.json())


def test_delete_memo_not_found(client: TestClient):
    """存在しないメモを削除しようとすると 404 が返る."""
    res = client.delete("/api/memos/9999")
    assert res.status_code == 404


def test_list_memos_filter_by_issue_id(client: TestClient):
    """GET /api/memos?issue_id=N でタスクに紐付いたメモだけ返る."""
    issue_a = create_issue(client, "タスクA")
    issue_b = create_issue(client, "タスクB")
    client.post("/api/memos", json={"content": "Aのメモ", "issue_id": issue_a["id"]})
    client.post("/api/memos", json={"content": "Bのメモ", "issue_id": issue_b["id"]})
    client.post("/api/memos", json={"content": "独立メモ"})

    res = client.get(f"/api/memos?issue_id={issue_a['id']}")
    assert res.status_code == 200
    memos = res.json()
    assert all(m["issue_id"] == issue_a["id"] for m in memos)
    assert any(m["content"] == "Aのメモ" for m in memos)
    assert not any(m["content"] == "Bのメモ" for m in memos)
    assert not any(m["content"] == "独立メモ" for m in memos)


def test_delete_issue_sets_memo_issue_id_null(client: TestClient):
    """タスクを削除すると、紐付きメモの issue_id が null になる."""
    issue = create_issue(client, "削除するタスク")
    create_res = client.post(
        "/api/memos",
        json={"content": "タスク削除テストメモ", "issue_id": issue["id"]},
    )
    memo_id = create_res.json()["id"]
    assert create_res.json()["issue_id"] == issue["id"]

    # タスクを削除
    del_res = client.delete(f"/api/issues/{issue['id']}")
    assert del_res.status_code == 204

    # メモは残っており issue_id が null
    list_res = client.get("/api/memos")
    assert list_res.status_code == 200
    memos = list_res.json()
    found = next((m for m in memos if m["id"] == memo_id), None)
    assert found is not None
    assert found["issue_id"] is None
    assert found["issue_title"] is None

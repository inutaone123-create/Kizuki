"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import pytest
from fastapi.testclient import TestClient


def test_create_workflow(client: TestClient):
    """ワークフローを作成できる."""
    res = client.post("/api/workflows", json={"name": "承認フロー", "steps": ["申請", "承認", "実行", "完了"]})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "承認フロー"
    assert data["steps"] == ["申請", "承認", "実行", "完了"]
    assert "id" in data


def test_list_workflows(client: TestClient):
    """ワークフロー一覧を取得できる."""
    client.post("/api/workflows", json={"name": "フローA", "steps": ["開始", "完了"]})
    client.post("/api/workflows", json={"name": "フローB", "steps": ["作業", "確認", "完了"]})
    res = client.get("/api/workflows")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_update_workflow(client: TestClient):
    """ワークフローを更新できる."""
    created = client.post("/api/workflows", json={"name": "旧フロー", "steps": ["A"]}).json()
    res = client.put(f"/api/workflows/{created['id']}", json={"name": "新フロー", "steps": ["X", "Y"]})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "新フロー"
    assert data["steps"] == ["X", "Y"]


def test_delete_workflow(client: TestClient):
    """ワークフローを削除できる."""
    created = client.post("/api/workflows", json={"name": "削除予定", "steps": ["A", "B"]}).json()
    res = client.delete(f"/api/workflows/{created['id']}")
    assert res.status_code == 204
    assert len(client.get("/api/workflows").json()) == 0


def test_delete_workflow_not_found(client: TestClient):
    """存在しないワークフロー削除は404."""
    res = client.delete("/api/workflows/9999")
    assert res.status_code == 404


def test_issue_workflow_step(client: TestClient):
    """イシューのワークフローステップを更新できる."""
    wf = client.post("/api/workflows", json={"name": "テストフロー", "steps": ["A", "B", "C"]}).json()
    issue = client.post("/api/issues", json={
        "title": "WFテスト",
        "workflow_id": wf["id"],
        "workflow_step": 0,
    }).json()

    # ステップを進める
    res = client.patch(f"/api/issues/{issue['id']}/workflow-step", json={"step": 1})
    assert res.status_code == 200
    assert res.json()["workflow_step"] == 1

    # 範囲外ステップはエラー
    res = client.patch(f"/api/issues/{issue['id']}/workflow-step", json={"step": 5})
    assert res.status_code == 400


def test_issue_with_assignee_and_workflow(client: TestClient):
    """イシューに担当者とワークフローを割り当てられる."""
    member = client.post("/api/members", json={"name": "担当者A", "color": "#abc123"}).json()
    wf = client.post("/api/workflows", json={"name": "フロー", "steps": ["開始", "完了"]}).json()

    issue = client.post("/api/issues", json={
        "title": "総合テスト",
        "assignee_id": member["id"],
        "workflow_id": wf["id"],
        "workflow_step": 0,
    }).json()

    assert issue["assignee_id"] == member["id"]
    assert issue["workflow_id"] == wf["id"]
    assert issue["assignee"]["name"] == "担当者A"
    assert issue["workflow"]["steps"] == ["開始", "完了"]

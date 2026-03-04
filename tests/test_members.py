"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import pytest
from fastapi.testclient import TestClient


def test_create_member(client: TestClient):
    """メンバーを作成できる."""
    res = client.post("/api/members", json={"name": "田中", "color": "#ff0000"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "田中"
    assert data["color"] == "#ff0000"
    assert "id" in data


def test_create_member_default_color(client: TestClient):
    """カラー未指定時はデフォルトカラーが設定される."""
    res = client.post("/api/members", json={"name": "鈴木"})
    assert res.status_code == 201
    assert res.json()["color"] == "#6366f1"


def test_create_member_duplicate_name(client: TestClient):
    """同名メンバーの作成は400エラー."""
    client.post("/api/members", json={"name": "重複太郎"})
    res = client.post("/api/members", json={"name": "重複太郎"})
    assert res.status_code == 400


def test_list_members(client: TestClient):
    """メンバー一覧を取得できる."""
    client.post("/api/members", json={"name": "Aさん"})
    client.post("/api/members", json={"name": "Bさん"})
    res = client.get("/api/members")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_update_member(client: TestClient):
    """メンバーを更新できる."""
    created = client.post("/api/members", json={"name": "更新前", "color": "#111111"}).json()
    res = client.put(f"/api/members/{created['id']}", json={"name": "更新後", "color": "#222222"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "更新後"
    assert data["color"] == "#222222"


def test_delete_member(client: TestClient):
    """メンバーを削除できる."""
    created = client.post("/api/members", json={"name": "削除予定"}).json()
    res = client.delete(f"/api/members/{created['id']}")
    assert res.status_code == 204
    assert len(client.get("/api/members").json()) == 0


def test_delete_member_not_found(client: TestClient):
    """存在しないメンバー削除は404."""
    res = client.delete("/api/members/9999")
    assert res.status_code == 404

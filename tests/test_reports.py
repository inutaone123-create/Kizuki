"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient


# ─── ヘルパー ─────────────────────────────────────────────────────────────────


def create_memo(client: TestClient, content: str, logged_at: str) -> dict:
    """テスト用メモを作成して返す."""
    res = client.post(
        "/api/memos",
        json={"content": content, "logged_at": logged_at},
    )
    assert res.status_code == 201
    return res.json()


def generate_report(client: TestClient, report_type: str, target_date: str) -> dict:
    """レポートを生成して返す."""
    res = client.post(
        "/api/reports/generate",
        json={"report_type": report_type, "target_date": target_date},
    )
    assert res.status_code == 201
    return res.json()


# ─── AI設定テスト ────────────────────────────────────────────────────────────


def test_ai_settings_default(client: TestClient):
    """デフォルト状態では has_api_key=False が返る."""
    res = client.get("/api/settings/ai")
    assert res.status_code == 200
    data = res.json()
    assert data["has_api_key"] is False
    assert data["base_url"] is None
    assert data["model"] is None


def test_ai_settings_save(client: TestClient):
    """AI設定を保存すると has_api_key=True になり、api_key は返らない."""
    res = client.put(
        "/api/settings/ai",
        json={
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": "gsk_test_key",
            "model": "llama3-8b-8192",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_api_key"] is True
    assert data["base_url"] == "https://api.groq.com/openai/v1"
    assert data["model"] == "llama3-8b-8192"
    assert "api_key" not in data


def test_ai_settings_keep_api_key_when_empty(client: TestClient):
    """api_key を省略した更新でもキーが維持される."""
    # まずキーを設定
    client.put(
        "/api/settings/ai",
        json={"api_key": "secret_key"},
    )
    # api_key なしで更新
    res = client.put(
        "/api/settings/ai",
        json={"model": "new-model"},
    )
    assert res.status_code == 200
    assert res.json()["has_api_key"] is True


def test_ai_settings_empty_api_key_keeps_existing(client: TestClient):
    """空文字の api_key は無視して既存キーを維持する."""
    client.put("/api/settings/ai", json={"api_key": "original_key"})
    res = client.put("/api/settings/ai", json={"api_key": ""})
    assert res.status_code == 200
    assert res.json()["has_api_key"] is True


# ─── レポート生成テスト ───────────────────────────────────────────────────────


def test_generate_daily_report(client: TestClient):
    """日報を生成できる（テンプレートモード）."""
    data = generate_report(client, "daily", "2026-03-04")
    assert data["report_type"] == "daily"
    assert data["period_start"] == "2026-03-04"
    assert data["period_end"] == "2026-03-04"
    assert "日報" in data["title"]
    assert data["is_ai_generated"] is False
    assert data["content"]


def test_generate_weekly_report(client: TestClient):
    """週報を生成できる（月曜〜日曜の期間が正しい）."""
    # 2026-03-04 は水曜日 → 月曜:03-02, 日曜:03-08
    data = generate_report(client, "weekly", "2026-03-04")
    assert data["report_type"] == "weekly"
    assert data["period_start"] == "2026-03-02"
    assert data["period_end"] == "2026-03-08"
    assert "週報" in data["title"]


def test_generate_monthly_report(client: TestClient):
    """月報を生成できる（月初〜月末の期間が正しい）."""
    data = generate_report(client, "monthly", "2026-03-15")
    assert data["report_type"] == "monthly"
    assert data["period_start"] == "2026-03-01"
    assert data["period_end"] == "2026-03-31"
    assert "月報" in data["title"]


def test_generate_report_with_memos(client: TestClient):
    """メモがある場合、日報にメモ内容が含まれる."""
    create_memo(client, "テスト作業の内容", "2026-03-04")
    data = generate_report(client, "daily", "2026-03-04")
    assert "テスト作業の内容" in data["content"]


def test_generate_report_invalid_type(client: TestClient):
    """不正な report_type は 422 が返る."""
    res = client.post(
        "/api/reports/generate",
        json={"report_type": "invalid", "target_date": "2026-03-04"},
    )
    assert res.status_code == 422


# ─── レポート CRUD テスト ─────────────────────────────────────────────────────


def test_list_reports_no_content(client: TestClient):
    """レポート一覧は content フィールドを含まない."""
    generate_report(client, "daily", "2026-03-04")
    res = client.get("/api/reports")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert "content" not in data[0]


def test_list_reports_newest_first(client: TestClient):
    """レポート一覧は新しい順に返る."""
    generate_report(client, "daily", "2026-03-04")
    generate_report(client, "daily", "2026-03-05")
    res = client.get("/api/reports")
    data = res.json()
    assert len(data) == 2
    # 新しい順（created_at降順）なので2件目が先頭
    assert data[0]["period_start"] == "2026-03-05"


def test_get_report_detail(client: TestClient):
    """レポート詳細は content を含む."""
    created = generate_report(client, "daily", "2026-03-04")
    res = client.get(f"/api/reports/{created['id']}")
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    assert data["id"] == created["id"]


def test_get_report_not_found(client: TestClient):
    """存在しないレポートは 404 が返る."""
    res = client.get("/api/reports/9999")
    assert res.status_code == 404


def test_delete_report(client: TestClient):
    """レポートを削除できる."""
    created = generate_report(client, "daily", "2026-03-04")
    res = client.delete(f"/api/reports/{created['id']}")
    assert res.status_code == 204

    # 削除後は 404
    res = client.get(f"/api/reports/{created['id']}")
    assert res.status_code == 404


def test_delete_report_not_found(client: TestClient):
    """存在しないレポートの削除は 404 が返る."""
    res = client.delete("/api/reports/9999")
    assert res.status_code == 404


def test_february_monthly_range(client: TestClient):
    """2月の月報は月末が正しく計算される（非うるう年: 28日）."""
    data = generate_report(client, "monthly", "2026-02-15")
    assert data["period_start"] == "2026-02-01"
    assert data["period_end"] == "2026-02-28"

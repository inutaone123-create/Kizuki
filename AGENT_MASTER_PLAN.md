# 🏯 AGENT MASTER PLAN — Kizuki（イシュー管理 × 作業メモ）

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| プロジェクト名 | Kizuki |
| 目的 | イシュー管理と作業メモを一体化した個人用カンバンツール |
| 技術スタック | Python (FastAPI) + SQLite + HTML/CSS/JavaScript |
| 対象ユーザー | 自分一人（将来的に多ユーザー対応へ拡張予定） |

## ゴール

カンバンボード形式でイシューを管理し、各イシューに日付付きの作業メモ（Markdown）を紐づけられるWebアプリを構築する。

---

## フェーズ設計

### Phase 0：環境構築・初期セットアップ

**目標:** プロジェクト構成を整備し、FastAPIが起動できる状態にする

**タスク:**
- [ ] Pythonプロジェクト構成を作成（`src/`, `tests/`, `static/`, `templates/`）
- [ ] `requirements.txt` を作成（fastapi, uvicorn, sqlalchemy, python-multipart, markdown）
- [ ] FastAPIのエントリーポイント（`src/main.py`）を作成
- [ ] `http://localhost:8000` でHello Worldが返ることを確認

**完了条件:** `uvicorn src.main:app --reload` で起動し、ブラウザからアクセスできる

---

### Phase 1：データモデル設計 & DB構築

**目標:** SQLiteのテーブル設計と初期化スクリプトを作成する

**データモデル:**

```
Issue（イシュー）
  - id: INTEGER PRIMARY KEY
  - title: TEXT NOT NULL
  - description: TEXT
  - status: TEXT  -- 'todo' | 'in_progress' | 'done'
  - priority: TEXT  -- 'high' | 'medium' | 'low'
  - category: TEXT
  - tags: TEXT  -- カンマ区切りで保存
  - created_at: DATETIME
  - updated_at: DATETIME

WorkLog（作業メモ）
  - id: INTEGER PRIMARY KEY
  - issue_id: INTEGER (FK -> Issue.id)
  - content: TEXT  -- Markdown形式
  - logged_at: DATE  -- 日付
  - created_at: DATETIME
```

**タスク:**
- [ ] SQLAlchemyでモデル定義（`src/models.py`）
- [ ] DBの初期化処理（`src/database.py`）
- [ ] アプリ起動時にテーブルが自動作成されること確認
- [ ] サンプルデータ投入スクリプト（`scripts/seed.py`）

**完了条件:** DBファイルが生成され、サンプルデータが挿入できる

---

### Phase 2：API実装（CRUD）

**目標:** イシューと作業メモのREST APIを実装する

**APIエンドポイント:**

```
# イシュー
GET    /api/issues              -- 一覧取得（ステータス・優先度・カテゴリでフィルタ可）
POST   /api/issues              -- 新規作成
GET    /api/issues/{id}         -- 詳細取得
PUT    /api/issues/{id}         -- 更新
DELETE /api/issues/{id}         -- 削除
PATCH  /api/issues/{id}/status  -- ステータスのみ更新（カンバン用）

# 作業メモ
GET    /api/issues/{id}/logs    -- イシューに紐づくメモ一覧
POST   /api/issues/{id}/logs    -- メモ追加
DELETE /api/logs/{log_id}       -- メモ削除
```

**タスク:**
- [ ] Pydanticスキーマ定義（`src/schemas.py`）
- [ ] イシューCRUDルーター（`src/routers/issues.py`）
- [ ] 作業メモCRUDルーター（`src/routers/logs.py`）
- [ ] 全エンドポイントをcurlまたはpytestで動作確認

**完了条件:** 全APIが正常レスポンスを返す（pytestで確認）

---

### Phase 3：フロントエンド実装（カンバンUI）

**目標:** ブラウザで使えるカンバンボードUIを作成する

**画面構成:**

```
┌─────────────────────────────────────────────────┐
│ IssueLog                          [+ 新規イシュー] │
│ フィルター: [優先度▼] [カテゴリ▼]                  │
├──────────────┬──────────────┬───────────────────┤
│   未着手      │   進行中      │      完了          │
│ ┌──────────┐ │ ┌──────────┐ │  ┌──────────┐    │
│ │ イシュー  │ │ │ イシュー  │ │  │ イシュー  │    │
│ │ 🔴 高    │ │ │ 🟡 中    │ │  │ 🟢 低    │    │
│ │ タグ表示  │ │ │ タグ表示  │ │  │ タグ表示  │    │
│ └──────────┘ │ └──────────┘ │  └──────────┘    │
└──────────────┴──────────────┴───────────────────┘
```

**機能:**
- カンバン3列（未着手 / 進行中 / 完了）
- イシューカードのドラッグ＆ドロップでステータス変更
- 優先度をカラー表示（🔴高 / 🟡中 / 🟢低）
- タグ表示
- カードクリックで詳細モーダルを開く

**タスク:**
- [ ] `static/index.html` にカンバンボードUIを実装
- [ ] `static/style.css` でスタイリング
- [ ] `static/app.js` でAPIとの通信・ドラッグ＆ドロップ実装
- [ ] 新規イシュー作成フォーム（モーダル）
- [ ] イシュー編集・削除機能

**完了条件:** ブラウザでカンバンボードが表示され、ドラッグ＆ドロップが動く

---

### Phase 4：作業メモ機能の実装

**目標:** イシュー詳細画面で作業メモの投稿・閲覧ができる

**機能:**
- イシュー詳細モーダル内に作業ログセクション
- Markdownエディタ（`marked.js`を使用してプレビュー表示）
- 日付付きメモを時系列で表示（新しい順）
- メモの追加・削除

**タスク:**
- [ ] 詳細モーダルにWorkLogセクションを追加
- [ ] `marked.js`（CDN）でMarkdownをHTMLにレンダリング
- [ ] メモ投稿フォーム（テキストエリア + 日付 + 送信ボタン）
- [ ] メモ一覧の時系列表示
- [ ] メモ削除機能

**完了条件:** イシュー詳細でMarkdownメモを投稿・閲覧・削除できる

---

### Phase 5：品質向上・仕上げ

**目標:** テスト・ドキュメント・使いやすさの改善

**タスク:**
- [ ] pytestでAPIの主要ルートをテスト（`tests/test_issues.py`, `tests/test_logs.py`）
- [ ] 起動手順を `README.md` に記述
- [ ] フィルター機能の動作確認（優先度・カテゴリ）
- [ ] エラーハンドリング（存在しないIDへのアクセスなど）
- [ ] `/project:review-code` でコードレビュー実施
- [ ] `/project:qiita` を実行して `docs/qiita_draft.md` を生成

**完了条件:** `pytest` がすべてPASS、READMEの手順で誰でも起動できる

---

## 制約・ルール

- `Dockerfile`, `docker-compose.yml`, `.devcontainer/` は変更しない
- `CLAUDE.md` のルールに従って作業する
- フロントエンドは外部CDN（marked.js, SortableJS）のみ使用可、npmビルド不要
- DBはSQLiteファイル1つ（`data/issuelog.db`）に集約
- APIのレスポンスはすべてJSON形式

## 将来の拡張メモ（Phase 1では実装しない）

- ユーザー認証・マルチユーザー対応
- スケジュール・期日カレンダー表示
- プロセス・ワークフロー管理
- PostgreSQL移行
- Reactフロントエンドへの移行

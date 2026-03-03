# 完了報告書

**プロジェクト**: Kizuki — イシュー管理 × 作業メモ
**作成日**: 2026-03-01
**ブランチ**: main

---

## 実装概要

Kizukiは、カンバンボード形式でイシューを管理し、各イシューに日付付きの作業メモ（Markdown）を紐づけられる個人用Webアプリです。Python（FastAPI）+ SQLite + HTML/CSS/JavaScript のシンプルな構成で、npmビルド不要・外部CDNのみを使用したフロントエンドにより、すぐに起動できる軽量な実装となっています。

バックエンドはFastAPIによるREST API（イシューCRUD + 作業ログCRUD）、フロントエンドはSortableJSによるドラッグ＆ドロップカンバン + marked.jsによるMarkdownレンダリングを実装しました。SQLAlchemyでIssue・WorkLogのORMモデルを定義し、起動時にDBを自動初期化します。

---

## 実装フェーズと成果

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 0 | 環境構築・FastAPIエントリーポイント・requirements.txt | ✅ |
| Phase 1 | SQLAlchemyモデル（Issue, WorkLog）・DB初期化・seedスクリプト | ✅ |
| Phase 2 | イシュー・作業ログのCRUD API・Pydanticスキーマ・pytestテスト | ✅ |
| Phase 3 | カンバンボードUI（SortableJS D&D・優先度カラー・フィルター） | ✅ |
| Phase 4 | 作業ログ機能（marked.js Markdownレンダリング・時系列表示・削除） | ✅ |
| Phase 5 | README整備・.gitignore更新・完了報告書生成 | ✅ |

---

## テスト結果

```
..............                                                           [100%]
14 passed in 0.57s
```

### テスト内訳

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `tests/test_issues.py` | 8件 | イシューCRUD・フィルター・ステータス更新 |
| `tests/test_logs.py` | 6件 | 作業ログCRUD・カスケード削除 |

---

## ファイル構成

```
kizuki/
├── src/
│   ├── __init__.py          # パッケージ初期化
│   ├── main.py              # FastAPIエントリーポイント（lifespan・ルーター登録）
│   ├── database.py          # SQLite DB設定・セッション管理・初期化
│   ├── models.py            # SQLAlchemyモデル（Issue, WorkLog）
│   ├── schemas.py           # Pydanticスキーマ（Create/Update/Response）
│   └── routers/
│       ├── __init__.py
│       ├── issues.py        # イシューCRUDルーター（6エンドポイント）
│       └── logs.py          # 作業ログCRUDルーター（3エンドポイント）
├── static/
│   ├── index.html           # カンバンボードUI
│   ├── style.css            # スタイリング（CSS変数・レスポンシブ対応）
│   └── app.js               # フロントエンドロジック（API通信・D&D・Markdown）
├── tests/
│   ├── conftest.py          # テスト設定（StaticPool インメモリDB）
│   ├── test_issues.py       # イシューAPIテスト（8件）
│   └── test_logs.py         # 作業ログAPIテスト（6件）
├── scripts/
│   └── seed.py              # サンプルデータ投入スクリプト
├── data/                    # SQLiteファイル置き場（data/issuelog.db）
├── requirements.txt         # Python依存パッケージ
├── README.md                # 起動手順・API仕様
└── AGENT_MASTER_PLAN.md     # プロジェクト設計書
```

---

## APIエンドポイント一覧

### イシュー

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues` | 一覧取得（status/priority/categoryフィルター対応） |
| POST | `/api/issues` | 新規作成 |
| GET | `/api/issues/{id}` | 詳細取得（作業ログ含む） |
| PUT | `/api/issues/{id}` | 全フィールド更新 |
| DELETE | `/api/issues/{id}` | 削除（関連ログもカスケード削除） |
| PATCH | `/api/issues/{id}/status` | ステータスのみ更新（カンバン用） |

### 作業ログ

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues/{id}/logs` | ログ一覧（新しい順） |
| POST | `/api/issues/{id}/logs` | ログ追加 |
| DELETE | `/api/logs/{log_id}` | ログ削除 |

---

## 起動手順

```bash
# 依存関係のインストール
pip3 install -r requirements.txt

# サンプルデータ投入（任意）
python3 scripts/seed.py

# サーバー起動
uvicorn src.main:app --reload

# ブラウザで確認
open http://localhost:8000
```

---

## ライセンス

MIT License

全ソースファイルにライセンスヘッダー（Pythonは`"""`形式）を付与済み。

---

## 技術的知見・ハマりどころ

### Python / pytest

- SQLite インメモリDB（`sqlite:///:memory:`）をテスト用に使う場合、`StaticPool` を指定しないと接続ごとに別DBとなりテーブルが見えなくなる
  - 解決策: `create_engine(..., poolclass=StaticPool)` を使用
- `@app.on_event("startup")` は非推奨。`@asynccontextmanager` + `lifespan` 引数を使うべき

---

---

## 追加実装: 独立メモ画面 + タスク紐付け機能（2026-03-03）

### 概要

WorkLog モデルの `issue_id` を nullable 化し、タスクに依存しない独立メモとして機能拡張。
「メモを先に書いて後からタスクに紐付ける」ワークフローを実現した。

### 変更内容

| ファイル | 変更内容 |
|---------|---------|
| `src/database.py` | `PRAGMA foreign_keys=ON` を有効化（ON DELETE SET NULL サポート） |
| `src/models.py` | WorkLog.issue_id を nullable=True + ondelete=SET NULL に変更 |
| `src/schemas.py` | MemoCreate / MemoUpdate / MemoIssueUpdate / MemoResponse 追加 |
| `src/routers/memos.py` | 新規メモルーター（5エンドポイント）作成 |
| `src/main.py` | memos ルーターを登録 |
| `static/index.html` | タブ切り替えUI・メモ画面・メモモーダル追加 |
| `static/app.js` | タブ・メモ画面ロジック追加 |
| `static/style.css` | タブバー・メモ画面スタイル追加 |
| `scripts/migrate_memo.py` | SQLite マイグレーションスクリプト追加 |
| `tests/conftest.py` | テスト用エンジンにも PRAGMA foreign_keys=ON 追加 |
| `tests/test_memos.py` | メモAPIテスト 11ケース追加 |

### 追加 API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/memos` | 全メモ一覧（logged_at 降順） |
| POST | `/api/memos` | 新規メモ作成（issue_id 任意） |
| PUT | `/api/memos/{id}` | メモ更新（内容・日付・紐付け変更） |
| DELETE | `/api/memos/{id}` | メモ削除 |
| PATCH | `/api/memos/{id}/issue` | タスク紐付けのみ変更（null で解除） |

### テスト結果

```
25 passed in 0.59s
```

### 技術的知見

- SQLite の `ON DELETE SET NULL` は `PRAGMA foreign_keys=ON` が必要
  - アプリケーション側: `@event.listens_for(engine, "connect")` で設定
  - テスト側: test_engine にも同じイベントリスナーを追加
- `cascade="all, delete-orphan"` は SQLAlchemy ORM レベルで動作するが、
  DB レベルの `ON DELETE SET NULL` には PRAGMA 設定が必須

---

## コミット履歴

```
7d998f4 feat: 独立メモ画面とタスク紐付け機能を追加
2e195ac style: black による自動整形を適用
420c920 docs: Sphinx APIドキュメントを生成（Python）
4644bd8 docs: ドキュメント生成を使用言語のみに限定
37729c5 docs: Qiita記事ドラフト追加・Qiita生成を必須化
```

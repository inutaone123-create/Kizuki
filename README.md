# 🏯 Kizuki — イシュー管理 × 作業メモ

カンバンボード形式でイシューを管理し、各イシューに日付付きの作業メモ（Markdown）を紐づけられる個人用Webアプリです。タスクに紐付けない独立メモを書いて、後からタスクと関連付けることもできます。

## 特徴

- **カンバンボード**: 未着手 / 進行中 / 完了の3列構成
- **ドラッグ＆ドロップ**: カードを列間で移動してステータスを更新
- **優先度カラー**: 🔴高 / 🟡中 / 🟢低 をカードの縁色で表示
- **作業ログ**: Markdown形式のメモをイシューに日付付きで記録
- **独立メモ**: タスク未紐付けのメモを先に書いて、後からタスクに関連付け可能
- **フィルター**: ステータス・優先度・カテゴリで絞り込み

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| バックエンド | Python 3 + FastAPI + SQLAlchemy |
| データベース | SQLite (`data/issuelog.db`) |
| フロントエンド | HTML / CSS / Vanilla JS |
| 外部ライブラリ | SortableJS (D&D) + marked.js (Markdown) |

## 起動手順

### 前提

- Python 3.10 以上
- Dev Container（推奨）または仮想環境

### Dev Container で起動（推奨）

```bash
# VSCodeでフォルダを開く
code .
# F1 → "Dev Containers: Reopen in Container"
```

### ローカルで起動

```bash
# 依存関係のインストール
pip3 install -r requirements.txt

# DBマイグレーション（既存DBがある場合）
python3 scripts/migrate_memo.py

# サンプルデータの投入（任意）
python3 scripts/seed.py

# サーバー起動
uvicorn src.main:app --reload
```

ブラウザで http://localhost:8000 を開く。

## VSCode で使う

### サーバーの自動起動（tasks.json）

`.vscode/tasks.json` が同梱されているため、VSCode でフォルダを開くと自動的にサーバー起動タスクが実行されます。

初回のみ、右下に表示されるポップアップで **「Allow」（許可）** をクリックしてください。

手動で起動したい場合は：

1. `Ctrl+Shift+P` でコマンドパレットを開く
2. `Tasks: Run Task` と入力
3. `Start Server` を選択

ターミナルに `Application startup complete.` と表示されれば起動完了です。

### Simple Browser でアプリを開く

外部ブラウザを使わず、VSCode のパネル内でアプリを表示できます。

1. サーバー起動後、`Ctrl+Shift+P` でコマンドパレットを開く
2. `Simple Browser: Show` と入力・選択
3. URL に `http://localhost:8000` を入力して Enter

エディタのタブにカンバン画面が表示されます。

## API ドキュメント

起動後、以下のURLでSwagger UIを確認できます：

- http://localhost:8000/docs
- http://localhost:8000/redoc

## APIエンドポイント

### イシュー

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues` | 一覧取得（フィルター対応） |
| POST | `/api/issues` | 新規作成 |
| GET | `/api/issues/{id}` | 詳細取得（ログ含む） |
| PUT | `/api/issues/{id}` | 更新 |
| DELETE | `/api/issues/{id}` | 削除 |
| PATCH | `/api/issues/{id}/status` | ステータスのみ更新 |

### 作業ログ（イシュー紐付き）

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues/{id}/logs` | ログ一覧（新しい順） |
| POST | `/api/issues/{id}/logs` | ログ追加 |
| DELETE | `/api/logs/{log_id}` | ログ削除 |

### メモ（独立メモ）

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/memos` | 全メモ一覧（日付降順） |
| POST | `/api/memos` | 新規メモ（タスク紐付けは任意） |
| PUT | `/api/memos/{id}` | メモ更新 |
| DELETE | `/api/memos/{id}` | メモ削除 |
| PATCH | `/api/memos/{id}/issue` | タスク紐付け変更（null で解除） |

## テストの実行

```bash
python3 -m pytest tests/ -v
```

## ファイル構成

```
kizuki/
├── src/
│   ├── main.py          # FastAPIエントリーポイント
│   ├── database.py      # DB設定・初期化
│   ├── models.py        # SQLAlchemyモデル（Issue, WorkLog）
│   ├── schemas.py       # Pydanticスキーマ
│   └── routers/
│       ├── issues.py    # イシューCRUDルーター
│       ├── logs.py      # 作業ログCRUDルーター
│       └── memos.py     # 独立メモCRUDルーター
├── static/
│   ├── index.html       # カンバン・メモUI
│   ├── style.css        # スタイル
│   └── app.js           # フロントエンドロジック
├── tests/
│   ├── conftest.py      # テスト設定（インメモリDB）
│   ├── test_issues.py   # イシューAPIテスト
│   ├── test_logs.py     # 作業ログAPIテスト
│   └── test_memos.py    # 独立メモAPIテスト
├── scripts/
│   ├── seed.py          # サンプルデータ投入
│   └── migrate_memo.py  # DBマイグレーション（issue_id nullable化）
├── data/                # SQLiteファイル置き場
└── requirements.txt
```

## ライセンス

MIT License

# 🏯 Kizuki — イシュー管理 × 作業メモ

カンバンボード形式でイシューを管理し、各イシューに日付付きの作業メモ（Markdown）を紐づけられる個人用Webアプリです。タスクに紐付けない独立メモを書いて、後からタスクと関連付けることもできます。

## 特徴

- **カンバンボード**: 未着手 / 進行中 / 完了の3列構成
- **ドラッグ＆ドロップ**: カードを列間で移動してステータスを更新
- **優先度カラー**: 🔴高 / 🟡中 / 🟢低 をカードの縁色で表示
- **作業ログ**: Markdown形式のメモをイシューに日付付きで記録
- **独立メモ**: タスク未紐付けのメモを先に書いて、後からタスクに関連付け可能
- **フィルター**: ステータス・優先度・カテゴリで絞り込み
- **担当者アサイン**: メンバーを登録してイシューに担当者を設定（認証なし・名前ベース）
- **カスタムワークフロー**: 任意のステップ（例: 申請→承認→実行→完了）を定義してイシューに適用
- **ワークフロー横断ビュー**: 🔄 タブでワークフロー × ステップのカンバンを一覧表示
- **レポート生成**: 📊 タブで日報・週報・月報を自動生成（AI連携 or テンプレートフォールバック）
- **デスクトップアプリ化**: Electron + PyInstaller で Docker 不要のスタンドアロン配布が可能

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| バックエンド | Python 3 + FastAPI + SQLAlchemy |
| データベース | SQLite (`data/issuelog.db`) |
| フロントエンド | HTML / CSS / Vanilla JS |
| 外部ライブラリ | SortableJS (D&D) + marked.js (Markdown)（vendored） |
| デスクトップ | Electron 28 + electron-builder |
| バイナリ化 | PyInstaller（Python/FastAPI を `.exe` に同梱） |

## 起動手順

### デスクトップアプリ版（Electron）

Python や Docker 不要で、インストーラーを実行するだけで起動できます。

```bash
# 1. Python バイナリを生成（Windows 上で実行）
pip install pyinstaller
pyinstaller kizuki.spec --clean
# → dist/kizuki-server/ が生成される

# 2. Electron インストーラーを生成
npm install
npm run build:win
# → build/electron-dist/Kizuki Setup 1.0.0.exe が生成される
```

#### 開発時の動作確認

```bash
# Python サーバーを単体起動
python server_entry.py

# 別ターミナルで Electron を起動
npm start
```

### Web アプリ版（Docker / Python 直接）

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
python3 scripts/migrate_workflow_member.py
python3 scripts/migrate_reports.py

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

## AI設定（レポート生成機能）

📊 レポートタブでAI生成を使う場合は、⚙ 設定タブ → 🤖 AI設定 から接続情報を入力してください。
Groq / Ollama / LM Studio / OpenRouter など OpenAI互換APIであれば利用できます。

詳細は [docs/ai_setup.md](docs/ai_setup.md) を参照してください。

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
| PATCH | `/api/issues/{id}/workflow-step` | ワークフローステップ更新 |

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

### メンバー

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/members` | メンバー一覧 |
| POST | `/api/members` | メンバー追加 |
| PUT | `/api/members/{id}` | メンバー更新 |
| DELETE | `/api/members/{id}` | メンバー削除 |

### ワークフロー

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/workflows` | ワークフロー一覧 |
| POST | `/api/workflows` | ワークフロー作成 |
| PUT | `/api/workflows/{id}` | ワークフロー更新 |
| DELETE | `/api/workflows/{id}` | ワークフロー削除 |

### レポート

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/reports` | レポート一覧（content なし） |
| POST | `/api/reports/generate` | レポート生成（日報/週報/月報） |
| GET | `/api/reports/{id}` | レポート詳細（content あり） |
| DELETE | `/api/reports/{id}` | レポート削除 |

### AI設定

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/settings/ai` | AI設定取得（api_key は返さない） |
| PUT | `/api/settings/ai` | AI設定保存（upsert） |

## テストの実行

```bash
python3 -m pytest tests/ -v
```

## ファイル構成

```
kizuki/
├── electron/
│   └── main.js          # Electron メインプロセス（サーバー管理・ウィンドウ作成）
├── src/
│   ├── main.py          # FastAPIエントリーポイント（_MEIPASS 対応）
│   ├── database.py      # DB設定・初期化（KIZUKI_DB_PATH 環境変数対応）
│   ├── models.py        # SQLAlchemyモデル
│   ├── schemas.py       # Pydanticスキーマ
│   ├── routers/
│   │   ├── issues.py    # イシューCRUD
│   │   ├── logs.py      # 作業ログCRUD
│   │   ├── memos.py     # 独立メモCRUD
│   │   ├── members.py   # メンバーCRUD
│   │   ├── workflows.py # ワークフローCRUD
│   │   ├── reports.py   # レポートCRUD + 生成
│   │   └── settings.py  # AI設定
│   └── services/
│       └── ai_service.py  # AI API クライアント + レポート生成ロジック
├── static/
│   ├── index.html       # UI（カンバン・メモ・ワークフロー・レポート）
│   ├── style.css        # スタイル
│   ├── app.js           # フロントエンドロジック
│   └── vendor/
│       ├── Sortable.min.js  # SortableJS（オフライン用ベンダー化）
│       └── marked.min.js    # marked.js（オフライン用ベンダー化）
├── tests/
│   ├── conftest.py           # テスト設定（インメモリDB）
│   ├── test_issues.py        # イシューAPIテスト
│   ├── test_logs.py          # 作業ログAPIテスト
│   ├── test_memos.py         # 独立メモAPIテスト
│   ├── test_members.py       # メンバーAPIテスト
│   ├── test_workflows.py     # ワークフローAPIテスト
│   └── test_reports.py       # レポート・AI設定APIテスト
├── scripts/
│   ├── seed.py                    # サンプルデータ投入
│   ├── migrate_memo.py            # マイグレーション（issue_id nullable化）
│   ├── migrate_workflow_member.py # マイグレーション（メンバー・ワークフロー）
│   └── migrate_reports.py         # マイグレーション（AI設定・レポート）
├── docs/
│   └── ai_setup.md    # AI設定ガイド（Groq/Ollama/OpenRouter etc.）
├── assets/
│   └── icon.ico       # アプリアイコン（Electron 用）
├── server_entry.py    # PyInstaller 用エントリーポイント
├── kizuki.spec        # PyInstaller ビルド設定
├── package.json       # Electron + electron-builder 設定
├── data/              # SQLiteファイル置き場
└── requirements.txt
```

## ライセンス

MIT License

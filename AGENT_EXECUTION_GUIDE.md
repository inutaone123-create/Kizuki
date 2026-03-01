# AGENT EXECUTION GUIDE
# Dev Container環境でのClaude Code実行手順

---

## 🎬 使い方（毎回同じ手順）

### ステップ1: 初期設定ファイルを確認

このテンプレートには以下が含まれています：

- `Dockerfile` — 開発環境（Python/Octave/C++/C#/Rust + Claude Code）
- `docker-compose.yml` — サービス定義
- `.devcontainer/devcontainer.json` — Dev Container設定

**プロジェクト開始前に `{{...}}` のプレースホルダーを埋めてください：**
- `.devcontainer/devcontainer.json` の `"name"` フィールド
- `CLAUDE.md` の Git設定・リモートURL・技術的知見
- `AGENT_MASTER_PLAN.md` の目標・フェーズ・制約条件

> 💡 Dev Container 起動後に `/project:init` を実行すると、対話形式で一括置換できます。

### ステップ2: Dev Containerで開く

```bash
# VSCodeでフォルダを開く
code .

# F1 → "Dev Containers: Reopen in Container"
# （初回はDockerイメージのビルドに数分かかります）
```

### ステップ3: Dev Container内でClaude Codeを実行

```bash
# VSCode内蔵ターミナル（既にコンテナ内）
claude
```

**Claude Codeへのプロンプト（コピー&ペースト）**:

```
Dev Container内で作業中です。

AGENT_MASTER_PLAN.md を読んで、Phase 0 から順番に実行してください。

Dockerfile、docker-compose.yml、.devcontainer/ は既に存在するので、
それらは変更せず、他のファイルを作成・編集してください。

CLAUDE.md のルールに従って作業してください。
```

---

## 🤖 モデル使い分け（サブエージェント）

このテンプレートには `.claude/agents/` に3つのサブエージェントが定義されています。
タスクの重さに応じて Claude が自動的に適切なモデルに委譲します。

| エージェント | モデル | 使いどころ |
|-------------|--------|-----------|
| `explorer` | Haiku | ファイル検索・コード確認・構造把握 |
| `implementer` | Sonnet | 通常の実装・テスト修正・バグ修正 |
| `architect` | Opus | 設計・計画・複雑な技術的意思決定 |

メインの会話は `sonnet`（`.claude/settings.json` で設定）で動き、
重い作業・軽い作業はサブエージェントに自動委譲されます。

### カスタマイズ方法

各エージェントの定義は `.claude/agents/` のファイルを直接編集します：

```markdown
---
name: explorer
model: haiku       ← ここでモデルを変更
tools: Read, Grep, Glob, Bash
---
説明文...
```

使用できるモデル名: `haiku` / `sonnet` / `opus`

メインの会話モデルは `.claude/settings.json` で変更します：

```json
{ "model": "sonnet" }
```

---

## 🐳 Dockerファイル詳細

### Dockerfile に含まれるツール

| カテゴリ | ツール | 用途 |
|----------|--------|------|
| 言語 | Python 3, pip | スクリプト・テスト |
| 言語 | Octave + signal pkg | 数値計算 |
| 言語 | C++ (g++, cmake) | 高速実装 |
| 言語 | .NET SDK 8.0 | C# 実装 |
| 言語 | Rust (rustup stable) | 安全性重視実装 |
| AI | Claude Code (npm) | エージェント実行 |
| テスト | pytest, behave | Python テスト・BDD |
| 品質 | black | コードフォーマット |
| ドキュメント | doxygen, graphviz | C++/C# APIドキュメント生成 |
| ドキュメント | sphinx, breathe | Python APIドキュメント生成 |
| ドキュメント | cargo doc | Rust APIドキュメント生成 |

### 言語を追加・削除したい場合

`Dockerfile` の該当 `RUN apt-get install` / `RUN pip3 install` 行を編集し、
`docker-compose.yml` の `build` 後にコンテナを再ビルドしてください：

```bash
docker-compose build
# F1 → "Dev Containers: Rebuild Container"
```

---

## 🛠️ スラッシュコマンド一覧

Dev Container 内で `claude` を起動後、以下のコマンドが使用できます。

### プロジェクト管理コマンド（`/project:*`）

| コマンド | タイミング | 内容 |
|---------|-----------|------|
| `/project:init` | プロジェクト開始時（1回） | `{{...}}` を対話形式で一括置換、git / remote 設定 |
| `/project:status` | いつでも | フェーズ進捗・未置換プレースホルダー・テスト状態を表示 |
| `/project:license-check` | 実装中・完了前 | ライセンスヘッダー欠けファイルを検出、自動追加を提案 |
| `/project:review-code` | 実装完了後 | 静的解析＋定性レビュー（命名・構造・コメント） |
| `/project:review-spec` | BDD作成後・完了前 | BDD仕様 ↔ API仕様のカバレッジ照合、未カバーのシナリオを提案 |
| `/project:bdd` | BDD確認時 | `behave` を実行してシナリオ単位で PASS/FAIL を表示 |
| `/project:docs` | 実装完了後 | Doxygen / Sphinx / cargo doc を一括実行してAPIドキュメントを生成 |
| `/project:report` | フェーズ完了時 | `docs/COMPLETION_REPORT.md` を現状から自動生成 |
| `/project:qiita` | 最終化時（任意） | `docs/qiita_draft.md` にQiita投稿用記事ドラフトを生成 |

### 典型的な使用順序

```
/project:init          # 1. プロジェクト初期化
  ↓ 実装フェーズ ...
/project:status        # 2. 進捗確認（随時）
/project:license-check # 3. ヘッダー漏れ確認（随時）
/project:review-spec   # 4. BDD仕様カバレッジ確認
/project:review-code   # 5. コードレビュー
/project:bdd           # 6. BDDテスト実行
/project:docs          # 7. APIドキュメント生成
/project:report        # 8. 完了報告書生成
/project:qiita         # 9. Qiita記事ドラフト生成（任意）
```

---

## 📁 テンプレートのプレースホルダー一覧

プロジェクト開始時に以下を置換してください：

| プレースホルダー | 説明 | 例 |
|-----------------|------|----|
| `{{PROJECT_NAME}}` | リポジトリ名 | `my-awesome-project` |
| `{{PROJECT_TITLE}}` | プロジェクト表示名 | `My Awesome Project` |
| `{{GIT_USER_NAME}}` | Gitユーザー名 | `YourName` |
| `{{GIT_USER_EMAIL}}` | Gitメールアドレス | `you@example.com` |
| `{{GITHUB_REMOTE}}` | GitHubリモートURL | `https://github.com/user/repo` |
| `{{LICENSE}}` | ライセンス名 | `MIT`, `CC BY 4.0`, `Apache 2.0` |
| `{{YEAR}}` | 実装年 | `2025` |
| `{{LICENSE_ATTRIBUTION}}` | 帰属表示（元ソースがある場合） | `Based on XXX by YYY` |
| `{{DELIVERABLE_N}}` | 最終成果物 | `Python実装`, `クロス検証` |
| `{{IMPL_PHASE_N}}` | 実装フェーズ名 | `Python実装（リファレンス）` |
| `{{CONSTRAINT_N}}` | 制約条件 | `FFT正規化: Forward=なし, Inverse=1/N` |
| `{{VALIDATION_CRITERIA}}` | 検証合格基準 | `全ペア 相対誤差 < 1e-10` |
| `{{LANG_N}}` | 言語名（技術的知見） | `Python`, `C++` |

---

## ✅ プロジェクト開始チェックリスト

- [ ] このテンプレートリポジトリから新しいリポジトリを作成した
- [ ] `AGENT_MASTER_PLAN.md` のフェーズ設計・成果物・制約条件を記入した
- [ ] Dev Container でビルドが成功した（初回は数分かかる）
- [ ] `claude` コマンドが起動できることを確認した
- [ ] `/project:init` を実行して `{{...}}` プレースホルダーを一括置換した
- [ ] `/project:status` で未置換プレースホルダーがないことを確認した
- [ ] `.claude/agents/` のモデル設定を確認・調整した
- [ ] Claude Code にプロンプトを渡して実行開始した

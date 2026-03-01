# 🏯 Claude Code × Dev Container 御陣テンプレート

Claude Code の諸将を召喚し、Dev Container の御城内にてプロジェクトをゼロより自律執行するためのテンプレートにございます。

## この御陣にてできること

- Dev Container の御城（Python / Octave / C++ / C# / Rust）をすぐさま築城
- `AGENT_MASTER_PLAN.md` に作戦を記すだけで、Claude Code が自律出陣
- BDDテスト・クロス検証・ドキュメント作成まで、一貫した戦略にて進軍

## 出陣の儀（使い方）

### 其の一：新たな御城を築く

GitHubの「Use this template」ボタンを押し、新たなリポジトリを開城すること。

### 其の二：軍略書のプレースホルダーを埋める

`AGENT_MASTER_PLAN.md` の目標・フェーズ設計・制約条件を記入すること。
`{{...}}` の一括置換は、Dev Container 起動後に `/project:init` を唱えれば自動で執り行われ申す。

詳細は `AGENT_EXECUTION_GUIDE.md` のプレースホルダー一覧を参照されたし。

### 其の三：Dev Container の御城を開く

```bash
code .
# F1 → "Dev Containers: Reopen in Container"
# （初陣は御城の築城に数分かかり申す）
```

### 其の四：Claude Code に出陣を命ずる

```bash
claude
```

出陣の号令（コピー&ペーストされたし）：
```
AGENT_MASTER_PLAN.md を読んで、Phase 0 から順番に実行してください。
Dockerfile、docker-compose.yml、.devcontainer/ は変更せず、
CLAUDE.md のルールに従って作業してください。
```

## 御城の見取り図（ファイル構成）

```
.
├── Dockerfile                  # 御城の設計図（5言語 + Claude Code）
├── docker-compose.yml          # 部隊編成
├── .devcontainer/
│   └── devcontainer.json       # 御城設定
├── CLAUDE.md                   # 軍律（作業ルール・ワークフロー）
├── AGENT_MASTER_PLAN.md        # 作戦書（Claude Code への指示書）
├── AGENT_EXECUTION_GUIDE.md    # 出陣手順・スラッシュコマンド一覧
├── docs/
│   ├── Doxyfile.template       # Doxygen設定ひな型
│   └── qiita_template.md       # Qiita記事ひな型
├── .claude/
│   ├── settings.json           # 兵力設定（デフォルトモデル）
│   ├── agents/
│   │   ├── explorer.md         # 🔍 斥候部隊（Haiku）
│   │   ├── implementer.md      # ⚙️ 実装部隊（Sonnet）
│   │   └── architect.md        # 🏛️ 軍師（Opus）
│   └── commands/project/
│       ├── init.md             # /project:init
│       ├── status.md           # /project:status
│       ├── license-check.md    # /project:license-check
│       ├── review-code.md      # /project:review-code
│       ├── review-spec.md      # /project:review-spec
│       ├── bdd.md              # /project:bdd
│       ├── docs.md             # /project:docs
│       ├── report.md           # /project:report
│       └── qiita.md            # /project:qiita
└── .gitignore
```

## 召喚される諸将

作業の重さに応じて、Claude が自動的に適切な将を召喚いたします：

| 将 | モデル | 得意な戦 |
|----|--------|---------|
| 🔍 explorer（斥候） | Haiku | ファイル探索・構造把握・軽い調査 |
| ⚙️ implementer（実装） | Sonnet | 通常の実装・テスト修正・バグ修正 |
| 🏛️ architect（軍師） | Opus | 設計・計画・複雑な技術的意思決定 |

各将は出陣時に名乗りを上げ申す。また `.claude/agent.log` に召喚の記録が残り候。

## 陣中の秘術（スラッシュコマンド）

`claude` 起動後、以下の呪文を唱えることができ申す：

| 呪文 | 唱えるとき | 効果 |
|------|-----------|------|
| `/project:init` | 開戦直後（1回） | `{{...}}` を対話形式で一括置換、git / remote 設定 |
| `/project:status` | いつでも | フェーズ進捗・未置換箇所・テスト状態を一覧表示 |
| `/project:license-check` | 実装中・完了前 | ライセンスヘッダー欠けを検出、自動追加を提案 |
| `/project:review-code` | 実装完了後 | 静的解析＋定性レビュー（命名・構造・コメント） |
| `/project:review-spec` | BDD作成後・完了前 | BDD仕様 ↔ API仕様のカバレッジ照合、未カバーを提案 |
| `/project:bdd` | BDD確認時 | `behave` を実行してシナリオ単位で PASS/FAIL を表示 |
| `/project:docs` | 実装完了後 | Doxygen / Sphinx / cargo doc を一括実行 |
| `/project:report` | 各フェーズ完了時 | `docs/COMPLETION_REPORT.md` を自動生成 |
| `/project:qiita` | 最終化時（任意） | `docs/qiita_draft.md` にQiita記事ドラフトを生成 |

## 御城に備わる兵器（開発環境）

| 兵器/流派 | 詳細 |
|----------|------|
| Python | 3.x + pytest, behave, numpy, scipy |
| Octave | latest + signal package |
| C++ | g++ + cmake + Eigen |
| C# | .NET SDK 8.0 |
| Rust | latest (rustup stable) |
| Claude Code | latest (npm) |
| Doxygen + Graphviz | C++/C# APIドキュメント生成 |
| Sphinx + Breathe | Python APIドキュメント生成 |

## 御法度（ライセンス）

MIT License

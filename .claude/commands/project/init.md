プロジェクト初期化コマンドです。`{{...}}` プレースホルダーをすべて実際の値に置換します。

以下の手順で実行してください：

## Step 1: プレースホルダーの収集

以下のファイルから `{{...}}` パターンを検索し、ユニークなプレースホルダー一覧を抽出してください：
- `CLAUDE.md`
- `AGENT_MASTER_PLAN.md`
- `.devcontainer/devcontainer.json`

重複は除外し、アルファベット順に並べてください。

## Step 2: ユーザーへの確認

抽出したプレースホルダーを表示し、各プレースホルダーの値をユーザーに質問してください。

以下は各プレースホルダーの意味です（参考）：
- `{{PROJECT_NAME}}` — リポジトリ名（例: `my-signal-processor`）
- `{{PROJECT_TITLE}}` — プロジェクト表示名（例: `My Signal Processor`）
- `{{GIT_USER_NAME}}` — Gitユーザー名（例: `YourName`）
- `{{GIT_USER_EMAIL}}` — Gitメールアドレス（例: `you@example.com`）
- `{{GITHUB_REMOTE}}` — GitHubリモートURL（例: `https://github.com/user/repo`）
- `{{LICENSE}}` — ライセンス名（例: `MIT`）
- `{{YEAR}}` — 実装年（例: `2026`）
- `{{LICENSE_ATTRIBUTION}}` — 帰属表示（元ソースがある場合。なければ空欄可）
- `{{SOURCE_AUTHOR}}` — 元ソースの著者（なければ `N/A`）
- `{{SOURCE_URL}}` — 元ソースのURL（なければ `N/A`）
- `{{SOURCE_LICENSE}}` — 元ソースのライセンス（なければ `N/A`）
- `{{ATTRIBUTION_NOTE}}` — 帰属注記（なければ空欄可）
- `{{DELIVERABLE_1〜3}}` — 最終成果物（例: `Python実装`）
- `{{IMPL_PHASE_1〜2}}` — 実装フェーズ名（例: `Python実装（リファレンス）`）
- `{{IMPL_PHASE_1〜2_TASKS}}` — 各フェーズのタスク内容
- `{{CONSTRAINT_1〜2}}` — 制約条件（例: `FFT正規化: Forward=なし, Inverse=1/N`）
- `{{VALIDATION_CRITERIA}}` — 検証合格基準（例: `全ペア 相対誤差 < 1e-10`）
- `{{TEST_COMMANDS}}` — テスト実行コマンド（例: `pytest tests/`）
- `{{CROSS_VALIDATION_COMMANDS}}` — クロス検証コマンド
- `{{FINAL_TEST_COMMAND}}` — 最終テストコマンド
- `{{FINAL_VALIDATION_COMMAND}}` — 最終検証コマンド
- `{{ADDITIONAL_STRUCTURE}}` — 追加のディレクトリ構造
- `{{FUNCTION_1〜2}}` — API関数名
- `{{INPUT_1〜2}}` — 関数の入力仕様
- `{{OUTPUT_1〜2}}` — 関数の出力仕様
- `{{ALGO_1〜2}}` — アルゴリズム/処理内容
- `{{VALIDATION_TASKS}}` — 検証フェーズのタスク
- `{{REF_LINK_1〜2}}` — 参考リンク
- `{{LANG_1〜2}}` — 使用言語名（技術的知見セクション用）
- `{{FEATURE_NAME}}` — BDD Feature名
- `{{FEATURE_DESCRIPTION}}` — BDD Feature説明
- `{{SCENARIO_1}}` / `{{SCENARIO_ERROR}}` — BDD シナリオ名
- `{{GIVEN_CONDITION}}` / `{{WHEN_ACTION}}` / `{{THEN_RESULT}}` — BDD ステップ

## Step 3: 置換の実行

ユーザーから値を受け取ったら、対象ファイル内のすべての該当プレースホルダーを置換してください。
値が未入力（スキップ）の場合はそのまま残してください。

## Step 4: Gitユーザー設定

`{{GIT_USER_NAME}}` と `{{GIT_USER_EMAIL}}` が入力された場合、以下のコマンドを実行してください：

```bash
git config --global user.name "入力された名前"
git config --global user.email "入力されたメール"
```

## Step 5: リモート設定

`{{GITHUB_REMOTE}}` が入力された場合、以下を実行してください：

```bash
git remote set-url origin "入力されたURL"
```

すでにリモートが存在しない場合は `git remote add origin` を使用してください。

## Step 6: 完了報告

置換したプレースホルダーの一覧と、まだ未入力のプレースホルダーがあれば一覧を表示して完了を報告してください。

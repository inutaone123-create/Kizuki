# AGENT MASTER PLAN
# Claude Code エージェント実行用マスタープラン

このドキュメントは、Dev Container環境でClaude Codeエージェントがプロジェクトを自律的に実行するための設計書です。
**プロジェクト開始前に、`{{...}}` のプレースホルダーをすべて埋めてください。**

---

## 🎯 プロジェクト目標

### プロジェクト名
{{PROJECT_TITLE}}

### 最終成果物
1. {{DELIVERABLE_1}}
2. {{DELIVERABLE_2}}
3. {{DELIVERABLE_3}}
<!-- 必要に応じて追加 -->

### 参考・元ソース（あれば）
- **著者/出典**: {{SOURCE_AUTHOR}}
- **URL/DOI**: {{SOURCE_URL}}
- **ライセンス**: {{SOURCE_LICENSE}}

### このプロジェクトのライセンス
- **ライセンス**: {{LICENSE}}
- **帰属表示**: {{ATTRIBUTION_NOTE}}

---

## 🐳 Dev Container環境

### 実行環境
- **場所**: Dev Container内
- **Claude Code**: コンテナ内にインストール済み
- **作業ディレクトリ**: /workspace

### 前提条件
- VSCode with Dev Containers拡張機能
- Docker Desktop（WSL2バックエンド）
- 初期設定ファイル（Dockerfile等）は既に配置済み

---

## 📁 プロジェクト構造（予定）

```
{{PROJECT_NAME}}/
├── README.md
├── LICENSE
├── Dockerfile
├── docker-compose.yml
├── .devcontainer/
├── CLAUDE.md
├── docs/
│   ├── COMPLETION_REPORT.md
│   └── IMPLEMENTATION_NOTES.md
├── features/              # BDD仕様
│   ├── *.feature
│   └── steps/
{{ADDITIONAL_STRUCTURE}}
```

---

## 🔢 実行フェーズ

### Phase 0: 確認と準備
- 現在地確認（/workspace）
- 既存ファイル確認
- Git設定（`git config --global --add safe.directory /workspace`）

### Phase 1: ライセンスとドキュメント基盤
- LICENSE作成
- README.md作成（帰属表示含む）

### Phase 2: プロジェクト設定
- .gitignore
- .vscode/settings.json

### Phase 3: BDD仕様定義
- features/*.feature 作成（以下のGherkinひな型を参考に）
- Step定義ファイル作成（`features/steps/` 以下）

**Gherkinひな型（`features/{{FEATURE_NAME}}.feature`）**:
```gherkin
Feature: {{FEATURE_NAME}}
  {{FEATURE_DESCRIPTION}}

  Scenario: {{SCENARIO_1}}
    Given {{GIVEN_CONDITION}}
    When {{WHEN_ACTION}}
    Then {{THEN_RESULT}}

  Scenario: エラーケース — {{SCENARIO_ERROR}}
    Given {{ERROR_GIVEN}}
    When {{ERROR_WHEN}}
    Then {{ERROR_THEN}}
```

**Step定義ひな型（`features/steps/{{FEATURE_NAME}}_steps.py`）**:
```python
from behave import given, when, then

@given(u'{{GIVEN_CONDITION}}')
def step_given(context):
    pass  # TODO: 実装

@when(u'{{WHEN_ACTION}}')
def step_when(context):
    pass  # TODO: 実装

@then(u'{{THEN_RESULT}}')
def step_then(context):
    pass  # TODO: 実装
```

### Phase 4〜N: 実装フェーズ
<!-- 実装するモジュール・言語・機能ごとにPhaseを定義する -->
### Phase 4: {{IMPL_PHASE_1}}
- {{IMPL_PHASE_1_TASKS}}

### Phase 5: {{IMPL_PHASE_2}}
- {{IMPL_PHASE_2_TASKS}}

### Phase N-2: 検証・クロス検証
- {{VALIDATION_TASKS}}

### Phase N-1: ドキュメント生成
- `/project:docs` を実行して全言語のAPIドキュメントを生成
- C++/C# → Doxygen（`docs/doxygen/html/index.html`）
- Python  → Sphinx（`docs/sphinx/_build/html/index.html`）
- Rust    → cargo doc（`target/doc/index.html`）
- 生成されたドキュメントに未記入の `@brief` / `"""` 等がないか確認
- `/project:license-check` でライセンスヘッダーの最終確認

### Phase N: 最終化
- `/project:report` で `docs/COMPLETION_REPORT.md` を生成
- `/project:qiita` で `docs/qiita_draft.md` を生成（任意）
  - `docs/qiita_template.md` を参照して構成を確認
  - TODO 箇所をユーザーが手動記入して完成させる

---

## 📜 ライセンス遵守要件

全ソースファイルに以下のヘッダーを付ける（CLAUDE.md のテンプレート参照）：
- 帰属表示: {{LICENSE_ATTRIBUTION}}
- ライセンス: {{LICENSE}}

---

## 🎯 共通API仕様 / インターフェース仕様

### {{FUNCTION_1}}
- 入力: {{INPUT_1}}
- 出力: {{OUTPUT_1}}
- アルゴリズム/処理: {{ALGO_1}}

### {{FUNCTION_2}}
- 入力: {{INPUT_2}}
- 出力: {{OUTPUT_2}}
- アルゴリズム/処理: {{ALGO_2}}

---

## ✅ 各Phaseの成功基準

### Phase 0-2
- [ ] Git設定完了
- [ ] LICENSE, README.md 作成
- [ ] .vscode設定完了

### Phase 3
- [ ] Feature ファイル作成
- [ ] Gherkin構文検証

### Phase 4〜N-1（各実装Phase）
- [ ] 実装完了
- [ ] テスト全パス
- [ ] ライセンスヘッダー含む

### Phase N-2（検証）
- [ ] {{VALIDATION_CRITERIA}}

### Phase N-1（ドキュメント生成）
- [ ] Doxygen / Sphinx / cargo doc が警告なく生成完了
- [ ] 全パブリック関数にドキュメントコメントあり
- [ ] `/project:license-check` で全ファイルにヘッダーあり確認

### Phase N
- [ ] COMPLETION_REPORT.md 生成済み（`/project:report`）
- [ ] 全テストパス確認
- [ ] qiita_draft.md 生成済み（`/project:qiita`、任意）

---

## 🚨 重要な制約条件

1. {{CONSTRAINT_1}}
2. {{CONSTRAINT_2}}
<!-- 数値精度・スケーリング・パス指定など、プロジェクト固有の制約を記載 -->

---

## 📊 期待される最終状態

```bash
# テスト実行
{{FINAL_TEST_COMMAND}}
# → All tests passed

# 検証実行
{{FINAL_VALIDATION_COMMAND}}
# → All comparisons PASSED
```

---

## 🎓 Claude Codeエージェントへの指示

**あなた（Claude Code）は、このMASTER_PLANに従って、Dev Container内でPhase 0からPhase Nまで自律的に実行してください。**

### 各Phaseで
1. ✅ 目標を理解
2. ✅ 必要なファイルを作成・編集
3. ✅ テストを実行
4. ✅ 成功基準を満たす
5. ✅ 次のPhaseへ

### エラー発生時
1. エラーを分析
2. 修正方法を判断
3. 自動的に修正
4. 再テスト
5. **3回試みても解決しない場合**: 作業を停止し、以下を報告してユーザーの指示を仰ぐ
   - 現在のPhase・実行コマンド
   - エラーメッセージ全文
   - 試みた修正内容

### 完了条件
- 全Phaseの成功基準を満たす
- 全テストがパス
- ライセンス表示が完璧

---

## 📝 補足情報

### 参考リンク
- {{REF_LINK_1}}
- {{REF_LINK_2}}

仕様レビューコマンドです。BDD仕様（features/）と AGENT_MASTER_PLAN.md の API仕様を照合し、カバレッジを確認します。

## Step 1: 仕様の収集

以下を読み込んでください：

- `AGENT_MASTER_PLAN.md`（API仕様: `{{FUNCTION_N}}`・入出力・制約条件）
- `features/*.feature`（BDDシナリオ）
- `features/steps/*.py`（Step定義）

```bash
find features/ -name "*.feature" | sort
find features/steps/ -name "*.py" | sort
```

## Step 2: API仕様の抽出

`AGENT_MASTER_PLAN.md` から以下を抽出してください：

1. 定義されている関数・モジュール名（`{{FUNCTION_N}}` を置換済みの値）
2. 各関数の入力・出力・アルゴリズム
3. 制約条件（`{{CONSTRAINT_N}}` を置換済みの値）

プレースホルダーが未置換の場合は「`/project:init` を先に実行してください」と案内して終了してください。

## Step 3: BDDカバレッジの照合

API仕様の各関数・制約について、対応するシナリオが `features/` に存在するかを確認してください：

**確認項目**
- [ ] 正常系シナリオが存在するか
- [ ] 異常系・エラーケースのシナリオが存在するか
- [ ] 制約条件（数値精度・境界値等）を検証するシナリオが存在するか
- [ ] Step定義が `pass` のまま未実装でないか

## Step 4: Step定義の実装状況確認

```bash
grep -n "pass  # TODO" features/steps/*.py 2>/dev/null
grep -rn "NotImplementedError\|raise\|pass$" features/steps/ 2>/dev/null
```

## Step 5: behave の実行（Step定義が実装済みの場合）

```bash
behave features/ --dry-run 2>&1 | tail -20
```

`--dry-run` でシナリオの構文チェックのみ行います。

## Step 6: 結果の表示

以下の形式でレポートを表示してください：

```
## 仕様レビュー結果

### API仕様のカバレッジ

| 関数/機能 | 正常系 | 異常系 | 制約検証 |
|----------|--------|--------|---------|
| func_name_1 | ✅ | ✅ | ⚠️ なし |
| func_name_2 | ✅ | ❌ なし | ✅ |
| ...         | ...  | ...  | ...  |

カバレッジ: X / Y 項目

### 未カバーの仕様
- `func_name_2` の異常系シナリオがない
  → 提案: `Scenario: 不正な入力値を渡した場合にエラーを返す`
- ...

### Step定義の実装状況
- ✅ 全Step実装済み
- ⚠️ 未実装の Step: N件
  - features/steps/xxx_steps.py L12: `pass  # TODO`
  - ...

### 構文チェック（dry-run）
- ✅ 全シナリオ構文OK / ❌ エラーあり

---
STATUS: ✅ 完了 / ⚠️ 部分完了 / ❌ 失敗
NEXT: （未カバーの仕様がある場合は追加すべきシナリオを提案。なければ「なし」）
```

## Step 7: シナリオの自動提案

未カバーの仕様がある場合、以下の形式でシナリオひな型を提案してください：

```gherkin
  Scenario: （提案するシナリオ名）
    Given （前提条件）
    When  （操作）
    Then  （期待結果）
```

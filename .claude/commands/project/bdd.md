BDDテスト（behave）を実行して結果をサマリー表示するコマンドです。

以下の手順で実行してください：

## Step 1: features/ の確認

`features/` ディレクトリと `.feature` ファイルの存在を確認してください。

存在しない場合は「BDD仕様ファイルがありません。`AGENT_MASTER_PLAN.md` の Phase 3 に従って `features/*.feature` を作成してください。」と案内して終了してください。

## Step 2: behave の実行

```bash
behave features/ --no-capture 2>&1
```

## Step 3: 結果の表示

以下の形式でサマリーを表示してください：

```
## BDDテスト結果

**実行日時**: YYYY-MM-DD HH:MM

### シナリオ別結果
- ✅ PASS: シナリオ名
- ❌ FAIL: シナリオ名
  エラー: <エラー内容1行>

### サマリー
- Feature:  X 個
- Scenario: X passed / Y failed / Z skipped
- Step:     X passed / Y failed / Z skipped / W undefined

**全体**: ✅ 全パス / ❌ 失敗あり
```

## Step 4: 失敗時の対応

FAILがある場合：
1. 失敗したシナリオのStep定義ファイルを特定
2. エラーの原因を分析して修正案を提示
3. ユーザーに修正を適用するか確認する

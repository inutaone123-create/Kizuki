プロジェクトのフェーズ進捗を確認するコマンドです。

以下の手順で現在の状態を調査・表示してください：

## Step 1: 基本情報の確認

```bash
git log --oneline -20
git status
git branch
```

## Step 2: AGENT_MASTER_PLAN.md のフェーズ一覧を読む

`AGENT_MASTER_PLAN.md` を読み込み、定義されている Phase 0〜N の一覧を取得してください。

## Step 3: 各フェーズの完了判定

以下の基準で各フェーズの完了状態を判定してください：

| フェーズ | 完了の判定基準 |
|---------|--------------|
| Phase 0（確認・準備） | `git log` にコミットがある / git設定済み |
| Phase 1（ライセンス・ドキュメント） | `LICENSE` ファイルが存在する |
| Phase 2（プロジェクト設定） | `.gitignore` が存在し `{{` を含まない |
| Phase 3（BDD仕様） | `features/*.feature` ファイルが存在する |
| 実装フェーズ | `git log` に該当Phaseのコミットメッセージがある |
| 検証フェーズ | `docs/COMPLETION_REPORT.md` が存在する |

## Step 4: プレースホルダーの残存確認

```bash
grep -r "{{" CLAUDE.md AGENT_MASTER_PLAN.md .devcontainer/ 2>/dev/null | grep -v "^Binary"
```

未置換のプレースホルダーが残っている場合は警告を表示してください。

## Step 5: テスト状態の確認

`pytest --tb=no -q 2>/dev/null` を実行してテストの現状を確認してください（pytest がインストールされている場合）。

## Step 6: 結果の表示

以下の形式で表示してください：

```
## プロジェクト進捗状況

**ブランチ**: main / feature/xxx
**最新コミット**: <メッセージ>

### フェーズ進捗
- [x] Phase 0: 確認と準備
- [x] Phase 1: ライセンス・ドキュメント
- [ ] Phase 2: プロジェクト設定
- [ ] Phase 3: BDD仕様定義
- [ ] Phase 4: ...

### ⚠️ 未置換プレースホルダー
- {{GIT_USER_NAME}} — CLAUDE.md
- ...
（なければ「✅ なし」）

### テスト状態
- pytest: X passed / Y failed / 未実行
```

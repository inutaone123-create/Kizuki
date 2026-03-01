Qiita投稿用の記事ドラフトを `docs/qiita_draft.md` に生成するコマンドです。

## Step 1: プロジェクト情報の収集

以下を読み込んでください：
- `AGENT_MASTER_PLAN.md`（プロジェクト目標・フェーズ・API仕様）
- `docs/COMPLETION_REPORT.md`（存在する場合：実装概要・テスト結果）
- `CLAUDE.md`（使用言語・ライセンス情報）
- `README.md`（プロジェクト概要）

また以下も実行して情報を補完してください：

```bash
git log --oneline | head -20
```

## Step 2: コード例の抜粋

各言語のソースファイルから、記事で紹介するのに適したコード例を自動抜粋してください。

抜粋の優先順位：
1. `AGENT_MASTER_PLAN.md` の `{{FUNCTION_1}}` / `{{FUNCTION_2}}` に対応するコア関数
2. 最も行数が少なく、かつ機能を端的に示す関数
3. テストファイル内の使用例（`test_*.py`, `*_test.cpp` 等）

各言語につき最大2〜3関数を抜粋してください。

## Step 3: テスト・ベンチマーク結果の取得

```bash
pytest --tb=no -q 2>/dev/null | tail -5
```

`COMPLETION_REPORT.md` にテスト結果が記載されている場合はそちらを優先してください。

## Step 4: docs/qiita_draft.md の生成

`docs/qiita_template.md` を参照しながら、収集した情報で以下の構成のドラフトを生成してください：

---

```markdown
---
title: 【TODO: タイトルを記入】
tags:
  - TODO
  - Python
  - C++
emoji: 🔬
type: tech
topics: []
published: false
---

## はじめに

<!-- TODO: 背景・動機・この記事で伝えたいことを2〜3段落で記述 -->

{{PROJECT_TITLE}} を実装しました。
<!-- AGENT: AGENT_MASTER_PLAN.md のプロジェクト目標をもとに背景を記述 -->

## 環境

| 項目 | バージョン |
|------|-----------|
| OS | Ubuntu 22.04 (Dev Container) |
| Python | 3.x |
| <!-- 使用言語を列挙 --> | |

## 実装概要

<!-- AGENT: AGENT_MASTER_PLAN.md の共通API仕様・フェーズ概要をもとに記述 -->

## 実装

<!-- AGENT: 抜粋したコード例を言語別に記載。コードブロックの言語タグを正確に付けること -->

### Python

```python
# TODO: コア関数のコード例を挿入
```

### C++

```cpp
// TODO: コア関数のコード例を挿入
```

<!-- 他の言語も同様に追加 -->

## 実行結果

<!-- AGENT: テスト結果・ベンチマーク・クロス検証結果を記載 -->

```
TODO: テスト出力を挿入
```

## まとめ

<!-- TODO: 学んだこと・工夫した点・今後の展望を箇条書きで -->

-
-
-

## 参考

<!-- AGENT: AGENT_MASTER_PLAN.md の参考リンクを列挙 -->

- [TODO](URL)
```

---

## Step 5: TODO の一覧表示

生成後、ファイル内の `<!-- TODO:` と `# TODO:` を検索し、記入が必要な箇所を一覧表示してください：

```
## ✍️ 手動記入が必要な箇所

1. タイトル（冒頭 title フィールド）
2. tags（Qiita のタグ）
3. はじめに（背景・動機）
4. ...
```

## Step 6: 既存ファイルの扱い

`docs/qiita_draft.md` がすでに存在する場合は、上書きするか確認をユーザーに求めてから実行してください。

完了後、`docs/qiita_draft.md` を開いて内容を確認するよう案内してください。

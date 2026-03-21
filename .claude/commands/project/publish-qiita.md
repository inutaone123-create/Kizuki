# Qiita記事投稿コマンド

指定したドラフトファイルを Qiita に投稿（または更新）します。

## 使い方

```
/project:publish-qiita docs/qiita_draft_08_report_edit.md
```

## 手順

1. 引数からドラフトファイルのパスを取得する。引数がなければ `docs/` 以下の最新の `qiita_draft_*.md` を使う。
2. 以下のコマンドを実行する：

```bash
cd /workspace && python scripts/publish_qiita.py $ARGUMENTS
```

3. 出力結果をユーザーに伝える。
   - 新規作成の場合：表示された URL をドラフトファイルの先頭コメントに追記する
   - 更新の場合：URLを確認して完了を伝える
4. 新規作成だった場合は、ドラフトファイルに `<!-- 公開URL: {URL} -->` を先頭行に追記し、`published: true` に変更してコミット＆プッシュする。

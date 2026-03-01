全言語のAPIドキュメントを生成するコマンドです。言語ごとに最適なツールを使用します。

## Step 1: 環境確認

以下のツールが使用可能か確認してください：

```bash
doxygen --version 2>/dev/null && echo "doxygen: OK" || echo "doxygen: 未インストール"
sphinx-build --version 2>/dev/null && echo "sphinx: OK" || echo "sphinx: 未インストール"
cargo --version 2>/dev/null && echo "cargo: OK" || echo "cargo: 未インストール"
```

## Step 2: 出力ディレクトリの準備

```bash
mkdir -p docs/doxygen docs/sphinx
```

## Step 3: C++ / C# → Doxygen

`Doxyfile` が存在する場合はそれを使用し、存在しない場合は `docs/Doxyfile.template` をコピーして生成してください。

```bash
# Doxyfileが存在しない場合
cp docs/Doxyfile.template Doxyfile 2>/dev/null || true

# 生成実行
doxygen Doxyfile 2>&1 | tail -20
```

C++ / C# ファイルが存在しない場合はこのステップをスキップしてください。

## Step 4: Python → Sphinx

Python ソースが存在する場合に実行してください。

```bash
# sphinx設定がなければ初期化
if [ ! -f docs/sphinx/conf.py ]; then
  sphinx-quickstart docs/sphinx \
    --quiet \
    --project="{{PROJECT_TITLE}}" \
    --author="{{GIT_USER_NAME}}" \
    --language=ja \
    --ext-autodoc \
    --ext-viewcode \
    --ext-napoleon
fi

# autodoc でAPIドキュメントを生成
sphinx-apidoc -o docs/sphinx . \
  --force \
  --separate \
  --module-first \
  --implicit-namespaces \
  -e 2>/dev/null

# ビルド
sphinx-build -b html docs/sphinx docs/sphinx/_build/html -q 2>&1 | tail -20
```

## Step 5: Rust → cargo doc

Rust の `Cargo.toml` が存在する場合に実行してください。

```bash
cargo doc --no-deps --document-private-items 2>&1 | tail -20
```

## Step 6: 結果の表示

生成されたドキュメントの場所と警告数を表示してください：

```
## ドキュメント生成結果

| 言語 | ツール | 出力先 | 状態 |
|------|--------|--------|------|
| C++/C# | Doxygen | docs/doxygen/html/index.html | ✅ / ❌ / ⏭️ スキップ |
| Python | Sphinx  | docs/sphinx/_build/html/index.html | ✅ / ❌ / ⏭️ スキップ |
| Rust   | cargo doc | target/doc/index.html | ✅ / ❌ / ⏭️ スキップ |

### ⚠️ 警告（あれば）
- <警告内容>
```

## Step 7: ドキュメントコメント未記入の検出

以下のパターンで未記入の関数・クラスを検索して報告してください：

- C++: `/// @brief` や `/** @brief` のない `public` 関数
- Python: docstring のない `def` / `class`（`__` 始まりは除外）
- Rust: `///` のない `pub fn` / `pub struct`

未記入が多い場合は「`CLAUDE.md` のドキュメントコメント規約を参照して追記してください」と案内してください。

コードレビューコマンドです。静的解析と定性レビューをセットで実行します。

## Step 1: 対象ファイルの収集

ソースファイルを言語別に収集してください（`build/`, `target/`, `obj/`, `bin/`, `.git/`, `node_modules/` は除外）：

```bash
find . -type f \( -name "*.py" -o -name "*.cpp" -o -name "*.h" -o -name "*.hpp" \
  -o -name "*.cs" -o -name "*.rs" -o -name "*.m" \) \
  | grep -v -E "(build|target|obj|bin|\.git|node_modules)/" \
  | sort
```

## Step 2: 静的解析の実行

言語別に以下を実行してください。ツールが存在しない場合はスキップしてください。

**Python**
```bash
python3 -m pylint $(find . -name "*.py" | grep -v -E "(build|\.git|test_)") \
  --score=no --disable=C0114,C0115,C0116 2>/dev/null | tail -20
python3 -m black --check . 2>/dev/null | tail -10
```

**Rust**
```bash
cargo clippy 2>&1 | grep -E "^error|^warning" | head -20
```

**C++**
```bash
# cppcheck がある場合
cppcheck --enable=warning,style,performance \
  $(find . -name "*.cpp" -o -name "*.h" | grep -v build/) 2>&1 | head -20
```

**C#**
```bash
dotnet format --verify-no-changes 2>&1 | tail -10
```

## Step 3: ライセンスヘッダー確認

`/project:license-check` と同等のチェックを実行し、ヘッダー欠けファイルがあれば一覧表示してください。

## Step 4: ドキュメントコメントの確認

以下のパターンで未記入の関数・クラスを検出してください：

- **Python**: docstring のない `def` / `class`（`__` 始まり・テストファイルは除外）
- **C++**: `/** @brief` / `/// @brief` のない関数定義
- **Rust**: `///` のない `pub fn` / `pub struct` / `pub enum`
- **C#**: `/// <summary>` のない `public` メソッド・クラス

## Step 5: 定性レビュー

収集したソースファイルを読み込み、以下の観点でレビューしてください：

**命名規則**
- 言語のコンベンション（Python: snake_case、C++: camelCase 等）に従っているか
- 変数名・関数名が意図を表しているか

**コード構造**
- 関数が単一責任の原則に従っているか（目安: 50行以上の関数は要確認）
- 重複コードがないか
- マジックナンバーが定数化されているか

**AGENT_MASTER_PLAN.md との整合性**
- 実装が API 仕様（`{{FUNCTION_1}}` 等）に沿っているか
- 制約条件（`{{CONSTRAINT_N}}`）が守られているか

## Step 6: 結果の表示

以下の形式でレポートを表示してください：

```
## コードレビュー結果

### 静的解析
| 言語 | ツール | 結果 |
|------|--------|------|
| Python | pylint | ✅ 警告なし / ⚠️ N件 |
| Rust | clippy | ✅ 警告なし / ⚠️ N件 |
| C++ | cppcheck | ✅ / ⚠️ / ⏭️ スキップ |
| C# | dotnet format | ✅ / ⚠️ / ⏭️ スキップ |

### ライセンスヘッダー
- ✅ 全ファイル OK / ❌ 欠けているファイル: N件

### ドキュメントコメント
- ✅ 全関数 OK / ⚠️ 未記入: N件
  - path/to/file.py: `def func_name`
  - ...

### 定性レビュー

**🟢 良い点**
- ...

**🟡 改善提案**
- path/to/file.py L42: （指摘内容）
- ...

**🔴 要対応**
- （重大な問題があれば）

---
STATUS: ✅ 問題なし / ⚠️ 軽微な指摘あり / 🔴 要対応あり
NEXT: （対応が必要な場合は修正方針を記載。なければ「なし」）
```

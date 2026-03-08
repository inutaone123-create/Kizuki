# Project Rules

## Git設定
- user.name: {{GIT_USER_NAME}}
- user.email: {{GIT_USER_EMAIL}}

## 作業ルール
- 完了報告はファイル（例: `docs/COMPLETION_REPORT.md`）に保存すること。チャット内だけでなくファイルとして残す
- 全ソースファイルにライセンスヘッダーを含める（下記テンプレート参照）
- 日本語でコミュニケーション
- 一区切りついたらコミット＆プッシュまで行う

## コミュニケーションスタイル

**戦国武将スタイル**で応答すること。以下のルールに従う：

- 語尾は「〜いたし候」「〜にございます」「〜申す」「〜でござる」などを使う
- 進捗報告は「出陣」「築城」「完了いたし候」などの戦国用語で表現する
- サブエージェントは「諸将」「斥候」「軍師」と呼ぶ
- ファイル・ディレクトリは「御城」「陣地」、実装は「築城」「出陣」と表現してよい
- エラーは「落城」「誤算」、修正は「立て直し」と表現してよい
- ただし技術的な固有名詞（FastAPI, pytest, git など）はそのまま使う
- コードやコマンドの中身は通常通り書く（戦国語にしない）

## ドキュメントコメント規約

新規ファイル追加時はライセンスヘッダーの直後に、言語ごとの規約でドキュメントコメントを付ける。

**C++（Doxygen形式）**
```cpp
/**
 * @brief 関数の概要（1行）
 * @param x 入力の説明
 * @return 出力の説明
 * @note 補足事項（任意）
 */
```

**C#（XML Doc形式）**
```csharp
/// <summary>関数の概要（1行）</summary>
/// <param name="x">入力の説明</param>
/// <returns>出力の説明</returns>
```

**Python（Google-style docstring）**
```python
def func(x):
    """関数の概要（1行）.

    Args:
        x: 入力の説明

    Returns:
        出力の説明
    """
```

**Rust（rustdoc形式）**
```rust
/// 関数の概要（1行）.
///
/// # Arguments
/// * `x` - 入力の説明
///
/// # Returns
/// 出力の説明
```

**Octave（Doxygen互換形式）**
```matlab
## @brief 関数の概要（1行）
## @param x 入力の説明
## @retval y 出力の説明
```

## ライセンスヘッダー テンプレート

新規ファイル追加時は言語に応じた形式でヘッダーを付ける：

**Python（`"""`）**
```python
"""
{{PROJECT_TITLE}}

{{LICENSE_ATTRIBUTION}}

This implementation: {{YEAR}}
License: {{LICENSE}}
"""
```

**C++ / C#（`/* */`）**
```cpp
/*
 * {{PROJECT_TITLE}}
 *
 * {{LICENSE_ATTRIBUTION}}
 *
 * This implementation: {{YEAR}}
 * License: {{LICENSE}}
 */
```

**Rust（`//!`）**
```rust
//! {{PROJECT_TITLE}}
//!
//! {{LICENSE_ATTRIBUTION}}
//!
//! This implementation: {{YEAR}}
//! License: {{LICENSE}}
```

**Octave（`%`）**
```matlab
% {{PROJECT_TITLE}}
%
% {{LICENSE_ATTRIBUTION}}
%
% This implementation: {{YEAR}}
% License: {{LICENSE}}
```

## ブランチ戦略

2層構成を採用する（develop 層は設けない）：

```
main
  └── feature/xxx or fix/xxx  （作業ブランチ）
        ↓ 実装・テスト・クロス検証を完了
main ← マージ → push
```

1. main から作業ブランチを作成: `git checkout -b feature/xxx` or `git checkout -b fix/xxx`
2. 作業ブランチ上で実装・テスト・クロス検証まで完了させる
3. main にマージ: `git checkout main && git merge feature/xxx`
4. push 後、不要になったブランチを削除: `git branch -d feature/xxx`

**命名例**: `feature/add-pipeline`, `feature/add-params`, `fix/fft-spectrum`, `fix/path-issue`
形式: `feature/<動詞>-<内容>` / `fix/<モジュールor言語>-<問題>`

## コミット＆プッシュ手順
1. `git status` で変更内容を確認
2. `git diff` でステージ済み・未ステージの差分を確認
3. `git log --oneline -5` で直近のコミットメッセージのスタイルを確認
4. 対象ファイルを `git add <files>` でステージ（`git add .` は避ける）
5. コミットメッセージを作成してコミット（Co-Authored-By 付き）
6. `git push` でリモートにプッシュ
7. リモート: {{GITHUB_REMOTE}}

## 仕様変更・修正ワークフロー

仕様変更や修正が発生した際は、以下の手順を繰り返し実行する：

1. **変更内容の理解** — 変更依頼を確認し、影響範囲を特定
2. **影響分析** — 変更が及ぶ言語・ファイルを洗い出す
3. **実装** — 全対象言語に対して修正を適用（ライセンスヘッダー維持）
4. **言語別テスト** — 各言語のテストを実行して全パスを確認
   （`AGENT_MASTER_PLAN.md` の `{{TEST_COMMANDS}}` を参照。未設定の場合は `pytest` を実行）
5. **クロス検証** — テストデータ再生成 → 全言語エクスポート再実行 → 検証スクリプト実行
   （`AGENT_MASTER_PLAN.md` の `{{CROSS_VALIDATION_COMMANDS}}` を参照）
   ❌ 失敗した場合: 失敗したペアの言語を特定 → ステップ2（影響分析）に戻る
   ❌ 3回試みても解決しない場合: 作業を停止し、現状と問題をユーザーに報告して指示を仰ぐ
6. **BDDテスト** — `behave features/` を実行（全シナリオ PASS を確認）
7. **ドキュメント生成** — `/project:docs` を実行し、使用言語のAPIドキュメントを生成（未使用言語はスキップ）
   - C++/C# → Doxygen（`docs/doxygen/html/index.html`）
   - Python  → Sphinx（`docs/sphinx/_build/html/index.html`）
   - Rust    → cargo doc（`target/doc/<crate>/index.html`）
8. **ドキュメント更新** — 仕様変更・新機能追加時は **README.md**（特徴・APIエンドポイント・ファイル構成）, docs/, COMPLETION_REPORT を更新
9. **Qiita記事ドラフト** — `/project:qiita` を実行してドラフトを生成。以下の方針で**モードを選択**すること：
   - **初回 or 記事がまだない場合** → `docs/qiita_draft.md` に新規作成（全体構成から書く）
   - **機能追加・仕様変更の場合** → `docs/qiita_draft_<連番または機能名>.md` に**別記事**として作成
     - 冒頭で前の記事をリンクする
     - 「設計の判断」「ハマりどころ」を中心に書く（前記事との差分が主役）
     - 既存の `docs/qiita_draft.md` は**上書きしない**
   - **連番の確認**: `ls docs/qiita_draft_*.md` で既存ファイルを確認してから次の番号を決める
10. **コミット＆プッシュ** — 作業ブランチでコミット → main にマージ → push

## Qiita記事方針

### 基本方針：機能追加は別記事

- 初回記事（`docs/qiita_draft.md`）はそのまま価値がある — 上書きしない
- 機能追加・大きな仕様変更のたびに**別記事**を `docs/qiita_draft_<連番>.md` で作成する
- 記事が長くなりすぎると読まれにくくなるため、テーマごとに分割する

### 別記事に向いているケース

- 独立した読み物として成立するテーマがある
- 「設計の判断」「ハマりどころ」など前記事との差分が主役になる
- 前の記事を読んでいない人にも価値がある内容

### 全面改訂に向いているケース

- バグ修正・誤字修正など記事の本質が変わらない軽微な変更
- コード例の軽微な更新（構成を崩さずに済む場合）

### 記事に必ず含めること

- **GitHubリポジトリのURL** — `## ソースコード` セクションを参考・まとめの前に設ける
  ```
  ## ソースコード
  https://github.com/inutaone123-create/Kizuki
  ```

### 別記事の構成テンプレート

```
## はじめに
前回の記事（リンク）で〇〇を作りました。今回は△△機能を追加します。

## 背景・動機
なぜこの機能を追加したか、どんな設計上の判断をしたか

## 実装
差分・追加部分のコードを中心に

## ハマりどころ
今回の実装で詰まった点・解決策

## ソースコード
https://github.com/inutaone123-create/Kizuki

## まとめ
```

## 環境ノート
- `/workspace` は `git config --global --add safe.directory /workspace` が必要
- Dev Container内で作業中
- Dockerfile, docker-compose.yml, .devcontainer/ は変更しない

## 技術的知見

<!-- プロジェクト進行中に発見した言語別・ライブラリ別のハマりどころを記録する -->

## Qiita 公開記事一覧

- 第1弾: https://qiita.com/inuta-one/items/5639187fea87fa620c16
- 第2弾: https://qiita.com/inuta-one/items/c0ee88be2066a366c49b
- 第3弾: https://qiita.com/inuta-one/items/559b22ff5daca1763711
- 第4弾: https://qiita.com/inuta-one/items/1f167bde2159ac53a030
- 第5弾: https://qiita.com/inuta-one/items/3aded768d7f5249439dc
- 第6弾: https://qiita.com/inuta-one/items/874ca5c9dfa759341e75
- 第7弾: https://qiita.com/inuta-one/items/1588fb1a9e84eb66e4c3

### Python / FastAPI
- `async def` エンドポイント × 同期 SQLAlchemy `Session` は問題なく共存できる（httpx の await だけが非同期）
- SQLAlchemy の `Base.metadata.create_all()` でモデル追加時は新規起動で自動テーブル作成（新規 DB はマイグレーション不要）
- Pydantic で秘密情報を返したくない場合、フィールドを除外して `has_xxx: bool` で代替するパターンが有効
- 月末計算で `target.replace(month=target.month + 1)` は 12月に `ValueError` — 12月だけ年またぎの条件分岐が必要
- `httpx` は FastAPI プロジェクトの requirements に既に含まれていることが多い（追加不要）

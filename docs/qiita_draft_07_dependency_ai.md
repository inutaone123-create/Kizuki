---
title: OSSから学んだ「タスク依存関係」と「AIワークフロー自動提案」をカンバンツールに実装した話
tags:
  - Python
  - FastAPI
  - SQLite
  - 個人開発
  - AI
emoji: 🔒
type: tech
topics: []
published: false
---

# OSSから学んだ「タスク依存関係」と「AIワークフロー自動提案」をカンバンツールに実装した話

## はじめに

前回の記事（[第6弾: ElectronでデスクトップApp化](https://qiita.com/inuta-one/items/874ca5c9dfa759341e75)）で、Kizuki を Windows アプリとして配布できるようにしました。

ある日、[multi-agent-shogun](https://github.com/yohey-w/multi-agent-shogun) という OSSを見ていて気づいたことがありました。

> 「タスクに `blocked_by`（依存関係）を持たせるって、カンバンツールにも欲しい概念だ」

multi-agent-shogun は AI エージェントを武将になぞらえて階層管理する面白いプロジェクトで、YAML でタスクの依存関係を管理する設計が採用されています。

```yaml
tasks:
  - id: "001"
    title: "調査"
    status: "done"
    blocked_by: []
  - id: "002"
    title: "実装"
    status: "waiting"
    blocked_by: ["001"]  # 001が完了するまで開始できない
```

この発想をそのまま Kizuki に取り込みつつ、ついでに「AI が作業パターンを分析してワークフローを自動提案する」機能も追加しました。

---

## 実装した機能

### 1. タスク依存関係（blockedBy）

- あるタスクが他タスクの完了を待つ「ブロッキング」関係を設定できる
- 未完了のブロッカーが存在するカードに **🔒 ブロック中** バッジを表示
- 詳細モーダルで依存関係の追加・削除が可能

### 2. AIワークフロー自動提案

- 既存タスクを分析して「こんなワークフローはどうですか？」と提案
- AI未設定でも3種のテンプレートからフォールバック提案
- カテゴリで絞り込んで再提案・ワンクリックで保存

---

## 設計の判断

### 中間テーブル方式を選んだ理由

タスク依存関係の持ち方は 2 択でした。

**案A: Issue テーブルに `blocked_by_id` カラムを追加**
```python
# シンプルだが1対1しか表現できない
blocked_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("issues.id"))
```

**案B: 中間テーブル `issue_dependencies` を新設**
```python
class IssueDependency(Base):
    __tablename__ = "issue_dependencies"
    issue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )
```

「1つのタスクが複数のタスクをブロックする」ケースを想定し、**案B** を採用しました。
`ondelete="CASCADE"` でタスク削除時に依存関係も自動削除されます。

---

### 循環依存の検出

AがBをブロックし、BがAをブロックする「デッドロック」を防ぐため、追加時に即座に検出します。

```python
@router.post("/{issue_id}/dependencies", status_code=201)
def add_dependency(issue_id: int, body: DependencyAdd, db: Session = Depends(get_db)):
    # 自己参照チェック
    if issue_id == body.blocked_by_id:
        raise HTTPException(status_code=400, detail="Self-dependency not allowed")

    # 循環依存チェック（直接の逆方向のみ）
    reverse = (
        db.query(IssueDependency)
        .filter(
            IssueDependency.issue_id == body.blocked_by_id,
            IssueDependency.blocked_by_id == issue_id,
        )
        .first()
    )
    if reverse:
        raise HTTPException(status_code=400, detail="Circular dependency not allowed")

    dep = IssueDependency(issue_id=issue_id, blocked_by_id=body.blocked_by_id)
    db.add(dep)
    db.commit()
```

今回は「直接の逆方向」のみチェックする実装にとどめました。A→B→C→A のような間接的な循環は現時点では許容しています（個人ツールとしての割り切り）。

---

### is_blocked の計算タイミング

`is_blocked`（ブロック中かどうか）は DB に持たせず、APIレスポンス生成時にリアルタイム計算します。

```python
@router.get("", response_model=list[IssueListResponse])
def list_issues(db: Session = Depends(get_db), ...):
    issues_list = query.order_by(Issue.updated_at.desc()).all()

    result = []
    for issue in issues_list:
        deps = db.query(IssueDependency).filter(
            IssueDependency.issue_id == issue.id
        ).all()
        blocked_by_ids = [d.blocked_by_id for d in deps]
        is_blocked = False
        if blocked_by_ids:
            blockers = db.query(Issue).filter(Issue.id.in_(blocked_by_ids)).all()
            is_blocked = any(b.status != "done" for b in blockers)  # 1件でも未完了なら
        item = IssueListResponse.model_validate(issue)
        item.blocked_by_ids = blocked_by_ids
        item.is_blocked = is_blocked
        result.append(item)
    return result
```

「ブロッカーが完了になった瞬間に自動で解除される」という自然な挙動になります。DB にフラグを持たせると同期ズレが起きる可能性があるため、計算式を信頼する設計にしました。

---

## AIワークフロー自動提案のフォールバック戦略

AI設定（OpenAI互換API）が未設定のユーザーでも使えるよう、カテゴリキーワードに基づくフォールバックを実装しました。

```python
_FALLBACK_WORKFLOWS = [
    {
        "name": "標準開発フロー",
        "steps": ["設計", "実装", "テスト", "レビュー", "完了"],
        "reason": "最も一般的な開発ワークフローです。",
    },
    {
        "name": "シンプルタスクフロー",
        "steps": ["着手", "作業中", "確認", "完了"],
        "reason": "シンプルなタスク管理に適したフローです。",
    },
    {
        "name": "承認フロー",
        "steps": ["申請", "審査", "承認", "実施", "完了"],
        "reason": "承認プロセスが必要な業務に適したフローです。",
    },
]

async def suggest_workflow(db: Session, category: str | None = None) -> dict:
    # ... AI呼び出し（失敗時またはAI未設定時はフォールバックへ）

    # カテゴリキーワードで適切なテンプレートを選択
    if category and any(kw in category for kw in ["承認", "申請", "審査"]):
        suggestion = _FALLBACK_WORKFLOWS[2]
    elif issues and len(issues) > 10:
        suggestion = _FALLBACK_WORKFLOWS[0]
    else:
        suggestion = _FALLBACK_WORKFLOWS[1]
```

AI が返す JSON の形式が不安定なことがあるため、パース時に防御コードを入れています。

```python
# JSON配列を抽出（コードブロック付きで返ってくることがある）
raw = raw.strip()
if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
        raw = raw[4:]
steps = json.loads(raw.strip())
```

---

## ハマりどころ

### Pydantic の `model_validate` 後にフィールドを上書きする

`IssueListResponse` は Pydantic モデルなので、`model_validate(issue)` でDBオブジェクトから変換した後にフィールドを書き換えようとしたら最初は動かなかったです。

```python
# ❌ これは動かない（Pydantic v2 はデフォルトで frozen に近い挙動）
item = IssueListResponse.model_validate(issue)
item.blocked_by_ids = blocked_by_ids  # AttributeError になる場合がある
```

`model_config` に `frozen=False`（デフォルト）を明示するか、`model_fields_set` を確認する必要があります。今回は以下のように `blocked_by_ids` と `is_blocked` を `IssueListResponse` の通常フィールドとして定義し、デフォルト値を持たせることで解決しました。

```python
class IssueListResponse(BaseModel):
    # ... 既存フィールド
    blocked_by_ids: list[int] = []   # デフォルト空リスト
    is_blocked: bool = False          # デフォルト False
```

これで `model_validate(issue)` でDBから変換 → 後からフィールドを上書きが問題なく動きます。

---

## テスト結果

```
tests/test_dependencies.py::TestDependencies::test_add_dependency PASSED
tests/test_dependencies.py::TestDependencies::test_get_dependencies PASSED
tests/test_dependencies.py::TestDependencies::test_is_blocked_in_list PASSED
tests/test_dependencies.py::TestDependencies::test_not_blocked_when_blocker_done PASSED
tests/test_dependencies.py::TestDependencies::test_self_dependency_rejected PASSED
tests/test_dependencies.py::TestDependencies::test_circular_dependency_rejected PASSED
tests/test_dependencies.py::TestDependencies::test_remove_dependency PASSED
tests/test_dependencies.py::TestDependencies::test_duplicate_dependency_rejected PASSED
tests/test_ai_suggest.py::TestSuggestWorkflow::test_suggest_returns_valid_structure PASSED
tests/test_ai_suggest.py::TestSuggestWorkflow::test_suggest_is_not_ai_without_settings PASSED
tests/test_ai_suggest.py::TestSuggestWorkflow::test_suggest_with_category PASSED
tests/test_ai_suggest.py::TestSuggestWorkflow::test_suggest_approval_flow_for_approval_category PASSED
tests/test_ai_suggest.py::TestSuggestWorkflow::test_suggest_with_existing_issues PASSED

68 passed in 1.65s
```

---

## ソースコード

https://github.com/inutaone123-create/Kizuki

---

## まとめ

- **OSSから学ぶ設計** — multi-agent-shogun の YAML タスク管理を見て「カンバンに依存関係が欲しい」と気づいた。実装のヒントはあらゆる場所に転がっている
- **中間テーブル vs カラム追加** — 多対多になる可能性があるなら中間テーブルが安全。最初から正規化しておくと後が楽
- **is_blocked は計算式で** — 状態フラグを DB に持たせるより、計算で導く方がズレが起きない
- **AI 機能はフォールバック必須** — AI 設定がなくても使えるテンプレート提案を用意しておくと UX が大きく改善する
- **Pydantic v2 のフィールド上書き** — `model_validate` 後の上書きはデフォルトフィールドとして定義しておくのがシンプル

次は……今のところ未定です。使いながらまた「あれが欲しい」と思ったら実装します 😄

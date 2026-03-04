---
title: 【Kizuki 機能追加】認証なしで使える「担当者アサイン」と「カスタムワークフロー」をFastAPI + Vanilla JSで実装した
tags:
  - Python
  - FastAPI
  - SQLAlchemy
  - SQLite
  - 個人開発
emoji: 🔄
type: tech
topics: []
published: false
---

## はじめに

前回の記事（[【Kizuki 機能追加】「メモを先に書いてあとからタスクに紐付ける」を FastAPI + SQLite で実現した](https://qiita.com/inuta-one/items/c0ee88be2066a366c49b)）では、個人用カンバンツール「Kizuki」にメモ機能を追加しました。

今回は**業務プロセス管理**の第一歩として、以下の2機能を追加しました。

1. **担当者アサイン** — 認証なし・名前登録だけでイシューに担当者を設定できる軽量な仕組み
2. **ワークフロー定義** — 「申請 → 承認 → 実行 → 完了」のようなカスタムステップを定義し、イシューに割り当てる

既存の3列カンバン（未着手 / 進行中 / 完了）はそのまま維持し、ワークフローはカードの**サブステップ情報**として表示する設計にしました。

---

## 背景・動機

個人用ツールとはいえ、タスクの「誰がやるか」と「どの段階か」は管理したくなります。ただし：

- **認証は重い** — 個人 + 身内向けのツールに OAuth や JWT を入れるのは過剰
- **汎用性が欲しい** — 「申請フロー」「レビューフロー」など用途に応じてステップを変えたい
- **既存 UI を壊したくない** — カンバンのドラッグ&ドロップは残したい

この3つの制約から「名前ベースのメンバー管理」＋「JSON配列でステップを持つワークフロー」というシンプルな設計にたどり着きました。

---

## データモデルの設計

### 新規テーブル: members

```python
class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")  # HEXカラー
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issues: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="assignee", passive_deletes=True
    )
```

認証不要なので `password` フィールドは持ちません。`color` は UI でバッジ表示するためのものです。

### 新規テーブル: workflows

```python
class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    steps: Mapped[str] = mapped_column(Text, nullable=False, default='["開始","完了"]')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

ステップは `["申請", "承認", "実行", "完了"]` のような **JSON文字列** として格納します。SQLite には配列型がないため、この方式を採りました。

### Issue テーブルへの追加カラム

```python
# Issueモデルへの追加フィールド
assignee_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True
)
workflow_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
)
workflow_step: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0始まりインデックス
```

担当者・ワークフローどちらも `SET NULL` で、削除時にイシューが孤立しない設計です。

---

## ハマりどころ①：SQLiteのALTER TABLE制限

SQLite は `ALTER TABLE ... ADD COLUMN` で `NOT NULL` カラムを追加できません（デフォルト値があれば追加できますが、`FOREIGN KEY` つきだと制限があります）。

そこで `migrate_memo.py` と同じアプローチで、**テーブル再作成方式**を採用しました：

```python
# scripts/migrate_workflow_member.py（抜粋）
def migrate(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")  # 外部キー制約を一時的に無効化
    try:
        cur = conn.cursor()

        # 1. 新スキーマで issues_new テーブルを作成
        cur.execute("""
            CREATE TABLE issues_new (
                id INTEGER PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                ...
                assignee_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
                workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
                workflow_step INTEGER
            )
        """)

        # 2. 既存データをコピー（新カラムは NULL で埋める）
        cur.execute("""
            INSERT INTO issues_new (id, title, ..., assignee_id, workflow_id, workflow_step)
            SELECT id, title, ..., NULL, NULL, NULL FROM issues
        """)

        # 3. 旧テーブルを削除 → リネーム
        cur.execute("DROP TABLE issues")
        cur.execute("ALTER TABLE issues_new RENAME TO issues")
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
```

**ポイント**: `PRAGMA foreign_keys = OFF` で無効化しないと、再作成中に参照整合性エラーが出ます。必ず `finally` で戻すことが大事です。

---

## ハマりどころ②：PydanticでJSON文字列をlist[str]に変換する

`Workflow.steps` はDBに文字列で入っていますが、APIレスポンスでは `list[str]` として返したい。

最初は `model_validate` をオーバーライドする方法を試みましたが、Pydantic v2 では `@field_validator` を使うのが正しいアプローチです：

```python
from pydantic import BaseModel, field_validator
import json

class WorkflowResponse(BaseModel):
    id: int
    name: str
    steps: list[str]  # DBでは文字列、レスポンスではリスト
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("steps", mode="before")
    @classmethod
    def parse_steps(cls, v):
        """steps JSON文字列をリストに変換する."""
        if isinstance(v, str):
            return json.loads(v)
        return v
```

`mode="before"` により、型検証の前に変換が走ります。`WorkflowInfo`（IssueResponseに埋め込む用）にも同じバリデータを追加しました。

---

## APIエンドポイント実装

### ワークフロー CRUD

```python
# src/routers/workflows.py（主要部分）

def _to_response(wf: Workflow) -> WorkflowResponse:
    """WorkflowモデルをWorkflowResponseに変換する."""
    steps = json.loads(wf.steps) if isinstance(wf.steps, str) else wf.steps
    return WorkflowResponse(id=wf.id, name=wf.name, steps=steps, created_at=wf.created_at)

@router.post("/api/workflows", response_model=WorkflowResponse, status_code=201)
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db)):
    wf = Workflow(name=body.name, steps=json.dumps(body.steps, ensure_ascii=False))
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _to_response(wf)
```

`ensure_ascii=False` で日本語のステップ名がそのまま保存されます。

### ワークフローステップ更新（PATCH）

```python
@router.patch("/api/issues/{issue_id}/workflow-step", response_model=IssueResponse)
def update_workflow_step(
    issue_id: int, body: WorkflowStepUpdate, db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not issue.workflow_id:
        raise HTTPException(status_code=400, detail="ワークフローが割り当てられていません")

    wf = db.query(Workflow).filter(Workflow.id == issue.workflow_id).first()
    steps = json.loads(wf.steps)
    if body.step < 0 or body.step >= len(steps):
        raise HTTPException(
            status_code=400,
            detail=f"ステップインデックスは 0〜{len(steps) - 1} の範囲で指定してください",
        )
    issue.workflow_step = body.step
    db.commit()
    db.refresh(issue)
    return issue
```

---

## フロントエンド: カンバンカードへの表示

カードのフッターに担当者バッジとワークフローステップを追加しました：

```javascript
// static/app.js（buildCard 関数内）
const assigneeHtml = issue.assignee
  ? `<span class="assignee-badge" style="background:${escHtml(issue.assignee.color)}">
       👤 ${escHtml(issue.assignee.name)}
     </span>`
  : "";

let wfStepHtml = "";
if (issue.workflow && issue.workflow_step != null) {
  const stepName = issue.workflow.steps[issue.workflow_step] || "";
  if (stepName) {
    wfStepHtml = `<span class="card-workflow-step">🔄 ${escHtml(stepName)}</span>`;
  }
}

const hasFooter = assigneeHtml || wfStepHtml;
// hasFooter のときだけ card-footer を描画（不要な余白を避ける）
```

## フロントエンド: 詳細モーダルのワークフロー進捗バー

```javascript
function renderWorkflowSection(issue) {
  const section = document.getElementById("workflow-section");
  if (!issue.workflow || issue.workflow_step == null) {
    section.style.display = "none";
    return;
  }
  const steps = issue.workflow.steps;
  const currentStep = issue.workflow_step;

  const stepsEl = document.getElementById("workflow-steps");
  stepsEl.innerHTML = steps.map((s, i) => {
    let cls = "";
    if (i < currentStep) cls = "done";        // 完了済み
    else if (i === currentStep) cls = "active"; // 現在地
    const arrow = i < steps.length - 1 ? `<span class="workflow-step-arrow">→</span>` : "";
    return `<div class="workflow-step-item">
      <span class="workflow-step-bubble ${cls}">${escHtml(s)}</span>${arrow}
    </div>`;
  }).join("");
}
```

`done`・`active`・（未着手）の3状態をCSSクラスで切り替えることで、シンプルにプログレス表示を実現しました。

---

## テスト結果

```
39 passed in 1.17s
```

既存25テストを維持しつつ、新規14テストを追加しました。

主なテストケース：
- メンバー作成・一覧・更新・削除
- 同名メンバー重複エラー
- ワークフロー CRUD
- ワークフローステップ更新（正常・範囲外エラー）
- イシューに担当者・ワークフローを割り当て、レスポンスにネストされた情報が含まれることを確認

```python
def test_issue_with_assignee_and_workflow(client: TestClient):
    """イシューに担当者とワークフローを割り当てられる."""
    member = client.post("/api/members", json={"name": "担当者A", "color": "#abc123"}).json()
    wf = client.post("/api/workflows", json={"name": "フロー", "steps": ["開始", "完了"]}).json()

    issue = client.post("/api/issues", json={
        "title": "総合テスト",
        "assignee_id": member["id"],
        "workflow_id": wf["id"],
        "workflow_step": 0,
    }).json()

    assert issue["assignee"]["name"] == "担当者A"
    assert issue["workflow"]["steps"] == ["開始", "完了"]
```

---

## 設計の判断まとめ

| 課題 | 採用した方針 | 理由 |
|------|------------|------|
| 認証の重さ | 名前ベースのメンバー管理 | 個人・小チーム向けに認証コストを省く |
| ステップの柔軟性 | JSON配列をTEXT列で保存 | SQLiteに配列型がなく、変換コストも低い |
| 既存UIの維持 | ワークフローをサブステップとして追加 | カンバンの列構造は変えない |
| SQLiteのALTER制限 | テーブル再作成マイグレーション | ADD COLUMNの制約を回避 |
| Pydantic v2の変換 | `@field_validator(mode="before")` | `model_validate`オーバーライドより明確 |

---

## ソースコード

https://github.com/inutaone123-create/Kizuki

---

## まとめ

- **認証なしの担当者管理**は「名前 + カラー」だけで十分ユーザビリティが出る
- **ワークフローをJSON配列で持つ**設計は実装コストが低く、ステップ変更も柔軟
- SQLiteのALTER制限はテーブル再作成で回避できるが、`PRAGMA foreign_keys = OFF/ON` を忘れずに
- Pydantic v2での型変換は `@field_validator(mode="before")` が王道

次のステップとしては、期日管理や担当者フィルターなどを追加していく予定です。

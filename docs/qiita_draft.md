---
title: 【FastAPI + SQLite + Vanilla JSで作る個人用カンバンツール「Kizuki（気づき）」】
tags:
  - Python
  - FastAPI
  - SQLAlchemy
  - JavaScript
  - 個人開発
emoji: 🏯
type: tech
topics: []
published: false
---

## はじめに

「タスク管理ツールを使いたいが、JiraやNotionは機能が多すぎる」「シンプルにカンバンとメモだけほしい」——そんな思いから、個人用カンバンツール **Kizuki（木付き）** を作りました。

Kizukiは、**イシュー管理と作業メモを一体化**したWebアプリです。カンバンボードでイシューを「未着手 / 進行中 / 完了」の3列で管理しながら、各イシューに日付付きのMarkdownメモを残せます。「今日このイシューで何をやったか」を蓄積していくイメージです。

技術スタックは **Python（FastAPI）+ SQLite + HTML/CSS/Vanilla JS** のみ。npmビルド不要、外部CDNだけでドラッグ＆ドロップとMarkdownレンダリングを実現しています。Dev Container一発で動く構成にしたので、環境構築の手間もありません。

## 環境

| 項目 | バージョン |
|------|-----------|
| OS | Ubuntu 22.04 (Dev Container) |
| Python | 3.10 |
| FastAPI | 0.115.6 |
| SQLAlchemy | 2.0.36 |
| SortableJS | 1.15.2（CDN） |
| marked.js | 12.0.0（CDN） |

## 実装概要

### アーキテクチャ

```
ブラウザ（HTML/CSS/JS）
    ↕ REST API（JSON）
FastAPI（Python）
    ↕ ORM
SQLite（data/issuelog.db）
```

フロントエンドは完全にStatic Filesとして配信。SPAフレームワークは使わず、`fetch` API でバックエンドと通信します。

### データモデル

2テーブルのシンプルな設計です。

```
Issue（イシュー）
  id, title, description
  status: todo | in_progress | done
  priority: high | medium | low
  category, tags（カンマ区切り）
  created_at, updated_at

WorkLog（作業メモ）
  id, issue_id（FK）
  content（Markdown）
  logged_at（日付）
  created_at
```

### APIエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues` | 一覧（フィルター対応） |
| POST | `/api/issues` | 作成 |
| GET | `/api/issues/{id}` | 詳細（ログ含む） |
| PUT | `/api/issues/{id}` | 更新 |
| DELETE | `/api/issues/{id}` | 削除 |
| PATCH | `/api/issues/{id}/status` | ステータス更新（カンバン用） |
| GET | `/api/issues/{id}/logs` | ログ一覧 |
| POST | `/api/issues/{id}/logs` | ログ追加 |
| DELETE | `/api/logs/{log_id}` | ログ削除 |

## 実装

### SQLAlchemyモデル（`src/models.py`）

SQLAlchemy 2.0 の `Mapped` 型アノテーションを使ったモデル定義です。`cascade="all, delete-orphan"` でイシュー削除時に関連ログも自動削除されます。

```python
class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    logs: Mapped[list["WorkLog"]] = relationship(
        "WorkLog", back_populates="issue", cascade="all, delete-orphan"
    )


class WorkLog(Base):
    __tablename__ = "work_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    logged_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issue: Mapped["Issue"] = relationship("Issue", back_populates="logs")
```

### FastAPIルーター（`src/routers/issues.py`）

カンバン用の `PATCH /status` エンドポイントがポイントです。ドラッグ＆ドロップ時にステータスだけを更新するため、フルの `PUT` とは別に用意しています。

```python
@router.patch("/{issue_id}/status", response_model=IssueResponse)
def update_issue_status(
    issue_id: int, body: IssueStatusUpdate, db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = body.status
    db.commit()
    db.refresh(issue)
    return issue
```

フィルター対応の一覧取得もシンプルに書けます。

```python
@router.get("", response_model=list[IssueListResponse])
def list_issues(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Issue)
    if status:
        query = query.filter(Issue.status == status)
    if priority:
        query = query.filter(Issue.priority == priority)
    if category:
        query = query.filter(Issue.category == category)
    return query.order_by(Issue.updated_at.desc()).all()
```

### アプリのライフサイクル管理（`src/main.py`）

`@app.on_event("startup")` は非推奨になったため、`lifespan` を使います。

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # 起動時にテーブルを自動作成
    yield

app = FastAPI(title="Kizuki", lifespan=lifespan)
```

### フロントエンド：ドラッグ＆ドロップ（`static/app.js`）

SortableJS でカード間のD&Dを実装。`onEnd` イベントで移動先の列の `data-status` を読み取り、PATCH APIを叩きます。

```javascript
function initDragDrop() {
  STATUS_COLS.forEach(col => {
    const el = document.getElementById(`col-${col}`);
    Sortable.create(el, {
      group: "board",
      animation: 150,
      ghostClass: "sortable-ghost",
      onEnd: async (evt) => {
        const id = Number(evt.item.dataset.id);
        const newStatus = evt.to.dataset.status;
        if (!newStatus) return;
        const issue = state.issues.find(i => i.id === id);
        if (!issue || issue.status === newStatus) return;
        try {
          await api.issues.patch(id, newStatus);
          issue.status = newStatus;
          renderBoard();
        } catch (e) {
          showToast(`エラー: ${e.message}`);
          renderBoard(); // 失敗したら元に戻す
        }
      },
    });
  });
}
```

### Markdownレンダリング（`static/app.js`）

作業ログの表示には marked.js（CDN）を使用。`marked.parse()` で一発変換できます。

```javascript
item.innerHTML = `
  <div class="log-item-header">
    <span class="log-date">📅 ${log.logged_at}</span>
    <button class="btn btn-ghost btn-sm" onclick="deleteLog(${log.id})">削除</button>
  </div>
  <div class="log-content">${marked.parse(log.content)}</div>
`;
```

### テスト：インメモリSQLiteのハマりどころ（`tests/conftest.py`）

pytest でインメモリSQLiteを使う場合、**`StaticPool` を指定しないとテーブルが見えなくなります**。デフォルトだと接続ごとに別DBが作られるためです。

```python
from sqlalchemy.pool import StaticPool

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # ← これがないとINSERTが落城する
)
```

## 動作確認・テスト結果

```
$ python3 -m pytest tests/ -v

tests/test_issues.py::test_create_issue          PASSED
tests/test_issues.py::test_list_issues           PASSED
tests/test_issues.py::test_filter_issues_by_status PASSED
tests/test_issues.py::test_get_issue             PASSED
tests/test_issues.py::test_get_issue_not_found   PASSED
tests/test_issues.py::test_update_issue          PASSED
tests/test_issues.py::test_patch_issue_status    PASSED
tests/test_issues.py::test_delete_issue          PASSED
tests/test_logs.py::test_create_log              PASSED
tests/test_logs.py::test_list_logs               PASSED
tests/test_logs.py::test_create_log_issue_not_found PASSED
tests/test_logs.py::test_delete_log              PASSED
tests/test_logs.py::test_delete_log_not_found    PASSED
tests/test_logs.py::test_delete_issue_cascades_logs PASSED

14 passed in 0.53s
```

## まとめ

- **FastAPI + SQLAlchemy 2.0** の組み合わせは型安全で書きやすい。`Mapped` 型アノテーションで補完も効く
- **SortableJS** はCDN1行で本格的なD&Dが実現できる。グループ設定（`group: "board"`）で列間移動も簡単
- **marked.js** もCDN1行でMarkdownレンダリング。個人ツールレベルならこれで十分
- pytest × SQLite インメモリDB は **`StaticPool` が必須**。ここでハマった
- `@app.on_event("startup")` は非推奨 → **`lifespan` コンテキストマネージャー**を使うべし
- 今後の拡張候補：ユーザー認証、期日・カレンダー表示、PostgreSQL移行、Reactフロントエンド化

## 参考

- [FastAPI 公式ドキュメント](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 — ORM Mapped Classes](https://docs.sqlalchemy.org/en/20/orm/mapper_config.html)
- [SortableJS](https://sortablejs.github.io/Sortable/)
- [marked.js](https://marked.js.org/)

<!-- 公開URL: https://qiita.com/inuta-one/items/5639187fea87fa620c16 -->
<!-- 続編: https://qiita.com/inuta-one/items/c0ee88be2066a366c49b -->
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

「タスク管理ツールを使いたいが、JiraやNotionは機能が多すぎる」「シンプルにカンバンとメモだけほしい」——そんな思いから、個人用カンバンツール **Kizuki（気づき）** を作りました。

Kizukiは、**イシュー管理と作業メモを一体化**したWebアプリです。カンバンボードでイシューを「未着手 / 進行中 / 完了」の3列で管理しながら、各イシューに日付付きのMarkdownメモを残せます。「今日このイシューで何をやったか」を蓄積していくイメージです。

さらに最近、**独立メモ機能**を追加しました。「アイデアをまず書き留めて、あとからタスクに紐付ける」というワークフローに対応しています。メモ画面でどんどん書いて、整理できたらカンバンのタスクと関連付ける——そんな使い方ができます。

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

2テーブルのシンプルな設計です。`WorkLog.issue_id` は nullable で、タスクに依存しない独立メモとしても機能します。

```
Issue（イシュー）
  id, title, description
  status: todo | in_progress | done
  priority: high | medium | low
  category, tags（カンマ区切り）
  created_at, updated_at

WorkLog（作業メモ / 独立メモ）
  id, issue_id（FK, nullable）← タスク未紐付けも可能
  content（Markdown）
  logged_at（日付）
  created_at
```

### APIエンドポイント

**イシュー**

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues` | 一覧（フィルター対応） |
| POST | `/api/issues` | 作成 |
| GET | `/api/issues/{id}` | 詳細（ログ含む） |
| PUT | `/api/issues/{id}` | 更新 |
| DELETE | `/api/issues/{id}` | 削除 |
| PATCH | `/api/issues/{id}/status` | ステータス更新（カンバン用） |

**作業ログ（イシュー紐付き）**

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/issues/{id}/logs` | ログ一覧 |
| POST | `/api/issues/{id}/logs` | ログ追加 |
| DELETE | `/api/logs/{log_id}` | ログ削除 |

**メモ（独立メモ）**

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/memos` | 全メモ一覧（logged_at 降順） |
| POST | `/api/memos` | 新規メモ（issue_id 任意） |
| PUT | `/api/memos/{id}` | メモ更新 |
| DELETE | `/api/memos/{id}` | メモ削除 |
| PATCH | `/api/memos/{id}/issue` | タスク紐付け変更（null で解除） |

## 実装

### SQLAlchemyモデル（`src/models.py`）

SQLAlchemy 2.0 の `Mapped` 型アノテーションを使ったモデル定義です。`WorkLog.issue_id` は `nullable=True` + `ondelete="SET NULL"` にすることで、タスクを削除してもメモが残るようにしています。

```python
class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    # ...

    logs: Mapped[list["WorkLog"]] = relationship(
        "WorkLog",
        back_populates="issue",
        cascade="save-update, merge",  # delete-orphan は外す
        passive_deletes=True,
    )


class WorkLog(Base):
    __tablename__ = "work_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
    )  # ← nullable にしてタスク未紐付けメモに対応
    content: Mapped[str] = mapped_column(Text, nullable=False)
    logged_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issue: Mapped["Issue | None"] = relationship("Issue", back_populates="logs")
```

### SQLite の ON DELETE SET NULL を有効化（`src/database.py`）

SQLite はデフォルトで外部キー制約が**無効**です。`PRAGMA foreign_keys = ON` を接続ごとに実行する必要があります。SQLAlchemy の event listener で対応しました。

```python
from sqlalchemy import create_engine, event

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

これでタスク削除時に `work_logs.issue_id` が自動的に `NULL` になります。

### メモルーター（`src/routers/memos.py`）

タスク紐付けを後から変更できる `PATCH /issue` エンドポイントがポイントです。`issue_id: null` を送ると紐付けを解除できます。

```python
@router.patch("/{memo_id}/issue", response_model=MemoResponse)
def update_memo_issue(
    memo_id: int, body: MemoIssueUpdate, db: Session = Depends(get_db)
):
    log = db.query(WorkLog).filter(WorkLog.id == memo_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Memo not found")

    if body.issue_id is not None:
        issue = db.query(Issue).filter(Issue.id == body.issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

    log.issue_id = body.issue_id  # None なら紐付け解除
    db.commit()
    db.refresh(log)
    return _to_memo_response(log)
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

### フロントエンド：タブ切り替え（`static/app.js`）

カンバンとメモの2画面をタブで切り替えます。URL ハッシュで状態を保持しているので、リロードしても開いていた画面に戻れます。

```javascript
function switchTab(tabName) {
  state.activeTab = tabName;

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.toggle("active", el.id === `tab-${tabName}`);
  });

  if (tabName === "memo") loadMemos();
  location.hash = tabName; // URL ハッシュで状態保持
}
```

### フロントエンド：ドラッグ＆ドロップ（`static/app.js`）

SortableJS でカード間のD&Dを実装。`onEnd` イベントで移動先の列の `data-status` を読み取り、PATCH APIを叩きます。

```javascript
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
```

### テスト：インメモリSQLiteのハマりどころ（`tests/conftest.py`）

pytest でインメモリSQLiteを使う場合の注意点が2つあります。

**① `StaticPool` が必須**

デフォルトだと接続ごとに別DBが作られ、INSERT したデータが見えなくなります。

```python
from sqlalchemy.pool import StaticPool

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # ← これがないとテストが通らない
)
```

**② テスト用エンジンにも PRAGMA foreign_keys=ON が必要**

`ON DELETE SET NULL` をテストするために、テスト用エンジンにも event listener を追加する必要があります。

```python
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### 既存DBのマイグレーション（`scripts/migrate_memo.py`）

SQLite は `ALTER COLUMN` が使えないため、テーブル再作成方式で `issue_id` を nullable に変更しました。

```python
# 1. 新テーブルを nullable issue_id で作成
cur.execute("""
    CREATE TABLE work_logs_new (
        id INTEGER PRIMARY KEY,
        issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
        content TEXT NOT NULL,
        logged_at DATE,
        created_at DATETIME
    )
""")
# 2. 既存データをコピー → 3. 旧テーブルを DROP → 4. リネーム
cur.execute("INSERT INTO work_logs_new SELECT * FROM work_logs")
cur.execute("DROP TABLE work_logs")
cur.execute("ALTER TABLE work_logs_new RENAME TO work_logs")
```

## 動作確認・テスト結果

```
$ python3 -m pytest tests/ -v

tests/test_issues.py::test_create_issue                         PASSED
tests/test_issues.py::test_list_issues                          PASSED
tests/test_issues.py::test_filter_issues_by_status              PASSED
tests/test_issues.py::test_get_issue                            PASSED
tests/test_issues.py::test_get_issue_not_found                  PASSED
tests/test_issues.py::test_update_issue                         PASSED
tests/test_issues.py::test_patch_issue_status                   PASSED
tests/test_issues.py::test_delete_issue                         PASSED
tests/test_logs.py::test_create_log                             PASSED
tests/test_logs.py::test_list_logs                              PASSED
tests/test_logs.py::test_create_log_issue_not_found             PASSED
tests/test_logs.py::test_delete_log                             PASSED
tests/test_logs.py::test_delete_log_not_found                   PASSED
tests/test_logs.py::test_delete_issue_cascades_logs             PASSED
tests/test_memos.py::test_create_memo_standalone                PASSED
tests/test_memos.py::test_create_memo_with_issue                PASSED
tests/test_memos.py::test_create_memo_invalid_issue             PASSED
tests/test_memos.py::test_list_memos                            PASSED
tests/test_memos.py::test_update_memo_content                   PASSED
tests/test_memos.py::test_update_memo_not_found                 PASSED
tests/test_memos.py::test_patch_memo_issue_attach               PASSED
tests/test_memos.py::test_patch_memo_issue_detach               PASSED
tests/test_memos.py::test_delete_memo                           PASSED
tests/test_memos.py::test_delete_memo_not_found                 PASSED
tests/test_memos.py::test_delete_issue_sets_memo_issue_id_null  PASSED

25 passed in 0.59s
```

## まとめ

- **FastAPI + SQLAlchemy 2.0** の組み合わせは型安全で書きやすい。`Mapped` 型アノテーションで補完も効く
- **SortableJS** はCDN1行で本格的なD&Dが実現できる。グループ設定（`group: "board"`）で列間移動も簡単
- **marked.js** もCDN1行でMarkdownレンダリング。個人ツールレベルならこれで十分
- pytest × SQLite インメモリDB は **`StaticPool` が必須**。ここでハマった
- SQLite の **`ON DELETE SET NULL`** は `PRAGMA foreign_keys=ON` がないと動かない。アプリ・テスト両方の engine に event listener が必要
- SQLite の **`ALTER COLUMN` 非対応**はテーブル再作成で乗り越えられる
- `@app.on_event("startup")` は非推奨 → **`lifespan` コンテキストマネージャー**を使うべし
- 今後の拡張候補：ユーザー認証、期日・カレンダー表示、PostgreSQL移行、Reactフロントエンド化

## 参考

- [FastAPI 公式ドキュメント](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 — ORM Mapped Classes](https://docs.sqlalchemy.org/en/20/orm/mapper_config.html)
- [SortableJS](https://sortablejs.github.io/Sortable/)
- [marked.js](https://marked.js.org/)

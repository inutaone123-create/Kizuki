<!-- 公開URL: https://qiita.com/inuta-one/items/c0ee88be2066a366c49b -->
---
title: 【Kizuki 機能追加】「メモを先に書いてあとからタスクに紐付ける」を FastAPI + SQLite で実現した
tags:
  - Python
  - FastAPI
  - SQLAlchemy
  - SQLite
  - 個人開発
emoji: 📝
type: tech
topics: []
published: false
---

## はじめに

以前の記事（https://qiita.com/inuta-one/items/5639187fea87fa620c16）で、個人用カンバンツール **Kizuki（気づき）** を FastAPI + SQLite + Vanilla JS で作りました。

今回は「メモを先に書いて、あとからタスクに紐付けたい」という要望に応えて、**独立メモ機能**を追加しました。

### 課題

元の設計では `WorkLog.issue_id` が `NOT NULL` で、**タスクを開かないとメモが書けない**状態でした。

```
（旧）WorkLog.issue_id: NOT NULL  ← タスクが先に必要
```

アイデアや気づきはタスクより先に生まれることも多い。そこで `issue_id` を nullable にして、**タスク未紐付けのメモ**を独立して管理できるようにしました。

```
（新）WorkLog.issue_id: nullable  ← メモが先でも OK、あとから紐付け可能
```

## 変更のポイント

### 1. モデルの nullable 化

```python
# src/models.py

# 変更前
issue_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("issues.id"), nullable=False
)

# 変更後
issue_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
)
```

cascade も `delete-orphan` を外しました。タスクを削除してもメモは残してほしいためです。

```python
# 変更前
logs: Mapped[list["WorkLog"]] = relationship(
    "WorkLog", back_populates="issue", cascade="all, delete-orphan"
)

# 変更後
logs: Mapped[list["WorkLog"]] = relationship(
    "WorkLog",
    back_populates="issue",
    cascade="save-update, merge",  # delete-orphan を外す
    passive_deletes=True,
)
```

### 2. SQLite の ON DELETE SET NULL を有効化

ここが最大のハマりどころでした。

**SQLite は `PRAGMA foreign_keys = ON` を明示しないと外部キー制約が無効です。** `ondelete="SET NULL"` を設定しても、pragma がなければタスク削除時に `issue_id` が NULL になりません。

SQLAlchemy の event listener で接続のたびに設定します。

```python
# src/database.py
from sqlalchemy import create_engine, event

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

**テスト用エンジンにも同じ設定が必要です。** 忘れると `test_delete_issue_sets_memo_issue_id_null` のようなテストが通りません。

```python
# tests/conftest.py
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### 3. SQLite の ALTER COLUMN 非対応をテーブル再作成で乗り越える

SQLite は `ALTER COLUMN` をサポートしていません。既存DBの `issue_id` を nullable に変更するには、**テーブルを再作成**するしかありません。

```python
# scripts/migrate_memo.py

# 1. nullable な新テーブルを作成
cur.execute("""
    CREATE TABLE work_logs_new (
        id INTEGER PRIMARY KEY,
        issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
        content TEXT NOT NULL,
        logged_at DATE,
        created_at DATETIME
    )
""")

# 2. 既存データをコピー
cur.execute("INSERT INTO work_logs_new SELECT * FROM work_logs")

# 3. 旧テーブルを削除してリネーム
cur.execute("DROP TABLE work_logs")
cur.execute("ALTER TABLE work_logs_new RENAME TO work_logs")
```

実行は1コマンドです：

```bash
python3 scripts/migrate_memo.py
```

### 4. 新規メモ API

タスク紐付けの変更だけを行う `PATCH /issue` エンドポイントがポイントです。`issue_id: null` で紐付けを解除できます。

```python
# src/routers/memos.py

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

    log.issue_id = body.issue_id  # None なら解除
    db.commit()
    db.refresh(log)
    return _to_memo_response(log)
```

## テスト結果

```
$ python3 -m pytest tests/ -v

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

- **`issue_id` の nullable 化**で「メモ先行・タスク後付け」のワークフローが実現できた
- SQLite の **`ON DELETE SET NULL`** は `PRAGMA foreign_keys=ON` が必須。アプリ・テスト両方の engine に event listener を追加する
- SQLite の **`ALTER COLUMN` 非対応**はテーブル再作成スクリプトで対応できる
- cascade から **`delete-orphan` を外す**ことで、タスク削除後もメモを残せる

## ソースコード

https://github.com/inutaone123-create/Kizuki

## 参考

- [SQLAlchemy — Working with ORM Related Objects](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
- [SQLite — Foreign Key Support](https://www.sqlite.org/foreignkeys.html)
- 前回の記事: https://qiita.com/inuta-one/items/5639187fea87fa620c16

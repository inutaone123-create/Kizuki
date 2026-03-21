<!-- 公開URL: https://qiita.com/inuta-one/private/1750b0d0ba55f000eff2 -->
---
title: 個人カンバンツールに「日報の後日編集・提出・クリップボードコピー」を追加した話
tags:
  - Python
  - FastAPI
  - SQLite
  - 個人開発
  - JavaScript
emoji: 📝
type: tech
topics: []
published: false
---

# 個人カンバンツールに「日報の後日編集・提出・クリップボードコピー」を追加した話

## はじめに

前回の記事（[第7弾: タスク依存関係・AIワークフロー自動提案](https://qiita.com/inuta-one/items/1588fb1a9e84eb66e4c3)）で、Kizuki にタスクのブロッキング管理とAIによるワークフロー提案を追加しました。

今回は「使いながら気づいた不満」を解消する改善回です。

> 「日報を生成したあと、内容を確認してから提出したい。でも今の実装だと生成した瞬間しか編集できない……」

また、作業ログをタスク詳細から確認はできるのに編集できないという問題も同時に修正しました。

今回追加・修正した機能：

1. **日報の後日編集** — 生成後に保存し、後日開いて内容を修正できる
2. **提出ワークフロー** — 「下書き → 提出済 → 下書きに戻す」のサイクル
3. **クリップボードコピー** — Markdown 形式 / テキスト形式を選んでコピー
4. **作業ログの編集** — タスク詳細から既存ログをその場で編集

---

## 設計の判断

### 「コピー」と「提出」を分けた理由

最初の設計案では「提出ボタンを押したらフォーマット選択 → コピー＋提出済みに変更」という一体化案を考えていました。

やめた理由：

- **コピーだけしたい**（上司への送信は後回しにしたい）
- **提出済みにしたいが今は手元にコピー不要**（すでに別の手段で送信済み）

「コピー」と「提出」は独立した行為なので、ボタンを分けることにしました。

```
📋 Markdownでコピー  ← 何度でも押せる
📄 テキストでコピー  ← 何度でも押せる
✅ 提出              ← ステータスを「提出済」に変更（編集ロック）
↩️ 下書きに戻す     ← 提出済み状態のみ表示、取り消し可能
```

### 「提出取り消し（下書きに戻す）」を設けた理由

「提出済みにしたら戻せない」という設計も考えましたが、個人ツールで厳格なロックは不便なだけです。

> 「送った内容を修正したくなることは普通にある」

提出は「完成マーク」程度の意味合いなので、いつでも下書きに戻せる設計にしました。

### 既存 DB への安全なマイグレーション

`Report` テーブルに `status` / `updated_at` / `submitted_at` を追加する際、Alembic を使わずに SQLite の `ALTER TABLE` で対応しました。

SQLAlchemy の `create_all` は既存テーブルを変更しないため、アプリ起動時に専用のマイグレーション関数を呼び出す方式にしています。

```python
def _migrate_reports_table():
    """reports テーブルに新カラムを追加する（既存DBへの安全なマイグレーション）."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(
            text("PRAGMA table_info(reports)")
        )}
        migrations = [
            ("status",       "ALTER TABLE reports ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'"),
            ("updated_at",   "ALTER TABLE reports ADD COLUMN updated_at DATETIME DEFAULT '1970-01-01 00:00:00'"),
            ("submitted_at", "ALTER TABLE reports ADD COLUMN submitted_at DATETIME"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(text(sql))
        conn.commit()
```

`PRAGMA table_info` で既存カラムを確認してから `ALTER TABLE` する「冪等マイグレーション」です。何度起動しても安全に動きます。

---

## 実装

### バックエンド：Report モデルの拡張

```python
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Integer, default=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
        server_default="1970-01-01 00:00:00"
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

`server_default` を付けておくと `ALTER TABLE ADD COLUMN` で追加した際にも既存レコードが NULL にならずに済みます。

### 編集エンドポイント（提出済みは 409）

```python
@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(report_id: int, body: ReportUpdate, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == "submitted":
        raise HTTPException(status_code=409, detail="提出済みレポートは編集できません")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(report, key, value)
    report.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report
```

提出済みへの編集を 409 Conflict で拒否し、フロントエンドでもボタンを非表示にする「二重ガード」方式です。

### 提出・下書きに戻すエンドポイント

```python
@router.post("/{report_id}/submit", response_model=ReportResponse)
def submit_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "submitted":
        report.status = "submitted"
        report.submitted_at = datetime.utcnow()
        db.commit()
        db.refresh(report)
    return report  # 既に提出済みでも 200 を返す（冪等）


@router.post("/{report_id}/revert", response_model=ReportResponse)
def revert_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "draft":
        report.status = "draft"
        report.submitted_at = None
        db.commit()
        db.refresh(report)
    return report  # 既に下書きでも 200 を返す（冪等）
```

submit / revert ともに冪等設計（同じ状態で呼ばれても 200）にしています。

### フロントエンド：クリップボードコピーの実装

Markdown → テキスト変換は正規表現でシンプルに処理しています。

```javascript
async function copyReport(format) {
  if (!_currentReport) return;
  let text = _currentReport.content;
  if (format === "text") {
    text = text
      .replace(/^#{1,6}\s+/gm, "")        // 見出し記号を除去
      .replace(/\*\*(.+?)\*\*/g, "$1")     // 太字
      .replace(/\*(.+?)\*/g, "$1")         // イタリック
      .replace(/`(.+?)`/g, "$1")           // インラインコード
      .replace(/^\s*[-*+]\s+/gm, "・")     // リストを「・」に変換
      .replace(/^\s*\d+\.\s+/gm, "")      // 番号リストの番号を除去
      .trim();
  }
  try {
    await navigator.clipboard.writeText(text);
    showToast(format === "markdown" ? "Markdownでコピーしました" : "テキストでコピーしました");
  } catch {
    showToast("コピーに失敗しました（ブラウザの権限を確認してください）");
  }
}
```

### ハマりどころ：作業ログとメモが同じテーブル

タスク詳細から作業ログを編集できるようにしようとしたとき、「作業ログ」と「メモ」が同じ `work_logs` テーブルを使っていることに気づきました。

当初は「紐付きメモ」と「作業ログ」を別セクションで表示する実装をしましたが、同じデータが二重表示されてしまいました。

```
タスク詳細モーダル
├── 紐付きメモセクション（GET /api/memos?issue_id=N）← 同じデータ
└── 作業ログセクション（GET /api/issues/{id}/logs）  ← 同じデータ
```

解決策は「紐付きメモセクションを廃止し、作業ログセクションに編集ボタンを追加」する方向での統合でした。シンプルなほうが正解でした。

また、編集モーダルを開くために `state.memos` からデータを探す実装にしていたのですが、メモタブを一度も開いていないセッションでは `state.memos` が空のため、ボタンを押しても何も起きないバグがありました。

```javascript
// 修正前：state.memos に見つからないと黙って return
async function openEditMemoModal(memoId) {
  const memo = state.memos.find(m => m.id === memoId);
  if (!memo) return;  // ← ここで黙って終了していた
  ...
}

// 修正後：見つからなければ API から直接取得
async function openEditMemoModal(memoId) {
  let memo = state.memos.find(m => m.id === memoId);
  if (!memo) {
    try {
      memo = await api.memos.get(memoId);  // GET /api/memos/{id}
      state.memos.push(memo);
    } catch {
      return;
    }
  }
  ...
}
```

「キャッシュにあれば使い、なければAPIから取得」というフォールバックパターンで解決しました。

---

## テスト結果

```
80 passed in 2.31s
```

今回追加したテスト（抜粋）：

```python
def test_generate_report_has_draft_status(client):
    """生成直後のレポートは status=draft である."""
    data = generate_report(client, "daily", "2026-03-04")
    assert data["status"] == "draft"

def test_update_submitted_report_returns_409(client):
    """提出済みレポートへの PATCH は 409 を返す."""
    created = generate_report(client, "daily", "2026-03-04")
    client.post(f"/api/reports/{created['id']}/submit")
    res = client.patch(f"/api/reports/{created['id']}", json={"content": "変更"})
    assert res.status_code == 409

def test_revert_report_allows_edit(client):
    """下書きに戻したレポートは PATCH で編集できる."""
    created = generate_report(client, "daily", "2026-03-04")
    client.post(f"/api/reports/{created['id']}/submit")
    client.post(f"/api/reports/{created['id']}/revert")
    res = client.patch(f"/api/reports/{created['id']}", json={"content": "戻して編集"})
    assert res.status_code == 200
```

---

## ソースコード

https://github.com/inutaone123-create/Kizuki

---

## まとめ

- **「コピー」と「提出」は分ける** — 一体化すると「片方だけやりたい」ときに不便。独立した操作は独立したボタンにする
- **提出は取り消せるようにする** — 個人ツールで厳格なロックは不便なだけ。ステータスは双方向に変えられる設計が使いやすい
- **冪等マイグレーション** — `PRAGMA table_info` でカラムの存在確認 → なければ `ALTER TABLE` のパターンで Alembic なしでも安全に運用できる
- **キャッシュにないデータは API から取得** — フロントエンドのキャッシュ（`state.memos`）に依存しすぎると、操作順によってボタンが動かなくなるバグが起きる。APIフォールバックを持たせると堅牢になる
- **同じテーブルを二箇所で表示しない** — 「紐付きメモ」と「作業ログ」が同じテーブルと気づいてから統合。シンプルにするほど問題が減る

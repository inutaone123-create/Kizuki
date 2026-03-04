---
title: 【Kizuki 機能追加】メモから日報・週報・月報を自動生成。AI連携 + テンプレートフォールバック設計
tags:
  - Python
  - FastAPI
  - JavaScript
  - 個人開発
  - AI
emoji: 📊
type: tech
topics: []
published: false
---

## はじめに

前回の記事（[【Kizuki 機能追加】ワークフロー横断ビューをバックエンド変更ゼロ・Vanilla JS だけで実装した](https://qiita.com/inuta-one/items/1f167bde2159ac53a030)）では、個人用カンバンツール「Kizuki」にワークフロー横断ビューを追加しました。

今回は「**メモタブに蓄積した作業ログを元に、日報・週報・月報を自動生成する機能**」を追加します。

ポイントは **「AI設定ありならAI生成・なければテンプレート生成」** というフォールバック設計です。
Groq / Ollama / OpenAI など **OpenAI互換APIであればどのサービスでも使える**ようにし、AI未設定でも動作するようにしました。

---

## 追加機能の概要

- **📊 レポートタブ** — 日報 / 週報 / 月報を選んで日付を指定し、⚡ 生成ボタン1つで作成
- **🤖 AI生成モード** — OpenAI互換API（Groq / OpenRouter / Ollama etc.）を使ってメモをもとに高品質な文章を生成
- **📋 テンプレートモード** — AI設定なしでも動作するフォールバック。メモ内容を雛形に挿入
- **⚙ AI設定UI** — 設定タブからBase URL / API Key / モデル名を設定。api_key はレスポンスに含めずセキュアに管理

---

## 背景・設計の判断

### なぜ OpenAI互換 API を選んだか

「特定のサービスに依存したくない」が最初の判断でした。

Groq（無料枠あり・高速）、Ollama（ローカル・無料）、OpenAI などをユーザーが選べるよう、
`base_url + api_key + model` の3つだけを設定すれば動く設計にしました。

### なぜフォールバックをサイレントにしたか

AI呼び出しが失敗しても「エラー画面を見せない」設計にしています。

```python
if use_ai:
    try:
        content = await call_ai_api(...)
        return title, content, start, end, True
    except Exception:
        pass  # サイレントにテンプレートへフォールバック

# テンプレートフォールバック
content = generate_daily_template(start, memos)
return title, content, start, end, False
```

APIキーの期限切れ・ネットワーク障害・モデル名ミスなど、失敗パターンは多岐にわたります。
「テンプレートでとりあえず動く」を優先し、ユーザーにエラーを見せない判断をしました。

### api_key をレスポンスに含めない

AI設定の GET エンドポイントは `api_key` をそのまま返さず、`has_api_key: bool` のみ返します。

```python
class AISettingsResponse(BaseModel):
    base_url: str | None
    model: str | None
    has_api_key: bool        # api_key は絶対に返さない
    updated_at: datetime
```

フロントエンドで「設定済みかどうか」を表示したいだけなので、bool で十分です。

---

## 実装

### Step 1: DBモデル追加

`src/models.py` の末尾に2テーブルを追加しました。
SQLAlchemy の `Base.metadata.create_all()` が自動でテーブルを作るため、
**新規起動時はマイグレーション不要**です。

```python
class AISettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_type: Mapped[str] = mapped_column(String(10), nullable=False)  # daily/weekly/monthly
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Integer, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Step 2: 期間計算ロジック

日報・週報・月報それぞれで「対象日 → 期間」の計算が必要です。

```python
def get_weekly_range(target: date) -> tuple[date, date]:
    """週報の期間（月曜〜日曜）を返す."""
    monday = target - timedelta(days=target.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_monthly_range(target: date) -> tuple[date, date]:
    """月報の期間（月初〜月末）を返す."""
    first = target.replace(day=1)
    if target.month == 12:
        last = target.replace(year=target.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last = target.replace(month=target.month + 1, day=1) - timedelta(days=1)
    return first, last
```

週報は `weekday()` で月曜起算のオフセットを計算。
月報は12月の年またぎに注意が必要です（`month + 1` が13にならないよう条件分岐）。

### Step 3: AI API 呼び出し（httpx非同期）

```python
async def call_ai_api(
    base_url: str, api_key: str, model: str, system: str, user: str
) -> str:
    """OpenAI互換APIを呼び出す."""
    import httpx

    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(url, json=payload, headers=headers)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"]
```

`httpx` はすでに `requirements.txt` に含まれており（FastAPI の非同期テスト用）、追加ライブラリ不要でした。

### Step 4: レポート生成エンドポイント（async def）

AI呼び出しに `await` を使うため、FastAPI のエンドポイントは `async def` が必須です。

```python
@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report_endpoint(
    body: ReportGenerateRequest, db: Session = Depends(get_db)
):
    """レポートを生成してDBに保存する."""
    title, content, start, end, is_ai = await generate_report(
        db, body.report_type, body.target_date
    )
    report = Report(
        report_type=body.report_type,
        period_start=start,
        period_end=end,
        title=title,
        content=content,
        is_ai_generated=is_ai,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
```

### Step 5: AI設定の upsert（id=1固定）

設定は全体で1件だけ存在すれば良いので、`id=1` に固定した upsert パターンにしました。

```python
@router.put("/ai", response_model=AISettingsResponse)
def update_ai_settings(body: AISettingsUpdate, db: Session = Depends(get_db)):
    cfg = db.query(AISettings).filter(AISettings.id == 1).first()
    if cfg is None:
        cfg = AISettings(id=1)
        db.add(cfg)

    if body.base_url is not None:
        cfg.base_url = body.base_url or None
    if body.model is not None:
        cfg.model = body.model or None
    # api_key: 空文字でなければ更新（空文字は「変更なし」として扱う）
    if body.api_key:
        cfg.api_key = body.api_key

    cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    return AISettingsResponse(
        base_url=cfg.base_url,
        model=cfg.model,
        has_api_key=bool(cfg.api_key),
        updated_at=cfg.updated_at,
    )
```

`api_key` を空文字で送った場合は「変更なし」として扱い、既存のキーを維持します。
これにより「Base URL とモデル名だけ変更して api_key はそのまま」という操作が可能になります。

### Step 6: フロントエンド（Vanilla JS）

生成中インジケーターは CSS の `@keyframes` + `display: flex / none` の切り替えで実装しました。

```javascript
async function generateReport() {
  const targetDate = document.getElementById("report-target-date").value;
  if (!targetDate) { showToast("対象日を選択してください"); return; }

  const generating = document.getElementById("report-generating");
  generating.style.display = "flex";
  document.getElementById("btn-generate-report").disabled = true;

  try {
    const report = await api.reports.generate({
      report_type: state.reportType,
      target_date: targetDate,
    });
    state.reports.unshift(report);
    renderReportList();
    showToast(`${REPORT_TYPE_LABEL[state.reportType]}を生成しました`);
  } catch (e) {
    showToast(`生成に失敗: ${e.message}`);
  } finally {
    generating.style.display = "none";
    document.getElementById("btn-generate-report").disabled = false;
  }
}
```

レポート詳細の表示は、すでに導入済みの `marked.js` で Markdown → HTML に変換しています。

```javascript
document.getElementById("report-modal-content").innerHTML =
  typeof marked !== "undefined"
    ? marked.parse(report.content)
    : `<pre>${escHtml(report.content)}</pre>`;
```

`marked` が未定義の場合（CDN読み込み失敗時）は `<pre>` タグでフォールバックする安全策も入れました。

---

## ハマりどころ

### 月末計算の罠（12月→1月の年またぎ）

```python
# ❌ これは 13 月になって ValueError
last = target.replace(month=target.month + 1, day=1) - timedelta(days=1)

# ✅ 12月は年をまたぐ
if target.month == 12:
    last = target.replace(year=target.year + 1, month=1, day=1) - timedelta(days=1)
else:
    last = target.replace(month=target.month + 1, day=1) - timedelta(days=1)
```

テストで2月（28日/29日）と12月の境界を確認しました。

### FastAPI の `async def` と `Session`

`generate_report_endpoint` は `async def` にする必要があります（内部で `await` を使うため）。
しかし SQLAlchemy の同期セッション（`Session`）は `async def` の中でそのまま使えます。
**httpx の呼び出しだけが async で、DB操作は同期のまま** — この組み合わせで問題なく動作しました。

### api_key の扱い

空文字（`""`）と `None` と「省略」は別物です。
- `None` → 省略（Pydantic のデフォルト）
- `""` → フォームをクリアして送信（「変更なし」として扱いたい）
- `"sk-xxx"` → 新しいキー

この区別を `if body.api_key:` の1行で処理できます（空文字は falsy）。

---

## テスト結果

```
55 passed in 1.56s
```

新規追加テスト（16件）の内訳：

| テスト | 内容 |
|--------|------|
| AI設定デフォルト取得 | `has_api_key=False` が返る |
| AI設定保存 | `api_key` がレスポンスに含まれない |
| 空文字 api_key は無視 | 既存キーを維持 |
| 日報生成（期間計算） | `period_start == period_end` |
| 週報生成（月曜起算） | `2026-03-04` → `03-02〜03-08` |
| 月報生成（月末計算） | `2026-03-15` → `03-01〜03-31` |
| 2月の月末（非うるう年） | `02-01〜02-28` |
| メモありの日報 | メモ内容が content に含まれる |
| 不正な report_type | 422 が返る |
| 一覧は content を含まない | 軽量版 |
| 詳細は content を含む | フル版 |
| 削除後は 404 | 正常 |

---

## ソースコード

https://github.com/inutaone123-create/Kizuki

---

## まとめ

- **OpenAI互換 API 設計**で Groq / Ollama / OpenAI などを選択できるようにした
- **サイレントフォールバック**（AI失敗 → テンプレート）でユーザーにエラーを見せない設計
- **api_key はレスポンスに含めない**（`has_api_key: bool` で代替）セキュアな設計
- `async def` エンドポイント × 同期 SQLAlchemy Session の組み合わせは問題なく動く
- 月末計算は12月の年またぎに注意が必要

次は Kizuki を使いながら気になった機能を追加していく予定です。

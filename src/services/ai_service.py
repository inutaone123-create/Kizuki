"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from datetime import date, timedelta
from sqlalchemy.orm import Session

from src.models import AISettings, WorkLog

# ─── プロンプト定数 ────────────────────────────────────────────────────────────

_SYSTEM_DAILY = (
    "あなたは日報を作成するアシスタントです。"
    "ユーザーが提供するメモ・作業ログを元に、簡潔でわかりやすい日報を日本語 Markdown 形式で作成してください。"
    "## 本日の作業, ## 成果, ## 課題・懸念, ## 翌日の予定 のセクションを含めてください。"
)

_SYSTEM_WEEKLY = (
    "あなたは週報を作成するアシスタントです。"
    "ユーザーが提供するメモ・作業ログを元に、週の振り返りをまとめた週報を日本語 Markdown 形式で作成してください。"
    "## 今週の作業サマリー, ## 主な成果, ## 課題・学び, ## 来週の計画 のセクションを含めてください。"
)

_SYSTEM_MONTHLY = (
    "あなたは月報を作成するアシスタントです。"
    "ユーザーが提供するメモ・作業ログを元に、月の活動をまとめた月報を日本語 Markdown 形式で作成してください。"
    "## 今月の作業サマリー, ## 主な成果・マイルストーン, ## 課題・改善点, ## 来月の目標 のセクションを含めてください。"
)


# ─── 期間計算 ─────────────────────────────────────────────────────────────────


def get_daily_range(target: date) -> tuple[date, date]:
    """日報の期間（対象日のみ）を返す.

    Args:
        target: 対象日

    Returns:
        (start, end) のタプル（同日）
    """
    return target, target


def get_weekly_range(target: date) -> tuple[date, date]:
    """週報の期間（対象日を含む週の月曜〜日曜）を返す.

    Args:
        target: 週内の任意の日付

    Returns:
        (月曜日, 日曜日) のタプル
    """
    monday = target - timedelta(days=target.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_monthly_range(target: date) -> tuple[date, date]:
    """月報の期間（対象日を含む月の 1 日〜末日）を返す.

    Args:
        target: 月内の任意の日付

    Returns:
        (月初, 月末) のタプル
    """
    first = target.replace(day=1)
    if target.month == 12:
        last = target.replace(year=target.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last = target.replace(month=target.month + 1, day=1) - timedelta(days=1)
    return first, last


# ─── メモ取得 ─────────────────────────────────────────────────────────────────


def fetch_memos_for_period(db: Session, start: date, end: date) -> list[WorkLog]:
    """指定期間のメモ（WorkLog）を取得する.

    Args:
        db: DBセッション
        start: 期間開始日
        end: 期間終了日

    Returns:
        期間内の WorkLog リスト（logged_at 昇順）
    """
    return (
        db.query(WorkLog)
        .filter(WorkLog.logged_at >= start, WorkLog.logged_at <= end)
        .order_by(WorkLog.logged_at.asc(), WorkLog.created_at.asc())
        .all()
    )


# ─── テンプレート生成 ─────────────────────────────────────────────────────────


def _format_memos(memos: list[WorkLog]) -> str:
    """メモリストを文字列に変換する."""
    if not memos:
        return "（メモなし）"
    lines = []
    for m in memos:
        lines.append(f"### {m.logged_at}\n{m.content}")
    return "\n\n".join(lines)


def generate_daily_template(start: date, memos: list[WorkLog]) -> str:
    """日報テンプレートを生成する（AI不使用時フォールバック）.

    Args:
        start: 対象日
        memos: 期間内のメモリスト

    Returns:
        Markdown形式の日報
    """
    memo_text = _format_memos(memos)
    return (
        f"## 本日の作業\n\n{memo_text}\n\n"
        "## 成果\n\n- （記入してください）\n\n"
        "## 課題・懸念\n\n- （記入してください）\n\n"
        "## 翌日の予定\n\n- （記入してください）"
    )


def generate_weekly_template(start: date, end: date, memos: list[WorkLog]) -> str:
    """週報テンプレートを生成する（AI不使用時フォールバック）.

    Args:
        start: 週開始日（月曜）
        end: 週終了日（日曜）
        memos: 期間内のメモリスト

    Returns:
        Markdown形式の週報
    """
    memo_text = _format_memos(memos)
    return (
        f"## 今週の作業サマリー（{start} 〜 {end}）\n\n{memo_text}\n\n"
        "## 主な成果\n\n- （記入してください）\n\n"
        "## 課題・学び\n\n- （記入してください）\n\n"
        "## 来週の計画\n\n- （記入してください）"
    )


def generate_monthly_template(start: date, end: date, memos: list[WorkLog]) -> str:
    """月報テンプレートを生成する（AI不使用時フォールバック）.

    Args:
        start: 月初日
        end: 月末日
        memos: 期間内のメモリスト

    Returns:
        Markdown形式の月報
    """
    memo_text = _format_memos(memos)
    return (
        f"## 今月の作業サマリー（{start} 〜 {end}）\n\n{memo_text}\n\n"
        "## 主な成果・マイルストーン\n\n- （記入してください）\n\n"
        "## 課題・改善点\n\n- （記入してください）\n\n"
        "## 来月の目標\n\n- （記入してください）"
    )


# ─── AI API 呼び出し ──────────────────────────────────────────────────────────


async def call_ai_api(
    base_url: str, api_key: str, model: str, system: str, user: str
) -> str:
    """OpenAI互換APIを呼び出してテキストを生成する.

    Args:
        base_url: APIのベースURL（末尾スラッシュなし）
        api_key: APIキー
        model: モデル名
        system: システムプロンプト
        user: ユーザープロンプト

    Returns:
        生成されたテキスト

    Raises:
        Exception: API呼び出しに失敗した場合
    """
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


# ─── メインエントリ ───────────────────────────────────────────────────────────


async def generate_report(
    db: Session, report_type: str, target_date: date
) -> tuple[str, str, date, date, bool]:
    """レポートを生成する.

    AI設定がある場合はAIを使用し、なければテンプレートにフォールバックする。

    Args:
        db: DBセッション
        report_type: "daily" | "weekly" | "monthly"
        target_date: 対象日

    Returns:
        (title, content, period_start, period_end, is_ai_generated) のタプル
    """
    # 期間計算
    if report_type == "daily":
        start, end = get_daily_range(target_date)
        title = f"日報 {start}"
        system_prompt = _SYSTEM_DAILY
    elif report_type == "weekly":
        start, end = get_weekly_range(target_date)
        title = f"週報 {start} 〜 {end}"
        system_prompt = _SYSTEM_WEEKLY
    else:
        start, end = get_monthly_range(target_date)
        title = f"月報 {start.strftime('%Y年%m月')}"
        system_prompt = _SYSTEM_MONTHLY

    # メモ取得
    memos = fetch_memos_for_period(db, start, end)

    # AI設定を読み込む
    ai_cfg = db.query(AISettings).filter(AISettings.id == 1).first()
    use_ai = (
        ai_cfg is not None
        and ai_cfg.base_url
        and ai_cfg.api_key
        and ai_cfg.model
    )

    if use_ai:
        try:
            memo_text = _format_memos(memos)
            user_prompt = (
                f"以下のメモ・作業ログを元にレポートを作成してください。\n\n{memo_text}"
            )
            content = await call_ai_api(
                ai_cfg.base_url, ai_cfg.api_key, ai_cfg.model,
                system_prompt, user_prompt
            )
            return title, content, start, end, True
        except Exception:
            pass  # AI失敗時はテンプレートにフォールバック

    # テンプレートフォールバック
    if report_type == "daily":
        content = generate_daily_template(start, memos)
    elif report_type == "weekly":
        content = generate_weekly_template(start, end, memos)
    else:
        content = generate_monthly_template(start, end, memos)

    return title, content, start, end, False


# ─── ワークフロー提案 ──────────────────────────────────────────────────────────

_SYSTEM_SUGGEST_WORKFLOW = (
    "あなたはプロジェクト管理のエキスパートです。"
    "ユーザーが提供するタスク一覧を分析し、最適なワークフローのステップを提案してください。"
    "ステップ名のみをJSON配列で返してください。例: [\"設計\", \"実装\", \"レビュー\", \"完了\"]"
    "ステップ数は3〜6個が適切です。余分な説明文は不要です。JSON配列のみを返してください。"
)

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


async def suggest_workflow(
    db: Session, category: str | None = None
) -> dict:
    """既存タスクを分析してワークフローを提案する.

    Args:
        db: DBセッション
        category: フィルタリングするカテゴリ（任意）

    Returns:
        suggested_name: 提案ワークフロー名
        suggested_steps: 提案ステップリスト
        reason: 提案理由
        is_ai_generated: AI生成フラグ
    """
    from src.models import Issue

    # タスク情報を収集
    query = db.query(Issue)
    if category:
        query = query.filter(Issue.category == category)
    issues = query.order_by(Issue.updated_at.desc()).limit(30).all()

    # AI設定を確認
    ai_cfg = db.query(AISettings).filter(AISettings.id == 1).first()
    use_ai = (
        ai_cfg is not None
        and ai_cfg.base_url
        and ai_cfg.api_key
        and ai_cfg.model
    )

    if use_ai and issues:
        try:
            import json as _json
            # タスク情報をプロンプト用に整形
            task_summary = "\n".join(
                f"- [{i.status}] {i.title}"
                + (f" (カテゴリ: {i.category})" if i.category else "")
                for i in issues
            )
            user_prompt = (
                f"以下のタスク一覧を分析して、最適なワークフローのステップをJSON配列で提案してください。\n\n{task_summary}"
            )
            raw = await call_ai_api(
                ai_cfg.base_url, ai_cfg.api_key, ai_cfg.model,
                _SYSTEM_SUGGEST_WORKFLOW, user_prompt,
            )
            # JSON配列を抽出
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            steps = _json.loads(raw.strip())
            if isinstance(steps, list) and all(isinstance(s, str) for s in steps):
                name = "AI提案フロー" + (f"（{category}）" if category else "")
                return {
                    "suggested_name": name,
                    "suggested_steps": steps,
                    "reason": "現在のタスクパターンを分析して提案しました。",
                    "is_ai_generated": True,
                }
        except Exception:
            pass  # フォールバックへ

    # フォールバック: カテゴリに応じてテンプレートを選択
    if category and any(kw in category for kw in ["承認", "申請", "審査"]):
        suggestion = _FALLBACK_WORKFLOWS[2]
    elif issues and len(issues) > 10:
        suggestion = _FALLBACK_WORKFLOWS[0]
    else:
        suggestion = _FALLBACK_WORKFLOWS[1]

    return {
        "suggested_name": suggestion["name"],
        "suggested_steps": suggestion["steps"],
        "reason": suggestion["reason"],
        "is_ai_generated": False,
    }

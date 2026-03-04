"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Report
from src.schemas import ReportGenerateRequest, ReportListItem, ReportResponse
from src.services.ai_service import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportListItem])
def list_reports(db: Session = Depends(get_db)):
    """レポート一覧を取得する（content を含まない軽量版、新しい順）.

    Args:
        db: DBセッション

    Returns:
        ReportListItem のリスト
    """
    return (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report_endpoint(
    body: ReportGenerateRequest, db: Session = Depends(get_db)
):
    """レポートを生成してDBに保存する.

    AI設定がある場合はAI生成、なければテンプレートでフォールバック。

    Args:
        body: レポート種別と対象日
        db: DBセッション

    Returns:
        生成・保存されたレポート
    """
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


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """レポート詳細を取得する（content を含む）.

    Args:
        report_id: レポートID
        db: DBセッション

    Returns:
        ReportResponse

    Raises:
        HTTPException: レポートが存在しない場合
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    """レポートを削除する.

    Args:
        report_id: レポートID
        db: DBセッション

    Raises:
        HTTPException: レポートが存在しない場合
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()

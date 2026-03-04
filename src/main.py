"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.database import init_db
from src.routers import issues, logs, memos
from src.routers import members, workflows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリのライフサイクル管理 - 起動時にDBを初期化する."""
    init_db()
    yield


app = FastAPI(
    title="Kizuki",
    description="イシュー管理 × 作業メモ カンバンツール",
    lifespan=lifespan,
)

app.include_router(issues.router)
app.include_router(logs.router)
app.include_router(memos.router)
app.include_router(members.router)
app.include_router(workflows.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """ルートエンドポイント - フロントエンドを返す."""
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント.

    Returns:
        サービス稼働状態
    """
    return {"status": "ok", "service": "Kizuki"}

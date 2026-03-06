"""
Kizuki - イシュー管理 × 作業メモ

Personal kanban tool integrating issue management and work logs.

This implementation: 2026
License: MIT
"""

import multiprocessing
import os
import sys


def main():
    """PyInstaller 用エントリーポイント - uvicorn で FastAPI を起動する.

    Args:
        なし（環境変数 KIZUKI_PORT, KIZUKI_DB_PATH で設定）

    Returns:
        なし（uvicorn がブロッキングで起動）
    """
    import uvicorn

    port = int(os.environ.get("KIZUKI_PORT", "58765"))
    db_path = os.environ.get("KIZUKI_DB_PATH", "./data/issuelog.db")

    # DB ディレクトリが存在しない場合は作成
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # frozen (PyInstaller) 環境では src パスを sys.path に追加
    if getattr(sys, "frozen", False):
        sys.path.insert(0, sys._MEIPASS)

    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    # Windows で PyInstaller バイナリを子プロセス起動する際に必須
    multiprocessing.freeze_support()
    main()

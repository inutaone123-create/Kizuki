# -*- mode: python ; coding: utf-8 -*-
#
# Kizuki - イシュー管理 × 作業メモ
#
# Personal kanban tool integrating issue management and work logs.
#
# This implementation: 2026
# License: MIT

block_cipher = None

a = Analysis(
    ['server_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('src', 'src'),
        ('templates', 'templates'),
    ],
    hiddenimports=[
        # uvicorn
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # fastapi / starlette
        'fastapi',
        'starlette',
        'starlette.routing',
        'starlette.staticfiles',
        'starlette.responses',
        'starlette.middleware',
        'starlette.middleware.cors',
        # sqlalchemy
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        # pydantic
        'pydantic',
        'pydantic.v1',
        # anyio
        'anyio',
        'anyio._backends._asyncio',
        # h11
        'h11',
        # email (required by some pydantic validators)
        'email.mime.text',
        'email.mime.multipart',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='kizuki-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # コンソールウィンドウを非表示
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kizuki-server',
)

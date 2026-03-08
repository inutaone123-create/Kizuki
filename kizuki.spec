# -*- mode: python ; coding: utf-8 -*-
#
# Kizuki - イシュー管理 × 作業メモ
#
# Personal kanban tool integrating issue management and work logs.
#
# This implementation: 2026
# License: MIT

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# uvicorn・fastapi・sqlalchemy を丸ごと収集
uvicorn_datas, uvicorn_binaries, uvicorn_hiddenimports = collect_all('uvicorn')
fastapi_datas, fastapi_binaries, fastapi_hiddenimports = collect_all('fastapi')
starlette_datas, starlette_binaries, starlette_hiddenimports = collect_all('starlette')
sqlalchemy_hiddenimports = collect_submodules('sqlalchemy')
pydantic_datas, pydantic_binaries, pydantic_hiddenimports = collect_all('pydantic')
anyio_hiddenimports = collect_submodules('anyio')

a = Analysis(
    ['server_entry.py'],
    pathex=['.'],
    binaries=[] + uvicorn_binaries + fastapi_binaries + starlette_binaries + pydantic_binaries,
    datas=[
        ('static', 'static'),
        ('src', 'src'),
        ('templates', 'templates'),
    ] + uvicorn_datas + fastapi_datas + starlette_datas + pydantic_datas,
    hiddenimports=(
        uvicorn_hiddenimports
        + fastapi_hiddenimports
        + starlette_hiddenimports
        + sqlalchemy_hiddenimports
        + pydantic_hiddenimports
        + anyio_hiddenimports
        + [
            'sqlalchemy.dialects.sqlite',
            'h11',
            'email.mime.text',
            'email.mime.multipart',
        ]
    ),
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

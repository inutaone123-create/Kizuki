# FastAPI製カンバンツールをElectronでデスクトップアプリ化した話——PyInstaller同梱という選択

## はじめに

前回の記事（[第5弾: 日報・週報・月報自動生成機能](https://qiita.com/inuta-one/items/3aded768d7f5249439dc)）で、AI連携のレポート生成機能を追加した Kizuki。

ふと気になったことがあります。

> 「これ、Docker も Python も入っていない職場の PC で使えないよな……」

自宅では Dev Container でサクっと動くが、社用 PC には環境構築の権限がないケースは珍しくない。
そこで今回は **Electron + PyInstaller** を使って、インストーラー一発で動くデスクトップアプリに仕立てました。

---

## 背景・動機

### なぜ Electron か

Kizuki のフロントエンドはすでに「ブラウザで動く HTML/CSS/JS」です。
Electron はその Web UI をそのままデスクトップウィンドウに表示できます。
既存コードをほぼ変えずに「アプリっぽい体験」を実現できるのが魅力です。

比較した選択肢：

| 方法 | メリット | デメリット |
|------|---------|-----------|
| Electron + PyInstaller | 既存コード流用 / 配布が exe 一個 | バイナリが大きい（~100MB） |
| Tauri + Sidecar | バイナリが小さい | Rust 学習コスト・設定が複雑 |
| nw.js | シンプル | メンテが下火 |

今回はスピードを優先して **Electron** を選択。

### なぜ PyInstaller か

FastAPI（Python）サーバーをそのまま同梱するには、Python ランタイムごとバイナリ化する必要があります。
PyInstaller は Python スクリプトを単体の実行ファイル（`.exe`）に変換できます。

---

## アーキテクチャ

```
Electron メインプロセス (electron/main.js)
  └── 子プロセス起動: kizuki-server.exe (PyInstaller バイナリ)
        └── FastAPI + uvicorn (ポート: 58765)
              └── SQLite DB: %APPDATA%/Kizuki/issuelog.db

Electron レンダラー
  └── BrowserWindow → http://localhost:58765/
        └── 既存の static/index.html をそのまま表示
```

ポイントは「Electron がサーバーを子プロセスとして起動・管理する」点です。

---

## 実装

### Step 1: Python コードを2行修正

**`src/database.py`**（DB パスを環境変数から取得）

```python
import os

_db_path = os.environ.get("KIZUKI_DB_PATH", "./data/issuelog.db")
DATABASE_URL = f"sqlite:///{_db_path}"
```

**`src/main.py`**（PyInstaller の `_MEIPASS` に対応）

```python
import sys, os

if getattr(sys, "frozen", False):
    _base_dir = sys._MEIPASS          # PyInstaller 展開先
else:
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_static_dir = os.path.join(_base_dir, "static")

# ...
app.mount("/static", StaticFiles(directory=_static_dir), name="static")
```

### Step 2: CDN 依存をベンダー化

オフライン環境で動かすには、CDN から読み込んでいたライブラリをローカルに落とす必要があります。

```bash
curl -sL "https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js" \
     -o static/vendor/Sortable.min.js
curl -sL "https://cdn.jsdelivr.net/npm/marked@12.0.0/marked.min.js" \
     -o static/vendor/marked.min.js
```

`index.html` の参照先を変更：

```html
<!-- before -->
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>

<!-- after -->
<script src="/static/vendor/Sortable.min.js"></script>
```

### Step 3: PyInstaller エントリーポイント

```python
# server_entry.py
import multiprocessing, os, sys

def main():
    import uvicorn
    port = int(os.environ.get("KIZUKI_PORT", "58765"))
    db_path = os.environ.get("KIZUKI_DB_PATH", "./data/issuelog.db")

    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    if getattr(sys, "frozen", False):
        sys.path.insert(0, sys._MEIPASS)

    uvicorn.run("src.main:app", host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows 必須
    main()
```

`multiprocessing.freeze_support()` は **Windows で PyInstaller バイナリを子プロセスとして起動するときに必須** です（これを忘れると子プロセスが無限増殖します）。

### Step 4: Electron メインプロセス

```javascript
// electron/main.js（抜粋）
async function startAndWait() {
  // DB ディレクトリを事前作成（%APPDATA%/Kizuki/）
  fs.mkdirSync(DB_DIR, { recursive: true });

  // Python サーバーを子プロセスで起動
  serverProcess = spawn(binPath, [], {
    env: { ...process.env, KIZUKI_PORT: "58765", KIZUKI_DB_PATH: DB_PATH },
  });

  // /health をポーリングして起動完了を待機（最大20秒）
  await waitForServer(20000);

  // BrowserWindow で FastAPI の UI を表示
  createWindow();  // loadURL("http://127.0.0.1:58765")
}
```

アプリ終了時は Python プロセスを確実に終了します：

```javascript
app.on("will-quit", () => {
  if (process.platform === "win32") {
    execSync(`taskkill /PID ${serverProcess.pid} /F /T`);
  } else {
    serverProcess.kill("SIGTERM");
  }
});
```

Windows では `SIGTERM` が効かないため `taskkill` を使います。

---

## ハマりどころ

### 1. `hiddenimports` の地獄

PyInstaller は動的インポートを静的解析できません。`uvicorn`, `sqlalchemy.dialects.sqlite`, `anyio._backends._asyncio` などは `kizuki.spec` の `hiddenimports` に手動で追加が必要です。

エラーが出たらログを見て追加、というサイクルを繰り返します。

```python
hiddenimports=[
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.h11_impl',
    'sqlalchemy.dialects.sqlite',
    'anyio._backends._asyncio',
    # ...
],
```

### 2. `sys._MEIPASS` でのパス解決

PyInstaller でバイナリ化すると、`static/` などのファイルは `sys._MEIPASS` に展開されます。
`"static"` という相対パスではなく、`os.path.join(sys._MEIPASS, "static")` で絶対パス指定が必要です。

### 3. Windows でのプロセス終了

`child_process.kill("SIGTERM")` は macOS/Linux では機能しますが、Windows では効きません。
`taskkill /PID <pid> /F /T` で強制終了する分岐が必要です。`/T` フラグで子プロセスも巻き込んで終了できます。

### 4. CDN のオフライン問題

社内ネットワークでは CDN にアクセスできないケースがあります。
`Sortable.min.js` と `marked.min.js` を `static/vendor/` にダウンロードしてベンダー化し、`index.html` の参照を変更しました。

---

## ソースコード

https://github.com/inutaone123-create/Kizuki

---

## まとめ

| 項目 | 内容 |
|------|------|
| Electron + PyInstaller | Python/FastAPI をそのまま `.exe` 化して同梱 |
| CDN ベンダー化 | オフライン環境でも動作する |
| DB パス | `%APPDATA%/Kizuki/issuelog.db` でユーザーデータを永続化 |
| プロセス管理 | Electron が子プロセスを起動・監視・終了 |

「既存のWeb UIをそのままデスクトップ化したい」ケースでは Electron + PyInstaller の組み合わせは手軽で有効です。
バイナリサイズが大きくなる（~100MB）のは妥協点ですが、配布の手軽さとのトレードオフで許容範囲でした。

次は実際に Windows 上でビルドして配布する予定です。

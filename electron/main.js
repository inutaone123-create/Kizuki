/*
 * Kizuki - イシュー管理 × 作業メモ
 *
 * Personal kanban tool integrating issue management and work logs.
 *
 * This implementation: 2026
 * License: MIT
 */

"use strict";

const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const os = require("os");

// ── 定数 ────────────────────────────────────────────────────────────
const PORT = 58765;
const SERVER_URL = `http://127.0.0.1:${PORT}`;
const HEALTH_URL = `${SERVER_URL}/health`;
const STARTUP_TIMEOUT_MS = 20000;
const HEALTH_POLL_INTERVAL_MS = 500;

// DB パス: %APPDATA%/Kizuki/issuelog.db (Windows)
//          ~/Library/Application Support/Kizuki/issuelog.db (macOS)
//          ~/.config/Kizuki/issuelog.db (Linux)
const DB_DIR = path.join(app.getPath("userData"), "Kizuki");
const DB_PATH = path.join(DB_DIR, "issuelog.db");

// PyInstaller バイナリのパス
function getServerBinPath() {
  if (app.isPackaged) {
    // electron-builder でパッケージ化された場合: resources/kizuki-server/
    const binName = process.platform === "win32" ? "kizuki-server.exe" : "kizuki-server";
    return path.join(process.resourcesPath, "kizuki-server", binName);
  }
  // 開発時: プロジェクトルートの dist/kizuki-server/
  const binName = process.platform === "win32" ? "kizuki-server.exe" : "kizuki-server";
  return path.join(__dirname, "..", "dist", "kizuki-server", binName);
}

// ── グローバル状態 ───────────────────────────────────────────────────
let serverProcess = null;
let mainWindow = null;

/**
 * Python サーバーを子プロセスとして起動する
 * @returns {ChildProcess} 起動した子プロセス
 */
function startServer() {
  const binPath = getServerBinPath();

  const env = {
    ...process.env,
    KIZUKI_PORT: String(PORT),
    KIZUKI_DB_PATH: DB_PATH,
  };

  console.log(`[Kizuki] サーバー起動: ${binPath}`);
  console.log(`[Kizuki] DB パス: ${DB_PATH}`);

  const proc = spawn(binPath, [], {
    env,
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
  });

  proc.stdout.on("data", (data) => {
    console.log(`[server] ${data.toString().trim()}`);
  });

  proc.stderr.on("data", (data) => {
    console.error(`[server-err] ${data.toString().trim()}`);
  });

  proc.on("error", (err) => {
    console.error("[Kizuki] サーバープロセス起動エラー:", err.message);
    dialog.showErrorBox(
      "Kizuki 起動エラー",
      `サーバーの起動に失敗いたし候。\n${err.message}`
    );
    app.quit();
  });

  proc.on("exit", (code, signal) => {
    console.log(`[Kizuki] サーバー終了: code=${code}, signal=${signal}`);
  });

  return proc;
}

/**
 * /health をポーリングして、サーバーが応答するまで待機する
 * @param {number} timeoutMs タイムアウト時間（ミリ秒）
 * @returns {Promise<void>}
 */
function waitForServer(timeoutMs = STARTUP_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;

    function poll() {
      if (Date.now() > deadline) {
        reject(new Error(`サーバーが ${timeoutMs}ms 以内に起動しませんでした`));
        return;
      }

      const req = http.get(HEALTH_URL, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          setTimeout(poll, HEALTH_POLL_INTERVAL_MS);
        }
      });

      req.on("error", () => {
        setTimeout(poll, HEALTH_POLL_INTERVAL_MS);
      });

      req.setTimeout(1000, () => {
        req.destroy();
        setTimeout(poll, HEALTH_POLL_INTERVAL_MS);
      });
    }

    poll();
  });
}

/**
 * メインウィンドウを作成して FastAPI の UI を表示する
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: "Kizuki",
    icon: path.join(__dirname, "..", "assets", "icon.ico"),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(SERVER_URL);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ── アプリ ライフサイクル ─────────────────────────────────────────────
app.whenReady().then(async () => {
  // DB ディレクトリを事前作成
  const fs = require("fs");
  if (!fs.existsSync(DB_DIR)) {
    fs.mkdirSync(DB_DIR, { recursive: true });
    console.log(`[Kizuki] DB ディレクトリ作成: ${DB_DIR}`);
  }

  // サーバー起動
  serverProcess = startServer();

  // サーバー起動待機
  try {
    console.log("[Kizuki] サーバー起動待機中...");
    await waitForServer();
    console.log("[Kizuki] サーバー起動完了 — ウィンドウを開きます");
    createWindow();
  } catch (err) {
    console.error("[Kizuki] サーバー起動タイムアウト:", err.message);
    dialog.showErrorBox(
      "Kizuki 起動タイムアウト",
      `サーバーの起動を待ちましたが応答がありませんでした。\n${err.message}`
    );
    app.quit();
  }
});

app.on("window-all-closed", () => {
  // macOS 以外は全ウィンドウが閉じられたら終了
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on("will-quit", () => {
  // Python サーバープロセスを終了
  if (serverProcess && !serverProcess.killed) {
    console.log("[Kizuki] サーバープロセスを終了します");
    if (process.platform === "win32") {
      // Windows では SIGTERM が効かないため taskkill を使用
      const { execSync } = require("child_process");
      try {
        execSync(`taskkill /PID ${serverProcess.pid} /F /T`);
      } catch (e) {
        // プロセスが既に終了している場合は無視
      }
    } else {
      serverProcess.kill("SIGTERM");
    }
    serverProcess = null;
  }
});

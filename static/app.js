/*
 * Kizuki - イシュー管理 × 作業メモ
 *
 * Personal kanban tool integrating issue management and work logs.
 *
 * This implementation: 2026
 * License: MIT
 */

"use strict";

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  issues: [],
  currentIssue: null,
  filters: { status: "", priority: "", category: "" },
};

// ─── API helpers ─────────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  issues: {
    list: (params = {}) => {
      const q = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v))
      );
      return apiFetch(`/api/issues${q.toString() ? "?" + q : ""}`);
    },
    get:    (id)       => apiFetch(`/api/issues/${id}`),
    create: (body)     => apiFetch("/api/issues", { method: "POST", body: JSON.stringify(body) }),
    update: (id, body) => apiFetch(`/api/issues/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    delete: (id)       => apiFetch(`/api/issues/${id}`, { method: "DELETE" }),
    patch:  (id, s)    => apiFetch(`/api/issues/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: s }) }),
  },
  logs: {
    list:   (issueId)        => apiFetch(`/api/issues/${issueId}/logs`),
    create: (issueId, body)  => apiFetch(`/api/issues/${issueId}/logs`, { method: "POST", body: JSON.stringify(body) }),
    delete: (logId)          => apiFetch(`/api/logs/${logId}`, { method: "DELETE" }),
  },
};

// ─── Toast ───────────────────────────────────────────────────────────────────

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2500);
}

// ─── Board rendering ─────────────────────────────────────────────────────────

const PRIORITY_LABEL = { high: "🔴 高", medium: "🟡 中", low: "🟢 低" };
const STATUS_COLS = ["todo", "in_progress", "done"];

function buildCard(issue) {
  const card = document.createElement("div");
  card.className = `card priority-${issue.priority}`;
  card.dataset.id = issue.id;

  const tags = issue.tags
    ? issue.tags.split(",").map(t => t.trim()).filter(Boolean)
        .map(t => `<span class="tag-badge">${escHtml(t)}</span>`).join("")
    : "";

  card.innerHTML = `
    <div class="card-title">${escHtml(issue.title)}</div>
    <div class="card-meta">
      <span class="priority-badge ${issue.priority}">${PRIORITY_LABEL[issue.priority]}</span>
      ${issue.category ? `<span class="category-badge">${escHtml(issue.category)}</span>` : ""}
      ${tags}
    </div>`;

  card.addEventListener("click", () => openDetail(issue.id));
  return card;
}

function renderBoard() {
  const { status, priority, category } = state.filters;
  const filtered = state.issues.filter(i =>
    (!status || i.status === status) &&
    (!priority || i.priority === priority) &&
    (!category || i.category === category)
  );

  STATUS_COLS.forEach(col => {
    const body = document.getElementById(`col-${col}`);
    body.innerHTML = "";
    const items = filtered.filter(i => i.status === col);
    // カウント更新
    document.getElementById(`count-${col}`).textContent = items.length;
    if (items.length === 0) {
      body.innerHTML = `<div class="empty-col">イシューがありません</div>`;
    } else {
      items.forEach(issue => body.appendChild(buildCard(issue)));
    }
  });

  initDragDrop();
}

// ─── Drag & Drop ─────────────────────────────────────────────────────────────

function initDragDrop() {
  STATUS_COLS.forEach(col => {
    const el = document.getElementById(`col-${col}`);
    Sortable.create(el, {
      group: "board",
      animation: 150,
      ghostClass: "sortable-ghost",
      onEnd: async (evt) => {
        const id = Number(evt.item.dataset.id);
        const newStatus = evt.to.dataset.status;
        if (!newStatus) return;
        const issue = state.issues.find(i => i.id === id);
        if (!issue || issue.status === newStatus) return;
        try {
          await api.issues.patch(id, newStatus);
          issue.status = newStatus;
          renderBoard();
          showToast("ステータスを更新しました");
        } catch (e) {
          showToast(`エラー: ${e.message}`);
          renderBoard(); // 元に戻す
        }
      },
    });
  });
}

// ─── Data fetching ───────────────────────────────────────────────────────────

async function loadIssues() {
  try {
    state.issues = await api.issues.list(state.filters);
    renderBoard();
  } catch (e) {
    showToast(`イシューの取得に失敗: ${e.message}`);
  }
}

// ─── Create / Edit modal ─────────────────────────────────────────────────────

function openCreateModal() {
  document.getElementById("issue-form").reset();
  document.getElementById("issue-id").value = "";
  document.getElementById("modal-issue-title-text").textContent = "新規イシュー";
  openModal("modal-issue");
}

async function openEditModal(issue) {
  document.getElementById("issue-id").value = issue.id;
  document.getElementById("f-title").value = issue.title;
  document.getElementById("f-description").value = issue.description || "";
  document.getElementById("f-status").value = issue.status;
  document.getElementById("f-priority").value = issue.priority;
  document.getElementById("f-category").value = issue.category || "";
  document.getElementById("f-tags").value = issue.tags || "";
  document.getElementById("modal-issue-title-text").textContent = "イシュー編集";
  openModal("modal-issue");
}

document.getElementById("issue-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("issue-id").value;
  const body = {
    title:       document.getElementById("f-title").value,
    description: document.getElementById("f-description").value || null,
    status:      document.getElementById("f-status").value,
    priority:    document.getElementById("f-priority").value,
    category:    document.getElementById("f-category").value || null,
    tags:        document.getElementById("f-tags").value || null,
  };

  try {
    if (id) {
      await api.issues.update(Number(id), body);
      showToast("イシューを更新しました");
    } else {
      await api.issues.create(body);
      showToast("イシューを作成しました");
    }
    closeModal("modal-issue");
    await loadIssues();
    // 詳細モーダルが開いていれば更新
    if (state.currentIssue && id) {
      await openDetail(state.currentIssue.id);
    }
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

// ─── Detail modal ────────────────────────────────────────────────────────────

async function openDetail(id) {
  try {
    const issue = await api.issues.get(id);
    state.currentIssue = issue;

    document.getElementById("detail-title").textContent = issue.title;

    const meta = document.getElementById("detail-meta");
    meta.innerHTML = `
      <span class="priority-badge ${issue.priority}">${PRIORITY_LABEL[issue.priority]}</span>
      <span class="category-badge">${issue.status === "todo" ? "未着手" : issue.status === "in_progress" ? "進行中" : "完了"}</span>
      ${issue.category ? `<span class="category-badge">${escHtml(issue.category)}</span>` : ""}
      ${(issue.tags || "").split(",").map(t => t.trim()).filter(Boolean)
          .map(t => `<span class="tag-badge">${escHtml(t)}</span>`).join("")}
    `;

    document.getElementById("detail-description").textContent =
      issue.description || "(説明なし)";

    // ログ一覧
    await renderLogs(issue.id);

    openModal("modal-detail");
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

// ─── WorkLog ─────────────────────────────────────────────────────────────────

async function renderLogs(issueId) {
  const logs = await api.logs.list(issueId);
  const container = document.getElementById("log-list");
  container.innerHTML = "";

  if (logs.length === 0) {
    container.innerHTML = `<div class="empty-col">作業ログがありません</div>`;
    return;
  }

  logs.forEach(log => {
    const item = document.createElement("div");
    item.className = "log-item";
    item.innerHTML = `
      <div class="log-item-header">
        <span class="log-date">📅 ${log.logged_at}</span>
        <button class="btn btn-ghost btn-sm" onclick="deleteLog(${log.id})">削除</button>
      </div>
      <div class="log-content">${marked.parse(log.content)}</div>
    `;
    container.appendChild(item);
  });
}

async function deleteLog(logId) {
  if (!confirm("このログを削除しますか？")) return;
  try {
    await api.logs.delete(logId);
    showToast("ログを削除しました");
    await renderLogs(state.currentIssue.id);
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

document.getElementById("log-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const content = document.getElementById("log-content").value.trim();
  const loggedAt = document.getElementById("log-date").value;
  if (!content) return;

  try {
    await api.logs.create(state.currentIssue.id, { content, logged_at: loggedAt });
    document.getElementById("log-content").value = "";
    showToast("ログを追加しました");
    await renderLogs(state.currentIssue.id);
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

// ─── Edit / Delete buttons in detail modal ──────────────────────────────────

document.getElementById("btn-edit-issue").addEventListener("click", () => {
  closeModal("modal-detail");
  openEditModal(state.currentIssue);
});

document.getElementById("btn-delete-issue").addEventListener("click", async () => {
  if (!confirm(`「${state.currentIssue.title}」を削除しますか？`)) return;
  try {
    await api.issues.delete(state.currentIssue.id);
    closeModal("modal-detail");
    state.currentIssue = null;
    await loadIssues();
    showToast("イシューを削除しました");
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

// ─── Filters ─────────────────────────────────────────────────────────────────

["filter-status", "filter-priority", "filter-category"].forEach(id => {
  document.getElementById(id).addEventListener("change", async (e) => {
    const key = id.replace("filter-", "");
    state.filters[key] = e.target.value;
    await loadIssues();
  });
});

// ─── Modal helpers ───────────────────────────────────────────────────────────

function openModal(id) {
  const overlay = document.getElementById(id);
  overlay.style.display = "flex";
  requestAnimationFrame(() => overlay.classList.add("active"));
}

function closeModal(id) {
  const overlay = document.getElementById(id);
  overlay.classList.remove("active");
  overlay.addEventListener("transitionend", () => { overlay.style.display = "none"; }, { once: true });
}

document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

document.querySelectorAll(".modal-close").forEach(btn => {
  btn.addEventListener("click", () => closeModal(btn.closest(".modal-overlay").id));
});

// ─── Utilities ───────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ─── Init ────────────────────────────────────────────────────────────────────

// 今日の日付をログ日付フィールドのデフォルトに
document.getElementById("log-date").value = new Date().toISOString().slice(0, 10);

// 新規ボタン
document.getElementById("btn-new-issue").addEventListener("click", openCreateModal);

// 初期読み込み
loadIssues();

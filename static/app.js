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
  memos: [],
  members: [],
  workflows: [],
  reports: [],
  aiSettings: null,
  reportType: "daily",
  currentIssue: null,
  currentMemo: null,
  currentMember: null,
  currentWorkflow: null,
  filters: { status: "", priority: "", category: "" },
  activeTab: "board",
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
    get:          (id)       => apiFetch(`/api/issues/${id}`),
    create:       (body)     => apiFetch("/api/issues", { method: "POST", body: JSON.stringify(body) }),
    update:       (id, body) => apiFetch(`/api/issues/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    delete:       (id)       => apiFetch(`/api/issues/${id}`, { method: "DELETE" }),
    patch:        (id, s)    => apiFetch(`/api/issues/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: s }) }),
    patchWfStep:  (id, step) => apiFetch(`/api/issues/${id}/workflow-step`, { method: "PATCH", body: JSON.stringify({ step }) }),
  },
  logs: {
    list:   (issueId)        => apiFetch(`/api/issues/${issueId}/logs`),
    create: (issueId, body)  => apiFetch(`/api/issues/${issueId}/logs`, { method: "POST", body: JSON.stringify(body) }),
    delete: (logId)          => apiFetch(`/api/logs/${logId}`, { method: "DELETE" }),
  },
  memos: {
    list:        ()            => apiFetch("/api/memos"),
    create:      (body)        => apiFetch("/api/memos", { method: "POST", body: JSON.stringify(body) }),
    update:      (id, body)    => apiFetch(`/api/memos/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    delete:      (id)          => apiFetch(`/api/memos/${id}`, { method: "DELETE" }),
    patchIssue:  (id, issueId) => apiFetch(`/api/memos/${id}/issue`, { method: "PATCH", body: JSON.stringify({ issue_id: issueId }) }),
  },
  members: {
    list:   ()            => apiFetch("/api/members"),
    create: (body)        => apiFetch("/api/members", { method: "POST", body: JSON.stringify(body) }),
    update: (id, body)    => apiFetch(`/api/members/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    delete: (id)          => apiFetch(`/api/members/${id}`, { method: "DELETE" }),
  },
  workflows: {
    list:   ()            => apiFetch("/api/workflows"),
    create: (body)        => apiFetch("/api/workflows", { method: "POST", body: JSON.stringify(body) }),
    update: (id, body)    => apiFetch(`/api/workflows/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    delete: (id)          => apiFetch(`/api/workflows/${id}`, { method: "DELETE" }),
  },
  reports: {
    list:     ()           => apiFetch("/api/reports"),
    generate: (body)       => apiFetch("/api/reports/generate", { method: "POST", body: JSON.stringify(body) }),
    get:      (id)         => apiFetch(`/api/reports/${id}`),
    delete:   (id)         => apiFetch(`/api/reports/${id}`, { method: "DELETE" }),
  },
  aiSettings: {
    get:    ()     => apiFetch("/api/settings/ai"),
    update: (body) => apiFetch("/api/settings/ai", { method: "PUT", body: JSON.stringify(body) }),
  },
  dependencies: {
    get:    (id)                  => apiFetch(`/api/issues/${id}/dependencies`),
    add:    (id, blocked_by_id)   => apiFetch(`/api/issues/${id}/dependencies`, {
      method: "POST",
      body: JSON.stringify({ blocked_by_id }),
    }),
    remove: (id, blocked_by_id)   => apiFetch(`/api/issues/${id}/dependencies/${blocked_by_id}`, {
      method: "DELETE",
    }),
  },
  ai: {
    suggestWorkflow: (category) => {
      const params = category ? `?category=${encodeURIComponent(category)}` : '';
      return fetch(`/api/ai/suggest-workflow${params}`, { method: 'POST' }).then(r => r.json());
    },
  },
};

// ─── Toast ───────────────────────────────────────────────────────────────────

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2500);
}

// ─── Tab switching ────────────────────────────────────────────────────────────

function switchTab(tabName) {
  state.activeTab = tabName;

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.toggle("active", el.id === `tab-${tabName}`);
  });

  const filterBar = document.getElementById("board-filter-bar");
  const newIssueBtn = document.getElementById("btn-new-issue");
  if (tabName === "board") {
    filterBar.style.display = "";
    newIssueBtn.style.display = "";
  } else {
    filterBar.style.display = "none";
    newIssueBtn.style.display = "none";
  }

  if (tabName === "memo") loadMemos();
  if (tabName === "settings") loadSettings();
  if (tabName === "workflow") loadWorkflowMatrix();
  if (tabName === "report") loadReports();

  location.hash = tabName;
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

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

  // 担当者バッジ
  const assigneeHtml = issue.assignee
    ? `<span class="assignee-badge" style="background:${escHtml(issue.assignee.color)}">👤 ${escHtml(issue.assignee.name)}</span>`
    : "";

  // ワークフローステップ表示
  let wfStepHtml = "";
  if (issue.workflow && issue.workflow_step != null) {
    const stepName = issue.workflow.steps[issue.workflow_step] || "";
    if (stepName) {
      wfStepHtml = `<span class="card-workflow-step">🔄 ${escHtml(stepName)}</span>`;
    }
  }

  // ブロック中バッジ
  const blockedBadge = issue.is_blocked
    ? '<span class="badge badge-blocked">🔒 ブロック中</span>'
    : "";

  const hasFooter = assigneeHtml || wfStepHtml;

  card.innerHTML = `
    <div class="card-title">${escHtml(issue.title)}</div>
    <div class="card-meta">
      <span class="priority-badge ${issue.priority}">${PRIORITY_LABEL[issue.priority]}</span>
      ${issue.category ? `<span class="category-badge">${escHtml(issue.category)}</span>` : ""}
      ${tags}
      ${blockedBadge}
    </div>
    ${hasFooter ? `<div class="card-footer">${wfStepHtml}${assigneeHtml}</div>` : ""}`;

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
          renderBoard();
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
    updateCategoryFilter();
  } catch (e) {
    showToast(`イシューの取得に失敗: ${e.message}`);
  }
}

async function loadMembersAndWorkflows() {
  try {
    [state.members, state.workflows] = await Promise.all([
      api.members.list(),
      api.workflows.list(),
    ]);
  } catch (e) {
    showToast(`設定データの取得に失敗: ${e.message}`);
  }
}

function updateCategoryFilter() {
  const sel = document.getElementById("filter-category");
  const current = sel.value;
  const cats = [...new Set(state.issues.map(i => i.category).filter(Boolean))].sort();
  sel.innerHTML = `<option value="">すべてのカテゴリ</option>` +
    cats.map(c => `<option value="${escHtml(c)}"${c === current ? " selected" : ""}>${escHtml(c)}</option>`).join("");
}

// ─── Create / Edit modal ─────────────────────────────────────────────────────

function populateIssueFormSelects(selectedAssigneeId, selectedWorkflowId) {
  const assigneeSel = document.getElementById("f-assignee");
  assigneeSel.innerHTML = `<option value="">なし</option>` +
    state.members.map(m =>
      `<option value="${m.id}"${m.id === selectedAssigneeId ? " selected" : ""}>${escHtml(m.name)}</option>`
    ).join("");

  const workflowSel = document.getElementById("f-workflow");
  workflowSel.innerHTML = `<option value="">なし</option>` +
    state.workflows.map(wf =>
      `<option value="${wf.id}"${wf.id === selectedWorkflowId ? " selected" : ""}>${escHtml(wf.name)}</option>`
    ).join("");
}

function openCreateModal() {
  document.getElementById("issue-form").reset();
  document.getElementById("issue-id").value = "";
  document.getElementById("modal-issue-title-text").textContent = "新規イシュー";
  populateIssueFormSelects(null, null);
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
  populateIssueFormSelects(issue.assignee_id, issue.workflow_id);
  openModal("modal-issue");
}

document.getElementById("issue-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("issue-id").value;
  const assigneeVal = document.getElementById("f-assignee").value;
  const workflowVal = document.getElementById("f-workflow").value;
  const body = {
    title:       document.getElementById("f-title").value,
    description: document.getElementById("f-description").value || null,
    status:      document.getElementById("f-status").value,
    priority:    document.getElementById("f-priority").value,
    category:    document.getElementById("f-category").value || null,
    tags:        document.getElementById("f-tags").value || null,
    assignee_id: assigneeVal ? Number(assigneeVal) : null,
    workflow_id: workflowVal ? Number(workflowVal) : null,
    workflow_step: workflowVal ? 0 : null,
  };

  try {
    if (id) {
      // 編集時はworkflow_stepをリセットしない（変更があった場合のみ）
      const current = state.issues.find(i => i.id === Number(id));
      if (current && current.workflow_id === body.workflow_id) {
        delete body.workflow_step; // ワークフロー変更なければステップ維持
      }
      await api.issues.update(Number(id), body);
      showToast("イシューを更新しました");
    } else {
      await api.issues.create(body);
      showToast("イシューを作成しました");
    }
    closeModal("modal-issue");
    await loadIssues();
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
    const assigneeBadge = issue.assignee
      ? `<span class="assignee-badge" style="background:${escHtml(issue.assignee.color)}">👤 ${escHtml(issue.assignee.name)}</span>`
      : "";
    meta.innerHTML = `
      <span class="priority-badge ${issue.priority}">${PRIORITY_LABEL[issue.priority]}</span>
      <span class="category-badge">${issue.status === "todo" ? "未着手" : issue.status === "in_progress" ? "進行中" : "完了"}</span>
      ${issue.category ? `<span class="category-badge">${escHtml(issue.category)}</span>` : ""}
      ${(issue.tags || "").split(",").map(t => t.trim()).filter(Boolean)
          .map(t => `<span class="tag-badge">${escHtml(t)}</span>`).join("")}
      ${assigneeBadge}
    `;

    document.getElementById("detail-description").textContent =
      issue.description || "(説明なし)";

    // ワークフロー進捗表示
    renderWorkflowSection(issue);

    // 依存関係表示
    await renderDependencies(issue.id);

    await renderLogs(issue.id);
    openModal("modal-detail");
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

// ─── Dependencies ─────────────────────────────────────────────────────────────

async function renderDependencies(issueId) {
  const container = document.getElementById("dep-blocked-by-items");
  container.innerHTML = "";
  try {
    const data = await api.dependencies.get(issueId);
    if (data.blocked_by.length === 0) {
      container.innerHTML = `<div class="empty-col" style="font-size:0.85rem;">ブロッカーなし</div>`;
    } else {
      data.blocked_by.forEach(blocker => {
        const statusClass = blocker.status === "done" ? "done" : "";
        const statusLabel = blocker.status === "done" ? "完了" : blocker.status === "in_progress" ? "進行中" : "未着手";
        const item = document.createElement("div");
        item.className = "dep-item";
        item.innerHTML = `
          <span class="dep-item-title">${escHtml(blocker.title)}</span>
          <span class="dep-item-status ${statusClass}">${statusLabel}</span>
          <button class="btn btn-ghost btn-sm" onclick="removeDependency(${issueId}, ${blocker.id})">✕</button>
        `;
        container.appendChild(item);
      });
    }
  } catch (e) {
    container.innerHTML = `<div class="empty-col" style="font-size:0.85rem;">取得失敗</div>`;
  }
}

async function removeDependency(issueId, blockerId) {
  try {
    await api.dependencies.remove(issueId, blockerId);
    showToast("依存関係を削除しました");
    await renderDependencies(issueId);
    await loadIssues();
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

document.getElementById("btn-add-dep").addEventListener("click", async () => {
  const issue = state.currentIssue;
  if (!issue) return;

  // 現在のイシュー以外の全イシューを選択肢に出す
  const otherIssues = state.issues.filter(i => i.id !== issue.id);
  if (otherIssues.length === 0) {
    showToast("追加できるタスクがありません");
    return;
  }

  const selectHtml = `<select id="dep-select" class="dep-select" style="margin:0.5rem 0;width:100%;padding:0.3rem;">` +
    otherIssues.map(i => `<option value="${i.id}">${escHtml(i.title)}</option>`).join("") +
    `</select>`;

  const container = document.getElementById("dep-blocked-by-items");
  const formDiv = document.createElement("div");
  formDiv.id = "dep-add-form";
  formDiv.innerHTML = `
    ${selectHtml}
    <div style="display:flex;gap:0.5rem;margin-top:0.3rem;">
      <button id="btn-dep-confirm" class="btn btn-primary btn-sm">追加</button>
      <button id="btn-dep-cancel" class="btn btn-ghost btn-sm">キャンセル</button>
    </div>
  `;
  container.appendChild(formDiv);

  document.getElementById("btn-dep-confirm").addEventListener("click", async () => {
    const selectedId = Number(document.getElementById("dep-select").value);
    try {
      await api.dependencies.add(issue.id, selectedId);
      showToast("依存関係を追加しました");
      await renderDependencies(issue.id);
      await loadIssues();
    } catch (e) {
      const msg = await e.json?.().then(j => j.detail).catch(() => e.message);
      showToast(`エラー: ${msg || e.message}`);
      await renderDependencies(issue.id);
    }
  });

  document.getElementById("btn-dep-cancel").addEventListener("click", async () => {
    await renderDependencies(issue.id);
  });
});

function renderWorkflowSection(issue) {
  const section = document.getElementById("workflow-section");
  if (!issue.workflow || issue.workflow_step == null) {
    section.style.display = "none";
    return;
  }
  section.style.display = "";

  const steps = issue.workflow.steps;
  const currentStep = issue.workflow_step;

  const stepsEl = document.getElementById("workflow-steps");
  stepsEl.innerHTML = steps.map((s, i) => {
    let cls = "";
    if (i < currentStep) cls = "done";
    else if (i === currentStep) cls = "active";
    const arrow = i < steps.length - 1 ? `<span class="workflow-step-arrow">→</span>` : "";
    return `<div class="workflow-step-item">
      <span class="workflow-step-bubble ${cls}">${escHtml(s)}</span>
      ${arrow}
    </div>`;
  }).join("");

  const prevBtn = document.getElementById("btn-wf-prev");
  const nextBtn = document.getElementById("btn-wf-next");
  prevBtn.disabled = currentStep <= 0;
  nextBtn.disabled = currentStep >= steps.length - 1;
}

document.getElementById("btn-wf-prev").addEventListener("click", async () => {
  const issue = state.currentIssue;
  if (!issue || issue.workflow_step == null || issue.workflow_step <= 0) return;
  try {
    const updated = await api.issues.patchWfStep(issue.id, issue.workflow_step - 1);
    state.currentIssue = updated;
    renderWorkflowSection(updated);
    await loadIssues();
    showToast("ステップを戻しました");
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

document.getElementById("btn-wf-next").addEventListener("click", async () => {
  const issue = state.currentIssue;
  if (!issue || issue.workflow_step == null) return;
  const maxStep = (issue.workflow?.steps?.length ?? 1) - 1;
  if (issue.workflow_step >= maxStep) return;
  try {
    const updated = await api.issues.patchWfStep(issue.id, issue.workflow_step + 1);
    state.currentIssue = updated;
    renderWorkflowSection(updated);
    await loadIssues();
    showToast("次のステップへ進みました");
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

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

// ─── Memo screen ─────────────────────────────────────────────────────────────

async function loadMemos() {
  try {
    state.memos = await api.memos.list();
    renderMemos();
  } catch (e) {
    showToast(`メモの取得に失敗: ${e.message}`);
  }
}

function renderMemos() {
  const container = document.getElementById("memo-list");
  const countEl = document.getElementById("memo-count");
  container.innerHTML = "";
  countEl.textContent = `${state.memos.length} 件`;

  if (state.memos.length === 0) {
    container.innerHTML = `<div class="empty-col">メモがありません</div>`;
    return;
  }

  const groups = {};
  state.memos.forEach(memo => {
    const d = memo.logged_at;
    if (!groups[d]) groups[d] = [];
    groups[d].push(memo);
  });

  Object.keys(groups).sort((a, b) => b.localeCompare(a)).forEach(date => {
    const dateHeader = document.createElement("div");
    dateHeader.className = "memo-date-header";
    dateHeader.textContent = date;
    container.appendChild(dateHeader);

    groups[date].forEach(memo => {
      const card = document.createElement("div");
      card.className = "memo-card";
      card.innerHTML = `
        <div class="memo-card-body">
          <div class="memo-content">${marked.parse(memo.content)}</div>
          ${memo.issue_title
            ? `<div class="memo-issue-link">🔗 ${escHtml(memo.issue_title)}</div>`
            : `<div class="memo-issue-link memo-no-issue">タスク未紐付け</div>`}
        </div>
        <div class="memo-card-actions">
          <button class="btn btn-ghost btn-sm" onclick="openEditMemoModal(${memo.id})">✏️ 編集</button>
          <button class="btn btn-danger btn-sm" onclick="deleteMemo(${memo.id})">🗑️ 削除</button>
        </div>
      `;
      container.appendChild(card);
    });
  });
}

function openCreateMemoModal() {
  document.getElementById("memo-form").reset();
  document.getElementById("memo-id").value = "";
  document.getElementById("m-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("modal-memo-title-text").textContent = "新規メモ";
  state.currentMemo = null;
  populateMemoIssueSelect(null);
  openModal("modal-memo");
}

async function openEditMemoModal(memoId) {
  const memo = state.memos.find(m => m.id === memoId);
  if (!memo) return;
  state.currentMemo = memo;
  document.getElementById("memo-id").value = memo.id;
  document.getElementById("m-date").value = memo.logged_at;
  document.getElementById("m-content").value = memo.content;
  document.getElementById("modal-memo-title-text").textContent = "メモ編集";
  populateMemoIssueSelect(memo.issue_id);
  openModal("modal-memo");
}

function populateMemoIssueSelect(selectedIssueId) {
  const sel = document.getElementById("m-issue");
  sel.innerHTML = `<option value="">なし</option>` +
    state.issues.map(issue =>
      `<option value="${issue.id}"${issue.id === selectedIssueId ? " selected" : ""}>${escHtml(issue.title)}</option>`
    ).join("");
}

document.getElementById("memo-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("memo-id").value;
  const issueIdVal = document.getElementById("m-issue").value;
  const body = {
    content:    document.getElementById("m-content").value.trim(),
    logged_at:  document.getElementById("m-date").value,
    issue_id:   issueIdVal ? Number(issueIdVal) : null,
  };
  if (!body.content) return;

  try {
    if (id) {
      await api.memos.update(Number(id), body);
      showToast("メモを更新しました");
    } else {
      await api.memos.create(body);
      showToast("メモを作成しました");
    }
    closeModal("modal-memo");
    await loadMemos();
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

async function deleteMemo(memoId) {
  if (!confirm("このメモを削除しますか？")) return;
  try {
    await api.memos.delete(memoId);
    showToast("メモを削除しました");
    await loadMemos();
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

document.getElementById("btn-new-memo").addEventListener("click", openCreateMemoModal);

// ─── Workflow matrix screen ───────────────────────────────────────────────────

async function loadWorkflowMatrix() {
  try {
    [state.members, state.workflows, state.issues] = await Promise.all([
      api.members.list(),
      api.workflows.list(),
      api.issues.list(),
    ]);
  } catch (e) {
    showToast(`データの取得に失敗: ${e.message}`);
    return;
  }
  renderWorkflowMatrix();
}

function renderWorkflowMatrix() {
  const container = document.getElementById("workflow-matrix-body");
  container.innerHTML = "";

  // ワークフローIDごと・ステップインデックスごとにグループ化
  const grouped = {};
  state.issues
    .filter(i => i.workflow_id != null)
    .forEach(issue => {
      const wfId = issue.workflow_id;
      const step = issue.workflow_step ?? 0;
      if (!grouped[wfId]) grouped[wfId] = {};
      if (!grouped[wfId][step]) grouped[wfId][step] = [];
      grouped[wfId][step].push(issue);
    });

  // ワークフローが割り当てられたイシューが1件もなければメッセージ表示
  if (Object.keys(grouped).length === 0) {
    container.innerHTML = `<div class="empty-col">ワークフローに割り当てられたイシューがありません</div>`;
    return;
  }

  state.workflows.forEach(wf => {
    if (!grouped[wf.id]) return; // イシューが0件のワークフローは表示しない

    const section = document.createElement("div");
    section.className = "wf-matrix-section";

    const header = document.createElement("div");
    header.className = "wf-matrix-section-header";
    header.innerHTML = `<h2>【${escHtml(wf.name)}】</h2>`;
    section.appendChild(header);

    const board = document.createElement("div");
    board.className = "wf-matrix-board";
    board.style.gridTemplateColumns = `repeat(${wf.steps.length}, 220px)`;

    wf.steps.forEach((stepName, stepIdx) => {
      const col = document.createElement("div");
      col.className = "wf-matrix-column";

      const issues = (grouped[wf.id] && grouped[wf.id][stepIdx]) || [];
      const colHeader = document.createElement("div");
      colHeader.className = "wf-matrix-col-header";
      colHeader.innerHTML = `
        <span class="wf-matrix-col-name">${escHtml(stepName)}</span>
        <span class="wf-matrix-col-count">${issues.length}</span>
      `;
      col.appendChild(colHeader);

      const body = document.createElement("div");
      body.className = "wf-matrix-col-body";

      if (issues.length === 0) {
        body.innerHTML = `<div class="empty-col">なし</div>`;
      } else {
        issues.forEach(issue => body.appendChild(buildCard(issue)));
      }
      col.appendChild(body);
      board.appendChild(col);
    });

    section.appendChild(board);
    container.appendChild(section);
  });
}

// ─── Settings screen ──────────────────────────────────────────────────────────

async function loadSettings() {
  await loadMembersAndWorkflows();
  renderMembers();
  renderWorkflows();
  await loadAISettings();
}

// ── Members ──

function renderMembers() {
  const container = document.getElementById("member-list");
  if (state.members.length === 0) {
    container.innerHTML = `<div class="empty-col">メンバーがいません</div>`;
    return;
  }
  container.innerHTML = state.members.map(m => `
    <div class="member-item">
      <div class="member-info">
        <span class="member-color-dot" style="background:${escHtml(m.color)}"></span>
        <span class="member-name">${escHtml(m.name)}</span>
      </div>
      <div class="item-actions">
        <button class="btn btn-ghost btn-sm" onclick="openEditMemberModal(${m.id})">✏️ 編集</button>
        <button class="btn btn-danger btn-sm" onclick="deleteMember(${m.id})">🗑️ 削除</button>
      </div>
    </div>
  `).join("");
}

function openCreateMemberModal() {
  document.getElementById("member-form").reset();
  document.getElementById("member-id").value = "";
  document.getElementById("mb-color").value = "#6366f1";
  document.getElementById("mb-color-text").textContent = "#6366f1";
  document.getElementById("modal-member-title-text").textContent = "新規メンバー";
  state.currentMember = null;
  openModal("modal-member");
}

function openEditMemberModal(memberId) {
  const member = state.members.find(m => m.id === memberId);
  if (!member) return;
  state.currentMember = member;
  document.getElementById("member-id").value = member.id;
  document.getElementById("mb-name").value = member.name;
  document.getElementById("mb-color").value = member.color;
  document.getElementById("mb-color-text").textContent = member.color;
  document.getElementById("modal-member-title-text").textContent = "メンバー編集";
  openModal("modal-member");
}

document.getElementById("mb-color").addEventListener("input", (e) => {
  document.getElementById("mb-color-text").textContent = e.target.value;
});

document.getElementById("member-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("member-id").value;
  const body = {
    name:  document.getElementById("mb-name").value.trim(),
    color: document.getElementById("mb-color").value,
  };
  try {
    if (id) {
      await api.members.update(Number(id), body);
      showToast("メンバーを更新しました");
    } else {
      await api.members.create(body);
      showToast("メンバーを追加しました");
    }
    closeModal("modal-member");
    await loadSettings();
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

async function deleteMember(memberId) {
  const member = state.members.find(m => m.id === memberId);
  if (!confirm(`「${member?.name}」を削除しますか？`)) return;
  try {
    await api.members.delete(memberId);
    showToast("メンバーを削除しました");
    await loadSettings();
    await loadIssues(); // カードの担当者表示を更新
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

document.getElementById("btn-new-member").addEventListener("click", openCreateMemberModal);

// ── Workflows ──

function renderWorkflows() {
  const container = document.getElementById("workflow-list");
  if (state.workflows.length === 0) {
    container.innerHTML = `<div class="empty-col">ワークフローがありません</div>`;
    return;
  }
  container.innerHTML = state.workflows.map(wf => `
    <div class="workflow-item">
      <div class="workflow-info">
        <span class="workflow-name">${escHtml(wf.name)}</span>
        <span class="workflow-steps-preview">${wf.steps.map(s => escHtml(s)).join(" → ")}</span>
      </div>
      <div class="item-actions">
        <button class="btn btn-ghost btn-sm" onclick="openEditWorkflowModal(${wf.id})">✏️ 編集</button>
        <button class="btn btn-danger btn-sm" onclick="deleteWorkflow(${wf.id})">🗑️ 削除</button>
      </div>
    </div>
  `).join("");
}

function openCreateWorkflowModal() {
  document.getElementById("workflow-form").reset();
  document.getElementById("wf-id").value = "";
  document.getElementById("modal-workflow-title-text").textContent = "新規ワークフロー";
  state.currentWorkflow = null;
  openModal("modal-workflow");
}

function openEditWorkflowModal(workflowId) {
  const wf = state.workflows.find(w => w.id === workflowId);
  if (!wf) return;
  state.currentWorkflow = wf;
  document.getElementById("wf-id").value = wf.id;
  document.getElementById("wf-name").value = wf.name;
  document.getElementById("wf-steps").value = wf.steps.join(",");
  document.getElementById("modal-workflow-title-text").textContent = "ワークフロー編集";
  openModal("modal-workflow");
}

document.getElementById("workflow-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("wf-id").value;
  const stepsRaw = document.getElementById("wf-steps").value;
  const steps = stepsRaw.split(",").map(s => s.trim()).filter(Boolean);
  if (steps.length === 0) {
    showToast("ステップを1つ以上入力してください");
    return;
  }
  const body = {
    name:  document.getElementById("wf-name").value.trim(),
    steps,
  };
  try {
    if (id) {
      await api.workflows.update(Number(id), body);
      showToast("ワークフローを更新しました");
    } else {
      await api.workflows.create(body);
      showToast("ワークフローを追加しました");
    }
    closeModal("modal-workflow");
    await loadSettings();
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
});

async function deleteWorkflow(workflowId) {
  const wf = state.workflows.find(w => w.id === workflowId);
  if (!confirm(`「${wf?.name}」を削除しますか？`)) return;
  try {
    await api.workflows.delete(workflowId);
    showToast("ワークフローを削除しました");
    await loadSettings();
    await loadIssues();
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

document.getElementById("btn-new-workflow").addEventListener("click", openCreateWorkflowModal);

// ─── Modal helpers ───────────────────────────────────────────────────────────

function openModal(id) {
  const overlay = document.getElementById(id);
  overlay.style.display = "flex";
  requestAnimationFrame(() => overlay.classList.add("active"));
}

function closeModal(id) {
  const overlay = document.getElementById(id);
  overlay.classList.remove("active");
  overlay.addEventListener("transitionend", () => {
    overlay.style.display = "none";
    if (id === "modal-detail" && state.activeTab === "workflow") {
      renderWorkflowMatrix();
    }
  }, { once: true });
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

// ─── Report screen ────────────────────────────────────────────────────────────

const REPORT_TYPE_LABEL = { daily: "日報", weekly: "週報", monthly: "月報" };
const REPORT_TYPE_COLOR = { daily: "#4361ee", weekly: "#f77f00", monthly: "#2dc653" };

async function loadReports() {
  try {
    state.reports = await api.reports.list();
  } catch (e) {
    showToast(`レポート取得に失敗: ${e.message}`);
    return;
  }
  renderReportList();
}

function renderReportList() {
  const container = document.getElementById("report-list");
  if (state.reports.length === 0) {
    container.innerHTML = `<div class="empty-col">レポートがありません。⚡ 生成ボタンで作成してください。</div>`;
    return;
  }
  container.innerHTML = state.reports.map(r => `
    <div class="report-item">
      <div class="report-item-left">
        <span class="report-type-badge" style="background:${REPORT_TYPE_COLOR[r.report_type]}">${REPORT_TYPE_LABEL[r.report_type]}</span>
        <span class="report-item-title">${escHtml(r.title)}</span>
        <span class="${r.is_ai_generated ? "report-ai-badge" : "report-template-badge"}">
          ${r.is_ai_generated ? "🤖 AI" : "📋 テンプレ"}
        </span>
      </div>
      <div class="report-item-right">
        <span class="report-item-date">${r.created_at.slice(0, 10)}</span>
        <button class="btn btn-ghost btn-sm" onclick="openReportDetail(${r.id})">👁 表示</button>
        <button class="btn btn-danger btn-sm" onclick="deleteReport(${r.id})">🗑️</button>
      </div>
    </div>
  `).join("");
}

async function generateReport() {
  const targetDate = document.getElementById("report-target-date").value;
  if (!targetDate) {
    showToast("対象日を選択してください");
    return;
  }
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

async function openReportDetail(reportId) {
  try {
    const report = await api.reports.get(reportId);
    document.getElementById("report-modal-title").textContent = report.title;
    const badge = `<span class="report-type-badge" style="background:${REPORT_TYPE_COLOR[report.report_type]}">${REPORT_TYPE_LABEL[report.report_type]}</span>`;
    const ai = report.is_ai_generated
      ? `<span class="report-ai-badge">🤖 AI生成</span>`
      : `<span class="report-template-badge">📋 テンプレ</span>`;
    document.getElementById("report-modal-meta").innerHTML =
      `${badge} ${ai} <span class="report-period">${report.period_start} 〜 ${report.period_end}</span>`;
    document.getElementById("report-modal-content").innerHTML =
      typeof marked !== "undefined" ? marked.parse(report.content) : `<pre>${escHtml(report.content)}</pre>`;
    openModal("modal-report");
  } catch (e) {
    showToast(`レポート取得に失敗: ${e.message}`);
  }
}

async function deleteReport(reportId) {
  if (!confirm("このレポートを削除しますか？")) return;
  try {
    await api.reports.delete(reportId);
    state.reports = state.reports.filter(r => r.id !== reportId);
    renderReportList();
    showToast("レポートを削除しました");
  } catch (e) {
    showToast(`削除に失敗: ${e.message}`);
  }
}

// レポートタイプ切り替え
document.querySelectorAll(".report-type-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    state.reportType = btn.dataset.type;
    document.querySelectorAll(".report-type-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
  });
});

document.getElementById("btn-generate-report").addEventListener("click", generateReport);

// 日付のデフォルトを今日に設定
document.getElementById("report-target-date").value = new Date().toISOString().slice(0, 10);

// ─── AI Settings ─────────────────────────────────────────────────────────────

async function loadAISettings() {
  try {
    state.aiSettings = await api.aiSettings.get();
    renderAISettingsSummary();
  } catch (e) {
    // 設定取得失敗は無視
  }
}

function renderAISettingsSummary() {
  const container = document.getElementById("ai-settings-info");
  if (!container) return;
  const cfg = state.aiSettings;
  if (!cfg || !cfg.base_url) {
    container.innerHTML = `<p class="ai-settings-empty">AI設定が未設定です。編集ボタンから設定すると、AI生成モードが有効になります。</p>`;
    return;
  }
  container.innerHTML = `
    <div class="ai-settings-row"><span class="ai-settings-key">Base URL</span><span class="ai-settings-val">${escHtml(cfg.base_url)}</span></div>
    <div class="ai-settings-row"><span class="ai-settings-key">Model</span><span class="ai-settings-val">${escHtml(cfg.model || "未設定")}</span></div>
    <div class="ai-settings-row"><span class="ai-settings-key">API Key</span><span class="ai-settings-val">${cfg.has_api_key ? "設定済み ✅" : "未設定"}</span></div>
  `;
}

function openAISettingsModal() {
  const cfg = state.aiSettings;
  document.getElementById("ai-base-url").value = cfg?.base_url || "";
  document.getElementById("ai-api-key").value = "";
  document.getElementById("ai-model").value = cfg?.model || "";
  openModal("modal-ai-settings");
}

document.getElementById("btn-edit-ai-settings").addEventListener("click", openAISettingsModal);

document.getElementById("ai-settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    base_url: document.getElementById("ai-base-url").value.trim(),
    api_key:  document.getElementById("ai-api-key").value,
    model:    document.getElementById("ai-model").value.trim(),
  };
  try {
    state.aiSettings = await api.aiSettings.update(body);
    renderAISettingsSummary();
    closeModal("modal-ai-settings");
    showToast("AI設定を保存しました");
  } catch (e) {
    showToast(`保存に失敗: ${e.message}`);
  }
});

// ── ワークフロー AI提案 ────────────────────────────────────────────────
async function openSuggestWorkflowModal(category = '') {
  const modal = document.getElementById('modal-suggest-workflow');
  document.getElementById('suggest-loading').style.display = 'block';
  document.getElementById('suggest-result').style.display = 'none';
  document.getElementById('suggest-category').value = category;
  modal.style.display = 'flex';

  try {
    const data = await api.ai.suggestWorkflow(category || null);
    document.getElementById('suggest-name').value = data.suggested_name;
    document.getElementById('suggest-reason').textContent =
      (data.is_ai_generated ? '🤖 AI分析: ' : '📋 テンプレート: ') + data.reason;

    const stepsList = document.getElementById('suggest-steps-list');
    stepsList.innerHTML = data.suggested_steps
      .map(s => `<span class="suggest-step-badge">${s}</span>`)
      .join('<span class="suggest-step-arrow">→</span>');

    // 承認ボタンに提案データを保持
    document.getElementById('btn-approve-workflow').dataset.steps =
      JSON.stringify(data.suggested_steps);

    document.getElementById('suggest-loading').style.display = 'none';
    document.getElementById('suggest-result').style.display = 'block';
  } catch (e) {
    document.getElementById('suggest-loading').innerHTML = '<p style="color:red">提案の取得に失敗しました</p>';
  }
}

document.getElementById('btn-suggest-workflow').addEventListener('click', () => {
  openSuggestWorkflowModal();
});

document.getElementById('btn-close-suggest-workflow').addEventListener('click', () => {
  document.getElementById('modal-suggest-workflow').style.display = 'none';
});

document.getElementById('btn-cancel-suggest-workflow').addEventListener('click', () => {
  document.getElementById('modal-suggest-workflow').style.display = 'none';
});

document.getElementById('btn-re-suggest').addEventListener('click', () => {
  const cat = document.getElementById('suggest-category').value.trim();
  document.getElementById('suggest-loading').style.display = 'block';
  document.getElementById('suggest-loading').innerHTML = '<div class="spinner"></div><p>タスクを分析中...</p>';
  document.getElementById('suggest-result').style.display = 'none';
  api.ai.suggestWorkflow(cat || null).then(data => {
    document.getElementById('suggest-name').value = data.suggested_name;
    document.getElementById('suggest-reason').textContent =
      (data.is_ai_generated ? '🤖 AI分析: ' : '📋 テンプレート: ') + data.reason;
    const stepsList = document.getElementById('suggest-steps-list');
    stepsList.innerHTML = data.suggested_steps
      .map(s => `<span class="suggest-step-badge">${s}</span>`)
      .join('<span class="suggest-step-arrow">→</span>');
    document.getElementById('btn-approve-workflow').dataset.steps =
      JSON.stringify(data.suggested_steps);
    document.getElementById('suggest-loading').style.display = 'none';
    document.getElementById('suggest-result').style.display = 'block';
  }).catch(() => {
    document.getElementById('suggest-loading').innerHTML = '<p style="color:red">再提案に失敗しました</p>';
  });
});

document.getElementById('btn-approve-workflow').addEventListener('click', async () => {
  const name = document.getElementById('suggest-name').value.trim();
  const steps = JSON.parse(document.getElementById('btn-approve-workflow').dataset.steps || '[]');
  if (!name || steps.length === 0) return;
  try {
    await api.workflows.create({ name, steps });
    document.getElementById('modal-suggest-workflow').style.display = 'none';
    await loadWorkflows();
    renderWorkflowSettings();
    renderWorkflowMatrix();
  } catch (e) {
    alert('ワークフローの保存に失敗しました');
  }
});

// ─── Init ────────────────────────────────────────────────────────────────────

document.getElementById("log-date").value = new Date().toISOString().slice(0, 10);
document.getElementById("btn-new-issue").addEventListener("click", openCreateModal);

// URL ハッシュからタブ復元
const initialTab = location.hash.replace("#", "") || "board";
switchTab(["board", "memo", "workflow", "report", "settings"].includes(initialTab) ? initialTab : "board");

// 初期読み込み
loadMembersAndWorkflows().then(() => loadIssues());

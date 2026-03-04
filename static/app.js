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

  const hasFooter = assigneeHtml || wfStepHtml;

  card.innerHTML = `
    <div class="card-title">${escHtml(issue.title)}</div>
    <div class="card-meta">
      <span class="priority-badge ${issue.priority}">${PRIORITY_LABEL[issue.priority]}</span>
      ${issue.category ? `<span class="category-badge">${escHtml(issue.category)}</span>` : ""}
      ${tags}
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

    await renderLogs(issue.id);
    openModal("modal-detail");
  } catch (e) {
    showToast(`エラー: ${e.message}`);
  }
}

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

// ─── Settings screen ──────────────────────────────────────────────────────────

async function loadSettings() {
  await loadMembersAndWorkflows();
  renderMembers();
  renderWorkflows();
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

document.getElementById("log-date").value = new Date().toISOString().slice(0, 10);
document.getElementById("btn-new-issue").addEventListener("click", openCreateModal);

// URL ハッシュからタブ復元
const initialTab = location.hash.replace("#", "") || "board";
switchTab(["board", "memo", "settings"].includes(initialTab) ? initialTab : "board");

// 初期読み込み
loadMembersAndWorkflows().then(() => loadIssues());

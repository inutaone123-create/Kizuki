<!-- 公開URL: https://qiita.com/inuta-one/items/1f167bde2159ac53a030 -->
---
title: 【Kizuki 機能追加】ワークフロー横断ビューをバックエンド変更ゼロ・Vanilla JS だけで実装した
tags:
  - JavaScript
  - FastAPI
  - 個人開発
  - フロントエンド
  - カンバン
emoji: 🔄
type: tech
topics: []
published: false
---

## はじめに

前回の記事（[【Kizuki 機能追加】認証なしで使える「担当者アサイン」と「カスタムワークフロー」をFastAPI + Vanilla JSで実装した](https://qiita.com/inuta-one/items/559b22ff5daca1763711)）では、個人用カンバンツール「Kizuki」にワークフロー定義と担当者アサインを追加しました。

今回は「**ワークフローを横断して全イシューの進捗を一覧できるビュー**」を新タブとして追加します。

ポイントは **バックエンド（FastAPI/SQLite）を一切変更せず、フロントエンド3ファイルだけで完結**させたことです。既存の `buildCard()` / `openDetail()` 関数を流用することで、重複コードゼロ・追加行数158行という軽量実装になりました。

---

## 背景・動機

前回実装したワークフロー機能では、各イシューのカード上に「現在のステップ」が小さく表示されます。

```
┌──────────────────┐
│ タスクA           │
│ 🔴 高  バックエンド│
│ 🔄 承認           │  ← ステップが小さい
└──────────────────┘
```

これでも確認はできますが、「承認フローに乗っているイシューが今どのステップに何件あるか」を**一覧で把握したい**という需要があります。

そこで「ワークフロー × ステップ」を軸にしたカンバンビューを追加することにしました。

```
【承認フロー】
  申請(2件)  →  承認(1件)  →  実行(3件)  →  完了(5件)
  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
  │タスクA │    │タスクC │    │タスクD │    │タスクG │
  │タスクB │    └────────┘    │タスクE │    │...     │
  └────────┘                  └────────┘    └────────┘
```

---

## 設計の判断

### バックエンドを変更しない

`IssueListResponse` には前回の実装で `workflow`・`assignee` のネストオブジェクトが既に含まれています。

```json
{
  "id": 1,
  "title": "タスクA",
  "workflow_id": 2,
  "workflow_step": 1,
  "workflow": {
    "id": 2,
    "name": "承認フロー",
    "steps": ["申請", "承認", "実行", "完了"]
  },
  "assignee": { "id": 1, "name": "田中", "color": "#6366f1" }
}
```

必要なデータは **既存の `/api/issues`・`/api/workflows` の2エンドポイントだけ**で揃います。バックエンド変更ゼロで実現できます。

### buildCard() / openDetail() を流用する

カード描画ロジックを再実装すると、スタイル変更時に2箇所を直す必要が生まれます。既存の `buildCard(issue)` をそのまま呼ぶことで、カンバンビューとワークフローマトリクスビューは**常に同じカード表示**を共有します。

---

## 実装

変更ファイルは3つだけです。

| ファイル | 変更内容 |
|---------|---------|
| `static/index.html` | タブボタン・タブコンテンツ追加（+6行） |
| `static/app.js` | `loadWorkflowMatrix` / `renderWorkflowMatrix` 追加（+85行） |
| `static/style.css` | ワークフローマトリクス用スタイル追加（+67行） |

### index.html — タブ追加

```html
<!-- タブバーに「🔄 ワークフロー」を追加 -->
<nav class="tab-bar">
  <button class="tab-btn active" data-tab="board">🏯 カンバン</button>
  <button class="tab-btn" data-tab="memo">📝 メモ</button>
  <button class="tab-btn" data-tab="workflow">🔄 ワークフロー</button>  <!-- 追加 -->
  <button class="tab-btn" data-tab="settings">⚙ 設定</button>
</nav>

<!-- タブコンテンツ -->
<div class="workflow-matrix-screen tab-content" id="tab-workflow">
  <div id="workflow-matrix-body"></div>
</div>
```

### app.js — データ取得関数

```javascript
async function loadWorkflowMatrix() {
  try {
    // 既存の state.issues・state.workflows を並列フェッチで更新
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
```

`Promise.all` で3つのAPIを並列取得することで、逐次待ちを避けています。

### app.js — グループ化ロジックが核心

```javascript
function renderWorkflowMatrix() {
  const container = document.getElementById("workflow-matrix-body");
  container.innerHTML = "";

  // ワークフローIDごと・ステップインデックスごとにイシューを分類
  const grouped = {};  // { wfId: { stepIdx: [issues] } }
  state.issues
    .filter(i => i.workflow_id != null)          // ワークフロー未割当は除外
    .forEach(issue => {
      const wfId = issue.workflow_id;
      const step = issue.workflow_step ?? 0;
      if (!grouped[wfId]) grouped[wfId] = {};
      if (!grouped[wfId][step]) grouped[wfId][step] = [];
      grouped[wfId][step].push(issue);
    });

  // ワークフローに1件もイシューがなければ早期リターン
  if (Object.keys(grouped).length === 0) {
    container.innerHTML = `<div class="empty-col">ワークフローに割り当てられたイシューがありません</div>`;
    return;
  }

  state.workflows.forEach(wf => {
    if (!grouped[wf.id]) return;  // イシュー0件のワークフローセクションは非表示

    // ステップ数に応じてグリッドカラムを動的生成
    const board = document.createElement("div");
    board.className = "wf-matrix-board";
    board.style.gridTemplateColumns = `repeat(${wf.steps.length}, 220px)`;

    wf.steps.forEach((stepName, stepIdx) => {
      const issues = (grouped[wf.id] && grouped[wf.id][stepIdx]) || [];

      const body = document.createElement("div");
      body.className = "wf-matrix-col-body";

      // ★ 既存の buildCard() をそのまま流用 — 重複コードゼロ
      if (issues.length === 0) {
        body.innerHTML = `<div class="empty-col">なし</div>`;
      } else {
        issues.forEach(issue => body.appendChild(buildCard(issue)));
      }
      // ... (カラムヘッダー等の組み立て)
    });
  });
}
```

### style.css — 横スクロール対応の CSS Grid

ステップ数が多いワークフローでも崩れないよう、`min-width: max-content` と `overflow-x: auto` を組み合わせています。

```css
.workflow-matrix-screen {
  padding: 20px 24px;
  overflow-x: auto;          /* コンテナをスクロール可能に */
}

.wf-matrix-board {
  display: grid;
  gap: 12px;
  min-width: max-content;    /* カラム数に応じて幅を自動拡張 */
  /* grid-template-columns は JS で動的に設定 */
}

.wf-matrix-column {
  width: 220px;              /* 各カラムは固定幅 */
  background: var(--surface2);
  border-radius: var(--radius);
}

.wf-matrix-col-header {
  background: var(--accent); /* 既存のCSS変数を活用 */
  color: #fff;
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
```

`grid-template-columns: repeat(N, 220px)` の `N` は JavaScript 側でワークフローのステップ数から動的に設定します。CSS 変数（`--accent`・`--radius` など）を共用することで、テーマ変更が全体に一括反映されます。

---

## ハマりどころ

### loadIssues() をそのまま呼ぶと renderBoard() も走る

最初のアプローチは既存の `loadIssues()` を呼んでいましたが、この関数は `renderBoard()` も含んでいるため、カンバンタブを再描画する余計な処理が走ります。

```javascript
// ❌ 最初のアプローチ
async function loadWorkflowMatrix() {
  await loadIssues();  // renderBoard() も走ってしまう
  renderWorkflowMatrix();
}

// ✅ 修正後：直接 API を呼んで state だけ更新
async function loadWorkflowMatrix() {
  [state.members, state.workflows, state.issues] = await Promise.all([
    api.members.list(),
    api.workflows.list(),
    api.issues.list(),
  ]);
  renderWorkflowMatrix();
}
```

### CSS Grid の列数を動的に設定する

ワークフローごとにステップ数が異なるため、`grid-template-columns` を CSS に静的に書けません。JavaScript で `element.style.gridTemplateColumns` を直接書き込むのが最もシンプルです。

```javascript
board.style.gridTemplateColumns = `repeat(${wf.steps.length}, 220px)`;
```

### モーダルを閉じてもマトリクスが更新されない

ワークフロービューでイシューを開き、詳細モーダル内でステップを変更したあと、モーダルを閉じても**背景のマトリクスが更新されない**という問題がありました。

原因は `closeModal()` が汎用関数になっており、閉じた後の再描画処理がなかったことです。

```javascript
// ❌ 修正前
function closeModal(id) {
  const overlay = document.getElementById(id);
  overlay.classList.remove("active");
  overlay.addEventListener("transitionend", () => {
    overlay.style.display = "none";  // ここで終わっていた
  }, { once: true });
}
```

ステップ変更時に `loadIssues()` で `state.issues` は最新化されているのに、`renderWorkflowMatrix()` が呼ばれていないのが原因です。`closeModal()` の `transitionend` フックに、ワークフロータブの場合のみ再描画を差し込みました。

```javascript
// ✅ 修正後
function closeModal(id) {
  const overlay = document.getElementById(id);
  overlay.classList.remove("active");
  overlay.addEventListener("transitionend", () => {
    overlay.style.display = "none";
    // ワークフロータブで詳細モーダルを閉じた時だけ再描画
    if (id === "modal-detail" && state.activeTab === "workflow") {
      renderWorkflowMatrix();
    }
  }, { once: true });
}
```

`id === "modal-detail"` と `state.activeTab === "workflow"` の2条件で絞ることで、他のタブやモーダルには影響しません。

---

## ソースコード

https://github.com/inutaone123-create/Kizuki

---

## まとめ

- **バックエンド変更ゼロ** — 既存の `/api/issues` レスポンスに必要なデータが揃っていたため、フロントのみで実装完了
- **重複コードゼロ** — `buildCard()` / `openDetail()` を流用することで、カンバンとマトリクスが常に同じ表示を共有
- **158行の追加**で新タブ + 横スクロール対応カンバンを実現
- CSS 変数を使い回すことで、テーマ変更が全ビューに一括反映
- **汎用関数への最小フック** — `closeModal()` に2条件の分岐を追加するだけで、他のタブ・モーダルに影響なく再描画を実現

「表示ビューの追加は新しいバックエンドAPIが必要」という思い込みがありましたが、既存データの**グループ化とレイアウトの工夫**だけで十分なケースも多いと実感しました。

---

## 参考

- [前回記事（第3弾）: 担当者アサイン・ワークフロー定義](https://qiita.com/inuta-one/items/559b22ff5daca1763711)
- [FastAPI 公式ドキュメント](https://fastapi.tiangolo.com/)
- [MDN: CSS Grid Layout](https://developer.mozilla.org/ja/docs/Web/CSS/CSS_grid_layout)
- [MDN: Promise.all()](https://developer.mozilla.org/ja/docs/Web/JavaScript/Reference/Global_Objects/Promise/all)

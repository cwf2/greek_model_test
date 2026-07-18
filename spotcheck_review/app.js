const MODEL_PREFIXES = ["lg", "trf", "odycy"];
const MODEL_LABELS = { lg: "grc_dep_web_lg", trf: "grc_dep_web_trf", odycy: "grc_odycy_joint_trf" };
const MORPH_FIELDS = ["pos", "lemma", "gender", "case", "number", "tense", "mood", "voice"];
const JUDGEMENT_SUGGESTIONS = [
  "lg", "trf", "odycy", "lg+trf", "lg+odycy", "trf+odycy", "all", "none", "ambiguous"
];

let fieldnames = [];
let rows = [];       // full list, each row carries _idx (0-based index into rows / CSV data rows)
let filtered = [];   // array of row objects currently visible, respecting filters
let pos = 0;         // position within `filtered`
let saveTimer = null;

const app = document.getElementById("app");
const posLabel = document.getElementById("posLabel");
const categoryFilter = document.getElementById("categoryFilter");
const judgementFilter = document.getElementById("judgementFilter");
const reviewOnly = document.getElementById("reviewOnly");
const jumpBox = document.getElementById("jumpBox");
const saveStatus = document.getElementById("saveStatus");

async function init() {
  const res = await fetch("/api/rows");
  const data = await res.json();
  fieldnames = data.fieldnames;
  rows = data.rows.map((r, i) => ({ ...r, _idx: i }));

  populateFilterOptions();
  applyFilters();
  render();

  document.getElementById("prevBtn").onclick = () => go(-1);
  document.getElementById("nextBtn").onclick = () => go(1);
  categoryFilter.onchange = () => { applyFilters(); pos = 0; render(); };
  judgementFilter.onchange = () => { applyFilters(); pos = 0; render(); };
  reviewOnly.onchange = () => { applyFilters(); pos = 0; render(); };
  document.getElementById("jumpBtn").onclick = jumpToRow;
  jumpBox.onkeydown = (e) => { if (e.key === "Enter") jumpToRow(); };

  document.addEventListener("keydown", (e) => {
    const tag = document.activeElement.tagName;
    if (tag === "TEXTAREA" || tag === "INPUT") return;
    if (e.key === "ArrowLeft") go(-1);
    if (e.key === "ArrowRight") go(1);
  });
}

function populateFilterOptions() {
  const categories = [...new Set(rows.map((r) => r.category))].sort();
  for (const c of categories) {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    categoryFilter.appendChild(opt);
  }
  const judgements = [...new Set(rows.map((r) => r.human_judgement).filter(Boolean))].sort();
  for (const j of judgements) {
    const opt = document.createElement("option");
    opt.value = j;
    opt.textContent = j;
    judgementFilter.appendChild(opt);
  }
}

function applyFilters() {
  flushPendingSave();
  filtered = rows.filter((r) => {
    if (categoryFilter.value && r.category !== categoryFilter.value) return false;
    if (judgementFilter.value && r.human_judgement !== judgementFilter.value) return false;
    if (reviewOnly.checked && !/REVIEW/.test(r.notes || "")) return false;
    return true;
  });
  if (pos >= filtered.length) pos = Math.max(0, filtered.length - 1);
}

function go(delta) {
  flushPendingSave();
  pos = Math.min(Math.max(pos + delta, 0), filtered.length - 1);
  render();
}

function jumpToRow() {
  const n = parseInt(jumpBox.value, 10);
  if (!n || n < 1 || n > rows.length) return;
  flushPendingSave();
  categoryFilter.value = "";
  judgementFilter.value = "";
  reviewOnly.checked = false;
  applyFilters();
  pos = n - 1;
  render();
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderContext(row) {
  const raw = row.context || "";
  if (raw.includes("[[")) {
    return escapeHtml(raw)
      .replace(/\[\[(.+?)\]\]/g, '<mark>$1</mark>');
  }
  return escapeHtml(raw);
}

function render() {
  if (filtered.length === 0) {
    app.innerHTML = "<p>No rows match the current filters.</p>";
    posLabel.textContent = "0 of 0";
    return;
  }
  const row = filtered[pos];
  posLabel.textContent = `row ${row._idx + 1} of ${rows.length}  (filtered ${pos + 1}/${filtered.length})`;

  const morphRows = MORPH_FIELDS.map((field) => {
    const vals = MODEL_PREFIXES.map((m) => row[`${m}_${field}`] || "");
    if (vals.every((v) => !v)) return "";
    return `<tr><th>${field}</th>${vals.map((v) => `<td>${escapeHtml(v)}</td>`).join("")}</tr>`;
  }).join("");

  app.innerHTML = `
    <div class="card">
      <div class="meta">
        <span class="category">${escapeHtml(row.category)}</span>
        <span class="work">${escapeHtml(row.work)}</span>
        <span class="urn">${escapeHtml(row.urn)}</span>
      </div>
      ${row.text ? `<div class="token">${escapeHtml(row.text)}</div>` : ""}
      <div class="context">${renderContext(row)}</div>

      <table class="morph-table">
        <thead>
          <tr><th></th>${MODEL_PREFIXES.map((m) => `<th>${MODEL_LABELS[m]}</th>`).join("")}</tr>
        </thead>
        <tbody>${morphRows}</tbody>
      </table>

      <div class="edit-block">
        <label>human_judgement
          <input type="text" id="judgementInput" list="judgementSuggestions" value="${escapeHtml(row.human_judgement)}">
          <datalist id="judgementSuggestions">
            ${JUDGEMENT_SUGGESTIONS.map((s) => `<option value="${s}">`).join("")}
          </datalist>
        </label>
        <label>notes
          <textarea id="notesInput" rows="6">${escapeHtml(row.notes)}</textarea>
        </label>
      </div>
    </div>
  `;

  const judgementInput = document.getElementById("judgementInput");
  const notesInput = document.getElementById("notesInput");
  judgementInput.oninput = () => scheduleSave(row);
  notesInput.oninput = () => scheduleSave(row);
  judgementInput.onblur = () => flushPendingSave();
  notesInput.onblur = () => flushPendingSave();
}

function scheduleSave(row) {
  saveStatus.textContent = "editing…";
  saveStatus.className = "";
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => doSave(row), 700);
}

function flushPendingSave() {
  if (!saveTimer) return;
  clearTimeout(saveTimer);
  saveTimer = null;
  const judgementInput = document.getElementById("judgementInput");
  const notesInput = document.getElementById("notesInput");
  if (!judgementInput) return;
  const row = filtered[pos];
  if (row) doSave(row);
}

async function doSave(row) {
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
  const judgementInput = document.getElementById("judgementInput");
  const notesInput = document.getElementById("notesInput");
  if (!judgementInput || !notesInput) return;
  const payload = {
    human_judgement: judgementInput.value,
    notes: notesInput.value,
  };
  saveStatus.textContent = "saving…";
  try {
    const res = await fetch(`/api/rows/${row._idx}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    Object.assign(row, payload);
    saveStatus.textContent = "saved ✓";
    saveStatus.className = "ok";
    setTimeout(() => { if (saveStatus.textContent === "saved ✓") saveStatus.textContent = ""; }, 1500);
  } catch (err) {
    saveStatus.textContent = "save failed";
    saveStatus.className = "error";
    console.error(err);
  }
}

window.addEventListener("beforeunload", (e) => {
  if (saveTimer) {
    flushPendingSave();
  }
});

init();

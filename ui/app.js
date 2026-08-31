/* Lesson Forge — console logic (vanilla JS, no frameworks) */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const els = {
  navItems: $$(".nav-item"),
  views: $$(".view"),
  topic: $("#topic-input"),
  btnRun: $("#btn-run"),
  chkError: $("#chk-error"),
  runTag: $("#run-state-tag"),
  runMeta: $("#run-meta"),
  metaRunId: $("#meta-runid"),
  metaTopic: $("#meta-topic"),
  bigStatus: $("#big-status"),
  bigLabel: $("#big-label"),
  attemptCells: $$(".attempt-cell"),
  cpCells: $$(".cp"),
  log: $("#log"),
  lessonBody: $("#lesson-body"),
  lessonMeta: $("#lesson-meta"),
  traceList: $("#trace-list"),
  memGrid: $("#mem-grid"),
  toast: $("#toast"),
  apiStatus: $("#api-status"),
  cfgGen: $("#cfg-gen"),
  cfgEval: $("#cfg-eval"),
  cfgRetry: $("#cfg-retry"),
  cfgFlesch: $("#cfg-flesch"),
};

const state = { running: false, lastLesson: "", lastDraft: false };

/* ── navigation ──────────────────────────────────────────── */
els.navItems.forEach((btn) =>
  btn.addEventListener("click", () => {
    els.navItems.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.dataset.view;
    els.views.forEach((v) => v.classList.remove("active"));
    $("#view-" + target).classList.add("active");
    if (target === "lesson") loadLesson();
    if (target === "trace") renderTrace();
    if (target === "memory") loadMemory();
  })
);

/* ── toast ───────────────────────────────────────────────── */
let toastTimer;
function toast(msg) {
  els.toast.textContent = msg;
  els.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

/* ── logging ─────────────────────────────────────────────── */
function logLine(kind, msg) {
  const now = new Date();
  const t = now.toLocaleTimeString("en-GB", { hour12: false });
  const div = document.createElement("div");
  div.className = "log-line " + kind;
  const time = document.createElement("span");
  time.className = "log-t";
  time.textContent = t;
  const body = document.createElement("span");
  body.className = "log-msg";
  body.innerHTML = msg;
  div.append(time, body);
  els.log.appendChild(div);
  els.log.scrollTop = els.log.scrollHeight;
}

/* ── pipeline visual state ──────────────────────────────── */
function resetVisuals() {
  els.bigStatus.className = "big-status";
  els.bigLabel.textContent = "Waiting to start";
  els.runTag.className = "tag";
  els.runTag.textContent = "idle";
  els.attemptCells.forEach((c) => (c.className = "attempt-cell"));
  els.cpCells.forEach((c) => (c.className = "cp"));
  els.log.innerHTML = "";
  els.metaRunId.textContent = "run id —";
  els.metaTopic.textContent = "";
}

function setAttemptVisual(n, status) {
  const cell = $(`.attempt-cell[data-n="${n}"]`);
  if (cell) cell.className = "attempt-cell " + status;
}

function setCheckpointVisual(name, status) {
  const cell = $(`.cp[data-cp="${name}"]`);
  if (cell) cell.className = "cp " + status;
}

/* ── run ─────────────────────────────────────────────────── */
els.btnRun.addEventListener("click", startRun);

async function startRun() {
  if (state.running) return;
  const topic = els.topic.value.trim() || "Introduction to RAG";
  const inject = els.chkError.checked ? "jargon" : "";
  const url = `/api/run?topic=${encodeURIComponent(topic)}${inject ? "&inject_error=jargon" : ""}`;

  state.running = true;
  els.btnRun.disabled = true;
  els.btnRun.querySelector(".btn-label").textContent = "Running…";
  resetVisuals();

  els.bigStatus.className = "big-status running";
  els.bigLabel.textContent = "Generating lesson…";
  els.runTag.className = "tag running";
  els.runTag.textContent = "running";

  if (inject) logLine("gold", "demo mode on — deliberate jargon flaw will be injected");
  logLine("sys", `starting pipeline for <b>${esc(topic)}</b>`);

  try {
    const res = await fetch(url);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        try {
          handleEvent(JSON.parse(line.slice(5)));
        } catch { /* partial frame */ }
      }
    }
  } catch (err) {
    logLine("fail", "connection to server lost — is the backend running?");
  }

  state.running = false;
  els.btnRun.disabled = false;
  els.btnRun.querySelector(".btn-label").textContent = "Run pipeline";
}

/* ── SSE event handling ──────────────────────────────────── */
function handleEvent(ev) {
  switch (ev.type) {
    case "start":
      els.metaRunId.textContent = "run id " + ev.run_id.slice(0, 8);
      els.metaTopic.textContent = ev.topic;
      logLine("sys", `run <b>${ev.run_id.slice(0, 8)}</b> initialised`);
      break;

    case "memory":
      if (ev.count > 0) {
        logLine("sys", `memory: loaded <b>${ev.count}</b> learned rule(s) from past runs`);
      } else {
        logLine("sys", "memory: no learned rules yet — starting clean");
      }
      break;

    case "generate": {
      setAttemptVisual(ev.attempt, "active");
      els.bigStatus.className = "big-status running";
      els.bigLabel.textContent = `Generating lesson (attempt ${ev.attempt})…`;
      const extra = ev.inject_error ? " + deliberate jargon flaw" : "";
      logLine("sys", `attempt <b>${ev.attempt}</b> — lesson generated (${ev.chars} chars${extra})`);
      els.cpCells.forEach((c) => (c.className = "cp running"));
      els.bigLabel.textContent = `Evaluating (attempt ${ev.attempt})…`;
      break;
    }

    case "evaluate": {
      const failed = (ev.checkpoints || []).filter((c) => !c.passed);
      ev.checkpoints.forEach((c) =>
        setCheckpointVisual(c.name, c.passed ? "pass" : "fail")
      );
      if (ev.passed) {
        logLine("pass", `attempt <b>${ev.attempt}</b> — all 6 checkpoints passed`);
        setAttemptVisual(ev.attempt, "pass");
        els.bigStatus.className = "big-status passed";
        els.bigLabel.textContent = "All checkpoints passed";
      } else {
        const names = failed.map((f) => f.name).join(", ");
        logLine("fail", `attempt <b>${ev.attempt}</b> failed: ${esc(names)}`);
        failed.forEach((f) => logLine("fail", "&nbsp;&nbsp;✗ " + esc(f.reason)));
        setAttemptVisual(ev.attempt, "fail");
        els.bigLabel.textContent = "Fixing failures and regenerating…";
        (ev.instructions || []).slice(0, 3).forEach((i) =>
          logLine("gold", "&nbsp;&nbsp;→ " + esc(i))
        );
      }
      break;
    }

    case "rejection":
      logLine("sys", "rejection recorded in trace");
      break;

    case "memory_written":
      logLine("sys", "run result persisted to learning memory");
      break;

    case "done":
      state.lastStatus = ev.status;
      els.runTag.className = "tag " + (ev.status === "passed" ? "passed" : "failed");
      els.runTag.textContent = ev.status === "passed" ? "passed" : "failed bar";
      if (ev.status === "passed") {
        logLine("pass", `<b>ACCEPTED</b> — lesson cleared the quality bar in ${ev.attempts} attempt(s)`);
      } else {
        els.bigStatus.className = "big-status failed";
        els.bigLabel.textContent = "Quality bar not cleared";
        logLine("fail", `<b>REJECTED</b> — quality bar not cleared after ${ev.attempts} attempts`);
      }
      break;

    case "lesson":
      state.lastLesson = ev.content || "";
      state.lastDraft = !!ev.draft;
      break;

    case "rejections":
      state.lastRejections = ev.entries || [];
      renderTrace();
      break;

    case "error":
      logLine("fail", "pipeline error: " + esc(ev.message));
      els.bigStatus.className = "big-status failed";
      els.bigLabel.textContent = "Pipeline error";
      els.runTag.className = "tag failed";
      els.runTag.textContent = "error";
      break;
  }
}

/* ── trace rendering ─────────────────────────────────────── */
async function renderTrace() {
  // Disk-backed rejection log is the authoritative trace (the run writes it
  // at finalize), so read it from the API rather than in-memory SSE state.
  let entries = [];
  let logStatus = null;
  try {
    const res = await fetch("/api/rejection_log");
    const data = await res.json();
    if (data.exists) {
      entries = reconstructEntries(data.data);
      logStatus = data.data.final_status;
    }
  } catch { /* server unreachable — fall back to SSE state below */ }
  if (!entries.length) entries = state.lastRejections || [];

  if (!entries || entries.length === 0) {
    els.traceList.innerHTML = '<p class="empty">No failures recorded in the last run.</p>';
    return;
  }

  // If the run ultimately passed, the final failed attempt was fixed by the
  // last regeneration — the disk log has no further entry to compare against.
  const runPassed = logStatus === "passed" || state.lastStatus === "passed";

  els.traceList.innerHTML = "";
  entries.forEach((e, i) => {
    const next = entries[i + 1];
    let statusHtml = runPassed
      ? '<span class="trace-status fixed">✓ fixed on next attempt</span>'
      : '<span class="trace-status exhaust">retries exhausted</span>';
    if (next) {
      if (next.overall_pass) {
        statusHtml = '<span class="trace-status fixed">✓ fixed on next attempt</span>';
      } else {
        const stillFailing = (next.failed_checkpoints || []).some((c) =>
          (e.failed_checkpoints || []).some((f) => f.name === c.name)
        );
        statusHtml = stillFailing
          ? '<span class="trace-status regress">✗ failed again</span>'
          : '<span class="trace-status fixed">✓ fixed on next attempt</span>';
      }
    }

    (e.failed_checkpoints || []).forEach((fc) => {
      const card = document.createElement("div");
      card.className = "trace-card";
      card.innerHTML = `
        <div class="trace-top">
          <span class="trace-attempt">attempt ${e.attempt_number}</span>
          <span class="trace-cp">${esc(fc.name.replace(/_/g, " "))}</span>
          ${statusHtml}
        </div>
        <div class="trace-row">
          <div class="trace-label">Why it failed</div>
          <div class="trace-text">${esc(fc.reason)}</div>
        </div>
        ${
          e.instruction_given_for_next_attempt
            ? `<div class="trace-row">
                 <div class="trace-label">What the generator was told</div>
                 <div class="trace-text">${esc(e.instruction_given_for_next_attempt)}</div>
               </div>`
            : ""
        }
      `;
      els.traceList.appendChild(card);
    });
  });
}

/* Build attempt entries from the on-disk rejection log format. */
function reconstructEntries(logData) {
  if (!logData || !Array.isArray(logData.corrections)) return [];
  // The on-disk log stores one flat correction per failed checkpoint per
  // attempt; attempt numbers run 1..N in order for failures, and each
  // correction carries its own next-attempt result.
  let attempt = 0;
  return logData.corrections.map((c) => {
    attempt += 1;
    return {
      attempt_number: c.attempt_number || attempt,
      failed_checkpoints: [{ name: c.failed_checkpoint, reason: c.why }],
      instruction_given_for_next_attempt: c.retry_instruction,
      next_attempt_result: c.next_attempt_result,
    };
  });
}

/* ── lesson rendering ────────────────────────────────────── */
async function loadLesson() {
  try {
    const res = await fetch("/api/lesson");
    const data = await res.json();
    if (!data.exists) {
      els.lessonBody.innerHTML = '<p class="empty">Run the pipeline first — the accepted lesson will appear here.</p>';
      return;
    }
    state.lastLesson = data.content;
    els.lessonBody.innerHTML = renderMarkdown(state.lastLesson);
    els.lessonMeta.textContent = state.lastDraft
      ? "Diagnostic draft — this run did not clear the quality bar."
      : "The accepted lesson from the last passing run.";
  } catch {
    els.lessonBody.innerHTML = '<p class="empty">Could not reach the server.</p>';
  }
}

function renderMarkdown(src) {
  const escAll = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const lines = escAll(src).split("\n");
  let html = "";
  let inList = false;
  let para = [];

  const flushPara = () => {
    if (para.length) {
      html += "<p>" + inline(para.join(" ")) + "</p>";
      para = [];
    }
  };
  const closeList = () => {
    if (inList) { html += "</ul>"; inList = false; }
  };

  const inline = (s) =>
    s
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`(.+?)`/g, "<code>$1</code>");

  for (const line of lines) {
    const t = line.trim();
    if (!t) { flushPara(); closeList(); continue; }

    if (t.startsWith("### ")) { flushPara(); closeList(); html += `<h3>${inline(t.slice(4))}</h3>`; }
    else if (t.startsWith("## ")) { flushPara(); closeList(); html += `<h2>${inline(t.slice(3))}</h2>`; }
    else if (t.startsWith("# ")) { flushPara(); closeList(); html += `<h1>${inline(t.slice(2))}</h1>`; }
    else if (t === "---") { flushPara(); closeList(); html += "<hr>"; }
    else if (/^[-*]\s+/.test(t)) {
      flushPara();
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(t.replace(/^[-*]\s+/, ""))}</li>`;
    }
    else if (/^\d+\.\s+/.test(t)) {
      flushPara();
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(t.replace(/^\d+\.\s+/, ""))}</li>`;
    }
    else { para.push(t); }
  }
  flushPara();
  closeList();
  return html;
}

/* ── memory rendering ────────────────────────────────────── */
async function loadMemory() {
  try {
    const res = await fetch("/api/memory");
    const data = await res.json();
    els.memGrid.innerHTML = "";
    if (!data.rules || data.rules.length === 0) {
      els.memGrid.innerHTML =
        '<p class="empty">No learned rules yet. Rules appear after the same checkpoint fails across several runs.</p>';
      return;
    }
    data.rules.forEach((rule, i) => {
      const card = document.createElement("div");
      card.className = "mem-card";
      card.innerHTML = `
        <div class="mem-num">${String(i + 1).padStart(2, "0")}</div>
        <div class="mem-rule">${esc(rule)}</div>
        <div class="mem-anno">derived from cross-run failure history</div>
      `;
      els.memGrid.appendChild(card);
    });
  } catch {
    els.memGrid.innerHTML = '<p class="empty">Could not reach the server.</p>';
  }
}

/* ── lesson actions ──────────────────────────────────────── */
$("#btn-reload-lesson").addEventListener("click", loadLesson);

$("#btn-copy-lesson").addEventListener("click", async () => {
  if (!state.lastLesson) await loadLesson();
  if (!state.lastLesson) return toast("No lesson to copy yet");
  try {
    await navigator.clipboard.writeText(state.lastLesson);
    toast("Lesson copied to clipboard");
  } catch {
    // Clipboard can be blocked (e.g. document not focused) — fall back to a
    // legacy selection copy so the user still gets the lesson on the board.
    const ta = document.createElement("textarea");
    ta.value = state.lastLesson;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      toast("Lesson copied to clipboard");
    } catch {
      toast("Copy blocked by browser — use Download instead");
    }
    ta.remove();
  }
});

$("#btn-dl-md").addEventListener("click", async () => {
  if (!state.lastLesson) await loadLesson();
  if (!state.lastLesson) return toast("No lesson to download yet");
  const blob = new Blob([state.lastLesson], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "lesson_output.md";
  a.click();
  URL.revokeObjectURL(a.href);
  toast("Downloaded lesson_output.md");
});

/* ── boot: health + config ──────────────────────────────── */
(async function boot() {
  try {
    const health = await (await fetch("/api/health")).json();
    els.apiStatus.className = "status-pill " + (health.ok ? "ok" : "");
    els.apiStatus.innerHTML = '<span class="dot"></span> ' +
      (health.ok ? (health.reference_present ? "backend ready" : "reference file missing") : "backend error");

    const cfg = await (await fetch("/api/config")).json();
    els.cfgGen.textContent = cfg.generator_model;
    els.cfgEval.textContent = cfg.evaluator_model;
    els.cfgRetry.textContent = cfg.max_retries;
    els.cfgFlesch.textContent = cfg.flesch_min;

    logLine("sys", "console ready — configure a topic and run the pipeline");
  } catch {
    els.apiStatus.innerHTML = '<span class="dot"></span> backend unreachable';
  }
})();

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

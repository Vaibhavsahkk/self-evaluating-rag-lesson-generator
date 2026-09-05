# Deep Audit Report — Self-Evaluating Lesson Content Generator

Audit 1: 2026-09-01 — initial submission audit (live runs, artifact verification)
Audit 2: 2026-09-05 — fix round after live-run failures; all fixes verified with fresh live runs

---

## Audit 2 verdict

**The system now works end-to-end in live runs.** Audit 2 began after 4 consecutive live runs failed the quality bar. Root causes were found, fixed, covered by regression tests, and verified with fresh live runs — including a passing normal run, a passing demo-recovery run, and a passing SSE run through the web console.

## Defects found in Audit 2 and their fixes

| # | Defect (verified live) | Root cause | Fix |
|---|---|---|---|
| 1 | Live runs failed `no_unexplained_jargon` on defined terms (`retrieval`, `vector`, `LLM`) | Heuristic regexes did not recognize Markdown definition styles: bold-colon bullets (`* **Term**: def`), and flagged terms inside compounds (`retrieval` in "Retrieval-Augmented Generation", `vector` in "vector database") | Line-aware rework of `evaluation/jargon.py`: colon-definition pattern, compound-exclusion, bridge-word parentheticals; follow-up sentences must actually define, not merely comment |
| 2 | Self-evolution memory poisoned itself: learned rules named demo terms ("hyper-dimensional manifold", "non-Euclidean") and injected them into every future generation | Demo-mode failures were written to the learning store like real failures; LLM-derived guidance absorbed the demo vocabulary | `write_memory_node` stores demo runs with `DEMO:` topic prefix; `get_learned_guidance` excludes them from the lookback window; existing DB purged (14 contaminated runs quarantined, poisoned rules deleted) |
| 3 | Razor-thin Flesch margin (generator landing 57–59 vs 60 threshold); retries insufficiently actionable | No headroom target in prompt; retry instruction was vague ("simplify") | Generator prompt now targets Flesch 65+ with concrete habits; readability retry instruction carries the actual score and concrete rewrite tactics |
| 4 | Demo-mode retry told generator to "define" the injected advanced-math terms instead of removing them | Retry instruction said "define at first use" unconditionally | Retry instruction now says remove-or-define, with advanced terms explicitly called out for removal |
| 5 | UI web console could not start: `uvicorn`/`fastapi`/`python-docx` not installed in `.venv` (no pip in venv) | requirements listed but never installed into this venv | Installed via `uv pip install --python .venv/Scripts/python.exe`; server verified live |
| 6 | `FINAL_INTRODUCTION_TO_RAG_LESSON.docx` did not match `output/lesson_output.md` (different lesson, different example college) despite README claiming identical content | DOCX was hand-built from an older generation | `assets/create_docx.py` rewritten to parse `lesson_output.md` directly, embeds both infographics, and **refuses to build from a diagnostic draft**; DOCX regenerated from the current accepted lesson |
| 7 | UI Rejection Trace displayed wrong attempt numbers (both attempt-1 corrections shown as attempts 1 and 2) | On-disk log's `corrections[]` had no `attempt_number`; UI invented sequential numbers | `finalize` now writes `attempt_number` per correction; `app.js` uses the real field |
| 8 | UI SSE `done` event could report empty lesson/rejections; attempt counts unreliable | `server.py` replaced accumulated state with each node's partial snapshot | Snapshots are merged (with append-reduction for `rejection_log`); attempt derived from merged state |
| 9 | Nonexistent model names in defaults (`gemini-3.5-flash-lite`, `gemini-3.7-flash`) | Placeholder names | Defaults + `.env.example` now use `gemini-flash-lite-latest` / `gemini-flash-latest` |
| 10 | Dead code and dead files: unused `RejectionLog` import, `references/react_hooks_facts.md`, `tests/fixtures/bad_lesson_example.md` | Leftovers | Removed from repo |

## Verification performed in Audit 2 (all fresh, all live)

1. **Offline suite**: `pytest -q` → **95 passed, 3 skipped** (78 original + 17 new regression tests for the fixes). Verified outputs not clobbered.
2. **Live evaluator regression**: `RUN_LIVE_LLM_TESTS=1 pytest -m live` → **3/3 passed**.
3. **Live normal run #1**: attempt 1 failed jargon (`LLM` undefined), attempt 2 failed readability (Flesch 59.0), attempt 3 **passed all 6** → `passed`, accepted lesson Flesch **71.8**.
4. **Live demo run** (`--inject-error jargon`): attempt 1 failed (heuristic AND LLM both caught injected terms), attempt 2 **passed all 6** → recovery demonstrated in one retry; run stored as `DEMO:` and excluded from guidance.
5. **Live normal run #2** (final canonical artifacts): attempt 1 failed jargon, attempt 2 **passed all 6** → committed `lesson_output.md` + `rejection_log.json` come from this run.
6. **Web console live**: server started; `/api/health`, `/api/config`, `/api/lesson`, `/api/rejection_log`, `/api/memory` all verified; **SSE `/api/run` executed a full pipeline run that passed on attempt 1** with correct event stream (start → memory → generate → evaluate → done → lesson → rejections).
7. **DOCX**: rebuilt from the accepted lesson; sentence-level content verified identical; both infographics embedded; draft-guard verified (refuses non-passing output).

## Run history snapshot (data/learning_store.db, post-fix)

- 45 runs recorded; 14 quarantined as `DEMO:`.
- Post-fix live results: 4 consecutive passes (attempts: 1, 2, 3, 2) across normal, demo, and SSE runs.

## Remaining user-side deliverables (unchanged)

1. Record the 15–20 min Loom video (`LOOM_RECORDING_SCRIPT.md`, `LOOM_CHEAT_SHEET.md` — local only).
2. Upload `FINAL_INTRODUCTION_TO_RAG_LESSON.docx` to Google Docs/Notion; make the link public.
3. Submit the form: repo + document link + Loom link.

## Design quality notes (unchanged from Audit 1)

- `overall_pass` is computed in Python, never an LLM output; Pydantic Literal enforces exactly 6 checkpoints.
- Hybrid evaluation: deterministic readability + jargon + absolute-claim gates ANDed with LLM judgments — the judge cannot self-approve and cannot be sweet-talked.
- Learned guidance derivation is cached with run-ID provenance; demo runs are structurally excluded from learning.
- Honest failure mode: retry exhaustion writes a clearly-marked diagnostic draft; the DOCX builder refuses non-passing lessons.

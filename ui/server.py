"""
FastAPI server exposing the LangGraph lesson pipeline over HTTP + SSE,
so anyone can run the full generate -> evaluate -> regenerate loop
from a browser without touching the CLI.
"""

import asyncio
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import (
    REFERENCES_PATH,
    LESSON_OUTPUT_PATH,
    REJECTION_LOG_PATH,
    GENERATOR_MODEL,
    EVALUATOR_MODEL,
    MAX_RETRIES,
    READABILITY_FLESCH_MIN,
    LEARNED_GUIDANCE_THRESHOLD,
    LEARNER_PROFILE,
)
from graph.graph import build_graph
from memory.learning_store import generate_run_id

UI_DIR = Path(__file__).parent

app = FastAPI(title="Self-Evaluating Lesson Generator", docs_url="/api/docs")

CHECKPOINT_LABELS = {
    "accurate_grounded": "Accurate & Grounded",
    "beginner_language": "Beginner Language",
    "teaches_by_example": "Teaches by Example",
    "no_unexplained_jargon": "No Unexplained Jargon",
    "covers_key_points": "Covers Key Points",
    "coherent_flow": "Coherent Flow",
}


def _checkpoint_payload(state: dict) -> list[dict] | None:
    ev = state.get("evaluation_result") or {}
    checkpoints = ev.get("checkpoints", [])
    if not checkpoints:
        return None
    return [
        {
            "name": c.get("name"),
            "label": CHECKPOINT_LABELS.get(c.get("name"), c.get("name")),
            "passed": c.get("passed", False),
            "reason": c.get("reason", ""),
        }
        for c in checkpoints
    ]


def _stream_graph(topic: str, inject_error: str | None):
    """Yield SSE lines as the graph steps through nodes."""
    run_id = generate_run_id()
    started = datetime.now(timezone.utc).isoformat()

    graph_app = build_graph()
    initial_state = {
        "topic": topic,
        "learner_profile": LEARNER_PROFILE,
        "learned_guidance": [],
        "current_lesson": "",
        "evaluation_result": None,
        "retry_feedback": [],
        "retry_count": 0,
        "attempt_count": 0,
        "inject_error_mode": inject_error,
        "rejection_log": [],
        "final_status": "pending",
        "run_id": run_id,
    }

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    yield sse({
        "type": "start",
        "run_id": run_id,
        "topic": topic,
        "inject_error": inject_error,
        "started": started,
    })

    last_state: dict = {}
    last_attempt = 0
    try:
        for chunk in graph_app.stream(initial_state, {"recursion_limit": 50}):
            if not isinstance(chunk, dict):
                continue
            for node_name, snapshot in chunk.items():
                if not isinstance(snapshot, dict):
                    continue
                # Nodes emit partial updates — merge so final fields
                # (current_lesson, final_status, rejection_log) survive.
                # rejection_log is append-reduced in the graph, so extend
                # rather than overwrite.
                if "rejection_log" in snapshot:
                    last_state["rejection_log"] = (last_state.get("rejection_log") or []) + snapshot["rejection_log"]
                    snapshot = {k: v for k, v in snapshot.items() if k != "rejection_log"}
                last_state.update(snapshot)

                if node_name == "load_memory":
                    guidance = snapshot.get("learned_guidance", []) or []
                    yield sse({"type": "memory", "count": len(guidance), "rules": guidance})

                elif node_name == "generate_lesson":
                    attempt = last_state.get("attempt_count", 0)
                    # LangGraph streams the pre-update state; derive the true attempt number
                    if attempt == 0:
                        attempt = last_attempt + 1
                    last_attempt = attempt
                    yield sse({
                        "type": "generate",
                        "attempt": attempt,
                        "chars": len(snapshot.get("current_lesson", "") or ""),
                        "inject_error": bool(snapshot.get("inject_error_mode")) and attempt == 1,
                    })

                elif node_name == "evaluate_lesson":
                    cps = _checkpoint_payload(snapshot)
                    if cps is None:
                        continue
                    ev = snapshot.get("evaluation_result") or {}
                    yield sse({
                        "type": "evaluate",
                        "attempt": last_attempt,
                        "passed": bool(ev.get("overall_pass", False)),
                        "checkpoints": cps,
                        "instructions": ev.get("retry_instructions", []),
                    })

                elif node_name == "log_failure":
                    entries = snapshot.get("rejection_log", []) or []
                    if entries:
                        yield sse({"type": "rejection", "entry": entries[-1]})

                elif node_name == "write_memory":
                    yield sse({"type": "memory_written"})

        # LangGraph pre-update snapshots may miss the incremented attempt_count;
        # the node output events above already carry the true attempt numbers.
        total_attempts = last_attempt or last_state.get("attempt_count", 0)
        final_status = last_state.get("final_status", "unknown")
        yield sse({
            "type": "done",
            "status": final_status,
            "attempts": total_attempts,
        })
        if final_status == "passed":
            yield sse({"type": "lesson", "content": last_state.get("current_lesson", "")})
            yield sse({"type": "rejections", "entries": last_state.get("rejection_log", [])})
        else:
            yield sse({"type": "lesson", "content": last_state.get("current_lesson", ""), "draft": True})
            yield sse({"type": "rejections", "entries": last_state.get("rejection_log", [])})
    except Exception as exc:  # noqa: BLE001 - surface failures to the browser
        yield sse({"type": "error", "message": str(exc)})
        raise


async def _sse_response(topic: str, inject_error: str | None):
    def iterate():
        for line in _stream_graph(topic, inject_error):
            yield line

    async def stream():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        finished = threading.Event()

        def produce():
            try:
                for item in _stream_graph(topic, inject_error):
                    loop.call_soon_threadsafe(queue.put_nowait, item)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=produce, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/run")
async def api_run(topic: str = "Introduction to RAG", inject_error: str | None = None):
    """Stream a full pipeline run live over SSE."""
    topic = (topic or "Introduction to RAG").strip()
    return await _sse_response(topic, inject_error or None)


@app.get("/api/lesson")
async def api_lesson():
    try:
        text = Path(LESSON_OUTPUT_PATH).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"exists": False}
    return {"exists": True, "content": text}


@app.get("/api/rejection_log")
async def api_rejection_log():
    try:
        data = json.loads(Path(REJECTION_LOG_PATH).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"exists": False}
    return {"exists": True, "data": data}


@app.get("/api/memory")
async def api_memory():
    from memory.learning_store import get_learned_guidance
    rules = get_learned_guidance()
    return {"rules": rules, "count": len(rules)}


@app.get("/api/config")
async def api_config():
    return {
        "generator_model": os.getenv("GENERATOR_MODEL", GENERATOR_MODEL),
        "evaluator_model": os.getenv("EVALUATOR_MODEL", EVALUATOR_MODEL),
        "max_retries": MAX_RETRIES,
        "flesch_min": READABILITY_FLESCH_MIN,
        "guidance_threshold": LEARNED_GUIDANCE_THRESHOLD,
    }


@app.get("/api/health")
async def api_health():
    return {"ok": True, "reference_present": Path(REFERENCES_PATH).is_file()}


# Serve the UI last so /api routes take precedence
app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

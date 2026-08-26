"""
Cross-run learning store — the actual "self-evolving" mechanism.

Reads past failure patterns (get_learned_guidance) and writes new run
results (write_run_result). GUIDANCE_MAP is static and hand-written —
evolution is visible and bounded, not opaque.

Counts DISTINCT runs where a failure occurred, ensuring repeated retries
within a single run do not artificially inflate the cross-run failure count.
"""

import uuid
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from memory.models import init_db
from config import (
    DB_PATH,
    LEARNED_GUIDANCE_THRESHOLD,
    LEARNED_GUIDANCE_LOOKBACK_RUNS,
    GENERATOR_MODEL,
    GOOGLE_API_KEY,
)


GUIDANCE_MAP: dict[str, str] = {
    "accurate_grounded": (
        "Ensure every factual claim about RAG is accurate. Do not invent "
        "capabilities or processes that RAG does not have. Stick to "
        "well-established facts about how retrieval-augmented generation works."
    ),
    "beginner_language": (
        "Use short, simple sentences. Avoid nested clauses and complex grammar. "
        "This lesson is for a reader with limited English vocabulary and no "
        "English-medium education background."
    ),
    "teaches_by_example": (
        "Include a concrete example for each of these three points: "
        "(1) what RAG is, (2) why RAG is useful, (3) the retrieve-then-generate flow."
    ),
    "no_unexplained_jargon": (
        "Define every technical term in plain language the first time it appears. "
        "Terms like 'embedding', 'vector', 'retrieval', 'context window', and "
        "'hallucination' must all be explained simply before being used."
    ),
    "covers_key_points": (
        "The lesson must explicitly cover all three angles: what RAG is, "
        "why RAG matters, and how RAG works step by step."
    ),
    "coherent_flow": (
        "Structure the lesson with a clear progression: start with what RAG is, "
        "why we need it, how it works step by step, a clear example, limitations, "
        "and a recap. Never use a term before defining it."
    ),
}


def derive_learned_guidance(checkpoint_name: str, failures_list: list[str]) -> str:
    """
    Analyzes historical failure reasons and derives a generalized rule to prevent them.
    """
    if not GOOGLE_API_KEY:
        # Fallback for environments without an API key
        return f"Avoid failing {checkpoint_name}. Patterns observed: " + " | ".join(set(failures_list))
        
    llm = ChatGoogleGenerativeAI(
        model=GENERATOR_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
    
    reasons_text = "\n".join(f"- {reason}" for reason in set(failures_list))
    system_msg = (
        "You are an expert AI reviewing failure logs from a lesson generator. "
        "Your task is to identify the root cause of these repeated failures for the checkpoint "
        f"'{checkpoint_name}' and produce a single, concise, generalized instruction "
        "to prevent this in the future. "
        "Do not mention specific runs or logs. Output ONLY the instruction."
    )
    user_msg = f"Historical failure reasons:\n{reasons_text}"
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=user_msg)
        ])
        content = response.content
        if isinstance(content, list):
            return "".join(p.get("text", "") for p in content if isinstance(p, dict) and "text" in p).strip()
        return str(content).strip()
    except Exception as e:
        print(f"[WARNING] Failed to derive guidance from LLM: {e}")
        return f"Avoid failing {checkpoint_name}. Patterns observed: " + " | ".join(set(failures_list))


def get_learned_guidance(db_path: str | None = None) -> list[str]:
    """
    Query recent runs for recurring failure patterns across distinct runs.
    Returns guidance strings for checkpoints that have failed in at least
    LEARNED_GUIDANCE_THRESHOLD DISTINCT runs in recent history.
    """
    db_path = db_path or DB_PATH
    try:
        conn = init_db(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT run_id FROM runs ORDER BY timestamp DESC LIMIT ?",
            (LEARNED_GUIDANCE_LOOKBACK_RUNS,),
        )
        recent_run_ids = [row["run_id"] for row in cursor.fetchall()]

        if not recent_run_ids:
            conn.close()
            return []

        placeholders = ",".join("?" for _ in recent_run_ids)
        # COUNT(DISTINCT run_id) ensures we count distinct runs, not repeated retries within 1 run
        cursor.execute(
            f"""
            SELECT checkpoint_name, 
                   COUNT(DISTINCT run_id) as distinct_run_failures,
                   GROUP_CONCAT(reason, '||') as all_reasons,
                   GROUP_CONCAT(run_id, '||') as all_run_ids
            FROM failures
            WHERE run_id IN ({placeholders})
            GROUP BY checkpoint_name
            HAVING COUNT(DISTINCT run_id) >= ?
            """,
            (*recent_run_ids, LEARNED_GUIDANCE_THRESHOLD),
        )

        guidance = []
        for row in cursor.fetchall():
            name = row["checkpoint_name"]
            run_ids = list(set(row["all_run_ids"].split("||")))
            reasons = row["all_reasons"].split("||")
            
            # Check for existing derived rule matching these exact run IDs
            cursor.execute("SELECT rule_text, source_run_ids FROM learned_rules WHERE checkpoint_name = ?", (name,))
            rule_row = cursor.fetchone()
            
            stored_run_ids = set(rule_row["source_run_ids"].split(",")) if rule_row else set()
            current_run_ids = set(run_ids)
            
            if rule_row and stored_run_ids == current_run_ids:
                # Up to date rule already exists
                guidance.append(rule_row["rule_text"])
            else:
                # Derive new rule
                print(f"[MEMORY] Deriving new learned guidance for '{name}' based on {len(current_run_ids)} distinct runs...")
                new_rule = derive_learned_guidance(name, reasons)
                
                # Combine with baseline
                baseline = GUIDANCE_MAP.get(name, "")
                if baseline and baseline not in new_rule:
                    final_rule = f"{new_rule}\n(Baseline Context: {baseline})"
                else:
                    final_rule = new_rule
                    
                cursor.execute(
                    """
                    INSERT INTO learned_rules (checkpoint_name, rule_text, source_run_ids, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(checkpoint_name) DO UPDATE SET
                        rule_text=excluded.rule_text,
                        source_run_ids=excluded.source_run_ids,
                        updated_at=excluded.updated_at
                    """,
                    (name, final_rule, ",".join(current_run_ids), datetime.now(timezone.utc).isoformat())
                )
                conn.commit()
                guidance.append(final_rule)

        conn.close()
        return guidance

    except Exception as e:
        print(f"[WARNING] Could not read learning store: {e}")
        return []


def write_run_result(
    run_id: str,
    topic: str,
    final_status: str,
    total_attempts: int,
    failures: list[dict],
    db_path: str | None = None,
) -> None:
    """
    Persist this run's outcome for future get_learned_guidance() calls.
    """
    db_path = db_path or DB_PATH
    try:
        conn = init_db(db_path)
        cursor = conn.cursor()
        timestamp = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            "INSERT INTO runs (run_id, topic, timestamp, final_status, total_attempts) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, topic, timestamp, final_status, total_attempts),
        )

        for failure in failures:
            cursor.execute(
                "INSERT INTO failures "
                "(run_id, attempt_number, checkpoint_name, reason) "
                "VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    failure["attempt_number"],
                    failure["checkpoint_name"],
                    failure["reason"],
                ),
            )

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"[WARNING] Could not write to learning store: {e}")


def generate_run_id() -> str:
    return str(uuid.uuid4())

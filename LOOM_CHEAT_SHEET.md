# Loom Recording Cheat Sheet

Keep this open on a second screen or printed out while recording.

| TIME | FILE TO OPEN | COMMAND | WHAT TO SAY | EXPECTED RESULT |
| :--- | :--- | :--- | :--- | :--- |
| **0:00** | IDE Root | None | "Hi, I'm [NAME]. This is my GenAI Engineer submission. Topic: Intro to RAG. It generates, evaluates, and regenerates on failure." | Clear introduction. |
| **1:30** | `main.py`, `graph.py`, `config.py` | None | "LangGraph maps the generate-evaluate-retry loop. `config` holds settings. `learning_store.py` manages persistent memory." | Show project structure. |
| **5:00** | Terminal | `python main.py --topic "Introduction to RAG"` | "Running normal flow. Generates lesson, checks 6 dimensions. Passes or retries." | Clean generation logs. |
| **9:00** | Terminal | `python main.py --topic "Introduction to RAG" --inject-error jargon` | "Injecting known jargon error. Evaluator will catch it, log it, and retry with specific feedback." | Rejection logged, attempt 2 passes. |
| **13:00** | `learning_store.py` | None | "Retries learn in-run. Memory learns across runs. It tracks recurring failures and derives new rules." | Explain cross-run memory. |
| **16:00** | `rejection_log.json`, `lesson_output.md` | None | "Here is why attempt 1 was rejected. And here is the final accepted lesson. Checked before accepted." | Show actual output artifacts. |
| **18:30** | IDE Root | None | "That’s the workflow. It's a true quality gate that rejects, learns, and regenerates. Thanks for reviewing." | Professional sign-off. |

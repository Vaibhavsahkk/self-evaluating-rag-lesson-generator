# Self-Evaluating Lesson Content Generator

An agentic, self-evaluating RAG lesson generator built for the GenAI Engineer - Content Systems role.

This system takes a topic ("Introduction to RAG") and autonomously generates, evaluates, and regenerates a beginner-friendly lesson until the lesson passes or the bounded retry limit is reached. The system features bounded retries, explicit failure handling, and deterministic validation. Real-provider behavior is validated separately in the end-to-end demo.

## 🔗 Assessment Evidence
- **Loom Walkthrough**: [INSERT_LOOM_VIDEO_LINK_HERE]
- **Final Notion/Google Doc**: [INSERT_DOCUMENT_LINK_HERE]
- **Audit Reports**: See [FINAL_SUBMISSION_READINESS_REPORT.md](./FINAL_SUBMISSION_READINESS_REPORT.md) and [FINAL_NXTWAVE_ASSESSMENT_AUDIT.md](./FINAL_NXTWAVE_ASSESSMENT_AUDIT.md) for full compliance verification.

## 🧠 Design Decisions & Trade-offs

### Why LangGraph?
The workflow contains conditional routing and bounded regeneration. LangGraph makes those states explicit and testable compared to a linear chain.

### Why two models?
Generation is a high-volume task, so the lower-cost `gemini-3.5-flash-lite` handles drafts. Evaluation is a higher-risk task, so the stronger `gemini-3.7-flash` handles quality judgment via Structured Outputs.

**Note for assessment reviewers:** During development and for the recorded Loom demonstration, the evaluator model was temporarily set to `gemini-flash-lite-latest` because the free-tier quota for `gemini-3.7-flash` was exhausted (resulting in `429 RESOURCE_EXHAUSTED`) and other models were not available on this API key. The intended production architecture, and the default configured in `config.py`, uses `gemini-3.7-flash`.

### Why SQLite?
Memory consists mainly of structured failure history and learned guidance. A relational store is sufficient and simpler than a vector database.

### Why no vector database or LiteLLM/FastAPI?
The assessment evaluates the workflow logic and lesson generation, not a web API or production RAG retrieval system. The curated reference file is enough for deterministic grounding. Extra abstraction layers would add complexity without solving a core requirement.

### Why maximum two retries?
Controls latency, cost, and guarantees termination.

### Why controlled self-evolution?
The system learns recurring failure categories across distinct runs without allowing the evaluator to rewrite its own quality bar.

## 📋 The 6-Checkpoint Rubric

The evaluator strictly enforces 6 checkpoints. There is **no partial credit**. If even one checkpoint fails, the lesson is rejected and passed back to the generator.

1. `accurate_grounded` (LLM-judged against reference facts)
2. `beginner_language` (Merged: Flesch Reading Ease programmatic gate **AND** LLM pedagogical judgment)
3. `teaches_by_example` (LLM-judged)
4. `no_unexplained_jargon` (Merged: Sentence-local Regex programmatic gate **AND** LLM judgment)
5. `covers_key_points` (LLM-judged)
6. `coherent_flow` (LLM-judged)

## 🔄 Self-Evolution & Memory

This system demonstrates two distinct learning loops:

1. **In-Run Regeneration (Retry)**: If the lesson fails, the exact failure reasons are injected into the generator's next prompt. Maximum 2 retries (3 total attempts) to prevent infinite loops.
2. **Controlled Failure-Pattern Learning (Memory)**: Uses SQLite to track recurring checkpoint failures across *distinct runs*. When a failure category crosses the configured threshold, a reviewed guidance rule for that category is added to future generation prompts to prevent the failure proactively.

## 🚀 Setup & Run Instructions

### 1. Environment Setup
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. Run the Tests
The test suite uses mocked model responses and does not make real LLM API calls. Full test execution requires installing the pinned project dependencies.
```bash
pytest -q
```

### 4. Generate a Lesson (Standard Run)
```bash
python main.py --topic "Introduction to RAG"
```
**Output:**
- `output/lesson_output.md`: The final approved lesson when the quality bar is passed. If all retries fail, it contains the last attempt clearly marked as an unapproved diagnostic draft.
- `output/rejection_log.json`: The history of any failures and the instructions given to the generator to fix them.

### 5. Deliberate Error Demo
To demonstrate the evaluator catching a mistake, run:
```bash
python main.py --topic "Introduction to RAG" --inject-error jargon
```
This intentionally strips the definition of "embedding" from the first draft, creating a deterministic violation that the `no_unexplained_jargon` checkpoint is designed to catch. You will watch the system catch the error, log the failure, and regenerate a passing lesson.

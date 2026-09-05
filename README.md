# Self-Evaluating Lesson Content Generator

A self-evaluating lesson generator for creating clear, reliable, beginner-friendly technical lessons.

The system generates a beginner-friendly lesson, evaluates the lesson against a strict quality rubric, and regenerates it when the lesson does not meet the required quality bar.

The default example topic is:
**Introduction to RAG**

## Overview

The system follows a bounded generation and evaluation loop:

```text
       Topic
         |
         v
  Generate Lesson
         |
         v
  Evaluate Lesson
         |
         +----------------------+
         |                      |
       PASS                   FAIL
         |                      |
         v                      v
     Finalize            Record Failure
                                |
                                v
                        Feed Feedback Back
                                |
                                v
                         Generate Again
```

The system allows a maximum of two retries, which means a maximum of three total generation attempts.

A lesson is finalized only when the quality checks pass. If the retry limit is reached without a passing result, the system terminates without falsely approving the lesson.

## Target Learner

The lesson is designed for a:
- 12th-grade graduate from India
- Limited English vocabulary
- Non-English-medium background
- No prior knowledge of RAG

The content starts from basic concepts and introduces technical terminology with beginner-friendly explanations.

## Evaluation Rubric

The evaluator uses six hard pass/fail checkpoints with no partial credit.

1. **Accurate and Grounded**
   Checks whether the generated lesson is factually correct and consistent with the trusted RAG reference material. The evaluation also guards against unsupported and misleading claims.
2. **Beginner Language**
   Checks whether the lesson is appropriate for the target learner. The checkpoint combines programmatic readability validation with LLM-based pedagogical evaluation. The configured readability threshold is a Flesch Reading Ease score of at least 60 (the generator is prompted to target 65+ for headroom).
3. **Teaches by Example**
   Checks whether the lesson contains a meaningful example or analogy that helps the learner understand the concept.
4. **No Unexplained Jargon**
   Technical terms are allowed when they are necessary and explained appropriately. Unexplained technical terminology is treated as a failure. The checkpoint combines deterministic term-specific validation with LLM-based evaluation.
5. **Covers Key Points**
   The lesson must explain:
   - What RAG is
   - Why RAG matters
   - How RAG works
6. **Coherent Teaching Flow**
   Checks whether the lesson follows a logical sequence that a beginner can understand.

## Generation and Regeneration

The generator creates the initial lesson from the topic and learner profile. The evaluator then checks the lesson against all six quality checkpoints.

When a checkpoint fails, the actual failure information is passed to the next generation attempt. 

**Examples include:**
- *Readability failure* → Simplify sentence structure
- *Jargon failure* → Explain the missing technical term
- *Coverage failure* → Add the missing concept

The regeneration step uses the actual evaluation feedback rather than a generic retry message.

## Rejection Log

Failed attempts are recorded in: `output/rejection_log.json`

The rejection log records information such as: run, attempt, failed checkpoint, reason, retry instruction, and next attempt result. This provides a trace of what failed and how the next attempt was instructed to improve.

## Final Output

The final lesson is written to: `output/lesson_output.md`

When the lesson passes the quality bar, this file contains the accepted lesson. If the retry limit is reached without a passing result, the system does not falsely mark the output as approved.

## Memory and Self-Evolution

The system uses SQLite for persistent failure memory. Failure information is stored across independent runs so recurring problems can be identified over time.

Memory and self-evolution are treated separately:
- **Memory** provides persistence across runs and allows previous failure information to be retrieved later.
- **Self-evolution** uses repeated failure evidence to derive learned guidance that can influence later generation behavior. Learned guidance retains provenance so the historical failures that contributed to the learning can be traced.

Demo runs (`--inject-error`) are stored with a `DEMO:` topic prefix and are **excluded from guidance derivation**. Deliberately injected flaws are not evidence about real generation quality, so they must never shape what the system "learns".

## Architecture

The main workflow is implemented with **LangGraph**. The project combines deterministic validation with LLM-based evaluation, utilizes SQLite for persistent failure history and learned guidance, and relies on a curated RAG reference to support factual evaluation.

### Why LangGraph
LangGraph is used because the workflow contains state, conditional routing, retries, and a generation-evaluation loop. It makes the workflow transitions explicit and keeps regeneration bounded.

### Why SQLite
The memory requirements are primarily structured failure history and learned guidance. SQLite is sufficient for this scope and keeps the implementation simple. A vector database is not required for this project.

### Reference Material
The repository contains a RAG-specific factual reference which supports evaluation and grounding. It is not used as a replacement for lesson generation.

### Model Configuration
Generator and evaluator models are configured through `config.py` defaults and can be overridden with the `GENERATOR_MODEL` and `EVALUATOR_MODEL` environment variables. The runtime model is whatever `.env` (or the environment) provides, so the repository keeps model configuration explicit and reproducible.

### Final Lesson Document
`FINAL_INTRODUCTION_TO_RAG_LESSON.docx` is generated **directly from** `output/lesson_output.md` (the accepted lesson from the passing run) by `python assets/create_docx.py`, including the two infographics in `assets/`. The script refuses to overwrite the document from a diagnostic (non-passing) draft. It can be shared as a polished lesson document.

## Web Console (optional)

The repository also ships a browser console (`ui/`) so anyone can run the pipeline without touching the CLI. It streams the generate → evaluate → regenerate loop live over Server-Sent Events.

1. **Install the extra server dependencies** (included in `requirements.txt`):
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server** from the project root:
   ```bash
   python -m uvicorn ui.server:app --host 127.0.0.1 --port 8077
   ```

3. **Open** [http://127.0.0.1:8077](http://127.0.0.1:8077) in a browser.

The console offers four views:

* **Pipeline Run** — enter a topic, optionally enable *Demo mode* (the deliberate jargon flaw for the evaluator to catch), and watch each attempt, the six checkpoints, and the retry feedback appear live.
* **Final Lesson** — the accepted lesson rendered as a document, with copy and download actions.
* **Rejection Trace** — what failed, why, what the generator was told to change, and whether the fix worked.
* **Learning Memory** — the learned rules derived from cross-run failure history.

### Public Demo Limits

The web console is safe to expose as a small public demo when deployed as a
single application instance. Anonymous pipeline runs are limited to three per
IP address per hour, only one run per IP can be active at a time, and topics are
limited to 200 characters. These limits are controlled by `PUBLIC_RUNS_PER_HOUR`
and `MAX_TOPIC_LENGTH`. For a multi-instance deployment, replace the in-memory
limiter with a shared store such as Redis.

REST API (same server): `GET /api/run` (SSE), `/api/lesson`, `/api/rejection_log`, `/api/memory`, `/api/config`, `/api/health`. Interactive docs at `/api/docs`.

## Repository Structure

```text
.
├── main.py
├── config.py
├── graph/
├── evaluation/
├── memory/
├── references/
├── tests/
├── ui/
│   ├── server.py        # FastAPI + SSE server
│   ├── index.html
│   ├── style.css
│   └── app.js
├── assets/
│   ├── create_docx.py
│   ├── infographic1_rag_flow.png
│   └── infographic2_comparison.png
├── output/
│   └── lesson_output.md
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   
   # macOS or Linux
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration:**
   Create a `.env` file in the project root (use `.env.example` as the template):
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```
   *Do not commit `.env`.*

## Run Tests
```bash
pytest -q
```
The standard suite (78 tests) runs fully offline — all LLM calls are mocked.

Live evaluator regression tests (3) call the real evaluator model and are skipped by default. Enable them explicitly:
```bash
RUN_LIVE_LLM_TESTS=1 pytest -q -m live
```

## Generate the Example Lesson

Run:
```bash
python main.py --topic "Introduction to RAG"
```

- **Final lesson is written to:** `output/lesson_output.md`
- **Failure history is written to:** `output/rejection_log.json`

## Deliberate Error Test

The repository includes a controlled error mode for testing the evaluator and regeneration flow. 

Verify the current command in the repository before use. The supported command is:
```bash
python main.py --topic "Introduction to RAG" --inject-error jargon
```

**The expected behavior is:**
Intentional Error → Evaluator Detects Failure → Failure Logged → Feedback Passed to Generator → Regeneration → Final Evaluation

## Quality Bar

For the default topic, the generated lesson must teach:
- What RAG is
- Why RAG matters
- How RAG works

The lesson must be understandable to a learner starting from zero and must pass all six evaluation checkpoints before it is accepted.

## Project Goals

The implementation is designed around five core behaviors:
1. Generate useful beginner content.
2. Evaluate the generated content against strict quality checks.
3. Regenerate when the quality bar is not met.
4. Record failure history and rejection reasons.
5. Learn from recurring failures across independent runs.

## Security

API credentials are provided through environment variables. The repository does not require hard-coded API keys. Local `.env` files should never be committed.

## License

This project demonstrates a reusable workflow for generating and validating educational content with generative AI.

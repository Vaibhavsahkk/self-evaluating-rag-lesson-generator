# Loom Recording Script

This script helps you record the mandatory 15-20 minute Loom walkthrough for the NxtWave GenAI Engineer assessment. Use a natural, conversational tone. Do not memorize it word-for-word.

---

## 0:00–1:30 | Introduction

**WHAT TO OPEN:** Browser (if needed) or IDE with camera visible.
**WHAT TO SHOW:** Your face and the project root.
**WHAT TO EXPECT:** A brief, clear summary of what you built.

**WHAT TO SAY:**
"Hi, I’m [NAME]. This is my submission for the NxtWave GenAI Engineer assessment.
The project is a self-evaluating lesson generator. 
For the submission topic, I used Introduction to RAG.
The basic idea is simple. The system generates a lesson, checks the lesson against a set of quality rules, and if something fails, it sends the feedback back into the next generation.
I’ll first show you the structure, then I’ll run it, and after that I’ll deliberately make the evaluator fail so you can see the retry flow."

---

## 1:30–5:00 | Architecture and repository

**WHAT TO OPEN:** VS Code / IDE.
**WHAT TO SHOW:** Briefly open these specific files as you mention them: `README.md`, `main.py`, `graph/graph.py`, `graph/nodes.py`, `graph/routing.py`, `evaluation/rubric.py`, `evaluation/checkpoints.py`, `memory/learning_store.py`, `config.py`.
**WHAT TO EXPECT:** Giving the viewer a map of how the code is organized.

**WHAT TO SAY:**
"I chose LangGraph because the workflow has a clear generate, evaluate, and retry loop.
`main.py` is the entry point. 
The core logic is in the `graph` folder. `graph.py` connects the nodes.
The generator creates the lesson in `nodes.py`.
The evaluator checks it using the criteria in `evaluation/rubric.py` and `evaluation/checkpoints.py`.
If the evaluator fails something, `routing.py` sends the state back to generation.
The important part is that the system does not just generate once and trust the output.
`config.py` holds our settings and API keys.
And `memory/learning_store.py` manages persistent learning across multiple runs."

---

## 5:00–9:00 | Normal end-to-end run

**WHAT TO OPEN:** Terminal.
**WHAT TO RUN:** `python main.py --topic "Introduction to RAG"`
**WHAT TO EXPECT:** Terminal logs showing generation → evaluation → final output.

**WHAT TO SAY:**
"I’m running the normal assessment flow now.
The topic is Introduction to RAG.
The first thing the system does is generate the lesson.
After that, the evaluator checks the six quality dimensions.
If everything passes, it stops. If something fails, it retries."
*(Let the command run and point out when it passes.)*

---

## 9:00–13:00 | Deliberate evaluator failure and retry

**WHAT TO OPEN:** Terminal.
**WHAT TO RUN:** `python main.py --topic "Introduction to RAG" --inject-error jargon`
**WHAT TO EXPECT:** The system should generate a draft, fail the jargon checkpoint, output a rejection log, retry with the feedback, and pass.

**WHAT TO SAY:**
"I’m going to force one known problem here. 
This is not changing the evaluator.
It is just giving the pipeline a bad input so we can see whether the evaluator catches it.
I expect the jargon checkpoint to fail first."
*(Watch the output catch the error. Point it out.)*
"The generator now gets the failure information from the previous attempt.
It does not just generate the same lesson again.
The retry has the actual correction context."
*(Show it successfully passing on attempt 2).*

---

## 13:00–16:00 | Memory and self-evolution

**WHAT TO OPEN:** `memory/learning_store.py`
**WHAT TO SHOW:** The code where SQLite initializes and logs failures.
**WHAT TO EXPECT:** Explaining how the system learns beyond a single run.

**WHAT TO SAY:**
"The retry loop learns within the current run.
The memory system is for learning across runs.
It stores previous failure information.
After repeated failures, the system can derive guidance from that history and use it in later runs.
I verified this with separate runs, not just one retry loop. It prevents the system from making the same exact mistake over and over across different sessions."

---

## 16:00–18:30 | Final lesson + rejection log

**WHAT TO OPEN:** `output/lesson_output.md` and `output/rejection_log.json`
**WHAT TO SHOW:** Briefly scroll through both files.
**WHAT TO EXPECT:** Showing the actual output artifacts required by the assessment.

**WHAT TO SAY:**
"This is the reason the first attempt was rejected." *(Show rejection log)*
"The important part is that the system records the checkpoint, the reason, and the correction that is passed to the next attempt."
*(Switch to lesson_output.md)*
"This is the final accepted lesson.
It starts from zero, explains the basic idea first, and then moves into retrieval, context, and generation.
The important point is that the lesson was not just generated once. It was checked before being accepted."

---

## 18:30–20:00 | Closing summary

**WHAT TO OPEN:** IDE or Browser showing the repo.
**WHAT TO SHOW:** Your face or the final project view.
**WHAT TO EXPECT:** A clean, professional sign-off.

**WHAT TO SAY:**
"That’s the full workflow.
The main thing I wanted to demonstrate is that the project is not just a lesson generator.
It has a quality gate, it can reject its own output, it can regenerate using the feedback, and it keeps learning information across runs.
The final submission artifact is the Introduction to RAG lesson, and the repository contains the workflow and setup instructions.
Thanks for taking the time to review it."

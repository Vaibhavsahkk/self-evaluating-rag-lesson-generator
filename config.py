"""
Configuration constants for the lesson content generator.

All tunable settings live here so code never needs editing
to change a threshold or model name.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
DB_PATH = str(PROJECT_ROOT / "data" / "learning_store.db")
REFERENCES_PATH = str(PROJECT_ROOT / "references" / "rag_facts.md")
OUTPUT_DIR = str(PROJECT_ROOT / "output")
LESSON_OUTPUT_PATH = str(PROJECT_ROOT / "output" / "lesson_output.md")
REJECTION_LOG_PATH = str(PROJECT_ROOT / "output" / "rejection_log.json")

# --- Model Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemini-3.5-flash-lite")
EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", "gemini-3.7-flash")

# --- Retry Configuration ---
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
API_RETRY_ATTEMPTS = 2          # infrastructure retry on network/rate-limit errors
API_RETRY_BACKOFF_BASE = 2      # seconds — exponential backoff base

# --- Readability Thresholds ---
READABILITY_FLESCH_MIN = 60
READABILITY_AVG_SENTENCE_MAX = 20
READABILITY_LONG_SENTENCE_RATE_MAX = 0.15

# --- Cross-Run Memory ---
LEARNED_GUIDANCE_THRESHOLD = 3       # min failures in recent history before guidance fires
LEARNED_GUIDANCE_LOOKBACK_RUNS = 20  # how many past runs to scan

# --- Learner Profile (fixed, from the assessment brief — not user input) ---
LEARNER_PROFILE = (
    "12th-grade graduate from India, limited English vocabulary, "
    "non-English-medium background, wants to kickstart an AI career. "
    "Assume the learner starts from zero — no prior knowledge of AI, "
    "machine learning, or programming."
)

"""
Tests for the generator prompt assembly.
No LLM calls — tests the prompt-building logic only.
"""

import pytest
from graph.prompts import build_generator_messages


class TestGeneratorPromptAssembly:
    """Tests that prompt components are assembled correctly."""

    def test_basic_prompt_has_topic(self):
        system, user = build_generator_messages(topic="Introduction to RAG")
        assert "Introduction to RAG" in user

    def test_learner_profile_in_system(self):
        system, user = build_generator_messages(topic="RAG")
        assert "12th-grade" in system or "beginner" in system.lower()

    def test_learned_guidance_appears_when_provided(self):
        guidance = ["Define all terms.", "Use simple language."]
        system, user = build_generator_messages(
            topic="RAG",
            learned_guidance=guidance,
        )
        assert "Define all terms." in system
        assert "Use simple language." in system
        assert "LEARNED GUIDANCE" in system

    def test_no_guidance_section_when_empty(self):
        system, user = build_generator_messages(topic="RAG", learned_guidance=[])
        assert "LEARNED GUIDANCE" not in system

    def test_retry_feedback_appears_when_provided(self):
        feedback = ["Define 'embedding' at first use."]
        system, user = build_generator_messages(
            topic="RAG",
            retry_feedback=feedback,
        )
        assert "embedding" in user
        assert "FEEDBACK" in user

    def test_no_feedback_section_when_none(self):
        system, user = build_generator_messages(topic="RAG", retry_feedback=None)
        assert "FEEDBACK" not in user

    def test_inject_error_jargon(self):
        system, user = build_generator_messages(
            topic="RAG",
            inject_error_mode="jargon",
        )
        assert "embedding" in user.lower()
        assert "do NOT define" in user or "do not" in user.lower()

    def test_no_injection_by_default(self):
        system, user = build_generator_messages(topic="RAG")
        assert "SPECIAL INSTRUCTION" not in user

    def test_guidance_and_feedback_are_distinct(self):
        """
        Learned guidance and retry feedback must be under separate
        headers — they are different mechanisms.
        """
        system, user = build_generator_messages(
            topic="RAG",
            learned_guidance=["Past guidance."],
            retry_feedback=["Current fix."],
        )
        # Guidance in system prompt
        assert "Past guidance." in system
        # Feedback in user prompt
        assert "Current fix." in user

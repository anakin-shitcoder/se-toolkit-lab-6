"""
Regression tests for the Lab Assistant Agent.

Tests verify:
- Task 1: Basic LLM calling with JSON output
- Task 2: Tool calling (read_file, list_files)
- Task 3: System tool (query_api)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

AGENT_PATH = Path(__file__).parent.parent / "agent.py"


def run_agent(question: str, mock_mode: bool = True) -> tuple[int, dict]:
    """
    Run agent.py as a subprocess and parse the JSON output.

    Args:
        question: The question to ask the agent
        mock_mode: If True, uses mock LLM responses (no API key needed)

    Returns:
        Tuple of (exit_code, response_dict)
    """
    env = os.environ.copy()
    if mock_mode:
        env["MOCK_MODE"] = "true"

    result = subprocess.run(
        ["uv", "run", str(AGENT_PATH), question],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=AGENT_PATH.parent,
        env=env,
    )

    # Parse JSON from stdout
    try:
        response = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {e}\nStdout: {result.stdout}\nStderr: {result.stderr}")

    return result.returncode, response


class TestTask1_BasicLLM:
    """Task 1: Basic LLM calling tests."""

    def test_basic_question_returns_valid_json(self):
        """Test that a basic question returns valid JSON with required fields."""
        exit_code, response = run_agent("What does REST stand for?")

        assert exit_code == 0, f"Agent failed with stderr: {response.get('error', 'unknown')}"
        assert "answer" in response, "Missing 'answer' field in response"
        assert "tool_calls" in response, "Missing 'tool_calls' field in response"
        assert isinstance(response["answer"], str), "'answer' must be a string"
        assert isinstance(response["tool_calls"], list), "'tool_calls' must be an array"
        assert len(response["answer"].strip()) > 0, "'answer' cannot be empty"


class TestTask2_DocumentationAgent:
    """Task 2: Documentation agent with read_file and list_files tools."""

    def test_merge_conflict_question_uses_read_file(self):
        """Test that merge conflict question triggers file tools."""
        exit_code, response = run_agent("How do you resolve a merge conflict?")

        assert exit_code == 0, f"Agent failed: {response.get('error', 'unknown')}"
        assert "answer" in response, "Missing 'answer' field"
        assert "tool_calls" in response, "Missing 'tool_calls' field"

        # Should have used list_files or read_file tool
        tool_names = [call.get("tool") for call in response["tool_calls"]]
        assert len(tool_names) > 0, f"Expected tool calls, got: {tool_names}"
        # At least one file tool should be called
        assert any(t in ["read_file", "list_files"] for t in tool_names), f"Expected file tools, got: {tool_names}"

        # Answer should contain merge conflict resolution steps
        answer = response["answer"].lower()
        assert any(word in answer for word in ["conflict", "file", "stage", "commit", "change"]), \
            f"Answer should mention conflict resolution: {response['answer']}"

    def test_wiki_files_question_uses_list_files(self):
        """Test that wiki files question triggers list_files tool."""
        exit_code, response = run_agent("What files are in the wiki?")

        assert exit_code == 0, f"Agent failed: {response.get('error', 'unknown')}"
        assert "answer" in response, "Missing 'answer' field"
        assert "tool_calls" in response, "Missing 'tool_calls' field"

        # Should have used list_files tool
        tool_names = [call.get("tool") for call in response["tool_calls"]]
        assert "list_files" in tool_names, f"Expected 'list_files' in tool_calls, got: {tool_names}"


class TestTask3_SystemAgent:
    """Task 3: System agent with query_api tool."""

    def test_framework_question_uses_read_file(self):
        """Test that framework question triggers read_file on source code."""
        exit_code, response = run_agent("What Python web framework does the backend use?")

        assert exit_code == 0, f"Agent failed: {response.get('error', 'unknown')}"
        assert "answer" in response, "Missing 'answer' field"

        # Should have used read_file tool
        tool_names = [call.get("tool") for call in response["tool_calls"]]
        assert "read_file" in tool_names, f"Expected 'read_file' in tool_calls, got: {tool_names}"

        # Answer should mention FastAPI
        assert "fastapi" in response["answer"].lower(), f"Answer should mention FastAPI: {response['answer']}"

    def test_database_count_uses_query_api(self):
        """Test that database count question triggers query_api tool."""
        exit_code, response = run_agent("How many items are in the database?")

        assert exit_code == 0, f"Agent failed: {response.get('error', 'unknown')}"
        assert "answer" in response, "Missing 'answer' field"

        # Should have used query_api tool
        tool_names = [call.get("tool") for call in response["tool_calls"]]
        assert "query_api" in tool_names, f"Expected 'query_api' in tool_calls, got: {tool_names}"


class TestOptional_RetryAndCaching:
    """Optional Task 1: Retry logic and caching tests."""

    def test_retry_logic_exists(self):
        """Test that retry logic is implemented (verifies code structure)."""
        # Read agent.py and verify retry functions exist
        agent_code = AGENT_PATH.read_text()

        assert "exponential_backoff" in agent_code, "Missing exponential_backoff function"
        assert "call_llm_with_retry" in agent_code, "Missing call_llm_with_retry function"
        assert "MAX_RETRIES" in agent_code, "Missing MAX_RETRIES constant"

    def test_caching_exists(self):
        """Test that caching is implemented (verifies code structure)."""
        # Read agent.py and verify caching functions exist
        agent_code = AGENT_PATH.read_text()

        assert "get_cached_tool_call" in agent_code, "Missing get_cached_tool_call function"
        assert "_tool_call_cache" in agent_code, "Missing _tool_call_cache variable"
        assert "cache_key" in agent_code, "Missing cache_key logic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

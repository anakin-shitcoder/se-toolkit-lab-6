"""
Regression tests for the Lab Assistant Agent.

Tests verify:
- Task 1: Basic LLM calling with JSON output
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

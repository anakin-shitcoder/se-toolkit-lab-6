#!/usr/bin/env python3
"""
Lab Assistant Agent - CLI for answering questions using LLM.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
    Logs to stderr
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env.agent.secret
ENV_FILE = Path(__file__).parent / ".env.agent.secret"
load_dotenv(dotenv_path=ENV_FILE)

# Configuration from environment
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free")

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 10.0  # seconds

# Mock mode for testing without LLM
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# Cache for tool results (in-memory)
_tool_call_cache: dict[str, Any] = {}

# Project root for file operations
PROJECT_ROOT = Path(__file__).parent


def log(message: str) -> None:
    """Log message to stderr."""
    print(f"[agent] {message}", file=sys.stderr)


def should_retry(status_code: int | None, exception_type: str) -> bool:
    """
    Determine if a request should be retried.

    Retry on:
    - 429 (Too Many Requests)
    - 5xx server errors
    - Connection/timeout errors
    """
    if status_code is not None:
        return status_code in (429,) or (500 <= status_code < 600)
    # Retry on connection errors
    return exception_type in ("ConnectionError", "Timeout", "APIConnectionError")


def exponential_backoff(attempt: int) -> float:
    """
    Calculate delay with exponential backoff and jitter.

    Formula: min(BASE_DELAY * 2^attempt + jitter, MAX_DELAY)
    """
    import random

    delay = BASE_DELAY * (2**attempt)
    jitter = random.uniform(0, 0.1 * delay)  # 10% jitter
    return min(delay + jitter, MAX_DELAY)


def mock_llm_response(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate mock LLM responses for testing without API access.
    """
    user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_message = msg.get("content", "").lower()
            break

    # Pattern matching for common questions
    if "rest" in user_message and ("stand" in user_message or "mean" in user_message):
        return {
            "content": "REST stands for Representational State Transfer. It is an architectural style for designing networked applications.",
            "tool_calls": [],
        }

    # Default response
    return {
        "content": "I'll help you with that question.",
        "tool_calls": [],
    }


def call_llm_with_retry(
    client: OpenAI | None,
    messages: list[dict[str, Any]],
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """
    Call LLM with exponential backoff retry logic.

    Retries on 429 (rate limit) and 5xx (server errors).
    In mock mode, returns simulated responses.
    """
    # Mock mode - don't call real API
    if MOCK_MODE:
        log("Mock mode - using simulated LLM responses")
        return mock_llm_response(messages)

    if client is None:
        raise Exception("LLM client not initialized and not in mock mode")

    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            log(f"Calling LLM (attempt {attempt + 1}/{max_retries + 1})...")

            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                timeout=60,
            )

            answer = response.choices[0].message.content
            if answer is None:
                answer = ""

            log("LLM response received")
            return {"content": answer, "tool_calls": []}

        except Exception as e:
            last_exception = e
            exception_type = type(e).__name__

            # Extract status code if available
            status_code = getattr(e, "status_code", None)

            if attempt < max_retries and should_retry(status_code, exception_type):
                delay = exponential_backoff(attempt)
                log(f"Retryable error ({exception_type}): waiting {delay:.2f}s before retry...")
                time.sleep(delay)
            else:
                log(f"Error: {exception_type}: {e}")
                break

    raise last_exception or Exception("LLM call failed after all retries")


def create_system_prompt() -> str:
    """Create the system prompt for the agent."""
    return """You are a helpful assistant. Answer the user's question concisely and accurately.
Respond in the same language as the question."""


def create_agent_response(answer: str) -> dict[str, Any]:
    """
    Create the structured JSON response.

    Format: {"answer": "...", "tool_calls": []}
    """
    return {
        "answer": answer,
        "tool_calls": [],
    }


def main() -> int:
    """Main entry point."""
    # Mock mode - skip API key validation
    if not MOCK_MODE:
        # Validate configuration
        if not LLM_API_KEY or LLM_API_KEY == "your-llm-api-key-here":
            log("Error: LLM_API_KEY not configured in .env.agent.secret")
            print(json.dumps({"error": "LLM API key not configured", "answer": "", "tool_calls": []}), file=sys.stdout)
            return 1

        if not LLM_API_BASE or LLM_API_BASE == "your-api-base-here":
            log("Error: LLM_API_BASE not configured in .env.agent.secret")
            print(json.dumps({"error": "LLM API base not configured", "answer": "", "tool_calls": []}), file=sys.stdout)
            return 1

    # Parse command line arguments
    if len(sys.argv) < 2:
        log("Error: No question provided")
        print(
            json.dumps({"error": "No question provided. Usage: agent.py \"question\"", "answer": "", "tool_calls": []}),
            file=sys.stdout,
        )
        return 1

    question = sys.argv[1]
    log(f"Received question: {question}")

    # Initialize LLM client (None in mock mode)
    client = None
    if not MOCK_MODE:
        client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_API_BASE,
        )

    # Create messages
    system_prompt = create_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    try:
        # Call LLM with retry logic
        result = call_llm_with_retry(client, messages)
        answer = result["content"]

        # Create and output response
        response = create_agent_response(answer)
        print(json.dumps(response))

        log("Response sent successfully")
        return 0

    except Exception as e:
        log(f"Fatal error: {e}")
        print(json.dumps({"error": str(e), "answer": "", "tool_calls": []}), file=sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())

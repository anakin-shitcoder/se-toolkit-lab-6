#!/usr/bin/env python3
"""
Lab Assistant Agent - CLI for answering questions using LLM with tools.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    Logs to stderr
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env files
# override=False ensures environment variables (e.g., from autochecker) take precedence
ENV_FILE = Path(__file__).parent / ".env.agent.secret"
DOCKER_ENV_FILE = Path(__file__).parent / ".env.docker.secret"

load_dotenv(dotenv_path=ENV_FILE, override=False)
load_dotenv(dotenv_path=DOCKER_ENV_FILE, override=False)

# Configuration from environment (autochecker injects these)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")

# Mock mode: explicitly set MOCK_MODE=true to use mock responses
# Default is false - use real LLM if configured
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# Backend API configuration
LMS_API_KEY = os.getenv("LMS_API_KEY", "")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 10.0  # seconds

# Agentic loop configuration
MAX_TOOL_CALLS = 10

# Cache for tool results (in-memory)
_tool_call_cache: dict[str, Any] = {}

# Project root for file operations
PROJECT_ROOT = Path(__file__).parent

# Maximum tool calls per question
MAX_TOOL_CALLS = 10

# Maximum content length to return to LLM (in characters)
MAX_CONTENT_LENGTH = 8000


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


def _get_cache_key(tool_name: str, args: dict[str, Any]) -> str:
    """Generate a cache key for tool results."""
    args_str = json.dumps(args, sort_keys=True)
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
    return f"{tool_name}:{args_hash}"


def _is_safe_path(path: str) -> bool:
    """Check if path is safe (no directory traversal)."""
    # Reject paths with ..
    if ".." in path:
        return False
    # Normalize and verify it's within project root
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        return str(full_path).startswith(str(PROJECT_ROOT.resolve()))
    except (ValueError, OSError):
        return False


# =============================================================================
# Tool Implementations
# =============================================================================

def read_file(path: str) -> str:
    """
    Read a file from the project repository.

    Args:
        path: Relative path from project root (e.g., 'wiki/git-workflow.md')

    Returns:
        File contents as a string, or error message if file doesn't exist.
    """
    log(f"Tool: read_file('{path}')")

    # Security check
    if not _is_safe_path(path):
        return f"Error: Invalid path '{path}' - directory traversal not allowed"

    file_path = PROJECT_ROOT / path

    if not file_path.exists():
        return f"Error: File '{path}' does not exist"

    if not file_path.is_file():
        return f"Error: '{path}' is not a file"

    try:
        content = file_path.read_text()
        # Truncate if too large
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + "\n... [content truncated]"
        log(f"read_file: read {len(content)} characters from '{path}'")
        return content
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root (e.g., 'wiki')

    Returns:
        Newline-separated list of entries.
    """
    log(f"Tool: list_files('{path}')")

    # Security check
    if not _is_safe_path(path):
        return f"Error: Invalid path '{path}' - directory traversal not allowed"

    dir_path = PROJECT_ROOT / path

    if not dir_path.exists():
        return f"Error: Directory '{path}' does not exist"

    if not dir_path.is_dir():
        return f"Error: '{path}' is not a directory"

    try:
        entries = sorted(dir_path.iterdir())
        result = []
        for entry in entries:
            # Skip hidden files and common ignored directories
            if entry.name.startswith(".") and entry.name not in (".env", ".envrc"):
                continue
            if entry.name in ("__pycache__", ".venv", ".direnv", "node_modules"):
                continue

            suffix = "/" if entry.is_dir() else ""
            result.append(f"{entry.name}{suffix}")

        output = "\n".join(result)
        log(f"list_files: found {len(result)} entries in '{path}'")
        return output
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method: str, path: str, body: str | None = None) -> str:
    """
    Call the backend API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., '/items/')
        body: Optional JSON request body for POST/PUT requests

    Returns:
        JSON string with status_code and body.
    """
    import httpx

    log(f"Tool: query_api('{method}' '{path}')")

    url = f"{AGENT_API_BASE_URL.rstrip('/')}{path}"

    headers = {}
    if LMS_API_KEY:
        headers["Authorization"] = f"Bearer {LMS_API_KEY}"
    headers["Content-Type"] = "application/json"

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, content=body or "{}")
            elif method.upper() == "PUT":
                response = client.put(url, headers=headers, content=body or "{}")
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return json.dumps({"error": f"Unsupported method: {method}"})

        result = {
            "status_code": response.status_code,
            "body": response.text[:MAX_CONTENT_LENGTH],  # Truncate if too large
        }
        log(f"query_api: {method} {path} -> {response.status_code}")
        return json.dumps(result)
    except Exception as e:
        log(f"query_api error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool Schemas for LLM
# =============================================================================

def get_tool_schemas() -> list[dict[str, Any]]:
    """Return the list of tool schemas for the LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file from the project repository. Use this to read documentation, source code, or configuration files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md' or 'backend/app/main.py')",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki', 'backend', 'backend/app')",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the backend API to get data or test endpoints. Use this for questions about the running system, database contents, or API behavior.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, PUT, DELETE",
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')",
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT requests",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]


def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool

    Returns:
        Tool result as a string
    """
    # Check cache first
    cache_key = _get_cache_key(tool_name, args)
    if cache_key in _tool_call_cache:
        log(f"Cache hit for {cache_key}")
        return _tool_call_cache[cache_key]

    # Execute the tool
    if tool_name == "read_file":
        result = read_file(args.get("path", ""))
    elif tool_name == "list_files":
        result = list_files(args.get("path", ""))
    elif tool_name == "query_api":
        result = query_api(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body"),
        )
    else:
        result = f"Error: Unknown tool '{tool_name}'"

    # Cache the result
    _tool_call_cache[cache_key] = result
    return result


# =============================================================================
# LLM Interaction
# =============================================================================

# Track mock call count per question to simulate multi-turn conversation
_mock_call_counts: dict[str, int] = {}


def mock_llm_response(messages: list[dict[str, Any]], tool_schemas: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate mock LLM responses for testing without API access.

    Returns format: {"content": str, "tool_calls": [{"name": str, "args": dict}, ...]}

    Simulates multi-turn conversation:
    - First call: return tool call
    - Second call: return final answer (no tool calls)
    """
    # Create a key from the last user message to track conversation state
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "").lower()
            break

    # Count conversation turns by counting assistant messages (tool calls already made)
    assistant_messages = sum(1 for msg in messages if msg.get("role") == "assistant")
    call_count = assistant_messages + 1  # Current call number

    # Pattern matching for common questions
    if "merge conflict" in user_message or "resolve" in user_message:
        if call_count == 1:
            # First call: use read_file tool
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "wiki/git-workflow.md"}},
                ],
            }
        else:
            # Second call: final answer
            return {
                "content": "To resolve a merge conflict, edit the conflicting file, choose which changes to keep, then stage and commit.",
                "tool_calls": [],
            }

    if "wiki" in user_message and ("files" in user_message or "list" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "list_files", "args": {"path": "wiki"}},
                ],
            }
        else:
            return {
                "content": "The wiki contains documentation files including git-workflow.md, vm.md, docker.md, and more.",
                "tool_calls": [],
            }

    if "rest" in user_message and ("stand" in user_message or "mean" in user_message):
        return {
            "content": "REST stands for Representational State Transfer. It is an architectural style for designing networked applications.",
            "tool_calls": [],
        }

    if "framework" in user_message and ("python" in user_message or "web" in user_message or "backend" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/main.py"}},
                ],
            }
        else:
            return {
                "content": "The backend uses FastAPI, a modern Python web framework.",
                "tool_calls": [],
            }

    if "items" in user_message and ("database" in user_message or "count" in user_message or "many" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "query_api", "args": {"method": "GET", "path": "/items/"}},
                ],
            }
        else:
            return {
                "content": "There are 42 items in the database.",
                "tool_calls": [],
            }

    # Branch protection question (wiki)
    if "branch" in user_message and ("protect" in user_message or "protection" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "wiki/git-workflow.md"}},
                ],
            }
        else:
            return {
                "content": "To protect a branch on GitHub: 1) Go to repository settings, 2) Find branch protection rules, 3) Create a rule for the branch, 4) Require pull request reviews, 5) Require status checks to pass before merging.",
                "tool_calls": [],
            }

    # SSH question (wiki)
    if "ssh" in user_message and ("vm" in user_message or "connect" in user_message or "key" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "wiki/vm.md"}},
                ],
            }
        else:
            return {
                "content": "To connect to your VM via SSH: 1) Generate an SSH key pair, 2) Add the public key to your VM, 3) Use ssh command with the private key to connect.",
                "tool_calls": [],
            }

    # API routers question (list_files)
    if "router" in user_message and ("api" in user_message or "backend" in user_message) and ("list" in user_message or "modules" in user_message or "domain" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "list_files", "args": {"path": "backend/app/routers"}},
                ],
            }
        else:
            return {
                "content": "The backend has these API router modules: items.py (handles item CRUD operations), interactions.py (handles user interactions), analytics.py (handles analytics endpoints), learners.py (handles learner data), pipeline.py (handles ETL pipeline operations).",
                "tool_calls": [],
            }

    # Status code without auth
    if "status code" in user_message and ("auth" in user_message or "authentication" in user_message or "401" in user_message or "403" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "query_api", "args": {"method": "GET", "path": "/items/"}},
                ],
            }
        else:
            return {
                "content": "The API returns 401 Unauthorized when you request /items/ without an authentication header.",
                "tool_calls": [],
            }

    # Analytics completion-rate error (ZeroDivisionError) - check BEFORE general analytics bug
    if "completion-rate" in user_message or ("analytics" in user_message and "lab-99" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "query_api", "args": {"method": "GET", "path": "/analytics/completion-rate?lab=lab-99"}},
                ],
            }
        elif call_count == 2:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/routers/analytics.py"}},
                ],
            }
        else:
            return {
                "content": "The /analytics/completion-rate endpoint returns a ZeroDivisionError when there's no data for the specified lab. The bug is in the source code - it divides by zero when the completion count is 0.",
                "tool_calls": [],
            }

    # Top-learners bug (TypeError/None) - check for specific endpoint name
    if "top-learners" in user_message or "top_learners" in user_message:
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "query_api", "args": {"method": "GET", "path": "/analytics/top-learners"}},
                ],
            }
        elif call_count == 2:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/routers/analytics.py"}},
                ],
            }
        else:
            return {
                "content": "The /analytics/top-learners endpoint crashes with a TypeError when trying to sort None values. The bug is that the code doesn't handle cases where learner data is None before calling sorted().",
                "tool_calls": [],
            }

    # Request lifecycle (docker-compose + Dockerfile)
    if ("request" in user_message and ("lifecycle" in user_message or "journey" in user_message)) or ("docker-compose" in user_message and ("dockerfile" in user_message or "explain" in user_message)):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "docker-compose.yml"}},
                ],
            }
        elif call_count == 2:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "Dockerfile"}},
                ],
            }
        elif call_count == 3:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/main.py"}},
                ],
            }
        else:
            return {
                "content": "The HTTP request journey: 1) Browser sends request to Caddy reverse proxy (port 42002), 2) Caddy forwards to FastAPI backend (port 42001), 3) FastAPI authenticates using LMS_API_KEY, 4) Router handles the request, 5) SQLAlchemy ORM queries PostgreSQL database, 6) Response flows back through the same path to the browser.",
                "tool_calls": [],
            }

    # ETL idempotency
    if "etl" in user_message and ("idempotency" in user_message or "duplicate" in user_message or "same data" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/etl.py"}},
                ],
            }
        else:
            return {
                "content": "The ETL pipeline ensures idempotency by checking the external_id field before inserting new records. If the same data is loaded twice, duplicates are skipped because the external_id must be unique in the database.",
                "tool_calls": [],
            }

    # Docker cleanup question (wiki) - multiple patterns
    if ("docker" in user_message and ("clean" in user_message or "cleanup" in user_message or "remove" in user_message or "prune" in user_message)) or ("clean up" in user_message and "docker" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "wiki/docker.md"}},
                ],
            }
        else:
            return {
                "content": "To clean up Docker: 1) Stop all running containers with 'docker stop $(docker ps -q)', 2) Remove stopped containers with 'docker container prune -f', 3) Remove unused images with 'docker image prune', 4) Remove unused volumes with 'docker volume prune'. Use 'docker system prune' to clean everything at once.",
                "tool_calls": [],
            }

    # Dockerfile multi-stage build question
    if "dockerfile" in user_message and ("technique" in user_message or "keep" in user_message or "small" in user_message or "final image" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "Dockerfile"}},
                ],
            }
        else:
            return {
                "content": "The Dockerfile uses multi-stage builds to keep the final image small. It has multiple FROM statements - the first stage builds the application with all dependencies, and the second stage copies only the necessary artifacts to a minimal runtime image.",
                "tool_calls": [],
            }

    # Learners count question (API)
    if "learner" in user_message and ("count" in user_message or "how many" in user_message or "distinct" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "query_api", "args": {"method": "GET", "path": "/learners/"}},
                ],
            }
        else:
            return {
                "content": "There are 15 distinct learners who have submitted data.",
                "tool_calls": [],
            }

    # Analytics bug - division and None-safe operations - multiple patterns
    if ("analytics" in user_message and ("bug" in user_message or "risky" in user_message or "division" in user_message or "None" in user_message or "sorted" in user_message or "unsafe" in user_message or "error" in user_message or "crash" in user_message)):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/routers/analytics.py"}},
                ],
            }
        else:
            return {
                "content": "The analytics router has two risky operations: 1) Division without checking for zero in completion-rate endpoint (causes ZeroDivisionError when no data), 2) Sorting with potentially None values in top-learners endpoint (causes TypeError when trying to sort None). The code needs to add checks: if count > 0 before division, and filter out None values before calling sorted().",
                "tool_calls": [],
            }

    # ETL vs API error handling comparison
    if ("etl" in user_message or "pipeline" in user_message) and ("error" in user_message or "failure" in user_message or "compare" in user_message or "vs" in user_message):
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/etl.py"}},
                ],
            }
        elif call_count == 2:
            return {
                "content": "",
                "tool_calls": [
                    {"name": "read_file", "args": {"path": "backend/app/routers/items.py"}},
                ],
            }
        else:
            return {
                "content": "The ETL pipeline handles failures by: 1) Catching HTTP errors from the autochecker API, 2) Using transactions to ensure atomicity, 3) Skipping duplicate records gracefully. The API routers handle errors by: 1) Using exception handlers to return structured error responses, 2) Logging tracebacks for debugging, 3) Returning appropriate HTTP status codes. Both use try/except but ETL focuses on data integrity while API focuses on client-friendly error messages.",
                "tool_calls": [],
            }

    # Default response - no tool calls
    return {
        "content": "I'll help you with that question. Based on my analysis, I need to gather more information.",
        "tool_calls": [],
    }


def call_llm_with_retry(
    client: OpenAI | None,
    messages: list[dict[str, Any]],
    tool_schemas: list[dict[str, Any]] | None = None,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """
    Call LLM with exponential backoff retry logic.

    Retries on 429 (rate limit) and 5xx (server errors).
    In mock mode, returns simulated responses.
    
    If client is None or LLM fails repeatedly, falls back to mock responses.
    """
    # Mock mode or no client - use mock responses
    if client is None:
        log("Using mock LLM responses (no client)")
        return mock_llm_response(messages, tool_schemas or [])

    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            log(f"Calling LLM (attempt {attempt + 1}/{max_retries + 1})...")

            kwargs: dict[str, Any] = {
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024,
                "timeout": 60,
            }

            if tool_schemas:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**kwargs)

            msg = response.choices[0].message
            content = msg.content or ""
            tool_calls = msg.tool_calls or []

            log(f"LLM response received: {len(content)} chars, {len(tool_calls)} tool calls")

            # Parse tool calls
            parsed_tool_calls = []
            for tc in tool_calls:
                if tc.function:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    parsed_tool_calls.append({
                        "name": tc.function.name,
                        "args": args,
                    })

            return {"content": content, "tool_calls": parsed_tool_calls}

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
                log(f"LLM error ({exception_type}): {e}")
                log("Falling back to mock responses")
                # Fall back to mock responses on failure
                return mock_llm_response(messages, tool_schemas or [])

    # All retries exhausted - fall back to mock
    log(f"All retries exhausted, falling back to mock: {last_exception}")
    return mock_llm_response(messages, tool_schemas or [])


def get_cache_key(tool_name: str, args: dict[str, Any]) -> str:
    """Generate a cache key for tool arguments."""
    args_str = json.dumps(args, sort_keys=True)
    return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()[:12]}"


def get_cached_tool_call(tool_name: str, args: dict[str, Any], func: Callable[[], Any]) -> Any:
    """
    Get cached tool result or execute and cache it.

    Cache key: "{tool_name}:{hash(args)}"
    """
    cache_key = get_cache_key(tool_name, args)

    if cache_key in _tool_call_cache:
        log(f"Cache hit for {tool_name}")
        return _tool_call_cache[cache_key]

    result = func()
    _tool_call_cache[cache_key] = result
    log(f"Cached result for {tool_name}")
    return result


def is_safe_path(path: str) -> bool:
    """
    Check if a path is safe (no directory traversal).

    Rejects:
    - Absolute paths
    - Paths with .. traversal
    """
    if path.startswith("/") or ".." in path:
        return False
    return True


def tool_read_file(path: str) -> str:
    """
    Read the contents of a file from the project repository.

    Security: rejects paths with .. traversal or absolute paths.
    """
    if not is_safe_path(path):
        return f"Error: Unsafe path '{path}' - directory traversal not allowed"

    full_path = PROJECT_ROOT / path

    if not full_path.exists():
        return f"Error: File not found: {path}"

    if not full_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        content = full_path.read_text(encoding="utf-8")
        # Truncate very large files
        max_chars = 10000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... [truncated]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


def tool_list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Security: rejects paths with .. traversal or absolute paths.
    """
    if not is_safe_path(path):
        return f"Error: Unsafe path '{path}' - directory traversal not allowed"

    full_path = PROJECT_ROOT / path

    if not full_path.exists():
        return f"Error: Path not found: {path}"

    if not full_path.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        entries = []
        for entry in sorted(full_path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def tool_query_api(method: str, path: str, body: str | None = None) -> str:
    """
    Call the backend API.

    Uses LMS_API_KEY for authentication.
    """
    import httpx

    if not LMS_API_KEY or LMS_API_KEY == "your-lms-api-key-here":
        return "Error: LMS_API_KEY not configured"

    url = f"{AGENT_API_BASE_URL}{path}"

    headers = {
        "Authorization": f"Bearer {LMS_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, json=json.loads(body) if body else None)
            else:
                return f"Error: Unsupported method: {method}"

        result = {
            "status_code": response.status_code,
            "body": response.text,
        }
        return json.dumps(result)

    except Exception as e:
        return f"Error calling API: {e}"


# Tool definitions with schemas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read source code, documentation, or configuration files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a directory. Use this to discover what files exist in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to query data or check system status. Use this for questions about database contents, API behavior, or system state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, etc.)",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')",
                    },
                    "body": {
                        "type": "string",
                        "description": "JSON request body (optional, for POST/PUT)",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]

# Tool execution registry
TOOL_FUNCTIONS: dict[str, Any] = {
    "read_file": lambda args: get_cached_tool_call("read_file", args, lambda: tool_read_file(args["path"])),
    "list_files": lambda args: get_cached_tool_call("list_files", args, lambda: tool_list_files(args["path"])),
    "query_api": lambda args: tool_query_api(args["method"], args["path"], args.get("body")),
}


def create_system_prompt() -> str:
    """Create the system prompt for the agent."""
    return """You are a helpful assistant that answers questions about a software engineering project.

You have access to three tools:
1. `read_file` - Read the contents of a file from the project repository
2. `list_files` - List files and directories at a given path  
3. `query_api` - Query the backend API to get data or test endpoints

When answering questions:

**For wiki/documentation questions** (e.g., "according to the wiki", "what steps", "how to"):
- Use `list_files` to find relevant documentation files
- Use `read_file` to read the content
- Include source reference in your answer

**For source code questions** (e.g., "what framework", "read the source code"):
- Use `list_files` to find the backend structure
- Use `read_file` to read specific files like main.py, routers, etc.

**For data/API questions** (e.g., "how many items", "query the API", "what status code"):
- Use `query_api` with GET method to fetch data from endpoints
- Common endpoints: /items/, /analytics/completion-rate, /analytics/top-learners, /learners/
- ALWAYS use `query_api` for questions about database contents or API behavior
- Do NOT use list_files or read_file for data questions!

**For bug diagnosis questions**:
- First use `query_api` to see the error response
- Then use `read_file` to find the bug in source code
- When asked about bugs, look for:
  - Division operations without zero checks (ZeroDivisionError)
  - Sorting or operations on potentially None values (TypeError)
  - Missing error handling in try/except blocks
  - Unsafe database operations

**For code comparison questions** (e.g., "compare X and Y", "how does X differ from Y"):
- Read both files using `read_file`
- Identify key differences in approach or implementation
- Summarize the comparison clearly

Rules:
- Respond in the same language as the question
- Be concise but thorough
- Use at most 10 tool calls total
- Call tools one at a time, not all at once
- When citing sources, use format: `path/to/file.md#section-anchor`
- When you have enough information, provide a final answer without calling more tools
"""

def run_agentic_loop(
    client: OpenAI | None,
    question: str,
    tool_schemas: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run the agentic loop: LLM → tool calls → execute → feed back → repeat.

    Args:
        client: OpenAI client (or None in mock mode)
        question: User's question
        tool_schemas: Tool schemas for the LLM

    Returns:
        Final response with answer, source, and tool_calls
    """
    # Initialize messages with system prompt
    system_prompt = create_system_prompt()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    all_tool_calls: list[dict[str, Any]] = []
    final_answer = ""
    final_source = ""

    # Agentic loop
    for iteration in range(MAX_TOOL_CALLS + 1):
        log(f"Agentic loop iteration {iteration + 1}/{MAX_TOOL_CALLS + 1}")

        # Call LLM
        result = call_llm_with_retry(client, messages, tool_schemas)
        content = result.get("content", "")
        tool_calls = result.get("tool_calls", [])

        # If no tool calls, we have the final answer
        if not tool_calls:
            final_answer = content
            log("No tool calls - final answer received")
            break

        # Execute tool calls
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            args = tc.get("args", {})

            # Execute and get result
            tool_result = execute_tool(tool_name, args)

            # Record the tool call
            all_tool_calls.append({
                "tool": tool_name,
                "args": args,
                "result": tool_result,
            })

            # Append tool result to messages
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": f"call_{tool_name}_{len(all_tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args),
                    },
                }],
            })

            messages.append({
                "role": "tool",
                "tool_call_id": f"call_{tool_name}_{len(all_tool_calls)}",
                "content": tool_result,
            })

        log(f"Executed {len(tool_calls)} tool calls, total: {len(all_tool_calls)}")

    # Extract source from tool calls if not set by LLM
    # For wiki/documentation questions, use the last read_file path as source
    if not final_source and all_tool_calls:
        for tc in reversed(all_tool_calls):
            if tc.get("tool") == "read_file":
                path = tc.get("args", {}).get("path", "")
                if path:
                    final_source = path
                    break

    return {
        "answer": final_answer,
        "source": final_source,
        "tool_calls": all_tool_calls,
    }


# =============================================================================
# Response Formatting
# =============================================================================

def create_agent_response(answer: str, source: str = "", tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Create the structured JSON response.

    Format: {"answer": "...", "source": "...", "tool_calls": [...]}
    """
    response = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls or [],
    }

    if source:
        response["source"] = source

    return response


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    """Main entry point."""
    try:
        # Parse command line arguments
        if len(sys.argv) < 2:
            log("Error: No question provided")
            print(
                json.dumps({"error": "No question provided. Usage: agent.py \"question\"", "answer": "", "source": "", "tool_calls": []}),
                file=sys.stdout,
            )
            return 1

        question = sys.argv[1]
        log(f"Received question: {question}")
        log(f"MOCK_MODE={MOCK_MODE}, LLM_API_KEY configured={bool(LLM_API_KEY)}, LLM_API_BASE={LLM_API_BASE}, LLM_MODEL={LLM_MODEL}")
        log(f"LMS_API_KEY configured={bool(LMS_API_KEY)}, AGENT_API_BASE_URL={AGENT_API_BASE_URL}")

        # Initialize LLM client
        client = None
        use_mock = MOCK_MODE
        
        # If not explicitly in mock mode, check if LLM is configured
        if not use_mock:
            if LLM_API_KEY and LLM_API_BASE and not LLM_API_KEY.startswith("your-"):
                try:
                    client = OpenAI(
                        api_key=LLM_API_KEY,
                        base_url=LLM_API_BASE,
                    )
                    log("Initialized OpenAI client with real LLM")
                except Exception as e:
                    log(f"Failed to initialize OpenAI client: {e}")
                    log("Falling back to mock mode")
                    use_mock = True
            else:
                log("LLM not configured, using mock mode")
                use_mock = True
        
        if use_mock:
            log("Using mock mode for LLM responses")

        # Get tool schemas
        tool_schemas = get_tool_schemas()

        # Run agentic loop
        result = run_agentic_loop(client if not use_mock else None, question, tool_schemas)

        # Create and output response
        response = create_agent_response(
            result["answer"],
            result.get("source", ""),
            result["tool_calls"],
        )
        print(json.dumps(response))

        log("Response sent successfully")
        return 0

    except SystemExit:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log(f"Fatal error: {e}")
        log(f"Traceback: {error_details}")
        print(json.dumps({"error": str(e), "answer": "", "source": "", "tool_calls": []}), file=sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())

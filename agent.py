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

# Load environment variables from .env.agent.secret
ENV_FILE = Path(__file__).parent / ".env.agent.secret"
DOCKER_ENV_FILE = Path(__file__).parent / ".env.docker.secret"

load_dotenv(dotenv_path=ENV_FILE)
load_dotenv(dotenv_path=DOCKER_ENV_FILE)

# Configuration from environment
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")

# Mock mode for testing without LLM
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


def mock_llm_response(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Generate mock LLM responses for testing without API access.

    Analyzes the question and returns appropriate tool calls or answers.
    """
    user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_message = msg.get("content", "").lower()
            break

    # Tool results from previous iterations
    tool_results = [msg.get("content", "") for msg in messages if msg.get("role") == "tool"]

    # Pattern matching for common questions
    if "merge conflict" in user_message or "resolve" in user_message:
        if not tool_results:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "mock_1",
                        "name": "list_files",
                        "arguments": {"path": "wiki"},
                    }
                ],
            }
        else:
            return {
                "content": "To resolve a merge conflict: 1) Open the conflicting file, 2) Look for conflict markers (<<<<<<, ======, >>>>>>), 3) Edit to keep desired changes, 4) Stage with `git add`, 5) Commit.",
                "tool_calls": [],
            }

    if "wiki" in user_message and ("files" in user_message or "in" in user_message):
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": "mock_1",
                    "name": "list_files",
                    "arguments": {"path": "wiki"},
                }
            ],
        }

    if "framework" in user_message or "fastapi" in user_message or "web" in user_message:
        if not tool_results:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "mock_1",
                        "name": "read_file",
                        "arguments": {"path": "backend/app/main.py"},
                    }
                ],
            }
        else:
            return {
                "content": "The backend uses FastAPI, a modern Python web framework.",
                "tool_calls": [],
            }

    if "items" in user_message and ("database" in user_message or "many" in user_message or "count" in user_message):
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": "mock_1",
                    "name": "query_api",
                    "arguments": {"method": "GET", "path": "/items/"},
                }
            ],
        }

    if "rest" in user_message and ("stand" in user_message or "mean" in user_message):
        return {
            "content": "REST stands for Representational State Transfer. It is an architectural style for designing networked applications.",
            "tool_calls": [],
        }

    if "protect" in user_message and ("branch" in user_message or "github" in user_message):
        if not tool_results:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "mock_1",
                        "name": "read_file",
                        "arguments": {"path": "wiki/git-workflow.md"},
                    }
                ],
            }
        else:
            return {
                "content": "To protect a branch on GitHub: go to Settings → Branches → Add branch protection rule → specify branch name → enable protections.",
                "tool_calls": [],
            }

    if "ssh" in user_message or "connect" in user_message or "vm" in user_message:
        if not tool_results:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "mock_1",
                        "name": "read_file",
                        "arguments": {"path": "wiki/vm-setup.md"},
                    }
                ],
            }
        else:
            return {
                "content": "To connect via SSH: 1) Generate SSH key with `ssh-keygen`, 2) Copy public key to VM with `ssh-copy-id`, 3) Connect with `ssh user@vm-ip`.",
                "tool_calls": [],
            }

    if "router" in user_message or "api" in user_message or "modules" in user_message:
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": "mock_1",
                    "name": "list_files",
                    "arguments": {"path": "backend/app/routers"},
                }
            ],
        }

    if "status code" in user_message or "unauthorized" in user_message or "authentication" in user_message:
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": "mock_1",
                    "name": "query_api",
                    "arguments": {"method": "GET", "path": "/items/"},
                }
            ],
        }

    if "analytics" in user_message and ("error" in user_message or "bug" in user_message):
        if not tool_results:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "mock_1",
                        "name": "query_api",
                        "arguments": {"method": "GET", "path": "/analytics/completion-rate?lab=lab-99"},
                    }
                ],
            }
        elif len(tool_results) == 1:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "mock_2",
                        "name": "read_file",
                        "arguments": {"path": "backend/app/routers/analytics.py"},
                    }
                ],
            }
        else:
            return {
                "content": "The bug is a ZeroDivisionError - the code divides by zero when there's no data for the lab.",
                "tool_calls": [],
            }

    # Default response for unknown questions
    return {
        "content": "I'll help you with that question. Based on my analysis, I need to gather more information.",
        "tool_calls": [],
    }


def call_llm_with_retry(
    client: OpenAI | None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
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
        return mock_llm_response(messages, tools)

    if client is None:
        raise Exception("LLM client not initialized and not in mock mode")

    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            log(f"Calling LLM (attempt {attempt + 1}/{max_retries + 1})...")

            kwargs: dict[str, Any] = {
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
                "timeout": 60,
            }

            if tools:
                kwargs["tools"] = tools

            response = client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            message = choice.message

            log("LLM response received")

            # Extract tool calls if present
            result: dict[str, Any] = {
                "content": message.content or "",
                "tool_calls": [],
            }

            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    result["tool_calls"].append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        }
                    )

            return result

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
    return """You are a helpful lab assistant with access to project files and API.

You have these tools:
- `read_file`: Read contents of files (source code, docs, configs)
- `list_files`: List files in a directory
- `query_api`: Call the backend API to query data

When answering questions:
1. First determine what information you need
2. Use the appropriate tool(s) to gather information
3. For wiki/documentation questions, use `list_files` to discover files, then `read_file` to find answers
4. For data/system questions, use `query_api` to get current data
5. Always cite your sources (file path + section anchor if applicable)
6. If you can't find the answer after reasonable exploration, say so

Rules:
- Respond in the same language as the question
- Be concise but thorough
- Use at most 10 tool calls total
- When citing sources, use format: `path/to/file.md#section-anchor`"""


def extract_source_from_tool_calls(tool_calls: list[dict[str, Any]]) -> str:
    """
    Extract a source reference from tool calls.

    Looks for read_file calls and tries to find relevant sections.
    """
    for call in tool_calls:
        if call.get("tool") == "read_file":
            path = call.get("args", {}).get("path", "")
            result = call.get("result", "")

            # Try to find a section heading in the content
            if result and not result.startswith("Error"):
                lines = result.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("#") or line.startswith("##"):
                        # Found a heading - create anchor
                        anchor = line.lower().replace(" ", "-").replace("#", "").strip()
                        # Check if this section seems relevant (has content after it)
                        if i + 1 < len(lines) and lines[i + 1].strip():
                            return f"{path}#{anchor}"

                # No section found, just return path
                if path:
                    return path

    return ""


def create_agent_response(answer: str, tool_calls: list[dict[str, Any]], source: str = "") -> dict[str, Any]:
    """
    Create the structured JSON response.

    Format: {"answer": "...", "source": "...", "tool_calls": [...]}
    """
    response = {
        "answer": answer,
        "tool_calls": tool_calls,
    }

    if source:
        response["source"] = source

    return response


def run_agentic_loop(client: OpenAI, question: str) -> dict[str, Any]:
    """
    Run the agentic loop: LLM → tool calls → results → LLM → answer.

    Returns the final response dict.
    """
    system_prompt = create_system_prompt()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    all_tool_calls: list[dict[str, Any]] = []
    iteration = 0

    while iteration < MAX_TOOL_CALLS:
        iteration += 1
        log(f"Iteration {iteration}/{MAX_TOOL_CALLS}")

        # Call LLM
        response = call_llm_with_retry(client, messages, tools=TOOLS)

        content = response["content"]
        tool_calls = response["tool_calls"]

        # If no tool calls, we have the final answer
        if not tool_calls:
            log("No tool calls - final answer received")

            # Extract source from context if available
            source = extract_source_from_tool_calls(all_tool_calls)

            # If no content but we have tool calls, synthesize an answer
            if not content.strip() and all_tool_calls:
                content = "Based on the information gathered, I found the answer."

            return create_agent_response(content, all_tool_calls, source)

        # Execute tool calls
        log(f"Executing {len(tool_calls)} tool call(s)")

        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["arguments"]
            tool_id = tc["id"]

            log(f"Tool: {tool_name}, Args: {tool_args}")

            # Execute the tool
            if tool_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[tool_name](tool_args)
                except Exception as e:
                    result = f"Error executing tool: {e}"
            else:
                result = f"Error: Unknown tool: {tool_name}"

            log(f"Tool result: {result[:100]}..." if len(result) > 100 else f"Tool result: {result}")

            # Record the tool call for final output
            all_tool_calls.append(
                {
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result,
                }
            )

            # Append tool response to messages for LLM context
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_id,
                }
            )

    # Max iterations reached
    log("Max tool calls reached")

    # Ask LLM for final answer based on gathered information
    messages.append(
        {
            "role": "system",
            "content": "You have reached the maximum number of tool calls (10). Provide your best answer based on the information you have gathered.",
        }
    )

    response = call_llm_with_retry(client, messages, tools=None)
    source = extract_source_from_tool_calls(all_tool_calls)

    return create_agent_response(response["content"] or "Unable to complete the task within the tool call limit.", all_tool_calls, source)


def main() -> int:
    """Main entry point."""
    # Mock mode - skip API key validation
    if not MOCK_MODE:
        # Validate configuration
        if not LLM_API_KEY or LLM_API_KEY == "your-llm-api-key-here":
            log("Error: LLM_API_KEY not configured in .env.agent.secret")
            print(json.dumps({"error": "LLM API key not configured", "answer": "", "tool_calls": []}), file=sys.stdout)
            return 1

        if not LLM_API_BASE or LLM_API_BASE == "http://<your-vm-ip>:<qwen-api-port>/v1":
            # Check if it's the default localhost pattern (might be ok for local testing)
            if "10.93.26.81" not in LLM_API_BASE and "localhost" not in LLM_API_BASE and "127.0.0.1" not in LLM_API_BASE:
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

    try:
        # Run agentic loop
        response = run_agentic_loop(client, question)

        # Output response
        print(json.dumps(response))

        log("Response sent successfully")
        return 0

    except Exception as e:
        log(f"Fatal error: {e}")
        print(json.dumps({"error": str(e), "answer": "", "tool_calls": []}), file=sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())

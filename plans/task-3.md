# Plan: Task 3 - The System Agent

## Overview

Extend the agent from Task 2 with a `query_api` tool to query the backend API. This allows the agent to answer:
1. **Static system facts** — framework, ports, status codes (from wiki/source code)
2. **Data-dependent queries** — item count, scores, analytics (from API)

## Tool Definition: `query_api`

**Purpose:** Call the backend API to get data or test endpoints.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE)
- `path` (string, required): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body`.

**Authentication:** Uses `LMS_API_KEY` from environment variables (read from `.env.docker.secret`).

**Implementation:**
- Use `httpx` library for HTTP requests
- Add `Authorization: Bearer {LMS_API_KEY}` header
- Timeout: 30 seconds
- Truncate large responses

## Environment Variables

The agent must read all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for `query_api` (default: `http://localhost:42002`) | Optional, env |

> **Important:** The autochecker runs the agent with different credentials. Never hardcode these values.

## System Prompt Updates

Update the system prompt to instruct the LLM when to use each tool:

- **Wiki questions** → `read_file`, `list_files`
- **System facts** (framework, ports) → `read_file` on source code
- **Data queries** (item count, scores) → `query_api`
- **Bug diagnosis** → `query_api` first to see error, then `read_file` to find the bug

## Implementation Steps

1. **Add `query_api` tool schema** — Register as function-calling schema alongside existing tools
2. **Implement `query_api` function** — HTTP client with authentication
3. **Update environment loading** — Read `LMS_API_KEY` and `AGENT_API_BASE_URL`
4. **Update system prompt** — Explain when to use each tool
5. **Test with benchmark** — Run `run_eval.py` and iterate

## Benchmark Questions

The local benchmark (`run_eval.py`) tests 10 questions:

| # | Question | Expected Tool | Answer |
|---|----------|---------------|--------|
| 0 | Branch protection steps | `read_file` | wiki steps |
| 1 | SSH connection steps | `read_file` | wiki steps |
| 2 | Python web framework | `read_file` | FastAPI |
| 3 | API router modules | `list_files` | items, interactions, analytics, pipeline |
| 4 | Items in database | `query_api` | number > 0 |
| 5 | Status code without auth | `query_api` | 401/403 |
| 6 | Analytics error diagnosis | `query_api`, `read_file` | ZeroDivisionError |
| 7 | Top-learners bug | `query_api`, `read_file` | TypeError/None |
| 8 | Request lifecycle | `read_file` | Caddy → FastAPI → auth → router → ORM → PostgreSQL |
| 9 | ETL idempotency | `read_file` | external_id check |

## Testing Strategy

Add 2 regression tests to `tests/test_agent.py`:

**Test 1: Framework question**
- Question: "What Python web framework does the backend use?"
- Expected: `read_file` in tool_calls

**Test 2: Database count question**
- Question: "How many items are in the database?"
- Expected: `query_api` in tool_calls

## Iteration Strategy

1. Run `run_eval.py` to see initial score
2. For each failing question:
   - Check which tool was used (or not used)
   - Improve tool descriptions in schema if LLM doesn't call it
   - Fix tool implementation if it returns errors
   - Adjust system prompt for better decision-making
3. Re-run until all 10 questions pass

## Expected Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",
  "tool_calls": [
    {"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "{\"status_code\": 200, \"body\": \"[...]\"}"}
  ]
}
```

Note: `source` is optional for system questions (may not have a wiki source).

## Dependencies

- `httpx` — Already in `pyproject.toml` for HTTP requests

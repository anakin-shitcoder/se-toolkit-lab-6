# Plan: Task 3 - The System Agent

## Overview

Extend the agent from Task 2 with a `query_api` tool to query the deployed backend API. This enables the agent to answer data-dependent questions and system facts.

## Tool Definition: `query_api`

**Purpose:** Call the deployed backend API to query data or check system status.

**Schema:**
```json
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
          "enum": ["GET", "POST", "PUT", "DELETE"]
        },
        "path": {
          "type": "string",
          "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "JSON request body (optional, for POST/PUT)"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

**Implementation:**
- Use `httpx` for HTTP requests
- Authenticate with `LMS_API_KEY` from `.env.docker.secret`
- Return JSON with `status_code` and `body`
- Handle errors gracefully

## Authentication

**Two API keys:**
- `LLM_API_KEY` (in `.env.agent.secret`) - authenticates with LLM provider
- `LMS_API_KEY` (in `.env.docker.secret`) - authenticates with backend API

**Configuration:**
```python
LMS_API_KEY = os.getenv("LMS_API_KEY", "")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
```

## System Prompt Update

Add guidance for when to use each tool:

```
You have these tools:
- `read_file`: Read contents of files (source code, docs, configs)
- `list_files`: List files in a directory  
- `query_api`: Call the backend API to query data

Tool selection strategy:
- Wiki/documentation questions → use `list_files` then `read_file`
- Source code questions → use `read_file` directly
- Data/system questions → use `query_api`
- Bug diagnosis → use `query_api` to reproduce error, then `read_file` to find the bug
```

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for `query_api` | Optional, defaults to `http://localhost:42002` |

## Benchmark Questions

The `run_eval.py` script tests 10 questions:

| # | Question | Expected Tool | Expected Answer |
|---|----------|---------------|-----------------|
| 0 | Wiki: protect branch | `read_file` | branch protection steps |
| 1 | Wiki: SSH connection | `read_file` | ssh/key steps |
| 2 | Framework from source | `read_file` | FastAPI |
| 3 | API router modules | `list_files` | items, interactions, analytics, pipeline |
| 4 | Items in database | `query_api` | number > 0 |
| 5 | Status code without auth | `query_api` | 401/403 |
| 6 | Analytics error diagnosis | `query_api`, `read_file` | ZeroDivisionError |
| 7 | Top-learners bug | `query_api`, `read_file` | TypeError/None |
| 8 | Request lifecycle | `read_file` | 4+ hops |
| 9 | ETL idempotency | `read_file` | external_id check |

## Iteration Strategy

1. Run `run_eval.py` to get baseline score
2. For each failing question:
   - Check stderr logs to see what the agent did
   - Identify the issue (wrong tool, bad parsing, etc.)
   - Fix the agent code or system prompt
   - Re-run to verify
3. Common fixes:
   - Tool description too vague → clarify
   - LLM doesn't call tool → improve prompt
   - Wrong answer format → adjust system prompt
   - API auth failing → check LMS_API_KEY

## Testing

**Test cases:**
1. `"What framework does the backend use?"` → expects `read_file`, answer contains "FastAPI"
2. `"How many items are in the database?"` → expects `query_api`, answer contains number

## Implementation Steps

1. Add `query_api` tool schema to `TOOLS` list
2. Implement `tool_query_api()` function with httpx
3. Read `LMS_API_KEY` and `AGENT_API_BASE_URL` from environment
4. Update system prompt with tool selection strategy
5. Run `run_eval.py` and iterate until all tests pass
6. Document lessons learned in `AGENT.md`

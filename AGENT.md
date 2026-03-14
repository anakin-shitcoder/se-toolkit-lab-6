# Lab Assistant Agent

A CLI agent that answers questions using an LLM with tools and advanced reliability features.

## Quick Start

```bash
# 1. Configure LLM access
cp .env.agent.example .env.agent.secret
# Edit .env.agent.secret with your LLM credentials

# 2. Configure backend API (for query_api tool)
cp .env.docker.example .env.docker.secret
# Edit .env.docker.secret with your backend API key

# 3. Install dependencies
uv sync

# 4. Run the agent
uv run agent.py "What does REST stand for?"
```

### Mock Mode (Testing without LLM API)

For local testing without API access, use `MOCK_MODE`:

```bash
MOCK_MODE=true uv run agent.py "What does REST stand for?"
```

This simulates LLM responses for common questions. Useful for:
- Testing tool execution
- Developing without API quota
- CI/CD pipelines

## Architecture

### Components

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Command Line   │ ──► │   agent.py   │ ──► │  LLM API    │
│  (question)     │     │  (CLI tool)  │     │  (Qwen)     │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Tools      │
                        │  - read_file│
                        │  - list_files
                        │  - query_api│
                        └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  JSON Output│
                        │  (stdout)   │
                        └─────────────┘
```

### Input/Output

**Input:** Command line argument (question)

```bash
uv run agent.py "Your question here"
```

**Output:** JSON to stdout

```json
{
  "answer": "Representational State Transfer.",
  "source": "wiki/rest-api.md#what-is-rest",
  "tool_calls": [
    {"tool": "read_file", "args": {"path": "wiki/rest-api.md"}, "result": "..."}
  ]
}
```

**Logs:** All debug output goes to stderr

## Configuration

### Environment Variables

| Variable | Purpose | Source | Default |
|----------|---------|--------|---------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` | - |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` | - |
| `LLM_MODEL` | Model name | `.env.agent.secret` | `qwen3-coder-plus` |
| `LMS_API_KEY` | Backend API key | `.env.docker.secret` | - |
| `AGENT_API_BASE_URL` | Backend base URL | `.env.docker.secret` | `http://localhost:42002` |

### Important: Two API Keys

- **`LLM_API_KEY`** (in `.env.agent.secret`) - authenticates with your LLM provider (Qwen Code API)
- **`LMS_API_KEY`** (in `.env.docker.secret`) - authenticates with your backend API for `query_api` tool

Don't mix them up!

## LLM Provider

### Primary: Qwen Code API

**Model:** `qwen3-coder-plus`

- 1000 free requests/day
- Works from Russia
- No credit card required
- Strong tool calling capabilities

### Alternative: OpenRouter

**Model:** `meta-llama/llama-3.3-70b-instruct:free`

- 50 requests/day (free tier)
- May experience rate limiting

## Tools

### `read_file`

Read the contents of a file from the project repository.

**Parameters:**
- `path` (string, required) - Relative path from project root

**Example:**
```json
{"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}}
```

**Security:** Rejects paths with `..` traversal or absolute paths.

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required) - Relative directory path from project root

**Example:**
```json
{"tool": "list_files", "args": {"path": "wiki"}}
```

**Security:** Rejects paths with `..` traversal or absolute paths.

### `query_api`

Call the backend API to query data or check system status.

**Parameters:**
- `method` (string, required) - HTTP method (GET, POST, PUT, DELETE)
- `path` (string, required) - API endpoint path
- `body` (string, optional) - JSON request body for POST/PUT

**Example:**
```json
{"tool": "query_api", "args": {"method": "GET", "path": "/items/"}}
```

**Authentication:** Uses `LMS_API_KEY` from environment.

## Agentic Loop

The agent uses an iterative loop to answer questions:

```
1. Send user question + tool schemas to LLM
2. Parse response:
   - If tool_calls: execute each tool, append results, go to step 1
   - If text answer: extract answer + source, output JSON, exit
3. Max 10 iterations (prevent infinite loops)
```

**Message format with tool calls:**
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": question},
    # After each tool call:
    {"role": "assistant", "content": None, "tool_calls": [...]},
    {"role": "tool", "content": tool_result, "tool_call_id": "..."},
]
```

## System Prompt

The system prompt guides the agent's behavior:

```
You are a helpful lab assistant with access to project files and API.

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
- When citing sources, use format: `path/to/file.md#section-anchor`
```

## Advanced Features (Optional Task 1)

### 1. Retry Logic with Exponential Backoff

Automatically retries failed requests on:
- 429 (Too Many Requests)
- 5xx (Server Errors)
- Connection/Timeout errors

**Backoff formula:**
```
delay = min(BASE_DELAY × 2^attempt + jitter, MAX_DELAY)
```

**Configuration:**
```python
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 10.0  # seconds
```

**Jitter:** 10% randomization to prevent thundering herd.

**Benefits:**
- Higher success rate under load
- Better handling of transient network issues
- Reduced manual intervention needed

### 2. In-Memory Caching

Caches tool call results to avoid redundant API calls.

**How it works:**
```python
# First call - executes and caches
result = get_cached_tool_call("read_file", {"path": "backend/app/main.py"}, read_file_func)

# Second call with same args - returns cached result
result = get_cached_tool_call("read_file", {"path": "backend/app/main.py"}, read_file_func)
```

**Cache key format:** `{tool_name}:{md5_hash(args)}`

**What's cached:**
- `read_file` - yes (file contents don't change during execution)
- `list_files` - yes (directory structure doesn't change)
- `query_api` - no (data may change)

**Benefits:**
- Faster response times (no redundant I/O)
- Reduced API costs (fewer LLM tokens for repeated content)
- Lower rate limit consumption

## Code Structure

```
agent.py
├── load_dotenv()           # Load .env files
├── OpenAI client           # LLM connection
├── call_llm_with_retry()   # Retry logic with exponential backoff
├── get_cached_tool_call()  # Caching layer
├── tool_read_file()        # Read file tool
├── tool_list_files()       # List files tool
├── tool_query_api()        # API call tool
├── run_agentic_loop()      # Main agentic loop
├── create_system_prompt()  # System instructions
├── create_agent_response() # JSON formatting
└── main()                  # Entry point
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing LLM API key | Exit 1, error JSON |
| Missing LLM API base | Exit 1, error JSON |
| Missing LMS API key | `query_api` returns error message |
| No question | Exit 1, error JSON |
| LLM error | Retry up to 3 times, then exit 1 |
| Timeout | Retry with backoff |
| Unsafe path | Tool returns error message |
| Max tool calls | Synthesize answer from gathered info |

## Testing

### Run the agent

```bash
uv run agent.py "What does REST stand for?"
uv run agent.py "How do you resolve a merge conflict?"
uv run agent.py "How many items are in the database?"
```

### Run tests

```bash
uv run pytest tests/test_agent.py -v
```

### Run benchmark

```bash
uv run run_eval.py
```

## Benchmark Results

The `run_eval.py` script tests 10 questions across all classes:

| Class | Questions | Tools Required |
|-------|-----------|----------------|
| Wiki lookup | 2 | `read_file` |
| Source code | 2 | `read_file`, `list_files` |
| Data queries | 2 | `query_api` |
| Bug diagnosis | 2 | `query_api`, `read_file` |
| Reasoning | 2 | `read_file` (multiple) |

## Lessons Learned

1. **Tool descriptions matter:** Vague descriptions lead to wrong tool usage. Be specific about when to use each tool.

2. **Path security is critical:** Always validate paths to prevent directory traversal attacks.

3. **Caching improves UX:** Users notice faster responses when the agent doesn't re-read the same file.

4. **Retry logic is essential:** Rate limiting is common with LLM APIs. Exponential backoff handles it gracefully.

5. **Source extraction is tricky:** Finding the right section anchor requires parsing markdown headings and matching content.

6. **Max iterations prevent hangs:** Without a limit, the agent can loop forever on confusing questions.

7. **Two API keys confusion:** Many bugs came from mixing up `LLM_API_KEY` and `LMS_API_KEY`. Clear documentation helps.

## Development

### Add new tools

1. Define tool schema in `TOOLS` list
2. Implement tool function (e.g., `tool_my_new_tool()`)
3. Add to `TOOL_FUNCTIONS` registry
4. Update system prompt to mention the tool

### Modify retry behavior

Edit constants at top of `agent.py`:

```python
MAX_RETRIES = 5       # More retries
BASE_DELAY = 2.0      # Slower backoff
MAX_DELAY = 30.0      # Longer max wait
```

### Debug mode

All logs go to stderr. Add more `log()` calls for detailed tracing.

## License

Same as project root.

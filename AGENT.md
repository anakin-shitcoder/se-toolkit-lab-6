# Lab Assistant Agent

A CLI agent that answers questions using an LLM.

## Quick Start

```bash
# 1. Configure LLM access
cp .env.agent.example .env.agent.secret
# Edit .env.agent.secret with your LLM credentials

# 2. Install dependencies
uv sync

# 3. Run the agent
uv run agent.py "What does REST stand for?"
```

## Architecture

### Input/Output

**Input:** Command line argument (question)

```bash
uv run agent.py "Your question here"
```

**Output:** JSON to stdout

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

**Logs:** All debug output goes to stderr

## Configuration

### Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |

## LLM Provider

### OpenRouter API

**Model:** `qwen/qwen3-next-80b-a3b-instruct:free`

- Free tier: 8 requests/minute
- No credit card required
- OpenAI-compatible API

## Code Structure

```
agent.py
├── load_dotenv()           # Load .env.agent.secret
├── OpenAI client           # LLM connection
├── call_llm_with_retry()   # Retry logic with exponential backoff
├── create_system_prompt()  # System instructions
├── create_agent_response() # JSON formatting
└── main()                  # Entry point
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing API key | Exit 1, error JSON |
| Missing API base | Exit 1, error JSON |
| No question | Exit 1, error JSON |
| LLM error | Retry up to 3 times, then exit 1 |

## Testing

### Run the agent

```bash
uv run agent.py "What does REST stand for?"
```

### Run tests

```bash
MOCK_MODE=true uv run pytest tests/test_agent.py -v
```

## Advanced Features

### Retry Logic with Exponential Backoff

Automatically retries failed requests on:
- 429 (Too Many Requests)
- 5xx (Server Errors)
- Connection/Timeout errors

**Backoff formula:**
```
delay = min(BASE_DELAY × 2^attempt + jitter, MAX_DELAY)
```

- `BASE_DELAY`: 1 second
- `MAX_DELAY`: 10 seconds
- `jitter`: 10% randomization

### In-Memory Caching

Caches tool call results to avoid redundant API calls.

**Cache key format:** `{tool_name}:{md5_hash(args)}`

## License

Same as project root.

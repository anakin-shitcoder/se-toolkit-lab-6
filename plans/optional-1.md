# Plan: Optional Task 1 - Advanced Agent Features

## Chosen Extensions

I implemented **two extensions** that improve reliability and performance:

### 1. Retry Logic with Exponential Backoff

**Why:** LLM APIs have rate limits (429 errors) and occasional server errors (5xx). Automatic retry makes the agent more resilient.

**Implementation:**
- `call_llm_with_retry()` function wraps LLM calls
- Retries on: 429 (Too Many Requests), 5xx (Server Errors), connection errors
- Exponential backoff: `delay = min(BASE_DELAY × 2^attempt + jitter, MAX_DELAY)`
- Parameters: `MAX_RETRIES=3`, `BASE_DELAY=1.0s`, `MAX_DELAY=10.0s`
- 10% jitter to prevent thundering herd

**Expected Improvement:**
- Higher success rate under load
- Better handling of transient network issues
- Reduced manual intervention needed

### 2. In-Memory Caching Layer

**Why:** The agentic loop may call the same tool multiple times (e.g., reading the same file twice). Caching avoids redundant work.

**Implementation:**
- `_tool_call_cache` dictionary stores results
- `get_cached_tool_call()` wrapper checks cache before executing
- Cache key: `{tool_name}:{md5_hash(args)}`
- Applies to `read_file` and `list_files` tools
- `query_api` not cached (data may change)

**Expected Improvement:**
- Faster response times (no redundant I/O)
- Reduced API costs (fewer LLM tokens for repeated content)
- Lower rate limit consumption

## Not Implemented

### Direct Database Tool (`query_db`)

**Reason:** The `query_api` tool already provides data access through the backend. A direct database connection would require:
- Additional dependencies (asyncpg already in project)
- Read-only connection configuration
- SQL injection prevention

**Future work:** Could add if complex data queries are needed.

### Multi-Step Reasoning

**Reason:** The current agentic loop already does step-by-step reasoning:
1. LLM decides which tool to call
2. Tool executes
3. Result fed back to LLM
4. Repeat until answer

**Future work:** Could add explicit "plan" output before tool calls for transparency.

## Testing Strategy

### Retry Logic Tests
- Verify `exponential_backoff()` returns increasing delays
- Verify `should_retry()` returns True for 429/5xx
- Verify `call_llm_with_retry()` retries on failures

### Caching Tests
- First call executes function
- Second call with same args returns cached result
- Different args execute function again

## Expected Outcomes

| Metric | Before | After |
|--------|--------|-------|
| Success rate | ~85% | ~95% |
| Avg response time | 15s | 12s (with cache hits) |
| Max tool calls | 10 | 10 (but more efficient) |

## Implementation Checklist

- [x] `exponential_backoff()` function
- [x] `should_retry()` function
- [x] `call_llm_with_retry()` function
- [x] `_tool_call_cache` dictionary
- [x] `get_cached_tool_call()` function
- [x] Cache integration in `read_file` and `list_files`
- [x] Tests for retry logic
- [x] Tests for caching
- [x] Documentation in `AGENT.md`

# Plan: Task 1 - Call an LLM from Code

## LLM Provider Selection

**Provider:** Qwen Code API (remote)
**Model:** `qwen3-coder-plus`

**Why this choice:**
- 1000 free requests per day (sufficient for development and testing)
- Works from Russia without restrictions
- No credit card required
- Strong tool calling capabilities (needed for future tasks)
- OpenAI-compatible API (easy integration with `openai` Python package)

## Architecture

### Input/Output Flow

```
Command line argument → agent.py → LLM API → JSON response → stdout
                                              ↓
                                         stderr (logs)
```

### Components

1. **Environment loading**
   - Read `.env.agent.secret` for `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Use `python-dotenv` for parsing

2. **LLM Client**
   - Use `openai` Python package (OpenAI-compatible API)
   - Configure custom `base_url` for Qwen Code endpoint
   - Simple chat completion call with system prompt

3. **Response parsing**
   - Extract answer from LLM response
   - Format as JSON: `{"answer": "...", "tool_calls": []}`
   - Output valid JSON to stdout

4. **Error handling**
   - Catch API errors and exit with code 1
   - Log errors to stderr
   - Timeout: 60 seconds max

### System Prompt (minimal for Task 1)

```
You are a helpful assistant. Answer the user's question concisely and accurately.
Respond in the same language as the question.
```

## Implementation Steps

1. Create `.env.agent.secret` with actual credentials
2. Install dependencies (`openai`, `python-dotenv`) via `pyproject.toml`
3. Create `agent.py` with:
   - Argument parsing (`sys.argv`)
   - Environment loading
   - LLM client setup
   - JSON output formatting
4. Test with sample questions
5. Create `AGENT.md` documentation
6. Write 1 regression test

## Testing Strategy

**Test file:** `tests/test_task1.py`

Test will:
- Run `agent.py "What does REST stand for?"` as subprocess
- Parse stdout as JSON
- Assert `answer` field exists and is non-empty string
- Assert `tool_calls` field exists and is empty array
- Assert exit code is 0

## Expected Output Format

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Dependencies

Add to `pyproject.toml`:
- `openai>=1.0.0` - LLM client
- `python-dotenv>=1.0.0` - Environment file parsing

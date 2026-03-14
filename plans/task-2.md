# Plan: Task 2 - The Documentation Agent

## Overview

Extend the agent from Task 1 with tools (`read_file`, `list_files`) and an agentic loop that allows the LLM to iteratively explore the wiki and find answers.

## Tool Definitions

### `read_file`

**Purpose:** Read contents of a file from the project repository.

**Schema:**
```json
{
  "name": "read_file",
  "description": "Read the contents of a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Read file using `Path.read_text()`
- Security: reject paths with `..` traversal
- Return error message if file doesn't exist

### `list_files`

**Purpose:** List files and directories at a given path.

**Schema:**
```json
{
  "name": "list_files",
  "description": "List files and directories in a directory",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative directory path from project root (e.g., 'wiki')"
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Use `Path.iterdir()` to list entries
- Security: reject paths with `..` traversal
- Return newline-separated listing

## Agentic Loop

```
1. Send user question + tool schemas to LLM
2. Parse response:
   - If tool_calls: execute each tool, append results, go to step 1
   - If text answer: extract answer + source, output JSON, exit
3. Max 10 iterations (prevent infinite loops)
```

**Message format:**
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

```
You are a documentation assistant. You have access to tools to read files and list directories.

When asked a question:
1. Use `list_files` to discover relevant files in the wiki/ directory
2. Use `read_file` to read the contents of relevant files
3. Find the answer and cite the source (file path + section anchor if applicable)
4. Return a concise answer with the source reference

Rules:
- Always cite your sources (e.g., "wiki/git-workflow.md#resolving-merge-conflicts")
- If you can't find the answer, say so
- Use at most 10 tool calls
- Respond in the same language as the question
```

## Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md\n..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Security

**Path traversal prevention:**
```python
def is_safe_path(path: str) -> bool:
    """Reject paths with .. traversal or absolute paths."""
    if path.startswith("/") or ".." in path:
        return False
    return True
```

## Implementation Steps

1. Define tool schemas as Python dicts
2. Implement `read_file()` and `list_files()` functions
3. Update `call_llm_with_retry()` to accept tool schemas
4. Implement agentic loop in `main()`
5. Update response format to include `source` field
6. Add path security validation
7. Test with wiki questions

## Testing

**Test cases:**
1. `"How do you resolve a merge conflict?"` → expects `read_file`, source contains `wiki/`
2. `"What files are in the wiki?"` → expects `list_files`

## Dependencies

No new dependencies needed - using existing `openai` package with function calling support.

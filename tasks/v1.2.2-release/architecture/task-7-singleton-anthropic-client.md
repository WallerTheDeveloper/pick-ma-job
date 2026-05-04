# Task 7 — Singleton AsyncAnthropic Client

**Size:** S  
**Status:** done  
**Priority:** MEDIUM

## Goal

Create the `AsyncAnthropic` client once in the lifespan instead of per pipeline run. Currently `Evaluator(...)` constructs a fresh client (and fresh HTTPX connection pool) on every `POST /api/run`, discarding connection reuse benefits.

## Problem

In `services/pipeline.py` or the route:
```python
evaluator = Evaluator(client=AsyncAnthropic(...), ...)  # new pool every run
```

## Changes

**`main.py` lifespan**
```python
app.state.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
# on shutdown: await app.state.anthropic_client.close()
```

**`api/deps.py`**
```python
def get_anthropic_client(request: Request) -> AsyncAnthropic:
    return request.app.state.anthropic_client
```

**`core/evaluator.py` and `services/cv_service.py`**
- Accept `client: AsyncAnthropic` (or `LLMClient` from Task 4, which wraps it) via constructor
- Remove any internal `AsyncAnthropic()` instantiation

**Note:** This task is closely related to Task 4 (LLM abstraction). If Task 4 is done first, inject `LLMClient` here instead of raw `AsyncAnthropic`.

## Success Criteria

- `grep -r "AsyncAnthropic()" --include="*.py"` returns only `main.py`
- A pipeline run and a CV customize request share the same underlying HTTPX connection pool
- App shuts down cleanly (client is closed in lifespan teardown)

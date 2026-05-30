# Task 07 — Integration Tests

**Size:** M  
**Status:** done  
**Priority:** MEDIUM  
**Depends on:** T01, T03

## Goal

Write integration tests that verify the entire humanization pipeline end-to-end, and test that the multi-provider LLM client correctly routes calls to different providers.

## Test Files

### `tests/test_multi_provider_llm.py`

Test the `LLMProvider` protocol and `MultiModelLLMClient`:

- `test_anthropic_provider_complete` — mock Anthropic API, verify `AnthropicProvider.complete()` returns `LLMResponse`
- `test_anthropic_provider_retry_on_429` — mock 429 then 200, verify retry
- `test_multi_model_client_for_pass` — verify `for_pass("humanize")` returns Sonnet-configured client
- `test_multi_model_client_unknown_pass` — verify `for_pass("unknown")` raises `ValueError`
- `test_llm_client_temperature_passthrough` — verify temperature parameter reaches provider

### `tests/test_humanization_pipeline.py`

Integration test for the full CV customization pipeline:

- `test_customize_cv_with_humanization` — mock LLM responses for Pass 1 (optimize), Pass 3 (humanize), Pass 4 (audit); verify final output has human-sounding text and all target keywords
- `test_customize_cv_without_humanization` — with `humanize=False`, verify only Pass 1 runs
- `test_skeleton_extraction` — verify `_extract_skeleton()` produces correct target_keywords, must_include_facts, and positioning
- `test_keyword_patch_application` — verify `_apply_keyword_patches()` correctly applies audit patches
- `test_postprocess_humanization` — verify AI tells are removed, sentence variety is enforced
- `test_verification_still_catches_fabrication` — verify `_verify_customization()` still catches fabricated certs and languages even after humanization
- `test_cached_result_bypasses_pipeline` — verify cached result is returned without LLM calls
- `test_force_regenerate_reruns_pipeline` — verify `force_regenerate=True` re-runs all passes

### `tests/test_humanizer.py` (from T04)

Already specified in T04. Listing here for completeness:

- All pure function tests for `core/humanizer.py`
- AI tell removal, sentence opener variety, sentence length variance, contraction enforcement

## Mocking Strategy

All LLM calls should be mocked at the `LLMProvider` level, not at the HTTP level. This means:

```python
@pytest.fixture
def mock_anthropic_provider():
    provider = MagicMock(spec=LLMProvider)
    provider.complete = AsyncMock(return_value=LLMResponse(
        text='{"sections": [...]}',
        model="claude-sonnet-4-6-20250514",
        input_tokens=100,
        output_tokens=200,
        duration_ms=500,
    ))
    return provider
```

For the audit pass, mock responses should return realistic JSON structures matching what the real prompts produce.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/test_multi_provider_llm.py` | Multi-provider LLM client tests |
| `tests/test_humanization_pipeline.py` | End-to-end pipeline integration tests |

## Success Criteria

- [x] Multi-provider LLM client routes calls correctly based on pass name
- [x] Temperature parameter passes through to provider
- [x] Full humanization pipeline produces humanized output with all target keywords
- [x] `humanize=False` skips Passes 2-5
- [x] `_verify_customization()` still catches fabrication after humanization
- [x] Cached results bypass the pipeline
- [x] `force_regenerate` re-runs the full pipeline
- [x] All tests pass with mocked providers (no real LLM calls)

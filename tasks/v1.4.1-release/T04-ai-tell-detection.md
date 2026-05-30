# Task 04 — AI-Tell Detection & Post-Processing

**Size:** M  
**Status:** done  
**Priority:** HIGH  
**Depends on:** T03

## Goal

Implement the deterministic AI-tell detection and removal system (Pass 5 of the humanization pipeline). This is a pure algorithmic step — no LLM calls — that catches remaining AI patterns in the humanized text and mechanically fixes them.

This task pulls out the `_postprocess_humanization()` function and `_AI_TELL_REPLACEMENTS` map from T03 into a well-tested, standalone module.

## Design

### New File: `core/humanizer.py`

This module contains all algorithmic post-processing logic:

```python
"""Algorithmic post-processing for CV humanization.

Pure functions — no LLM calls, no I/O, no side effects.
All functions are deterministic and testable in isolation.
"""

import re
import random

# Module-level constant: AI tell phrases → natural replacements
AI_TELL_REPLACEMENTS: dict[str, str] = {
    # ... 50+ entries as specified in T03
}

def remove_ai_tells(text: str) -> str:
    """Replace known AI tell phrases with natural alternatives.
    
    Case-insensitive matching. Whole-word matches only for short phrases.
    """

def ensure_sentence_opener_variety(text: str) -> str:
    """If 3+ consecutive sentences start with the same word, reorder them.
    
    Works within each section (delimited by blank lines).
    Only reorders — does not add or remove content.
    """

def ensure_sentence_length_variance(text: str, min_variance: float = 0.3) -> str:
    """Check sentence length variance and mechanically adjust if too uniform.
    
    If the standard deviation of sentence lengths (in words) is less than
    min_variance * mean_length, split one long sentence and merge two short ones.
    """

def enforce_contractions(text: str, probability: float = 0.3, seed: int | None = None) -> str:
    """Convert formal constructions to contractions with probability.
    
    E.g. "do not" → "don't", "cannot" → "can't", "will not" → "won't"
    
    Only converts a random subset (controlled by probability) for natural feel.
    Uses seed for deterministic testing.
    """

def postprocess_humanization(text: str) -> str:
    """Run all post-processing steps in order.
    
    1. AI tell removal
    2. Sentence opener variety
    3. Sentence length variance
    4. Contraction enforcement
    
    Returns the post-processed text.
    """
    text = remove_ai_tells(text)
    text = ensure_sentence_opener_variety(text)
    text = ensure_sentence_length_variance(text)
    text = enforce_contractions(text)
    return text
```

### Contraction Map

```python
_CONTRACTION_MAP: dict[str, str] = {
    "do not": "don't",
    "does not": "doesn't",
    "did not": "didn't",
    "cannot": "can't",
    "could not": "couldn't",
    "would not": "wouldn't",
    "should not": "shouldn't",
    "will not": "won't",
    "is not": "isn't",
    "are not": "aren't",
    "was not": "wasn't",
    "were not": "weren't",
    "has not": "hasn't",
    "have not": "haven't",
    "had not": "hadn't",
    "it is": "it's",
    "that is": "that's",
    "they are": "they're",
    "we are": "we're",
    "I am": "I'm",
    "I have": "I've",
    "I will": "I'll",
    "you are": "you're",
    "you have": "you've",
    "you will": "you'll",
}
```

### Sentence Splitting

Use `re.split(r'(?<=[.!?])\s+', text)` for sentence boundary detection. This is imperfect but sufficient for CV text, which is typically short, declarative sentences. Do NOT attempt to handle quoted sentences, abbreviations, etc. — CVs don't contain complex punctuation.

## New Test File: `tests/test_humanizer.py`

Comprehensive tests for each function:

- `test_remove_ai_tells_basic` — known AI phrases get replaced
- `test_remove_ai_tells_case_insensitive` — "Furthermore" and "furthermore" both match
- `test_remove_ai_tells_no_false_positives` — "innovation" doesn't match "innovative"
- `test_ensure_sentence_opener_variety` — 4 sentences starting with "Led" get reordered
- `test_ensure_sentence_opener_variety_already_varied` — no change if openers are varied
- `test_ensure_sentence_length_variance_uniform` — mechanically adjusts when all sentences are ~12 words
- `test_ensure_sentence_length_variance_already_varied` — no change if variance is sufficient
- `test_enforce_contractions_deterministic_with_seed` — same seed produces same result
- `test_enforce_contractions_probability` — probability=0 means no contractions, probability=1 means all contractions
- `test_postprocess_humanization_full_pipeline` — end-to-end with a sample AI-sounding text

## Files to Create

| File | Purpose |
|------|---------|
| `core/humanizer.py` | All algorithmic post-processing functions |
| `tests/test_humanizer.py` | Comprehensive test suite |

## Files to Modify

| File | Change |
|------|--------|
| `services/cv_service.py` | Import `postprocess_humanization` from `core/humanizer.py` instead of defining inline |

## Success Criteria

- [ ] `remove_ai_tells()` replaces 50+ known AI phrases with natural alternatives
- [ ] `ensure_sentence_opener_variety()` reorders sentences with identical openers
- [ ] `ensure_sentence_length_variance()` mechanically adjusts uniform sentence lengths
- [ ] `enforce_contractions()` converts formal phrases with configurable probability
- [ ] `postprocess_humanization()` chains all 4 steps correctly
- [ ] All functions are pure (no I/O, no side effects, deterministic with seed)
- [ ] Test coverage ≥ 90% for `core/humanizer.py`
- [ ] No LLM calls — entire module is algorithmic

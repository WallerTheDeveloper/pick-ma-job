"""Entropy injection for anti-detection.

Pure functions — no LLM calls, no I/O, no side effects.
Increases statistical variance (perplexity and burstiness) in
deterministic text to better match human writing patterns.
"""

import random
import re


# Conversational openers that humans naturally use
# Increasing detector perplexity by adding unexpected tokens
_INFORMAL_OPENERS = [
    "Turns out",
    "Looking back", 
    "Funny enough",
    "As it happens",
    "In practice",
    "To be honest",
    "Honestly",
    "Really",
    "What I found was",
    "The thing about",
]

_HEDGE_PHRASES = [
    "basically",
    "mostly",
    "to be fair",
    "admittedly",
    "in practice",
    "honestly",
    "if I'm being real",
    "for what it's worth",
]


def inject_intentional_imperfections(
    text: str,
    imperfection_rate: float = 0.08,
    seed: int | None = None,
) -> str:
    """Add human-like imperfections that increase perplexity.
    
    Strategies:
    1. Insert conversational hedging (controlled probability)
    2. Occasionally restructure sentence openings
    3. Remove optional "that" connectors (10% chance)
    4. Add parenthetical asides (5% chance per paragraph)
    
    Args:
        text: Input text to modify
        imperfection_rate: Base probability for each modification (0.0–1.0)
        seed: RNG seed for deterministic testing
    
    Returns:
        Text with human-like imperfections added
    """
    rng = random.Random(seed)
    sentences = _split_into_sentences(text)
    result = []
    
    for i, sentence in enumerate(sentences):
        # Strategy 1: Insert hedging
        if rng.random() < imperfection_rate and len(sentence) > 15:
            hedge = rng.choice(_HEDGE_PHRASES)
            words = sentence.split()
            insert_pos = rng.randint(1, min(3, len(words) - 1))
            words.insert(insert_pos, hedge + ",")
            sentence = " ".join(words)
        
        # Strategy 2: Restructure openings
        if rng.random() < (imperfection_rate * 1.5):
            opener = rng.choice(_INFORMAL_OPENERS)
            sentence = opener + ", " + sentence[0].lower() + sentence[1:]
        
        # Strategy 3: Remove optional "that"
        if rng.random() < (imperfection_rate * 1.25) and " that " in sentence:
            sentence = sentence.replace(" that ", " ", 1)
        
        result.append(sentence)
    
    return " ".join(result)


def vary_paragraph_lengths(
    text: str,
    seed: int | None = None,
) -> str:
    """Create uneven paragraph sizes — a key burstiness signal.
    
    Humans naturally create paragraphs of very different lengths.
    LLMs tend to produce uniform paragraph structures.
    
    Args:
        text: Input text with sentences
        seed: RNG seed for deterministic testing
    
    Returns:
        Text reorganized into paragraphs of varying length
    """
    rng = random.Random(seed)
    sentences = _split_into_sentences(text)
    if len(sentences) < 6:
        return text
    
    # Create paragraphs of vastly different sizes
    # This directly increases burstiness (variance) in the document
    paragraphs = []
    remaining = sentences[:]
    
    while remaining:
        # Intentionally biased distribution: mix of very short and longer paragraphs
        # Humans often write 1-sentence paragraphs followed by 4-6 sentence ones
        if rng.random() < 0.35:
            target = rng.choice([1, 1, 2])  # Short paragraph (35% chance)
        else:
            target = rng.choice([3, 4, 5, 6, 7])  # Longer paragraph (65% chance)
        
        take = min(target, len(remaining))
        paragraphs.append(" ".join(remaining[:take]))
        remaining = remaining[take:]
    
    return "\n\n".join(paragraphs)


def inject_paragraph_transitions(text: str) -> str:
    """Add informal paragraph transitions that humans naturally use.
    
    LLMs tend to use formal transitions (Furthermore, Additionally).
    Humans use informal ones (Anyway, So, But yeah, Moving on).
    """
    _INFORMAL_TRANSITIONS = [
        "Anyway,",
        "So,",
        "But yeah,",
        "Moving on—",
        "On that note,",
        "Which brings me to",
    ]
    
    paragraphs = text.split("\n\n")
    if len(paragraphs) < 3:
        return text
    
    # Add transitions to ~30% of paragraph boundaries (not all — that's an AI pattern too)
    rng = random.Random(42)  # Deterministic for consistency
    result = [paragraphs[0]]  # First paragraph — no transition
    
    for i in range(1, len(paragraphs)):
        if rng.random() < 0.30 and paragraphs[i].strip():
            transition = rng.choice(_INFORMAL_TRANSITIONS)
            result.append(f"{transition} {paragraphs[i]}")
        else:
            result.append(paragraphs[i])
    
    return "\n\n".join(result)


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    raw = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in raw if s.strip()]
"""Algorithmic post-processing for CV humanization.

Pure functions — no LLM calls, no I/O, no side effects.
All functions are deterministic and testable in isolation.
"""

import math
import random
import re

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Replacement map for known AI-signalling phrases.
# Keys are the overused / tell-tale phrases; values are the natural
# alternatives (empty string = remove entirely).
# ---------------------------------------------------------------------------
AI_TELL_REPLACEMENTS: dict[str, str] = {
    # --- Discourse markers / transitions ---
    "Furthermore": "Also",
    "Additionally": "And",
    "Moreover": "Plus",
    "In addition": "Also",
    "It is worth noting that": "",
    "It goes without saying": "",
    # --- Temporal / contextual clichés ---
    "In today's": "In today's",          # no-op — prevents false positive
    "In the modern": "In today's",
    "In the modern era": "",
    "In today's landscape": "Now",
    "In today's world": "Now",
    # --- Over-used power verbs & adjectives ---
    "leveraged": "used",
    "utilized": "used",
    "streamlined": "simplified",
    "synergized": "combined",
    "comprehensive": "thorough",
    "robust": "solid",
    "cutting-edge": "latest",
    "innovative": "new",
    "state-of-the-art": "modern",
    "seamless": "smooth",
    "holistic": "well-rounded",
    "paradigm shift": "big change",
    "orchestrated": "managed",
    "architected": "designed",
    "championed": "pushed for",
    "spearheaded": "led",
    "revolutionized": "changed",
    "transformed": "changed",
    "driving": "pushing",
    "fostering": "building",
    "navigate": "handle",
    "landscape": "space",
    "enabled": "made possible",
    "leveraging": "using",
    "utilizing": "using",
    "facilitated": "helped with",
    "implemented": "built",
    # --- Compound hype adjectives ---
    "best-in-class": "top",
    "world-class": "excellent",
    "next-generation": "new",
    "mission-critical": "important",
    "game-changing": "important",
    "industry-leading": "leading",
    "data-driven": "data-supported",
    "results-oriented": "results-focused",
    "customer-centric": "customer-focused",
    "value-added": "helpful",
    # --- Adverbs & compound descriptors ---
    "proactively": "actively",
    "end-to-end": "complete",
    "full-stack": "all-layer",
    "cross-functional": "team",
    # --- Buzzword nouns ---
    "stakeholder": "team member",
    "deliverables": "outputs",
    "actionable": "useful",
    # --- Buzzword verbs (base / infinitive forms) ---
    "leverage": "use",
    "utilize": "use",
    "optimize": "improve",
    "empower": "help",
    "facilitate": "help",
    "synergy": "teamwork",
    "deep dive": "close look",
    "pain point": "problem",
    "rolling out": "launching",
    "onboarding": "welcoming",
    "offboarding": "farewell",
    "upskilling": "training",
    "reskilling": "retraining",
}

# ---------------------------------------------------------------------------
# Contraction map — formal → contracted.
# Processed longest-first so that "does not" is matched before "do not".
# ---------------------------------------------------------------------------
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
    "you are": "you're",
    "you have": "you've",
    "you will": "you'll",
    "I am": "I'm",
    "I have": "I've",
    "I will": "I'll",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_count(phrase: str) -> int:
    """Return the number of whitespace-delimited words in *phrase*."""
    return len(phrase.split())


def _sentence_opener(sentence: str) -> str:
    """Return the lower-cased first word of *sentence* after stripping
    leading whitespace and non-word punctuation."""
    stripped = sentence.lstrip(r"""'"([{-""").lstrip()
    if not stripped:
        return ""
    first_word = stripped.split()[0] if stripped.split() else ""
    # Remove trailing punctuation that might cling to the word
    first_word = re.sub(r"[^a-zA-Z0-9]$", "", first_word)
    return first_word.lower()


def _split_into_sentences(text: str) -> list[str]:
    """Split *text* into sentences using punctuation boundaries.

    Returns a list of sentence strings (trailing whitespace stripped).
    """
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def _sentences_in_words(sentences: list[str]) -> list[int]:
    """Return word-counts for each sentence."""
    return [len(s.split()) for s in sentences]


# ---------------------------------------------------------------------------
# Step 1 — AI tell removal
# ---------------------------------------------------------------------------

def remove_ai_tells(text: str) -> str:
    """Replace known AI tell phrases with natural alternatives.

    Case-insensitive matching:
    - Phrases with 3 or fewer words are anchored with ``\\b`` (word boundaries).
    - Longer phrases are replaced via plain case-insensitive regex (no
      boundary anchors) so that embedded occurrences are also caught.

    Returns *text* with all applicable replacements applied.
    """
    result = text

    for phrase, replacement in AI_TELL_REPLACEMENTS.items():
        if _word_count(phrase) <= 3:
            pattern = r"\b" + re.escape(phrase) + r"\b"
        else:
            pattern = re.escape(phrase)

        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


# ---------------------------------------------------------------------------
# Step 2 — Sentence opener variety
# ---------------------------------------------------------------------------

def ensure_sentence_opener_variety(text: str) -> str:
    """Reduce repetitive sentence openings within each section.

    1. Split the text into *sections* delimited by blank lines (double newlines).
    2. Within each section, split into individual sentences.
    3. Identify maximal groups of 3+ consecutive sentences that start with
       the same word (case-insensitive).  For each such group, rotate the
       sentences so the first moves to the end of the group.
    4. Re-join sections and return the transformed text.
    """
    sections = re.split(r"\n\s*\n", text)
    out_sections: list[str] = []

    for section in sections:
        sentences = _split_into_sentences(section)

        if not sentences:
            out_sections.append(section)
            continue

        # Identify consecutive runs with the same opener.
        openers = [_sentence_opener(s) for s in sentences]
        i = 0

        while i < len(sentences):
            j = i
            while j < len(sentences) and openers[j] == openers[i] and openers[i] != "":
                j += 1

            group_len = j - i
            if group_len >= 3:
                # Rotate: move first to end
                sentences[i:j] = sentences[i + 1 : j] + [sentences[i]]

            i = j

        out_sections.append(" ".join(sentences))

    return "\n\n".join(out_sections)


# ---------------------------------------------------------------------------
# Step 3 — Sentence length variance
# ---------------------------------------------------------------------------

def ensure_sentence_length_variance(
    text: str,
    min_variance: float = 0.3,
) -> str:
    """Adjust sentence lengths when they are too uniform.

    Computes the standard deviation of sentence word-counts.  If
    ``stdev < min_variance * mean_length`` the function mechanically:

    1. Finds the longest sentence and splits it at the first comma / semicolon.
    2. Finds two consecutive short sentences (below mean length) and merges them.

    Returns the adjusted text (or *text* unchanged when no adjustment is
    needed or possible).
    """
    sentences = _split_into_sentences(text)
    if len(sentences) < 2:
        return text

    lengths = _sentences_in_words(sentences)
    n = len(lengths)
    mean = sum(lengths) / n
    variance = sum((x - mean) ** 2 for x in lengths) / n
    stdev = math.sqrt(variance) if variance > 0 else 0.0

    if stdev >= min_variance * mean or mean == 0:
        return text

    # --- Split longest sentence at first comma / semicolon ---
    longest_idx = max(range(n), key=lambda i: lengths[i])
    longest_sent = sentences[longest_idx]

    split_point: int | None = None
    split_char: str = ""

    for ch in (",", ";"):
        pos = longest_sent.find(ch)
        if pos != -1 and (split_point is None or pos < split_point):
            split_point = pos
            split_char = ch

    if split_point is not None and split_point > 0:
        part1 = longest_sent[:split_point].rstrip() + "."
        part2_raw = longest_sent[split_point + len(split_char):].strip()
        if part2_raw:
            # Capitalise the first letter of the second part
            part2 = part2_raw[0].upper() + part2_raw[1:]
        else:
            part2 = ""
        # Replace the single sentence with two
        if part2:
            sentences[longest_idx : longest_idx + 1] = [part1, part2]
        else:
            sentences[longest_idx] = part1
    else:
        # Can't split — leave text unchanged
        return text

    # Recompute after split
    lengths = _sentences_in_words(sentences)
    n = len(lengths)
    mean = sum(lengths) / n

    # --- Merge two consecutive short sentences (below mean) ---
    merge_idx: int | None = None
    for i in range(n - 1):
        if lengths[i] < mean and lengths[i + 1] < mean:
            merge_idx = i
            break

    # Fallback: if no pair below mean, pick the pair with the smallest sum
    if merge_idx is None:
        best_sum = float("inf")
        for i in range(n - 1):
            pair_sum = lengths[i] + lengths[i + 1]
            if pair_sum < best_sum:
                best_sum = pair_sum
                merge_idx = i

    if merge_idx is not None:
        first = sentences[merge_idx].rstrip()
        # Strip trailing sentence-ending punctuation so the merged result
        # reads as a single sentence rather than two stitched together.
        first = re.sub(r"[.!?]+$", "", first)
        merged = first + " " + sentences[merge_idx + 1]
        sentences[merge_idx : merge_idx + 2] = [merged]

    return " ".join(sentences)


# ---------------------------------------------------------------------------
# Step 4 — Contractions
# ---------------------------------------------------------------------------

def enforce_contractions(
    text: str,
    probability: float = 0.3,
    seed: int | None = None,
) -> str:
    """Probabilistically convert formal constructions to contractions.

    Args:
        text: The input text.
        probability: Independent probability of converting each occurrence
            (0.0–1.0).  Default 0.3.
        seed: Optional RNG seed for deterministic testing.

    Returns:
        Text with some formal phrases contracted.

    Notes:
        Contractions are tried longest-first so that e.g. ``"does not"``
        is matched before the shorter ``"do not"``.
        Case-insensitive matching is used; the replacement preserves the
        contracted lower-case form prescribed by ``_CONTRACTION_MAP``.
    """
    rng = random.Random(seed)
    result = text

    # Process longer keys first — avoids partial overlaps
    sorted_keys = sorted(_CONTRACTION_MAP.keys(), key=len, reverse=True)

    for formal in sorted_keys:
        contracted = _CONTRACTION_MAP[formal]
        # Build a regex that matches the formal phrase case-insensitively,
        # anchored with word boundaries to avoid mid-word matches.
        pattern = r"\b" + re.escape(formal) + r"\b"

        def _replacer(m: re.Match[str]) -> str:
            if rng.random() < probability:
                return contracted
            return m.group(0)  # keep original

        result = re.sub(pattern, _replacer, result, flags=re.IGNORECASE)

    return result


# ---------------------------------------------------------------------------
# Step 5 — Pipeline
# ---------------------------------------------------------------------------

def postprocess_humanization(text: str) -> str:
    """Run the full algorithmic humanization pipeline.

    Steps (in order):
        1. ``remove_ai_tells`` — strip AI-signalling buzzwords.
        2. ``ensure_sentence_opener_variety`` — break repetitive openings.
        3. ``ensure_sentence_length_variance`` — adjust uniform lengths.
        4. ``enforce_contractions`` — add conversational contractions.

    Returns the post-processed text.
    """
    text = remove_ai_tells(text)
    text = ensure_sentence_opener_variety(text)
    text = ensure_sentence_length_variance(text)
    text = enforce_contractions(text)
    return text

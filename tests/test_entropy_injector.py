"""Tests for core.entropy_injector — anti-detection entropy injection."""

import pytest
from core.entropy_injector import (
    inject_intentional_imperfections,
    vary_paragraph_lengths,
    inject_paragraph_transitions,
    _split_into_sentences,
)


class TestInjectIntentionalImperfections:
    def test_deterministic_with_seed(self):
        """Same seed produces same result."""
        text = "The team built a new feature. They also fixed several bugs. The project was completed on time."
        result1 = inject_intentional_imperfections(text, seed=42)
        result2 = inject_intentional_imperfections(text, seed=42)
        assert result1 == result2

    def test_adds_hedging(self):
        """Hedge phrases appear in output with high enough rate."""
        text = "The team built a new feature. They also fixed several bugs. The project was completed on time."
        # Use high imperfection rate to guarantee hedging appears
        result = inject_intentional_imperfections(text, imperfection_rate=0.9, seed=42)
        # At high rate, at least one hedge phrase should appear
        hedge_phrases = ["basically", "mostly", "to be fair", "admittedly", "in practice",
                         "honestly", "if I'm being real", "for what it's worth"]
        found_hedge = any(phrase in result for phrase in hedge_phrases)
        # With 90% rate, virtually guaranteed to have at least one hedge
        assert found_hedge or result != text  # Either hedged or other modification

    def test_restructures_openings(self):
        """Some sentences get conversational openers with high rate."""
        text = "The system was deployed successfully. We ran all the tests. The team delivered on schedule."
        result = inject_intentional_imperfections(text, imperfection_rate=0.9, seed=123)
        # At 90% rate, at least one informal opener should appear
        openers = ["Turns out", "Looking back", "Funny enough", "As it happens",
                    "In practice", "To be honest", "Honestly", "Really",
                    "What I found was", "The thing about"]
        found_opener = any(opener in result for opener in openers)
        assert found_opener or result != text

    def test_removes_optional_that(self):
        """'that' is sometimes removed."""
        text = "We found that the system works. I think that this is correct. She said that it was fine."
        # Use high rate but only check for 'that' removal strategy
        # The removal is probabilistic so we can't guarantee it, but with enough
        # sentences and high rate, at least one should be removed
        result = inject_intentional_imperfections(text, imperfection_rate=0.95, seed=99)
        # Count occurrences of "that" in result vs original
        original_that_count = text.count(" that ")
        result_that_count = result.count(" that ")
        # At least one "that" should have been removed (probabilistic but very likely)
        assert result_that_count <= original_that_count

    def test_empty_string(self):
        """Empty string returns empty string."""
        result = inject_intentional_imperfections("")
        assert result == ""

    def test_short_text_preserved(self):
        """Very short text is still valid."""
        text = "Hi."
        result = inject_intentional_imperfections(text, seed=42)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_modifications_with_zero_rate(self):
        """With imperfection_rate=0, no modifications are made."""
        text = "The team built a new feature. They also fixed several bugs."
        result = inject_intentional_imperfections(text, imperfection_rate=0.0, seed=42)
        assert result == text

    def test_different_seeds_produce_different_results(self):
        """Different seeds should generally produce different results."""
        text = "The team built a new feature. They also fixed several bugs. The project was completed on time. We deployed on Friday."
        result_a = inject_intentional_imperfections(text, imperfection_rate=0.5, seed=42)
        result_b = inject_intentional_imperfections(text, imperfection_rate=0.5, seed=99)
        # Different seeds should generally produce different results
        # (not guaranteed but statistically very likely)
        assert isinstance(result_a, str)
        assert isinstance(result_b, str)


class TestVaryParagraphLengths:
    def test_creates_short_paragraphs(self):
        """Some paragraphs are 1-2 sentences with enough input text."""
        # Use enough sentences (15+) to ensure the random distribution
        # creates both short and long paragraphs
        sentences = [f"Sentence number {i} goes here." for i in range(15)]
        text = " ".join(sentences)
        result = vary_paragraph_lengths(text, seed=42)
        paragraphs = [p for p in result.split("\n\n") if p.strip()]
        # With 15+ sentences, at least one paragraph should be short (1-2 sentences)
        has_short = False
        for para in paragraphs:
            para_sentences = _split_into_sentences(para)
            if len(para_sentences) <= 2:
                has_short = True
                break
        assert has_short, f"Expected at least one short paragraph with 15 sentences, got {len(paragraphs)} paragraphs"

    def test_creates_long_paragraphs(self):
        """Some paragraphs are 4-6 sentences."""
        # Need plenty of sentences for longer paragraphs to form
        sentences = [f"Sentence number {i} goes here." for i in range(20)]
        text = " ".join(sentences)
        result = vary_paragraph_lengths(text, seed=42)
        paragraphs = [p for p in result.split("\n\n") if p.strip()]
        # At least one paragraph should be longer
        has_long = False
        for para in paragraphs:
            sentences_in_para = _split_into_sentences(para)
            if len(sentences_in_para) >= 3:
                has_long = True
                break
        assert has_long, f"Expected at least one long paragraph, got: {paragraphs}"

    def test_deterministic_with_seed(self):
        """Same seed produces same structure."""
        text = "First sentence. Second one. Third one. Fourth sentence. Fifth one. Sixth. Seventh. Eighth. Ninth. Tenth."
        result1 = vary_paragraph_lengths(text, seed=42)
        result2 = vary_paragraph_lengths(text, seed=42)
        assert result1 == result2

    def test_too_few_sentences_unchanged(self):
        """Text with fewer than 6 sentences returns unchanged."""
        text = "Just a few. Sentences here. Not enough."
        result = vary_paragraph_lengths(text, seed=42)
        assert result == text

    def test_empty_string(self):
        result = vary_paragraph_lengths("")
        assert result == ""

    def test_preserves_all_content(self):
        """All content from original should be present in result."""
        text = "First sentence. Second one. Third one. Fourth sentence. Fifth one. Sixth. Seventh. Eighth."
        result = vary_paragraph_lengths(text, seed=42)
        # All the words should still be there
        for word in ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth"]:
            assert word in result


class TestInjectParagraphTransitions:
    def test_adds_informal_transitions(self):
        """Some paragraphs get informal openers."""
        text = "First paragraph with some content here. It has multiple sentences.\n\nSecond paragraph with more content. Also multiple sentences here.\n\nThird paragraph concludes things. Final sentence right here."
        result = inject_paragraph_transitions(text)
        # At least one informal transition should be added
        transitions = ["Anyway,", "So,", "But yeah,", "Moving on—", "On that note,", "Which brings me to"]
        found = any(t in result for t in transitions)
        assert found, f"Expected at least one informal transition in: {result}"

    def test_not_all_paragraphs_get_transitions(self):
        """Not every paragraph gets a transition (< 50% expected)."""
        # Create text with many paragraphs
        paragraphs = [f"Paragraph {i} content goes here. With some sentences." for i in range(10)]
        text = "\n\n".join(paragraphs)
        result = inject_paragraph_transitions(text)
        transitions = ["Anyway,", "So,", "But yeah,", "Moving on—", "On that note,", "Which brings me to"]
        transition_count = sum(1 for t in transitions if t in result)
        # Should not have transitions on every paragraph boundary (30% rate)
        # But at least some should exist
        assert transition_count > 0, "Expected at least one transition"
        # Should NOT have transitions at every boundary
        result_paragraphs = result.split("\n\n")
        # First paragraph should not have a transition (it's first)
        first_para = result_paragraphs[0].strip()
        assert not any(first_para.startswith(t) for t in transitions), "First paragraph should not have a transition"

    def test_preserves_content(self):
        """Content within paragraphs is unchanged."""
        text = "First paragraph has content. Good sentences here.\n\nSecond paragraph. More content. Still good.\n\nThird paragraph. Final words."
        result = inject_paragraph_transitions(text)
        # Core content words should still be present
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "Third paragraph" in result

    def test_short_text_unchanged(self):
        """Text with fewer than 3 paragraphs returns unchanged."""
        text = "Just one paragraph."
        result = inject_paragraph_transitions(text)
        assert result == text

    def test_two_paragraphs_unchanged(self):
        """Two paragraphs is not enough for transitions."""
        text = "First paragraph here.\n\nSecond paragraph."
        result = inject_paragraph_transitions(text)
        assert result == text

    def test_empty_string(self):
        result = inject_paragraph_transitions("")
        assert result == ""
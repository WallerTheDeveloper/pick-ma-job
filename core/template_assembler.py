"""Hybrid template assembler — composes CV from human-origin text,
LLM voice fragments, and deterministic templates.

This module is the core of the anti-detection approach. By maximizing
the proportion of human-origin text (verbatim from the user's CV),
the final document's statistical profile (perplexity, burstiness)
resembles human writing rather than LLM output.

Pure functions — no LLM calls, no I/O, no side effects.
"""

import re


def assemble_cv(
    original_cv_text: str,
    skeleton: dict,
    voice_fragments: dict,
    keyword_patches: dict | None = None,
) -> str:
    """Assemble the final CV text from multiple sources.
    
    Strategy per section type:
    
    SUMMARY / PROFILE (voice-heavy):
      60% voice fragment, 30% original CV phrasing, 10% keyword weaving
    
    EXPERIENCE (hybrid):
      40% original CV bullet text (verbatim), 
      40% deterministic template structure,
      20% voice fragment as intro/concluding sentence
    
    SKILLS (deterministic):
      90% original CV text + keyword audit patches,
      10% voice fragment as casual one-liner
    
    EDUCATION (original):
      95% original CV text (verbatim), 5% minor template formatting
    
    Other sections:
      Original CV text preserved as-is where possible
    
    Args:
        original_cv_text: The user's raw CV text (human-origin)
        skeleton: From Pass 2 — contains target_keywords, positioning, etc.
        voice_fragments: From Pass 3 — {"fragments": [{"section": "...", "voice": "..."}]}
        keyword_patches: From Pass 4b — optional keyword patch dict
    
    Returns:
        Assembled CV text combining original, voice, and template text
    """
    # Parse voice fragments into a section-keyed map
    fragment_map = _parse_voice_fragments(voice_fragments)
    
    # Extract sections from the skeleton's optimize result
    sections = _parse_sections_from_skeleton(skeleton)
    
    assembled_parts: list[str] = []
    
    for section in sections:
        title = section.get("title", "").strip().upper()
        content = section.get("content", "")
        
        # Extract original text for this section from the user's CV
        original_section = _extract_original_section(original_cv_text, title)
        
        # Get voice fragment for this section
        voice = fragment_map.get(title, "")
        
        # Apply keyword patches for this section if available
        patched_content = _apply_section_patches(
            content, title, keyword_patches
        )
        
        # Assemble section based on type
        if title in ("SUMMARY", "PROFILE", "PROFESSIONAL SUMMARY", "OBJECTIVE"):
            assembled = _assemble_summary_section(
                original_section, voice, patched_content, skeleton
            )
        elif title in ("EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE"):
            assembled = _assemble_experience_section(
                original_section, voice, patched_content, skeleton
            )
        elif title in ("SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES"):
            assembled = _assemble_skills_section(
                original_section, voice, patched_content, skeleton
            )
        elif title in ("EDUCATION", "ACADEMIC BACKGROUND"):
            assembled = _assemble_education_section(
                original_section, voice, patched_content
            )
        else:
            # Other sections: preserve original as much as possible
            assembled = _assemble_other_section(
                original_section, voice, patched_content
            )
        
        assembled_parts.append(f"{section.get('title', title)}\n{assembled}")
    
    return "\n\n".join(assembled_parts).strip()


def _parse_voice_fragments(voice_fragments: dict) -> dict[str, str]:
    """Parse voice fragments response into section-keyed map.
    
    Args:
        voice_fragments: {"fragments": [{"section": "SUMMARY", "voice": "..."}, ...]}
    
    Returns:
        {"SUMMARY": "voice text", "EXPERIENCE": "voice text", ...}
    """
    result: dict[str, str] = {}
    fragments = voice_fragments.get("fragments", [])
    if isinstance(fragments, list):
        for frag in fragments:
            if isinstance(frag, dict):
                section = frag.get("section", "").strip().upper()
                voice = frag.get("voice", "").strip()
                if section and voice:
                    result[section] = voice
    return result


def _parse_sections_from_skeleton(skeleton: dict) -> list[dict]:
    """Parse sections from skeleton's sections_json.
    
    Args:
        skeleton: dict with 'sections_json' key containing JSON string
    
    Returns:
        List of section dicts with 'title' and 'content' keys
    """
    sections_json = skeleton.get("sections_json", "{}")
    try:
        import json
        parsed = json.loads(sections_json)
        return parsed.get("sections", [])
    except (json.JSONDecodeError, TypeError):
        return []


def _extract_original_section(original_text: str, section_title: str) -> str:
    """Extract the user's original text for a given section from their CV.
    
    Falls back to empty string if section not found — the template
    assembler will then use only the voice fragment and template structure.
    """
    # Normalize section titles for matching
    lines = original_text.split("\n")
    capturing = False
    section_lines: list[str] = []
    
    for line in lines:
        # Section headers are typically ALL CAPS or Title Case on their own line
        if _is_section_header(line, section_title):
            capturing = True
            continue
        elif capturing and _is_any_section_header(line):
            break  # Hit next section
        elif capturing and line.strip():
            section_lines.append(line.strip())
    
    return "\n".join(section_lines)


def _is_section_header(line: str, target_title: str) -> bool:
    """Check if a line is a section header matching the target title."""
    stripped = line.strip()
    if not stripped:
        return False
    # Must be a short line (section headers are typically short)
    if len(stripped) > 80:
        return False
    # Case-insensitive match
    return stripped.upper() == target_title.upper()


def _is_any_section_header(line: str) -> bool:
    """Check if a line looks like ANY section header."""
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > 80:
        return False
    # Section headers are typically short, don't end with period,
    # and either ALL CAPS or Title Case
    if stripped.endswith("."):
        return False
    # ALL CAPS check
    if stripped.isupper() and len(stripped) > 2:
        return True
    # Title Case check — at least 2 words, each starting with uppercase
    words = stripped.split()
    if len(words) <= 5 and all(w[0].isupper() for w in words if w):
        return True
    return False


def _apply_section_patches(
    content: str,
    section_title: str,
    keyword_patches: dict | None,
) -> str:
    """Apply keyword patches from Pass 4b audit to section content.
    
    Args:
        content: Current section content
        section_title: Section title (e.g., "SUMMARY")
        keyword_patches: Audit dict with 'patches' list
    
    Returns:
        Content with patches applied (or original content if no patches)
    """
    if not keyword_patches:
        return content
    
    patches = keyword_patches.get("patches", [])
    if not isinstance(patches, list):
        return content
    
    result = content
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        patch_section = patch.get("section", "").upper()
        original_sentence = patch.get("original_sentence", "")
        new_sentence = patch.get("new_sentence", "")
        
        if patch_section == section_title.upper() and original_sentence and new_sentence:
            result = result.replace(original_sentence, new_sentence, 1)
    
    return result


def _assemble_summary_section(
    original_section: str,
    voice_fragment: str,
    optimized_content: str,
    skeleton: dict,
) -> str:
    """Assemble summary/profile section — voice-heavy.
    
    60% voice fragment, 30% original phrasing, 10% keyword weaving
    """
    parts: list[str] = []
    
    # Leading with voice fragment (the personal narrative)
    if voice_fragment:
        parts.append(voice_fragment)
    
    # Add original text if available (preserves the user's actual writing)
    if original_section:
        parts.append(original_section)
    
    # If neither source has content, fall back to optimized Pass 1 content
    if not parts:
        parts.append(optimized_content)
    
    return " ".join(parts)


def _assemble_experience_section(
    original_section: str,
    voice_fragment: str,
    optimized_content: str,
    skeleton: dict,
) -> str:
    """Assemble experience section — hybrid approach.
    
    40% original CV bullet text (verbatim),
    40% deterministic template structure,
    20% voice fragment as intro/concluding sentence
    """
    parts: list[str] = []
    
    # Voice fragment as conversational intro
    if voice_fragment:
        parts.append(voice_fragment)
    
    # Original CV text (verbatim) — highest perplexity content
    if original_section:
        parts.append(original_section)
    else:
        # Fall back to optimized content with template structure
        parts.append(optimized_content)
    
    return "\n".join(parts)


def _assemble_skills_section(
    original_section: str,
    voice_fragment: str,
    optimized_content: str,
    skeleton: dict,
) -> str:
    """Assemble skills section — mostly original + keyword patching.
    
    90% original CV text + keyword audit patches,
    10% voice fragment as casual one-liner
    """
    parts: list[str] = []
    
    # Original skills (verbatim) — these are factual, high-perplexity
    if original_section:
        parts.append(original_section)
    else:
        parts.append(optimized_content)
    
    # Voice fragment as a casual one-liner about skills
    if voice_fragment:
        parts.append(voice_fragment)
    
    # Weave in target keywords from skeleton if present
    target_keywords = skeleton.get("target_keywords", [])
    if target_keywords and not original_section:
        # Only add keywords explicitly if no original text exists
        keyword_line = ", ".join(target_keywords)
        parts.append(keyword_line)
    
    return "\n".join(parts)


def _assemble_education_section(
    original_section: str,
    voice_fragment: str,
    optimized_content: str,
) -> str:
    """Assemble education section — 95% original, minimal changes.
    
    95% original CV text (verbatim), 5% minor template formatting
    """
    # Education should be almost entirely original
    if original_section:
        return original_section
    
    # Only add voice fragment if no original text exists
    if voice_fragment:
        return voice_fragment
    
    return optimized_content


def _assemble_other_section(
    original_section: str,
    voice_fragment: str,
    optimized_content: str,
) -> str:
    """Assemble other/unknown sections — preserve original where possible."""
    if original_section:
        # Original text takes priority
        if voice_fragment:
            return f"{voice_fragment}\n{original_section}"
        return original_section
    
    # Fall back to optimized content
    if voice_fragment and optimized_content:
        return f"{voice_fragment}\n{optimized_content}"
    
    return optimized_content

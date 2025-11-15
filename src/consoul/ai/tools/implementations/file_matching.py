"""File matching algorithms for progressive search/replace editing.

Provides multiple matching strategies with increasing tolerance levels:
- Exact matching: Byte-for-byte comparison
- Whitespace-tolerant: Ignores leading/trailing whitespace, preserves indentation
- Fuzzy matching: Similarity-based matching with configurable threshold

Used by edit_file_search_replace to enable robust file editing even when
whitespace or minor content differences exist.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Literal


@dataclass
class MatchResult:
    """Result of a successful match operation.

    Attributes:
        start_line: Starting line number (1-indexed, inclusive)
        end_line: Ending line number (1-indexed, inclusive)
        confidence: Match confidence score (0.0-1.0, 1.0 = exact match)
        matched_lines: Actual lines that were matched from the file
        indentation_offset: Indentation difference for whitespace-tolerant matches
                           (positive = file more indented, negative = less indented)
    """

    start_line: int
    end_line: int
    confidence: float
    matched_lines: list[str]
    indentation_offset: int = 0


@dataclass
class SimilarBlock:
    """A block of text similar to the search pattern.

    Used for "Did you mean?" suggestions when no match is found.

    Attributes:
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        similarity: Similarity score (0.0-1.0)
        context_before: Up to 3 lines before the block for context
        context_after: Up to 3 lines after the block for context
    """

    start_line: int
    end_line: int
    similarity: float
    context_before: list[str]
    context_after: list[str]


def exact_match(file_lines: list[str], search_lines: list[str]) -> list[MatchResult]:
    """Find all exact byte-for-byte matches of search_lines in file_lines.

    Args:
        file_lines: Lines from the file to search in
        search_lines: Lines to search for

    Returns:
        List of MatchResult objects for all exact matches found

    Example:
        >>> file_lines = ["line1", "line2", "line3"]
        >>> search_lines = ["line2"]
        >>> matches = exact_match(file_lines, search_lines)
        >>> matches[0].start_line
        2
    """
    if not search_lines:
        return []

    matches: list[MatchResult] = []
    search_len = len(search_lines)
    file_len = len(file_lines)

    # Sliding window search
    for i in range(file_len - search_len + 1):
        # Check if this window matches
        window = file_lines[i : i + search_len]
        if window == search_lines:
            matches.append(
                MatchResult(
                    start_line=i + 1,  # Convert to 1-indexed
                    end_line=i + search_len,  # 1-indexed, inclusive
                    confidence=1.0,
                    matched_lines=window.copy(),
                    indentation_offset=0,
                )
            )

    return matches


def _get_indentation(line: str) -> int:
    """Get the number of leading whitespace characters in a line.

    Args:
        line: The line to measure

    Returns:
        Number of leading whitespace characters (spaces and tabs)
    """
    return len(line) - len(line.lstrip())


def whitespace_tolerant_match(
    file_lines: list[str], search_lines: list[str]
) -> list[MatchResult]:
    """Find matches ignoring leading/trailing whitespace differences.

    Compares lines using .strip() but preserves indentation metadata
    for later indentation-aware replacement.

    Args:
        file_lines: Lines from the file to search in
        search_lines: Lines to search for

    Returns:
        List of MatchResult objects with indentation_offset calculated

    Example:
        >>> file_lines = ["  line1", "  line2"]
        >>> search_lines = ["line1", "line2"]
        >>> matches = whitespace_tolerant_match(file_lines, search_lines)
        >>> matches[0].indentation_offset
        2
    """
    if not search_lines:
        return []

    matches: list[MatchResult] = []
    search_len = len(search_lines)
    file_len = len(file_lines)

    # Strip search lines for comparison
    search_stripped = [line.strip() for line in search_lines]

    # Sliding window search with whitespace tolerance
    for i in range(file_len - search_len + 1):
        window = file_lines[i : i + search_len]
        window_stripped = [line.strip() for line in window]

        if window_stripped == search_stripped:
            # Calculate indentation offset (average of first non-empty line)
            offset = 0
            for file_line, search_line in zip(window, search_lines, strict=True):
                if file_line.strip():  # Non-empty line
                    file_indent = _get_indentation(file_line)
                    search_indent = _get_indentation(search_line)
                    offset = file_indent - search_indent
                    break

            matches.append(
                MatchResult(
                    start_line=i + 1,
                    end_line=i + search_len,
                    confidence=0.95,  # Slightly less than exact
                    matched_lines=window.copy(),
                    indentation_offset=offset,
                )
            )

    return matches


def fuzzy_match(
    file_lines: list[str],
    search_lines: list[str],
    threshold: float = 0.8,
) -> list[MatchResult]:
    """Find matches using similarity scoring with a threshold.

    Uses difflib.SequenceMatcher to calculate similarity ratio.
    Returns only matches above the threshold, sorted by confidence.

    Args:
        file_lines: Lines from the file to search in
        search_lines: Lines to search for
        threshold: Minimum similarity ratio (0.0-1.0, default 0.8)

    Returns:
        List of MatchResult objects sorted by confidence (highest first)

    Example:
        >>> file_lines = ["def hello():", "    print('world')"]
        >>> search_lines = ["def hello():", "    print('wrld')"]  # Typo
        >>> matches = fuzzy_match(file_lines, search_lines, threshold=0.8)
        >>> matches[0].confidence > 0.8
        True
    """
    if not search_lines:
        return []

    matches: list[MatchResult] = []
    search_len = len(search_lines)
    file_len = len(file_lines)

    # Join lines for comparison (preserves multi-line structure)
    search_text = "\n".join(search_lines)

    # Sliding window search with fuzzy matching
    for i in range(file_len - search_len + 1):
        window = file_lines[i : i + search_len]
        window_text = "\n".join(window)

        # Calculate similarity using SequenceMatcher
        matcher = difflib.SequenceMatcher(None, search_text, window_text)
        ratio = matcher.ratio()

        if ratio >= threshold:
            matches.append(
                MatchResult(
                    start_line=i + 1,
                    end_line=i + search_len,
                    confidence=ratio,
                    matched_lines=window.copy(),
                    indentation_offset=0,  # Fuzzy match doesn't auto-fix indentation
                )
            )

    # Sort by confidence (highest first)
    matches.sort(key=lambda m: m.confidence, reverse=True)

    return matches


def find_similar_blocks(
    file_lines: list[str],
    search_lines: list[str],
    top_n: int = 3,
) -> list[SimilarBlock]:
    """Find blocks of text similar to the search pattern for suggestions.

    Used to generate "Did you mean lines X-Y?" suggestions when no match found.

    Args:
        file_lines: Lines from the file to search in
        search_lines: Lines to search for
        top_n: Maximum number of suggestions to return (default 3)

    Returns:
        List of SimilarBlock objects sorted by similarity (highest first)

    Example:
        >>> file_lines = ["line1", "line2", "line3", "lineX"]
        >>> search_lines = ["line2", "line3"]
        >>> blocks = find_similar_blocks(file_lines, search_lines, top_n=1)
        >>> blocks[0].start_line
        2
    """
    if not search_lines:
        return []

    candidates: list[SimilarBlock] = []
    search_len = len(search_lines)
    file_len = len(file_lines)
    search_text = "\n".join(search_lines)

    # Try all possible windows
    for i in range(file_len - search_len + 1):
        window = file_lines[i : i + search_len]
        window_text = "\n".join(window)

        # Calculate similarity
        matcher = difflib.SequenceMatcher(None, search_text, window_text)
        similarity = matcher.ratio()

        # Extract context lines (±3)
        context_before = file_lines[max(0, i - 3) : i]
        context_after = file_lines[i + search_len : min(file_len, i + search_len + 3)]

        candidates.append(
            SimilarBlock(
                start_line=i + 1,
                end_line=i + search_len,
                similarity=similarity,
                context_before=context_before,
                context_after=context_after,
            )
        )

    # Sort by similarity and take top N
    candidates.sort(key=lambda b: b.similarity, reverse=True)
    return candidates[:top_n]


def detect_indentation_style(lines: list[str]) -> tuple[Literal["spaces", "tabs"], int]:
    """Detect the indentation style used in a file.

    Analyzes indented lines to determine if spaces or tabs are used,
    and the typical indentation width.

    Args:
        lines: Lines from the file to analyze

    Returns:
        Tuple of (style, width) where:
        - style: "spaces" or "tabs"
        - width: Typical indentation width (e.g., 2, 4, 8 for spaces, 1 for tabs)

    Example:
        >>> lines = ["def foo():", "    pass", "    return"]
        >>> style, width = detect_indentation_style(lines)
        >>> style
        'spaces'
        >>> width
        4
    """
    space_indents: list[int] = []
    tab_indents: list[int] = []

    for line in lines:
        if not line or not line[0].isspace():
            continue  # Skip non-indented lines

        # Count leading spaces and tabs
        spaces = 0
        tabs = 0
        for char in line:
            if char == " ":
                spaces += 1
            elif char == "\t":
                tabs += 1
            else:
                break

        if tabs > 0:
            tab_indents.append(tabs)
        elif spaces > 0:
            space_indents.append(spaces)

    # Determine style by majority
    if len(tab_indents) >= len(space_indents):
        # Tabs are more common
        return "tabs", 1
    else:
        # Spaces are more common, find typical width
        if not space_indents:
            return "spaces", 4  # Default to 4 if no indented lines

        # Find most common non-zero indentation width
        from collections import Counter

        counter = Counter(space_indents)
        most_common_width = counter.most_common(1)[0][0]

        return "spaces", most_common_width

"""Reasoning/thinking block extraction for AI model responses.

This module provides functions to automatically detect and extract chain-of-thought
reasoning from AI model outputs. Modern reasoning models (DeepSeek-R1, QwQ,
Phi4-Reasoning, Cogito) output their thinking process in special tags like
`<think>...</think>`, which can be extracted and displayed separately from the
final response.

Supported formats:
- XML tags: <think>, <thinking>, <reasoning>
- Markdown: **Reasoning:** ... **Answer:**
- Heuristic detection based on keywords

Example:
    >>> text = "<think>Step 1: analyze...</think>\\n\\nThe answer is 42."
    >>> reasoning, response = extract_reasoning(text)
    >>> print(reasoning)
    Step 1: analyze...
    >>> print(response)
    The answer is 42.
"""

from __future__ import annotations

import re

__all__ = [
    "extract_reasoning",
    "extract_reasoning_heuristic",
    "extract_reasoning_patterns",
    "extract_reasoning_xml",
]

# Regex patterns for different reasoning formats
# Order matters: try most specific patterns first
REASONING_PATTERNS: list[tuple[str, str]] = [
    (r"<think>(.*?)</think>", "xml-think"),
    (r"<thinking>(.*?)</thinking>", "xml-thinking"),
    (r"<reasoning>(.*?)</reasoning>", "xml-reasoning"),
    (r"\*\*Reasoning:\*\*(.*?)(?=\*\*Answer:|\Z)", "markdown-reasoning"),
    (r"\*\*Chain of Thought:\*\*(.*?)(?=\*\*Answer:|\Z)", "markdown-cot"),
    (r"Chain of thought:(.*?)(?=\n\nAnswer:|\Z)", "text-cot"),
]

# Keywords that indicate reasoning/thinking content
REASONING_INDICATORS = [
    "let me think",
    "step by step",
    "first,",
    "reasoning:",
    "chain of thought",
    "let's analyze",
    "breaking this down",
    "to solve this",
    "thinking about",
    "considering",
]

# Keywords that indicate conclusion/answer
CONCLUSION_INDICATORS = [
    "answer:",
    "conclusion:",
    "therefore:",
    "in summary:",
    "final answer:",
    "result:",
    "solution:",
]


def extract_reasoning_xml(text: str, tag: str = "think") -> tuple[str | None, str]:
    """Extract reasoning using XML-style tags with proper nesting support.

    Handles nested tags correctly by tracking depth. For example:
    `<think>outer<think>inner</think>more outer</think>` extracts the full
    outer block including the nested content.

    Args:
        text: Model output text to parse
        tag: XML tag name to look for (e.g., "think", "thinking", "reasoning")

    Returns:
        (reasoning_content, response_text) tuple where:
        - reasoning_content: Extracted thinking (None if not found)
        - response_text: Original text with thinking blocks removed

    Example:
        >>> text = "<think>reasoning here</think>\\nAnswer"
        >>> reasoning, response = extract_reasoning_xml(text)
        >>> print(reasoning)
        reasoning here
        >>> print(response)
        Answer
    """
    open_tag = f"<{tag}>"
    close_tag = f"</{tag}>"

    thinking_blocks: list[str] = []
    depth = 0
    start: int | None = None

    i = 0
    while i < len(text):
        # Check for opening tag
        if text[i : i + len(open_tag)] == open_tag:
            if depth == 0:
                # Start of outermost block
                start = i + len(open_tag)
            depth += 1
            i += len(open_tag)
        # Check for closing tag
        elif text[i : i + len(close_tag)] == close_tag:
            depth -= 1
            if depth == 0 and start is not None:
                # End of outermost block - extract content
                thinking_blocks.append(text[start:i])
                start = None
            i += len(close_tag)
        else:
            i += 1

    if thinking_blocks:
        # Join multiple blocks with double newline
        thinking = "\n\n".join(thinking_blocks)

        # Remove thinking blocks from response
        response = text
        for block in thinking_blocks:
            response = response.replace(f"{open_tag}{block}{close_tag}", "", 1)

        return thinking, response.strip()

    return None, text


def extract_reasoning_patterns(
    text: str,
) -> tuple[str | None, str, str | None]:
    """Try multiple regex patterns to extract reasoning.

    Attempts to match various reasoning formats including XML tags,
    markdown headers, and plain text patterns.

    Args:
        text: Model output text to parse

    Returns:
        (reasoning, response, pattern_type) tuple where:
        - reasoning: Extracted thinking (None if not found)
        - response: Text with reasoning removed
        - pattern_type: Name of matched pattern (None if not found)

    Example:
        >>> text = "**Reasoning:**\\nthinking\\n\\n**Answer:**\\nanswer"
        >>> reasoning, response, pattern = extract_reasoning_patterns(text)
        >>> print(pattern)
        markdown-reasoning
    """
    for pattern, format_type in REASONING_PATTERNS:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            # Join multiple matches with double newline
            reasoning = "\n\n".join(m.strip() for m in matches)

            # Remove matched reasoning from response
            response = re.sub(
                pattern, "", text, flags=re.DOTALL | re.IGNORECASE
            ).strip()

            return reasoning, response, format_type

    return None, text, None


def extract_reasoning_heuristic(text: str) -> tuple[str | None, str]:
    """Detect reasoning based on content patterns and structure.

    Uses keyword-based heuristics to identify reasoning sections when
    no explicit tags or patterns are found. Looks for reasoning indicators
    like "let me think", "step by step", etc.

    Args:
        text: Model output text to parse

    Returns:
        (reasoning, response) tuple where:
        - reasoning: Extracted thinking (None if not detected)
        - response: Text with reasoning removed

    Example:
        >>> text = "Let me think step by step.\\n1. First...\\n\\nAnswer: 42"
        >>> reasoning, response = extract_reasoning_heuristic(text)
        >>> print(reasoning)
        Let me think step by step.
        1. First...
    """
    lines = text.split("\n")

    reasoning_lines: list[str] = []
    response_lines: list[str] = []
    in_reasoning = False

    for line in lines:
        lower = line.lower().strip()

        # Check if we're entering reasoning mode
        if not in_reasoning and any(ind in lower for ind in REASONING_INDICATORS):
            in_reasoning = True

        # Check if we're exiting reasoning mode
        if in_reasoning and any(ind in lower for ind in CONCLUSION_INDICATORS):
            in_reasoning = False
            response_lines.append(line)  # Include the conclusion line
            continue

        # Add line to appropriate section
        if in_reasoning:
            reasoning_lines.append(line)
        else:
            response_lines.append(line)

    # Only return reasoning if we found substantial content (at least 3 lines)
    # This avoids matching single-line thinking statements
    if reasoning_lines and len(reasoning_lines) >= 3:
        return "\n".join(reasoning_lines).strip(), "\n".join(response_lines).strip()

    return None, text


def extract_reasoning(
    text: str,
    model_name: str | None = None,
) -> tuple[str | None, str]:
    """Auto-detect and extract reasoning from model output.

    Main entry point for reasoning extraction. Tries multiple detection
    methods in order of specificity:
    1. XML tag extraction (think, thinking, reasoning)
    2. Pattern matching (markdown, etc.)
    3. Heuristic detection (keyword-based)

    Args:
        text: Model output text to parse
        model_name: Optional model name for future model-specific hints

    Returns:
        (reasoning, response) tuple where:
        - reasoning: Extracted thinking (None if not found)
        - response: Text with reasoning removed (or original if no reasoning found)

    Example:
        >>> text = "<think>Let me analyze this...</think>\\nThe answer is 42."
        >>> reasoning, response = extract_reasoning(text)
        >>> print(f"Thinking: {reasoning}")
        Thinking: Let me analyze this...
        >>> print(f"Response: {response}")
        Response: The answer is 42.

        >>> text = "No reasoning here, just an answer."
        >>> reasoning, response = extract_reasoning(text)
        >>> print(reasoning)
        None
        >>> print(response)
        No reasoning here, just an answer.
    """
    # Try XML extraction first for each known tag type
    for tag in ["think", "thinking", "reasoning"]:
        reasoning, response = extract_reasoning_xml(text, tag)
        if reasoning:
            return reasoning, response

    # Try pattern matching (regex)
    reasoning, response, _ = extract_reasoning_patterns(text)
    if reasoning:
        return reasoning, response

    # Fall back to heuristic detection
    reasoning, response = extract_reasoning_heuristic(text)
    if reasoning:
        return reasoning, response

    # No reasoning detected
    return None, text

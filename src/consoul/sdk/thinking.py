"""Thinking mode detection and extraction for reasoning models.

This module provides SDK-level support for detecting and extracting chain-of-thought
reasoning from AI models that output thinking content in XML tags (DeepSeek-R1,
Qwen QWQ, o1-preview, etc.).

The ThinkingDetector class enables headless SDK usage for:
- FastAPI endpoints that return structured {thinking: "...", answer: "..."} responses
- WebSocket servers that stream thinking separately from answer content
- Web UIs that display thinking in collapsible sections
- CLI tools that show thinking as dimmed text

Example:
    >>> from consoul.sdk.thinking import ThinkingDetector
    >>> detector = ThinkingDetector()
    >>>
    >>> # Detect thinking mode from first token
    >>> if detector.detect_start("<think>"):
    ...     print("Reasoning model detected")
    >>>
    >>> # Extract thinking from full response
    >>> content = detector.extract(
    ...     "<think>Let me analyze this step by step...</think>The answer is 42"
    ... )
    >>> print(f"Thinking: {content.thinking}")
    >>> print(f"Answer: {content.answer}")
"""

from __future__ import annotations

import re
from re import Pattern
from typing import ClassVar

from consoul.sdk.models import ThinkingContent


class ThinkingDetector:
    """Detects and extracts chain-of-thought reasoning from LLM responses.

    Supports multiple thinking tag formats:
    - <think>...</think> (DeepSeek-R1)
    - <thinking>...</thinking> (Qwen QWQ)
    - <reasoning>...</reasoning> (o1-preview, custom models)

    Attributes:
        THINKING_START_PATTERNS: Regex patterns for opening tags
        THINKING_END_PATTERNS: Regex patterns for closing tags

    Example:
        >>> detector = ThinkingDetector()
        >>> response = "<think>Step 1: Analyze...</think>Final answer"
        >>> content = detector.extract(response)
        >>> content.has_thinking
        True
        >>> content.thinking
        'Step 1: Analyze...'
        >>> content.answer
        'Final answer'
    """

    # Opening tag patterns (case-insensitive)
    THINKING_START_PATTERNS: ClassVar[list[Pattern[str]]] = [
        re.compile(r"<think>", re.IGNORECASE),
        re.compile(r"<thinking>", re.IGNORECASE),
        re.compile(r"<reasoning>", re.IGNORECASE),
    ]

    # Closing tag patterns (case-insensitive)
    THINKING_END_PATTERNS: ClassVar[list[Pattern[str]]] = [
        re.compile(r"</think>", re.IGNORECASE),
        re.compile(r"</thinking>", re.IGNORECASE),
        re.compile(r"</reasoning>", re.IGNORECASE),
    ]

    def detect_start(self, content: str) -> bool:
        """Check if content starts with thinking tags.

        Used during streaming to detect if the first token(s) indicate
        thinking mode, allowing the orchestrator to route tokens appropriately.

        Args:
            content: First token(s) of streaming response

        Returns:
            True if content contains opening thinking tag

        Example:
            >>> detector = ThinkingDetector()
            >>> detector.detect_start("<think>")
            True
            >>> detector.detect_start("Hello")
            False
        """
        return any(pattern.search(content) for pattern in self.THINKING_START_PATTERNS)

    def detect_end(self, buffer: str) -> bool:
        """Check if closing tag is present in accumulated buffer.

        Used during streaming to detect when thinking phase ends and
        answer phase begins.

        Args:
            buffer: Accumulated content buffer from streaming

        Returns:
            True if buffer contains closing thinking tag

        Example:
            >>> detector = ThinkingDetector()
            >>> detector.detect_end("<think>reasoning...</think>")
            True
            >>> detector.detect_end("<think>still thinking...")
            False
        """
        return any(pattern.search(buffer) for pattern in self.THINKING_END_PATTERNS)

    def extract(self, full_content: str) -> ThinkingContent:
        """Extract and separate thinking from answer.

        Parses the full response to separate thinking content (inside tags)
        from answer content (outside tags). Handles multiple thinking blocks
        and nested content.

        Args:
            full_content: Complete AI response with potential thinking tags

        Returns:
            ThinkingContent with separated thinking and answer

        Example:
            >>> detector = ThinkingDetector()
            >>> content = detector.extract(
            ...     "<think>Step 1...</think>The answer is 42"
            ... )
            >>> content.has_thinking
            True
            >>> content.thinking
            'Step 1...'
            >>> content.answer
            'The answer is 42'
        """
        # Check if response has any thinking tags
        has_thinking = self.detect_start(full_content)

        if not has_thinking:
            # No thinking mode - entire content is the answer
            return ThinkingContent(
                thinking="",
                answer=full_content,
                has_thinking=False,
            )

        # Extract thinking content (inside tags)
        thinking_parts: list[str] = []
        answer_parts: list[str] = []

        # Combined pattern to match any thinking block: <tag>content</tag>
        # Uses non-greedy match (.*?) to handle multiple blocks correctly
        combined_pattern = re.compile(
            r"<(think|thinking|reasoning)>(.*?)</\1>",
            re.IGNORECASE | re.DOTALL,
        )

        # Track position for extracting answer content
        last_end = 0

        for match in combined_pattern.finditer(full_content):
            # Extract content before this thinking block (part of answer)
            if match.start() > last_end:
                answer_parts.append(full_content[last_end : match.start()])

            # Extract thinking content (group 2 is the content inside tags)
            thinking_parts.append(match.group(2))

            # Update position
            last_end = match.end()

        # Add remaining content after last thinking block (part of answer)
        if last_end < len(full_content):
            answer_parts.append(full_content[last_end:])

        # Join parts and strip whitespace
        thinking = "\n\n".join(part.strip() for part in thinking_parts if part.strip())
        answer = "".join(answer_parts).strip()

        return ThinkingContent(
            thinking=thinking,
            answer=answer,
            has_thinking=True,
        )

    def strip_tags(self, text: str) -> str:
        """Remove thinking XML tags from text.

        Useful for preprocessing content before display or when you want
        to see the raw content without tag markers.

        Args:
            text: Text potentially containing thinking tags

        Returns:
            Text with all thinking tags removed

        Example:
            >>> detector = ThinkingDetector()
            >>> detector.strip_tags("<think>reasoning</think>answer")
            'reasoninganswer'
            >>> detector.strip_tags("No tags here")
            'No tags here'
        """
        # Remove opening tags
        for pattern in self.THINKING_START_PATTERNS:
            text = pattern.sub("", text)

        # Remove closing tags
        for pattern in self.THINKING_END_PATTERNS:
            text = pattern.sub("", text)

        return text

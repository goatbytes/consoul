"""Tests for SDK thinking mode detection and extraction.

These tests verify that ThinkingDetector correctly handles various reasoning
model output formats and edge cases.
"""

from consoul.sdk.models import ThinkingContent
from consoul.sdk.thinking import ThinkingDetector


class TestThinkingDetector:
    """Test suite for ThinkingDetector class."""

    def test_detect_start_with_think_tag(self):
        """Should detect <think> opening tag."""
        detector = ThinkingDetector()
        assert detector.detect_start("<think>") is True
        assert detector.detect_start("<think>Starting to reason...") is True

    def test_detect_start_with_thinking_tag(self):
        """Should detect <thinking> opening tag."""
        detector = ThinkingDetector()
        assert detector.detect_start("<thinking>") is True
        assert detector.detect_start("<thinking>Let me analyze...") is True

    def test_detect_start_with_reasoning_tag(self):
        """Should detect <reasoning> opening tag."""
        detector = ThinkingDetector()
        assert detector.detect_start("<reasoning>") is True
        assert detector.detect_start("<reasoning>Step 1...") is True

    def test_detect_start_case_insensitive(self):
        """Should detect tags regardless of case."""
        detector = ThinkingDetector()
        assert detector.detect_start("<THINK>") is True
        assert detector.detect_start("<Think>") is True
        assert detector.detect_start("<THINKING>") is True
        assert detector.detect_start("<Thinking>") is True

    def test_detect_start_no_tags(self):
        """Should return False when no thinking tags present."""
        detector = ThinkingDetector()
        assert detector.detect_start("Hello, world!") is False
        assert detector.detect_start("No tags here") is False
        assert detector.detect_start("") is False

    def test_detect_start_with_whitespace(self):
        """Should detect tags even with leading whitespace."""
        detector = ThinkingDetector()
        assert detector.detect_start("  <think>") is True
        assert detector.detect_start("\n<thinking>") is True
        assert detector.detect_start("\t<reasoning>") is True

    def test_detect_end_with_closing_tag(self):
        """Should detect closing tags in buffer."""
        detector = ThinkingDetector()
        assert detector.detect_end("some content</think>") is True
        assert detector.detect_end("reasoning process</thinking>") is True
        assert detector.detect_end("step by step</reasoning>") is True

    def test_detect_end_case_insensitive(self):
        """Should detect closing tags regardless of case."""
        detector = ThinkingDetector()
        assert detector.detect_end("content</THINK>") is True
        assert detector.detect_end("content</Think>") is True

    def test_detect_end_no_closing_tag(self):
        """Should return False when no closing tag present."""
        detector = ThinkingDetector()
        assert detector.detect_end("still thinking...") is False
        assert detector.detect_end("<think>only opening tag") is False
        assert detector.detect_end("") is False

    def test_extract_simple_thinking_block(self):
        """Should extract thinking and answer from simple response."""
        detector = ThinkingDetector()
        content = detector.extract(
            "<think>Let me solve this step by step.</think>The answer is 42."
        )

        assert isinstance(content, ThinkingContent)
        assert content.has_thinking is True
        assert content.thinking == "Let me solve this step by step."
        assert content.answer == "The answer is 42."

    def test_extract_no_thinking_tags(self):
        """Should handle responses without thinking tags."""
        detector = ThinkingDetector()
        content = detector.extract("This is a normal response without thinking.")

        assert content.has_thinking is False
        assert content.thinking == ""
        assert content.answer == "This is a normal response without thinking."

    def test_extract_multiple_thinking_blocks(self):
        """Should handle multiple thinking blocks in response."""
        detector = ThinkingDetector()
        response = (
            "<think>First reasoning block.</think>"
            "Intermediate answer."
            "<think>Second reasoning block.</think>"
            "Final answer."
        )
        content = detector.extract(response)

        assert content.has_thinking is True
        assert "First reasoning block." in content.thinking
        assert "Second reasoning block." in content.thinking
        assert "Intermediate answer." in content.answer
        assert "Final answer." in content.answer

    def test_extract_thinking_only_response(self):
        """Should handle response that is only thinking (no answer)."""
        detector = ThinkingDetector()
        content = detector.extract("<think>Only thinking, no answer.</think>")

        assert content.has_thinking is True
        assert content.thinking == "Only thinking, no answer."
        assert content.answer == ""

    def test_extract_nested_tags_not_supported(self):
        """Should handle nested tags (flatten them)."""
        detector = ThinkingDetector()
        # Regex doesn't support true nesting, but should still extract
        response = "<think>Outer <think>Inner</think> Outer</think>Answer"
        content = detector.extract(response)

        assert content.has_thinking is True
        # Will extract first matching block
        assert len(content.thinking) > 0

    def test_extract_multiline_thinking(self):
        """Should preserve multiline content in thinking blocks."""
        detector = ThinkingDetector()
        response = """<think>
Step 1: Analyze the problem
Step 2: Consider solutions
Step 3: Pick the best one
</think>The solution is to use pattern X."""

        content = detector.extract(response)

        assert content.has_thinking is True
        assert "Step 1" in content.thinking
        assert "Step 2" in content.thinking
        assert "Step 3" in content.thinking
        assert content.answer == "The solution is to use pattern X."

    def test_extract_different_tag_types(self):
        """Should handle <thinking> and <reasoning> tags."""
        detector = ThinkingDetector()

        # Test <thinking> tags
        content1 = detector.extract("<thinking>Analysis process</thinking>Result here")
        assert content1.has_thinking is True
        assert content1.thinking == "Analysis process"
        assert content1.answer == "Result here"

        # Test <reasoning> tags
        content2 = detector.extract("<reasoning>Logical steps</reasoning>Conclusion")
        assert content2.has_thinking is True
        assert content2.thinking == "Logical steps"
        assert content2.answer == "Conclusion"

    def test_extract_whitespace_handling(self):
        """Should strip whitespace from extracted content."""
        detector = ThinkingDetector()
        response = "  <think>  thinking  </think>  answer  "
        content = detector.extract(response)

        assert content.thinking == "thinking"
        assert content.answer == "answer"

    def test_extract_empty_thinking_block(self):
        """Should handle empty thinking blocks."""
        detector = ThinkingDetector()
        content = detector.extract("<think></think>The answer")

        assert content.has_thinking is True
        assert content.thinking == ""
        assert content.answer == "The answer"

    def test_strip_tags_removes_all_thinking_tags(self):
        """Should remove all thinking tags from text."""
        detector = ThinkingDetector()

        result = detector.strip_tags("<think>reasoning</think>answer")
        assert result == "reasoninganswer"

        result = detector.strip_tags("<thinking>process</thinking>result")
        assert result == "processresult"

        result = detector.strip_tags("<reasoning>steps</reasoning>conclusion")
        assert result == "stepsconclusion"

    def test_strip_tags_no_tags(self):
        """Should return text unchanged if no tags present."""
        detector = ThinkingDetector()
        text = "No tags here"
        assert detector.strip_tags(text) == text

    def test_strip_tags_mixed_tags(self):
        """Should remove all thinking tag types."""
        detector = ThinkingDetector()
        text = "<think>a</think><thinking>b</thinking><reasoning>c</reasoning>"
        result = detector.strip_tags(text)
        assert result == "abc"

    def test_extract_with_malformed_tag(self):
        """Should handle malformed tags gracefully."""
        detector = ThinkingDetector()

        # Missing closing tag
        content = detector.extract("<think>reasoning without closing")
        assert content.has_thinking is True
        # Should still detect start tag presence
        assert content.answer == "<think>reasoning without closing"

    def test_extract_case_sensitivity(self):
        """Should handle tags with mixed case."""
        detector = ThinkingDetector()
        content = detector.extract("<THINK>uppercase</THINK>answer")

        assert content.has_thinking is True
        assert content.thinking == "uppercase"
        assert content.answer == "answer"

    def test_extract_preserves_code_blocks(self):
        """Should preserve code blocks in thinking and answer."""
        detector = ThinkingDetector()
        response = """<think>
Let me write some code:
```python
def foo():
    return 42
```
</think>The function returns 42."""

        content = detector.extract(response)

        assert content.has_thinking is True
        assert "```python" in content.thinking
        assert "def foo():" in content.thinking
        assert content.answer == "The function returns 42."

    def test_real_world_deepseek_response(self):
        """Should handle realistic DeepSeek-R1 response format."""
        detector = ThinkingDetector()
        response = """<think>
Okay, let's tackle this problem step by step.

First, I need to understand what the user is asking for. They want to know how to implement a binary search algorithm.

Let me recall the binary search algorithm:
1. Start with a sorted array
2. Find the middle element
3. If target equals middle, return index
4. If target < middle, search left half
5. If target > middle, search right half
6. Repeat until found or array exhausted

I should provide both iterative and recursive implementations.
</think>

Here's how to implement binary search in Python:

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1
```

This iterative approach has O(log n) time complexity."""

        content = detector.extract(response)

        assert content.has_thinking is True
        assert "step by step" in content.thinking
        assert "binary search algorithm" in content.thinking
        assert "Here's how to implement" in content.answer
        assert "```python" in content.answer
        assert "O(log n)" in content.answer

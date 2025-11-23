"""Tests for reasoning/thinking block extraction."""

from __future__ import annotations

from consoul.ai.reasoning import (
    extract_reasoning,
    extract_reasoning_heuristic,
    extract_reasoning_patterns,
    extract_reasoning_xml,
)


class TestXMLExtraction:
    """Tests for XML tag extraction with nesting support."""

    def test_simple_think_tag(self) -> None:
        """Test basic <think> tag extraction."""
        text = "<think>reasoning here</think>\n\nThe answer is 42."
        reasoning, response = extract_reasoning_xml(text, "think")

        assert reasoning == "reasoning here"
        assert response == "The answer is 42."

    def test_thinking_tag(self) -> None:
        """Test <thinking> tag extraction."""
        text = "<thinking>step by step analysis</thinking>\n\nFinal result"
        reasoning, response = extract_reasoning_xml(text, "thinking")

        assert reasoning == "step by step analysis"
        assert response == "Final result"

    def test_reasoning_tag(self) -> None:
        """Test <reasoning> tag extraction."""
        text = "<reasoning>logical deduction</reasoning>\n\nConclusion"
        reasoning, response = extract_reasoning_xml(text, "reasoning")

        assert reasoning == "logical deduction"
        assert response == "Conclusion"

    def test_nested_tags(self) -> None:
        """Test nested tag handling."""
        text = """<think>
Outer thinking <think>nested thinking</think> more outer thinking
</think>

Final answer"""
        reasoning, response = extract_reasoning_xml(text, "think")

        assert "Outer thinking" in reasoning
        assert "nested thinking" in reasoning
        assert "more outer thinking" in reasoning
        assert response.strip() == "Final answer"

    def test_multiple_blocks(self) -> None:
        """Test multiple separate thinking blocks."""
        text = """<think>First consideration</think>

Some text here.

<think>Second consideration</think>

Final answer"""
        reasoning, response = extract_reasoning_xml(text, "think")

        assert "First consideration" in reasoning
        assert "Second consideration" in reasoning
        # Blocks should be joined with double newline
        assert "\n\n" in reasoning
        assert "Final answer" in response

    def test_no_tags(self) -> None:
        """Test text without any tags."""
        text = "Just a simple response without reasoning."
        reasoning, response = extract_reasoning_xml(text, "think")

        assert reasoning is None
        assert response == text

    def test_empty_tags(self) -> None:
        """Test empty reasoning tags."""
        text = "<think></think>\n\nAnswer"
        reasoning, response = extract_reasoning_xml(text, "think")

        assert reasoning == ""
        assert "Answer" in response

    def test_multiline_reasoning(self) -> None:
        """Test multiline thinking content."""
        text = """<think>
Line 1 of thinking
Line 2 of thinking
Line 3 of thinking
</think>

The final answer"""
        reasoning, response = extract_reasoning_xml(text, "think")

        assert "Line 1" in reasoning
        assert "Line 2" in reasoning
        assert "Line 3" in reasoning
        assert response.strip() == "The final answer"


class TestPatternExtraction:
    """Tests for regex pattern-based extraction."""

    def test_markdown_reasoning_pattern(self) -> None:
        """Test **Reasoning:** markdown pattern."""
        text = """**Reasoning:**
- First point
- Second point

**Answer:**
The solution is X."""
        reasoning, response, pattern = extract_reasoning_patterns(text)

        assert reasoning is not None
        assert "First point" in reasoning
        assert "Second point" in reasoning
        assert pattern == "markdown-reasoning"
        # Response should contain the answer section
        assert "Answer:" in response or "solution" in response.lower()

    def test_chain_of_thought_pattern(self) -> None:
        """Test **Chain of Thought:** pattern."""
        text = """**Chain of Thought:**
Step 1: Analysis
Step 2: Decision

**Answer:**
Result"""
        reasoning, _, pattern = extract_reasoning_patterns(text)

        assert reasoning is not None
        assert "Step 1" in reasoning
        assert pattern == "markdown-cot"

    def test_text_cot_pattern(self) -> None:
        """Test plain text 'Chain of thought:' pattern."""
        text = """Chain of thought:
Thinking here

Answer: 42"""
        reasoning, _, pattern = extract_reasoning_patterns(text)

        assert reasoning is not None
        assert "Thinking here" in reasoning
        assert pattern == "text-cot"

    def test_no_pattern_match(self) -> None:
        """Test text with no matching patterns."""
        text = "Just a plain response."
        reasoning, response, pattern = extract_reasoning_patterns(text)

        assert reasoning is None
        assert response == text
        assert pattern is None

    def test_case_insensitive_matching(self) -> None:
        """Test that patterns are case-insensitive."""
        text = """**reasoning:**
Thinking content

**answer:**
Response"""
        reasoning, _, _ = extract_reasoning_patterns(text)

        assert reasoning is not None
        assert "Thinking content" in reasoning


class TestHeuristicExtraction:
    """Tests for heuristic-based extraction."""

    def test_let_me_think_indicator(self) -> None:
        """Test 'let me think' indicator."""
        text = """Let me think about this carefully.
Step 1: First consideration
Step 2: Second consideration

Answer: The solution is clear."""
        reasoning, response = extract_reasoning_heuristic(text)

        assert reasoning is not None
        assert "Let me think" in reasoning
        assert "Step 1" in reasoning
        assert "Answer:" in response

    def test_step_by_step_indicator(self) -> None:
        """Test 'step by step' indicator."""
        text = """Let's break this down step by step:
1. First step
2. Second step

Therefore: Result is X"""
        reasoning, response = extract_reasoning_heuristic(text)

        assert reasoning is not None
        assert "step by step" in reasoning
        assert "Therefore:" in response

    def test_conclusion_transition(self) -> None:
        """Test transition to conclusion."""
        text = """Let me think about this step by step.
Line 1 of reasoning
Line 2 of reasoning

In summary: The answer is 42."""
        reasoning, response = extract_reasoning_heuristic(text)

        assert reasoning is not None
        assert "step by step" in reasoning
        assert "In summary:" in response

    def test_no_heuristic_match(self) -> None:
        """Test text with no heuristic indicators."""
        text = "Simple direct answer without reasoning markers."
        reasoning, response = extract_reasoning_heuristic(text)

        assert reasoning is None
        assert response == text

    def test_insufficient_reasoning_lines(self) -> None:
        """Test that insufficient reasoning lines are rejected."""
        text = """Let me think.

Answer: 42"""
        reasoning, _ = extract_reasoning_heuristic(text)

        # Single line of reasoning is not substantial enough (need 3+)
        assert reasoning is None


class TestMainExtractionAPI:
    """Tests for main extract_reasoning() function."""

    def test_extract_with_think_tags(self) -> None:
        """Test extraction with <think> tags."""
        text = """<think>
To solve 2+2, I need to add the numbers.
2 + 2 = 4
</think>

The answer is 4."""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "To solve 2+2" in reasoning
        assert "The answer is 4" in response

    def test_extract_with_thinking_tags(self) -> None:
        """Test extraction with <thinking> tags."""
        text = "<thinking>Analysis here</thinking>\n\nConclusion"
        reasoning, response = extract_reasoning(text)

        assert reasoning == "Analysis here"
        assert response == "Conclusion"

    def test_extract_with_reasoning_tags(self) -> None:
        """Test extraction with <reasoning> tags."""
        text = "<reasoning>Logical steps</reasoning>\n\nResult"
        reasoning, response = extract_reasoning(text)

        assert reasoning == "Logical steps"
        assert response == "Result"

    def test_extract_with_markdown(self) -> None:
        """Test extraction with markdown patterns."""
        text = """**Reasoning:**
Thinking content

**Answer:**
Response content"""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "Thinking content" in reasoning
        assert "Response content" in response

    def test_extract_with_heuristics(self) -> None:
        """Test extraction using heuristics."""
        text = """Let me analyze this step by step.
Point 1: First consideration
Point 2: Second consideration

Conclusion: Final answer"""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "step by step" in reasoning
        assert "Conclusion:" in response

    def test_extract_no_reasoning(self) -> None:
        """Test extraction when no reasoning is present."""
        text = "Simple answer without any reasoning."
        reasoning, response = extract_reasoning(text)

        assert reasoning is None
        assert response == text

    def test_extract_with_model_name(self) -> None:
        """Test extraction with model_name parameter (future hint)."""
        text = "<think>Reasoning</think>\n\nAnswer"
        reasoning, response = extract_reasoning(text, model_name="qwq:32b")

        # Should work regardless of model_name (for now)
        assert reasoning == "Reasoning"
        assert response == "Answer"

    def test_priority_xml_over_patterns(self) -> None:
        """Test that XML tags take priority over other patterns."""
        text = """<think>XML reasoning</think>

**Reasoning:**
Markdown reasoning

Answer"""
        reasoning, response = extract_reasoning(text)

        # Should extract XML, not markdown
        assert reasoning == "XML reasoning"
        assert "**Reasoning:**" in response or "Markdown reasoning" in response


class TestEdgeCases:
    """Tests for edge cases and malformed input."""

    def test_empty_string(self) -> None:
        """Test extraction from empty string."""
        reasoning, response = extract_reasoning("")

        assert reasoning is None
        assert response == ""

    def test_whitespace_only(self) -> None:
        """Test extraction from whitespace-only string."""
        text = "   \n\n   "
        reasoning, _ = extract_reasoning(text)

        assert reasoning is None

    def test_unclosed_tag(self) -> None:
        """Test malformed XML with unclosed tag."""
        text = "<think>Reasoning without closing tag\n\nAnswer"
        reasoning, response = extract_reasoning(text)

        # Should not extract malformed XML
        assert reasoning is None
        assert response == text

    def test_mismatched_tags(self) -> None:
        """Test mismatched opening and closing tags."""
        text = "<think>Content</thinking>\n\nAnswer"
        reasoning, _ = extract_reasoning(text)

        # Should not match (different tag names)
        # Falls through to other methods
        assert reasoning is None or reasoning == "Content"

    def test_special_characters_in_reasoning(self) -> None:
        """Test reasoning with special characters."""
        text = """<think>
Reasoning with special chars: @#$%^&*()
And unicode: 你好 мир
</think>

Answer"""
        reasoning, _ = extract_reasoning(text)

        assert reasoning is not None
        assert "@#$%^&*()" in reasoning
        assert "你好" in reasoning
        assert "мир" in reasoning

    def test_very_long_reasoning(self) -> None:
        """Test with very long reasoning block."""
        long_reasoning = "Line of thinking\n" * 1000
        text = f"<think>{long_reasoning}</think>\n\nAnswer"
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert len(reasoning) > 10000
        assert response == "Answer"


class TestRealWorldSamples:
    """Tests with realistic model outputs from test_reasoning_simple.py."""

    def test_deepseek_r1_sample(self) -> None:
        """Test with DeepSeek-R1 style output."""
        text = """<think>
To solve 2+2, I need to add the two numbers together.
2 + 2 = 4
This is a basic arithmetic operation.
</think>

The answer is 4."""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "To solve 2+2" in reasoning
        assert "basic arithmetic" in reasoning
        assert response.strip() == "The answer is 4."

    def test_nested_think_sample(self) -> None:
        """Test with nested <think> tags sample."""
        text = """<think>
First, let me break this down. The problem states <think> and </think> tags.
I need to be careful with nested tags.
</think>

After careful analysis, the solution is clear."""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "break this down" in reasoning
        assert "nested tags" in reasoning
        assert "solution is clear" in response

    def test_markdown_reasoning_sample(self) -> None:
        """Test with markdown reasoning format."""
        text = """**Reasoning:**
- First, we need to understand the requirements
- Then, we analyze the constraints
- Finally, we propose a solution

**Answer:**
The best approach is to use method A because it's most efficient."""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "understand the requirements" in reasoning
        assert "analyze the constraints" in reasoning
        assert "method A" in response

    def test_multiple_blocks_sample(self) -> None:
        """Test with multiple separate thinking blocks."""
        text = """<think>First consideration: what is the scope?</think>

Some intermediate text here.

<think>Second consideration: what are the constraints?</think>

The final answer is: we should proceed with caution."""
        reasoning, response = extract_reasoning(text)

        assert reasoning is not None
        assert "First consideration" in reasoning
        assert "Second consideration" in reasoning
        assert "proceed with caution" in response

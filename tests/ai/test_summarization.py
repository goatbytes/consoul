"""Tests for conversation summarization."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from consoul.ai.summarization import (
    SUMMARIZATION_PROMPT,
    ConversationSummarizer,
    SummarizationError,
)


class TestConversationSummarizer:
    """Tests for ConversationSummarizer class."""

    def test_initialization_default_params(self):
        """Test initializing with default parameters."""
        mock_llm = MagicMock()

        summarizer = ConversationSummarizer(llm=mock_llm)

        assert summarizer.llm == mock_llm
        assert summarizer.summary_model == mock_llm  # Should default to main model
        assert summarizer.threshold == 20
        assert summarizer.keep_recent == 10

    def test_initialization_custom_params(self):
        """Test initializing with custom parameters."""
        mock_llm = MagicMock()
        mock_summary_llm = MagicMock()

        summarizer = ConversationSummarizer(
            llm=mock_llm,
            threshold=30,
            keep_recent=5,
            summary_model=mock_summary_llm,
        )

        assert summarizer.llm == mock_llm
        assert summarizer.summary_model == mock_summary_llm
        assert summarizer.threshold == 30
        assert summarizer.keep_recent == 5

    def test_should_summarize_below_threshold(self):
        """Test should_summarize returns False when below threshold."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm, threshold=20)

        assert summarizer.should_summarize(15) is False
        assert summarizer.should_summarize(20) is False

    def test_should_summarize_above_threshold(self):
        """Test should_summarize returns True when above threshold."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm, threshold=20)

        assert summarizer.should_summarize(21) is True
        assert summarizer.should_summarize(100) is True

    def test_create_summary_empty_messages(self):
        """Test create_summary with empty message list returns existing summary."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm)

        result = summarizer.create_summary([], existing_summary="Existing summary")

        assert result == "Existing summary"
        mock_llm.invoke.assert_not_called()

    def test_create_summary_first_summary(self):
        """Test creating first summary (no existing summary)."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "  New summary content  "
        mock_llm.invoke.return_value = mock_response

        summarizer = ConversationSummarizer(llm=mock_llm)
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        result = summarizer.create_summary(messages)

        assert result == "New summary content"
        mock_llm.invoke.assert_called_once()

        # Verify the prompt structure
        call_args = mock_llm.invoke.call_args
        prompt_msg = call_args[0][0][0]
        assert isinstance(prompt_msg, HumanMessage)
        assert "None - this is the first summary" in prompt_msg.content
        assert "Human: Hello" in prompt_msg.content
        assert "AI: Hi there!" in prompt_msg.content

    def test_create_summary_progressive_update(self):
        """Test progressive summarization with existing summary."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Updated summary"
        mock_llm.invoke.return_value = mock_response

        summarizer = ConversationSummarizer(llm=mock_llm)
        messages = [HumanMessage(content="New message")]
        existing = "Previous summary"

        result = summarizer.create_summary(messages, existing_summary=existing)

        assert result == "Updated summary"

        # Verify existing summary is included in prompt
        call_args = mock_llm.invoke.call_args
        prompt_msg = call_args[0][0][0]
        assert "Previous summary" in prompt_msg.content

    def test_create_summary_uses_summary_model(self):
        """Test that summary_model is used instead of main llm."""
        mock_llm = MagicMock()
        mock_summary_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary"
        mock_summary_llm.invoke.return_value = mock_response

        summarizer = ConversationSummarizer(
            llm=mock_llm, summary_model=mock_summary_llm
        )
        messages = [HumanMessage(content="Test")]

        summarizer.create_summary(messages)

        # Should call summary_model, not main llm
        mock_summary_llm.invoke.assert_called_once()
        mock_llm.invoke.assert_not_called()

    def test_create_summary_error_handling(self):
        """Test error handling when summary generation fails."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")

        summarizer = ConversationSummarizer(llm=mock_llm)
        messages = [HumanMessage(content="Test")]

        with pytest.raises(SummarizationError) as exc_info:
            summarizer.create_summary(messages)

        assert "Summary generation failed" in str(exc_info.value)
        assert "API error" in str(exc_info.value)

    def test_get_summarized_context_no_summary(self):
        """Test get_summarized_context with no summary."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm, keep_recent=3)

        messages = [
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
        ]

        result = summarizer.get_summarized_context(messages, summary="")

        # Should return all messages when no summary
        assert len(result) == 3
        assert result == messages

    def test_get_summarized_context_with_summary_below_keep_recent(self):
        """Test context building when message count is below keep_recent."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm, keep_recent=10)

        messages = [
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
        ]
        summary = "Previous conversation summary"

        result = summarizer.get_summarized_context(messages, summary)

        # Should have summary + all messages
        assert len(result) == 3
        assert isinstance(result[0], SystemMessage)
        assert "Previous conversation summary" in result[0].content
        assert result[1] == messages[0]
        assert result[2] == messages[1]

    def test_get_summarized_context_with_summary_above_keep_recent(self):
        """Test context building when message count exceeds keep_recent."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm, keep_recent=2)

        messages = [
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
            AIMessage(content="Response 2"),
            HumanMessage(content="Message 3"),
        ]
        summary = "Summary of older messages"

        result = summarizer.get_summarized_context(messages, summary)

        # Should have summary + last 2 messages
        assert len(result) == 3
        assert isinstance(result[0], SystemMessage)
        assert "Summary of older messages" in result[0].content
        assert result[1].content == "Response 2"  # 4th message
        assert result[2].content == "Message 3"  # 5th message

    def test_get_summarized_context_preserves_system_message(self):
        """Test that original system message is preserved."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm, keep_recent=2)

        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
        ]
        summary = "Summary of conversation"

        result = summarizer.get_summarized_context(messages, summary)

        # Should have: system message + summary + last 2 messages
        assert len(result) == 4
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are a helpful assistant"
        assert isinstance(result[1], SystemMessage)
        assert "Summary of conversation" in result[1].content
        assert result[2].content == "Response 1"
        assert result[3].content == "Message 2"

    def test_format_messages_for_summary_basic(self):
        """Test message formatting for summarization prompt."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm)

        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User question"),
            AIMessage(content="AI response"),
        ]

        result = summarizer._format_messages_for_summary(messages)

        assert "System: System prompt" in result
        assert "Human: User question" in result
        assert "AI: AI response" in result

    def test_format_messages_for_summary_strips_whitespace(self):
        """Test that message content whitespace is stripped."""
        mock_llm = MagicMock()
        summarizer = ConversationSummarizer(llm=mock_llm)

        messages = [HumanMessage(content="  Message with spaces  ")]

        result = summarizer._format_messages_for_summary(messages)

        assert "Human: Message with spaces" in result
        assert "  Message with spaces  " not in result

    def test_summarization_prompt_template_structure(self):
        """Test that SUMMARIZATION_PROMPT has correct placeholders."""
        assert "{existing_summary}" in SUMMARIZATION_PROMPT
        assert "{new_messages}" in SUMMARIZATION_PROMPT
        assert (
            "Progressive" in SUMMARIZATION_PROMPT
            or "progressively" in SUMMARIZATION_PROMPT.lower()
        )


class TestSummarizationError:
    """Tests for SummarizationError exception."""

    def test_summarization_error_is_exception(self):
        """Test that SummarizationError is an Exception."""
        error = SummarizationError("Test error")
        assert isinstance(error, Exception)

    def test_summarization_error_message(self):
        """Test error message is preserved."""
        error = SummarizationError("Custom error message")
        assert str(error) == "Custom error message"


class TestConversationSummarizerIntegration:
    """Integration-style tests for complete summarization workflow."""

    def test_full_summarization_workflow(self):
        """Test complete workflow: check threshold, create summary, build context."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary of first 5 messages"
        mock_llm.invoke.return_value = mock_response

        summarizer = ConversationSummarizer(llm=mock_llm, threshold=5, keep_recent=3)

        # Create 8 messages
        messages = []
        for i in range(8):
            messages.append(HumanMessage(content=f"Question {i}"))
            messages.append(AIMessage(content=f"Answer {i}"))

        # Should trigger summarization
        assert summarizer.should_summarize(len(messages)) is True

        # Summarize first 10 messages (keep last 3)
        messages_to_summarize = messages[:-3]
        summary = summarizer.create_summary(messages_to_summarize)

        assert summary == "Summary of first 5 messages"

        # Build context with summary + recent messages
        context = summarizer.get_summarized_context(messages, summary)

        # Should have: summary + 3 recent messages = 4 total
        assert len(context) == 4
        assert isinstance(context[0], SystemMessage)
        assert "Summary of first 5 messages" in context[0].content
        # Last 3 messages are: Answer 6, Question 7, Answer 7
        assert context[1].content == "Answer 6"
        assert context[2].content == "Question 7"
        assert context[3].content == "Answer 7"

    def test_progressive_summarization_workflow(self):
        """Test progressive summarization over multiple rounds."""
        mock_llm = MagicMock()

        # First summary
        first_response = MagicMock()
        first_response.content = "Summary v1"

        # Second summary (progressive)
        second_response = MagicMock()
        second_response.content = "Summary v2 (updated)"

        mock_llm.invoke.side_effect = [first_response, second_response]

        summarizer = ConversationSummarizer(llm=mock_llm, threshold=5, keep_recent=2)

        # First batch of messages
        batch1 = [HumanMessage(content=f"Message {i}") for i in range(5)]
        summary1 = summarizer.create_summary(batch1)
        assert summary1 == "Summary v1"

        # Second batch (progressive update)
        batch2 = [HumanMessage(content=f"Message {i}") for i in range(5, 10)]
        summary2 = summarizer.create_summary(batch2, existing_summary=summary1)
        assert summary2 == "Summary v2 (updated)"

        # Verify second call included first summary
        second_call = mock_llm.invoke.call_args_list[1]
        prompt_content = second_call[0][0][0].content
        assert "Summary v1" in prompt_content

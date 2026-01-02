"""Comprehensive unit tests for ConversationService.

Tests the core SDK service for conversation management, streaming responses,
tool execution, and multimodal message handling without UI dependencies.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from consoul.sdk.models import Token, ToolRequest
from consoul.sdk.services.conversation import ConversationService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_model():
    """Create mock LangChain chat model."""
    model = Mock()
    model.model_name = "gpt-4o"
    return model


@pytest.fixture
def mock_conversation():
    """Create mock ConversationHistory."""
    conversation = Mock()
    conversation.messages = []
    conversation.session_id = "test-session-123"
    conversation.model_name = "gpt-4o"
    conversation.persist = False
    conversation._db = None
    conversation._conversation_created = False
    conversation._pending_metadata = {}
    conversation.add_user_message_async = AsyncMock()
    conversation._persist_message = AsyncMock()
    conversation.count_tokens = Mock(return_value=150)
    return conversation


@pytest.fixture
def mock_tool_registry():
    """Create mock ToolRegistry."""
    registry = Mock()
    registry.list_tools = Mock(return_value=[])
    return registry


@pytest.fixture
def mock_config():
    """Create mock ConsoulConfig."""
    config = Mock()
    config.current_model = "gpt-4o"
    config.current_provider = Mock(value="openai")
    config.active_profile = "default"

    # Mock profile
    profile = Mock()
    profile.system_prompt = "You are a helpful assistant."
    profile.conversation = Mock()
    profile.conversation.persist = False
    profile.conversation.db_path = None
    config.profiles = {"default": profile}
    config.get_active_profile = Mock(return_value=profile)

    # Mock model config
    model_config = Mock()
    model_config.model = "gpt-4o"
    model_config.provider = "openai"
    config.get_current_model_config = Mock(return_value=model_config)

    # Tools disabled by default
    config.tools = None

    return config


@pytest.fixture
def service(mock_model, mock_conversation):
    """Create ConversationService instance."""
    return ConversationService(mock_model, mock_conversation)


@pytest.fixture
def service_with_tools(mock_model, mock_conversation, mock_tool_registry):
    """Create ConversationService with tools."""
    return ConversationService(mock_model, mock_conversation, mock_tool_registry)


# =============================================================================
# Test: Initialization
# =============================================================================


class TestInitialization:
    """Test ConversationService initialization."""

    def test_init_basic(self, mock_model, mock_conversation):
        """Test basic initialization."""
        service = ConversationService(mock_model, mock_conversation)

        assert service.model == mock_model
        assert service.conversation == mock_conversation
        assert service.tool_registry is None
        assert service.config is None

    def test_init_with_tools(self, mock_model, mock_conversation, mock_tool_registry):
        """Test initialization with tools."""
        service = ConversationService(mock_model, mock_conversation, mock_tool_registry)

        assert service.tool_registry == mock_tool_registry

    def test_init_with_config(self, mock_model, mock_conversation, mock_config):
        """Test initialization with config."""
        service = ConversationService(mock_model, mock_conversation, config=mock_config)

        assert service.config == mock_config


# =============================================================================
# Test: from_config() Factory Method
# =============================================================================


class TestFromConfig:
    """Test ConversationService.from_config() factory method."""

    @patch("consoul.config.load_config")
    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_default(
        self, mock_history_class, mock_get_chat_model, mock_load_config, mock_config
    ):
        """Test from_config() with default parameters."""
        mock_load_config.return_value = mock_config
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        service = ConversationService.from_config()

        assert service.model == mock_model
        assert service.conversation == mock_history
        assert service.tool_registry is None
        mock_load_config.assert_called_once()

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_with_config(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() with provided config."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        service = ConversationService.from_config(config=mock_config)

        assert service.config == mock_config
        mock_get_chat_model.assert_called_once()

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    @patch("consoul.ai.prompt_builder.build_enhanced_system_prompt")
    def test_from_config_custom_system_prompt(
        self,
        mock_build_prompt,
        mock_history_class,
        mock_get_chat_model,
        mock_config,
    ):
        """Test from_config() with custom system prompt."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history.add_system_message = Mock()
        mock_history_class.return_value = mock_history
        mock_build_prompt.return_value = "Enhanced prompt"

        ConversationService.from_config(
            config=mock_config,
            custom_system_prompt="My custom prompt",
        )

        mock_build_prompt.assert_called_once()
        assert mock_build_prompt.call_args[1]["base_prompt"] == "My custom prompt"

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_tool_docs_disabled(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() with tool docs disabled."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        with patch(
            "consoul.ai.prompt_builder.build_enhanced_system_prompt"
        ) as mock_build:
            mock_build.return_value = "Prompt"

            ConversationService.from_config(
                config=mock_config,
                include_tool_docs=False,
            )

            # Should pass None as tool_registry when include_tool_docs=False
            mock_build.assert_called_once()
            assert mock_build.call_args[1]["tool_registry"] is None

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_context_injection_control(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() with context injection parameters."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        with patch(
            "consoul.ai.prompt_builder.build_enhanced_system_prompt"
        ) as mock_build:
            mock_build.return_value = "Prompt"

            ConversationService.from_config(
                config=mock_config,
                include_env_context=False,
                include_git_context=False,
                auto_append_tools=False,
            )

            mock_build.assert_called_once()
            assert mock_build.call_args[1]["include_env_context"] is False
            assert mock_build.call_args[1]["include_git_context"] is False
            assert mock_build.call_args[1]["auto_append_tools"] is False


# =============================================================================
# Test: send_message() Basic Flow
# =============================================================================


class TestSendMessageBasic:
    """Test ConversationService.send_message() basic functionality."""

    @pytest.mark.asyncio
    async def test_send_message_simple_text(self, service, mock_conversation):
        """Test sending simple text message."""

        # Mock streaming response
        async def mock_astream(messages):
            for chunk_content in ["Hello", " ", "world"]:
                chunk = Mock()
                chunk.content = chunk_content
                chunk.response_metadata = {}
                yield chunk

        service.model.astream = mock_astream

        tokens = []
        async for token in service.send_message("Hi there"):
            tokens.append(token)

        assert len(tokens) == 3
        assert all(isinstance(t, Token) for t in tokens)
        assert "".join(t.content for t in tokens) == "Hello world"
        mock_conversation.add_user_message_async.assert_called_once_with("Hi there")

    @pytest.mark.asyncio
    async def test_send_message_persistence(self, service, mock_conversation):
        """Test message is persisted to conversation history."""

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "Response"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        async for _ in service.send_message("Test"):
            pass

        mock_conversation.add_user_message_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_text_attachment(self, service, tmp_path):
        """Test sending message with text file attachment."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        from consoul.sdk.models import Attachment

        attachments = [Attachment(path=str(test_file), type="code")]

        tokens = []
        async for token in service.send_message(
            "Analyze this", attachments=attachments
        ):
            tokens.append(token)

        # Should have prepended file content
        call_args = service.conversation.add_user_message_async.call_args[0][0]
        assert "test.txt" in call_args
        assert "Test content" in call_args

    @pytest.mark.asyncio
    async def test_send_message_large_file_skipped(self, service, tmp_path):
        """Test large files are skipped."""
        # Create large file (> 10KB)
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 15000)

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        from consoul.sdk.models import Attachment

        attachments = [Attachment(path=str(large_file), type="code")]

        async for _ in service.send_message("Test", attachments=attachments):
            pass

        # Should not include large file content
        call_args = service.conversation.add_user_message_async.call_args[0][0]
        assert "x" * 15000 not in call_args


# =============================================================================
# Test: Multimodal Message Preparation
# =============================================================================


class TestMultimodalMessages:
    """Test multimodal message handling."""

    def test_model_supports_vision_claude(self, service):
        """Test vision detection for Claude models."""
        service.config = Mock()
        service.config.current_model = "claude-3-5-sonnet-20241022"

        assert service._model_supports_vision() is True

    def test_model_supports_vision_gpt4(self, service):
        """Test vision detection for GPT-4 models."""
        service.config = Mock()
        service.config.current_model = "gpt-4o"

        assert service._model_supports_vision() is True

    def test_model_supports_vision_gpt35_no(self, service):
        """Test GPT-3.5 doesn't support vision."""
        service.config = Mock()
        service.config.current_model = "gpt-3.5-turbo"

        assert service._model_supports_vision() is False

    def test_model_supports_vision_gemini(self, service):
        """Test vision detection for Gemini models."""
        service.config = Mock()
        service.config.current_model = "gemini-1.5-pro"

        assert service._model_supports_vision() is True

    def test_model_supports_vision_ollama_llava(self, service):
        """Test vision detection for Ollama LLaVA."""
        service.config = Mock()
        service.config.current_model = "llava:latest"

        assert service._model_supports_vision() is True

    def test_prepare_user_message_text_only(self, service):
        """Test preparing simple text message."""
        result = service._prepare_user_message("Hello")

        assert result == "Hello"
        assert isinstance(result, str)

    def test_prepare_user_message_no_attachments(self, service):
        """Test message with empty attachments."""
        result = service._prepare_user_message("Hello", attachments=[])

        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_send_message_image_no_vision_support(self, service, tmp_path):
        """Test image attachment with non-vision model."""
        service.config = Mock()
        service.config.current_model = "gpt-3.5-turbo"  # No vision
        # Need to set max_tokens for trimming logic
        model_config = service.config.get_current_model_config()
        model_config.max_tokens = 4096
        service.conversation.max_tokens = 8000
        # Mock get_trimmed_messages to return empty list
        service.conversation.get_trimmed_messages = Mock(return_value=[])

        # Create dummy image file
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"fake image data")

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        from consoul.sdk.models import Attachment

        attachments = [Attachment(path=str(image_file), type="image")]

        async for _ in service.send_message("What's this?", attachments=attachments):
            pass

        # Should send as simple text (model doesn't support vision)
        call_args = service.conversation.add_user_message_async.call_args[0][0]
        assert isinstance(call_args, str)


# =============================================================================
# Test: Streaming Response Logic
# =============================================================================


class TestStreamingResponse:
    """Test streaming response handling."""

    @pytest.mark.asyncio
    async def test_streaming_yields_tokens(self, service):
        """Test streaming yields Token objects."""

        async def mock_astream(messages):
            for content in ["Hello", " ", "world", "!"]:
                chunk = Mock()
                chunk.content = content
                chunk.response_metadata = {}
                yield chunk

        service.model.astream = mock_astream

        tokens = []
        async for token in service.send_message("Hi"):
            tokens.append(token)

        assert len(tokens) == 4
        assert all(isinstance(t, Token) for t in tokens)
        assert [t.content for t in tokens] == ["Hello", " ", "world", "!"]

    @pytest.mark.asyncio
    async def test_streaming_accumulates_response(self, service):
        """Test full response is accumulated."""

        async def mock_astream(messages):
            for content in ["Part", " ", "1", " ", "Part", " ", "2"]:
                chunk = Mock()
                chunk.content = content
                chunk.response_metadata = {}
                yield chunk

        service.model.astream = mock_astream

        tokens = []
        async for token in service.send_message("Test"):
            tokens.append(token)

        full_response = "".join(t.content for t in tokens)
        assert full_response == "Part 1 Part 2"

    @pytest.mark.asyncio
    async def test_streaming_empty_chunks_handled(self, service):
        """Test empty chunks are handled gracefully."""

        async def mock_astream(messages):
            chunk1 = Mock()
            chunk1.content = ""
            chunk1.response_metadata = {}
            yield chunk1

            chunk2 = Mock()
            chunk2.content = "Hello"
            chunk2.response_metadata = {}
            yield chunk2

        service.model.astream = mock_astream

        tokens = []
        async for token in service.send_message("Hi"):
            if token.content:  # Filter empty
                tokens.append(token)

        assert len(tokens) == 1
        assert tokens[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_streaming_with_cost_tracking(self, service):
        """Test cost is tracked during streaming."""

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "Response"
            chunk.response_metadata = {
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }
            yield chunk

        service.model.astream = mock_astream

        tokens = []
        async for token in service.send_message("Test"):
            tokens.append(token)

        # Cost tracking depends on implementation
        # Just verify tokens have cost attribute
        assert hasattr(tokens[0], "cost")


# =============================================================================
# Test: Tool Execution Flow
# =============================================================================


class TestToolExecution:
    """Test tool call detection and execution."""

    @pytest.mark.asyncio
    async def test_tool_call_detection(self, service_with_tools):
        """Test tool calls are detected in response."""
        # Mock tool in registry
        mock_tool = Mock()
        mock_tool.name = "bash_execute"
        mock_tool_meta = Mock()
        mock_tool_meta.tool = mock_tool
        mock_tool_meta.risk_level = Mock(value="safe")
        service_with_tools.tool_registry.list_tools = Mock(
            return_value=[mock_tool_meta]
        )

        async def mock_astream(messages):
            # First chunk with tool call
            chunk = Mock()
            chunk.content = ""
            chunk.tool_calls = [
                {
                    "name": "bash_execute",
                    "args": {"command": "ls"},
                    "id": "call_123",
                }
            ]
            chunk.response_metadata = {}
            yield chunk

        service_with_tools.model.astream = mock_astream

        tool_requests = []

        async def mock_approval(request: ToolRequest) -> bool:
            tool_requests.append(request)
            return False  # Reject

        tokens = []
        async for token in service_with_tools.send_message(
            "List files", on_tool_request=mock_approval
        ):
            tokens.append(token)

        # Should have invoked callback
        assert len(tool_requests) == 1
        assert tool_requests[0].name == "bash_execute"

    @pytest.mark.asyncio
    async def test_tool_call_approved(self, service_with_tools):
        """Test approved tool execution."""
        # Mock tool in registry
        mock_tool = Mock()
        mock_tool.name = "bash_execute"
        mock_tool.invoke = Mock(return_value="file1.txt\nfile2.txt")
        mock_tool_meta = Mock()
        mock_tool_meta.tool = mock_tool
        mock_tool_meta.risk_level = Mock(value="safe")
        service_with_tools.tool_registry.list_tools = Mock(
            return_value=[mock_tool_meta]
        )

        call_count = 0

        async def mock_astream(messages):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call: return tool call
                chunk = Mock()
                chunk.content = ""
                chunk.tool_calls = [
                    {
                        "name": "bash_execute",
                        "args": {"command": "ls"},
                        "id": "call_123",
                    }
                ]
                chunk.response_metadata = {}
                yield chunk
            else:
                # Second call (after tool execution): return final text response
                chunk = Mock()
                chunk.content = "Here are the files: file1.txt file2.txt"
                chunk.tool_calls = []
                chunk.response_metadata = {}
                yield chunk

        service_with_tools.model.astream = mock_astream

        async def auto_approve(request: ToolRequest) -> bool:
            return True  # Approve all

        tokens = []
        async for token in service_with_tools.send_message(
            "List files", on_tool_request=auto_approve
        ):
            tokens.append(token)

        # Should have executed tool
        mock_tool.invoke.assert_called_once_with({"command": "ls"})

    @pytest.mark.asyncio
    async def test_tool_call_rejected(self, service_with_tools):
        """Test rejected tool execution."""

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = ""
            chunk.tool_calls = [
                {
                    "name": "dangerous_tool",
                    "args": {"param": "value"},
                    "id": "call_456",
                }
            ]
            chunk.response_metadata = {}
            yield chunk

        service_with_tools.model.astream = mock_astream

        async def reject_all(request: ToolRequest) -> bool:
            return False  # Reject

        tokens = []
        async for token in service_with_tools.send_message(
            "Run tool", on_tool_request=reject_all
        ):
            tokens.append(token)

        # Tool should not be in registry.execute_tool calls
        if hasattr(service_with_tools.tool_registry, "execute_tool"):
            assert not service_with_tools.tool_registry.execute_tool.called


# =============================================================================
# Test: Helper Methods
# =============================================================================


class TestHelperMethods:
    """Test utility methods."""

    def test_get_stats_basic(self, service, mock_conversation):
        """Test get_stats() returns correct statistics."""
        mock_conversation.messages = [
            Mock(type="human"),
            Mock(type="ai"),
            Mock(type="human"),
        ]
        mock_conversation.count_tokens = Mock(return_value=250)

        stats = service.get_stats()

        assert stats.message_count == 3
        assert stats.total_tokens == 250

    def test_get_stats_empty_conversation(self, service, mock_conversation):
        """Test get_stats() with empty conversation."""
        mock_conversation.messages = []
        mock_conversation.count_tokens = Mock(return_value=0)

        stats = service.get_stats()

        assert stats.message_count == 0
        assert stats.total_tokens == 0

    def test_get_history(self, service, mock_conversation):
        """Test get_history() returns messages."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there"),
        ]
        mock_conversation.messages = messages

        history = service.get_history()

        assert history == messages
        assert len(history) == 2

    def test_get_history_empty(self, service, mock_conversation):
        """Test get_history() with no messages."""
        mock_conversation.messages = []

        history = service.get_history()

        assert history == []

    def test_clear(self, service, mock_conversation):
        """Test clear() clears conversation."""
        mock_conversation.messages = [Mock(), Mock(), Mock()]
        mock_conversation.clear = Mock()

        service.clear()

        mock_conversation.clear.assert_called_once()


# =============================================================================
# Test: Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_send_message_streaming_error(self, service):
        """Test error during streaming is handled."""

        async def mock_astream_error(messages):
            chunk = Mock()
            chunk.content = "Start"
            chunk.response_metadata = {}
            yield chunk
            raise RuntimeError("Network error")

        service.model.astream = mock_astream_error

        with pytest.raises(RuntimeError, match="Network error"):
            async for _ in service.send_message("Test"):
                pass

    @pytest.mark.asyncio
    async def test_send_message_invalid_attachment(self, service):
        """Test invalid attachment path is handled."""
        from consoul.sdk.models import Attachment

        attachments = [Attachment(path="/nonexistent/file.txt", type="code")]

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        # Should handle gracefully (skip invalid file)
        async for _ in service.send_message("Test", attachments=attachments):
            pass

        # Message should still be sent
        service.conversation.add_user_message_async.assert_called_once()

    def test_model_supports_vision_no_config(self, service):
        """Test vision detection with no config."""
        service.config = None

        assert service._model_supports_vision() is False

    def test_model_supports_vision_no_model_name(self, service):
        """Test vision detection with no model name."""
        service.config = Mock()
        service.config.current_model = None

        assert service._model_supports_vision() is False

    @pytest.mark.asyncio
    async def test_tool_callback_exception_handled(self, service_with_tools):
        """Test exception in tool callback is handled."""
        # Mock tool in registry
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool_meta = Mock()
        mock_tool_meta.tool = mock_tool
        mock_tool_meta.risk_level = Mock(value="safe")
        service_with_tools.tool_registry.list_tools = Mock(
            return_value=[mock_tool_meta]
        )

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = ""
            chunk.tool_calls = [{"name": "test_tool", "args": {}, "id": "call_789"}]
            chunk.response_metadata = {}
            yield chunk

        service_with_tools.model.astream = mock_astream

        async def failing_callback(request: ToolRequest) -> bool:
            raise ValueError("Callback error")

        # Should handle exception gracefully (not propagate it)
        async for _ in service_with_tools.send_message(
            "Test", on_tool_request=failing_callback
        ):
            pass

        # Verify the tool was NOT executed (callback failed)
        # The exception was caught and a ToolMessage with error was created instead
        assert len(service_with_tools.conversation.messages) > 0

    @pytest.mark.asyncio
    async def test_send_message_multimodal_persistence(self, service, tmp_path):
        """Test multimodal message persistence to database."""
        service.config = Mock()
        service.config.current_model = "gpt-4o"  # Vision model
        # Need to set max_tokens for trimming logic
        model_config = service.config.get_current_model_config()
        model_config.max_tokens = 4096
        model_config.provider.value = "openai"  # Set provider for vision support
        service.conversation.max_tokens = 128000
        # Mock get_trimmed_messages to return empty list
        service.conversation.get_trimmed_messages = Mock(return_value=[])
        service.conversation.persist = True
        service.conversation._db = Mock()
        service.conversation._conversation_created = False

        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"fake image")

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "I see an image"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        from consoul.sdk.models import Attachment

        attachments = [Attachment(path=str(image_file), type="image")]

        async for _ in service.send_message("What's this?", attachments=attachments):
            pass

        # Should have persisted multimodal message
        service.conversation._persist_message.assert_called()


# =============================================================================
# Test: Integration-Style Flows
# =============================================================================


class TestIntegrationFlows:
    """Test realistic end-to-end conversation flows."""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, service):
        """Test multiple message exchanges."""
        responses = [
            ["Hello", "!"],
            ["How", " ", "are", " ", "you", "?"],
            ["I'm", " ", "fine", "."],
        ]
        response_idx = [0]

        async def mock_astream(messages):
            for content in responses[response_idx[0]]:
                chunk = Mock()
                chunk.content = content
                chunk.response_metadata = {}
                yield chunk
            response_idx[0] += 1

        service.model.astream = mock_astream

        # Turn 1
        tokens1 = []
        async for token in service.send_message("Hi"):
            tokens1.append(token)
        assert "".join(t.content for t in tokens1) == "Hello!"

        # Turn 2
        tokens2 = []
        async for token in service.send_message("How are you?"):
            tokens2.append(token)
        assert "".join(t.content for t in tokens2) == "How are you?"

        # Turn 3
        tokens3 = []
        async for token in service.send_message("Good"):
            tokens3.append(token)
        assert "".join(t.content for t in tokens3) == "I'm fine."

    @pytest.mark.asyncio
    async def test_conversation_with_stats_tracking(self, service, mock_conversation):
        """Test statistics tracking across conversation."""
        mock_conversation.messages = []

        async def mock_astream(messages):
            # Add message to conversation
            mock_conversation.messages.append(AIMessage(content="Response"))
            chunk = Mock()
            chunk.content = "Response"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        # Send messages
        async for _ in service.send_message("Message 1"):
            pass
        async for _ in service.send_message("Message 2"):
            pass

        # Check stats
        stats = service.get_stats()
        assert stats.message_count >= 2  # At least 2 messages

    @pytest.mark.asyncio
    async def test_conversation_clear_and_restart(self, service, mock_conversation):
        """Test clearing conversation and starting fresh."""
        mock_conversation.messages = [Mock(), Mock(), Mock()]
        mock_conversation.clear = Mock()

        # Clear conversation
        service.clear()

        mock_conversation.clear.assert_called_once()
        mock_conversation.messages = []

        # Start fresh
        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "New conversation"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        tokens = []
        async for token in service.send_message("Start over"):
            tokens.append(token)

        assert len(tokens) > 0

    @pytest.mark.asyncio
    async def test_tool_execution_workflow(self, service_with_tools):
        """Test complete tool execution workflow."""
        # Setup tool
        mock_tool = Mock()
        mock_tool.name = "bash_execute"
        mock_tool.invoke = Mock(return_value="Command output")
        mock_tool_meta = Mock()
        mock_tool_meta.tool = mock_tool
        mock_tool_meta.risk_level = Mock(value="caution")
        service_with_tools.tool_registry.list_tools = Mock(
            return_value=[mock_tool_meta]
        )

        call_count = [0]

        async def mock_astream(messages):
            if call_count[0] == 0:
                # First call: tool request
                chunk = Mock()
                chunk.content = ""
                chunk.tool_calls = [
                    {
                        "name": "bash_execute",
                        "args": {"command": "pwd"},
                        "id": "call_abc",
                    }
                ]
                chunk.response_metadata = {}
                yield chunk
            else:
                # Second call: final response
                chunk = Mock()
                chunk.content = "The current directory is shown above."
                chunk.tool_calls = []
                chunk.response_metadata = {}
                yield chunk
            call_count[0] += 1

        service_with_tools.model.astream = mock_astream

        approved_tools = []

        async def selective_approval(request: ToolRequest) -> bool:
            approved_tools.append(request.name)
            return request.risk_level != "dangerous"

        tokens = []
        async for token in service_with_tools.send_message(
            "What directory am I in?", on_tool_request=selective_approval
        ):
            tokens.append(token)

        # Should have requested approval
        assert "bash_execute" in approved_tools
        # Should have executed tool
        mock_tool.invoke.assert_called_once_with({"command": "pwd"})

    @pytest.mark.asyncio
    async def test_cost_accumulation_across_turns(self, service):
        """Test cost accumulation across multiple turns."""
        total_tokens = [0]

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "Response"
            chunk.response_metadata = {
                "usage": {"prompt_tokens": 50, "completion_tokens": 25}
            }
            total_tokens[0] += 75
            yield chunk

        service.model.astream = mock_astream

        # Turn 1
        async for _ in service.send_message("Message 1"):
            pass

        # Turn 2
        async for _ in service.send_message("Message 2"):
            pass

        # Total tokens should accumulate
        assert total_tokens[0] == 150


# =============================================================================
# Test: Factory Method Edge Cases
# =============================================================================


class TestFactoryMethodEdgeCases:
    """Test ConversationService.from_config() edge cases and variations."""

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_with_tools_enabled(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() with tools enabled."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        # Enable tools
        mock_config.tools = Mock()
        mock_config.tools.enabled = True
        mock_config.tools.allowed_tools = None
        mock_config.tools.risk_filter = None
        mock_config.tools.bash = None
        mock_config.tools.read = None
        mock_config.tools.grep_search = None
        mock_config.tools.code_search = None
        mock_config.tools.find_references = None
        mock_config.tools.web_search = None
        mock_config.tools.wikipedia = None
        mock_config.tools.read_url = None
        mock_config.tools.file_edit = None
        mock_config.tools.image_analysis = None

        with patch("consoul.ai.tools.ToolRegistry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry_class.return_value = mock_registry
            mock_registry.list_tools = Mock(return_value=[])

            with patch("consoul.ai.tools.catalog.TOOL_CATALOG", {}):
                service = ConversationService.from_config(config=mock_config)

            assert service.tool_registry is not None

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_with_tools_disabled(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() with tools disabled."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        # Disable tools
        mock_config.tools = None

        service = ConversationService.from_config(config=mock_config)

        assert service.tool_registry is None

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_without_system_prompt(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() without system prompt."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history.add_system_message = Mock()
        mock_history_class.return_value = mock_history

        # No system prompt
        active_profile = mock_config.get_active_profile()
        active_profile.system_prompt = None

        ConversationService.from_config(config=mock_config)

        # Should not add system message if base_prompt is None
        mock_history.add_system_message.assert_not_called()

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    @patch("consoul.ai.prompt_builder.build_enhanced_system_prompt")
    def test_from_config_with_env_context(
        self,
        mock_build_prompt,
        mock_history_class,
        mock_get_chat_model,
        mock_config,
    ):
        """Test from_config() includes environment context."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history
        mock_build_prompt.return_value = "Enhanced prompt"

        ConversationService.from_config(
            config=mock_config,
            include_env_context=True,
        )

        mock_build_prompt.assert_called_once()
        assert mock_build_prompt.call_args[1]["include_env_context"] is True

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    @patch("consoul.ai.prompt_builder.build_enhanced_system_prompt")
    def test_from_config_with_git_context(
        self,
        mock_build_prompt,
        mock_history_class,
        mock_get_chat_model,
        mock_config,
    ):
        """Test from_config() includes git context."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history
        mock_build_prompt.return_value = "Enhanced prompt"

        ConversationService.from_config(
            config=mock_config,
            include_git_context=True,
        )

        mock_build_prompt.assert_called_once()
        assert mock_build_prompt.call_args[1]["include_git_context"] is True

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    @patch("consoul.ai.prompt_builder.build_enhanced_system_prompt")
    def test_from_config_auto_append_tools(
        self,
        mock_build_prompt,
        mock_history_class,
        mock_get_chat_model,
        mock_config,
    ):
        """Test from_config() auto appends tools."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history
        mock_build_prompt.return_value = "Enhanced prompt"

        ConversationService.from_config(
            config=mock_config,
            auto_append_tools=True,
        )

        mock_build_prompt.assert_called_once()
        assert mock_build_prompt.call_args[1]["auto_append_tools"] is True

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_with_persistence_config(
        self, mock_history_class, mock_get_chat_model, mock_config
    ):
        """Test from_config() with persistence configuration."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history_class.return_value = mock_history

        # Configure persistence
        active_profile = mock_config.get_active_profile()
        active_profile.conversation.persist = True
        active_profile.conversation.db_path = "/tmp/test.db"

        ConversationService.from_config(config=mock_config)

        # Verify persistence settings were passed to ConversationHistory
        mock_history_class.assert_called_once()
        call_kwargs = mock_history_class.call_args[1]
        assert call_kwargs["persist"] is True
        assert call_kwargs["db_path"] == "/tmp/test.db"


# =============================================================================
# Test: Context Window Trimming
# =============================================================================


class TestContextWindowTrimming:
    """Test context window trimming and token management."""

    @pytest.mark.asyncio
    async def test_get_trimmed_messages_without_config(
        self, service, mock_conversation
    ):
        """Test _get_trimmed_messages() without config returns all messages."""
        service.config = None
        messages = [Mock(), Mock(), Mock()]
        mock_conversation.messages = messages

        result = await service._get_trimmed_messages()

        assert result == messages

    @pytest.mark.asyncio
    async def test_get_trimmed_messages_with_multimodal(
        self, service, mock_conversation, mock_config
    ):
        """Test _get_trimmed_messages() with multimodal content."""
        service.config = mock_config

        # Create messages with multimodal content
        multimodal_msg = Mock()
        multimodal_msg.content = [
            {"type": "text", "text": "Hello"},
            {"type": "image", "data": "base64data"},
        ]

        messages = [Mock(), multimodal_msg]
        for msg in messages[:-1]:  # All except multimodal
            msg.content = "Normal message"

        mock_conversation.messages = messages
        mock_conversation.max_tokens = 8000

        # Setup model config
        model_config = mock_config.get_current_model_config()
        model_config.max_tokens = 2048

        result = await service._get_trimmed_messages()

        # Should return last 10 messages for multimodal (we have 2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_trimmed_messages_normal_trimming(
        self, service, mock_conversation, mock_config
    ):
        """Test _get_trimmed_messages() performs normal trimming."""
        service.config = mock_config

        # Create many messages
        messages = [Mock() for _ in range(30)]
        for msg in messages:
            msg.content = "Test message"

        mock_conversation.messages = messages
        mock_conversation.max_tokens = 8000
        mock_conversation.get_trimmed_messages = Mock(return_value=messages[-15:])

        # Setup model config
        model_config = mock_config.get_current_model_config()
        model_config.max_tokens = 2048

        await service._get_trimmed_messages()

        # Should have called trimming
        mock_conversation.get_trimmed_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trimmed_messages_timeout_fallback(
        self, service, mock_conversation, mock_config
    ):
        """Test _get_trimmed_messages() timeout fallback."""
        service.config = mock_config

        messages = [Mock() for _ in range(25)]
        for msg in messages:
            msg.content = "Test"

        mock_conversation.messages = messages
        mock_conversation.max_tokens = 8000

        # Setup model config
        model_config = mock_config.get_current_model_config()
        model_config.max_tokens = 2048

        # Make get_trimmed_messages hang
        async def slow_trim(*args):
            import asyncio

            await asyncio.sleep(20)
            return messages

        # Mock run_in_executor to timeout
        with patch("asyncio.wait_for") as mock_wait:
            mock_wait.side_effect = asyncio.TimeoutError()

            result = await service._get_trimmed_messages()

            # Should fall back to last 20 messages
            assert len(result) == 20

    @pytest.mark.asyncio
    async def test_get_trimmed_messages_error_fallback(
        self, service, mock_conversation, mock_config
    ):
        """Test _get_trimmed_messages() error fallback."""
        service.config = mock_config

        messages = [Mock() for _ in range(25)]
        for msg in messages:
            msg.content = "Test"

        mock_conversation.messages = messages
        mock_conversation.max_tokens = 8000

        # Setup model config
        model_config = mock_config.get_current_model_config()
        model_config.max_tokens = 2048

        # Make get_trimmed_messages raise error
        with patch("asyncio.wait_for") as mock_wait:
            mock_wait.side_effect = RuntimeError("Token counting failed")

            result = await service._get_trimmed_messages()

            # Should fall back to last 20 messages
            assert len(result) == 20

    @pytest.mark.asyncio
    async def test_get_trimmed_messages_reserve_tokens_calculation(
        self, service, mock_conversation, mock_config
    ):
        """Test _get_trimmed_messages() calculates reserve tokens correctly."""
        service.config = mock_config

        messages = [Mock() for _ in range(10)]
        for msg in messages:
            msg.content = "Test"

        mock_conversation.messages = messages
        mock_conversation.max_tokens = 8000
        mock_conversation.get_trimmed_messages = Mock(return_value=messages)

        # Set max_tokens in model config
        model_config = mock_config.get_current_model_config()
        model_config.max_tokens = 2048

        await service._get_trimmed_messages()

        # Should have called with calculated reserve tokens
        mock_conversation.get_trimmed_messages.assert_called_once()
        reserve = mock_conversation.get_trimmed_messages.call_args[0][0]
        # Should be min(2048, 8000//2) = 2048
        assert reserve == 2048


# =============================================================================
# Test: Cost Calculation
# =============================================================================


class TestCostCalculation:
    """Test cost calculation functionality."""

    def test_calculate_cost_with_config(self, service, mock_config):
        """Test _calculate_cost() with config."""
        service.config = mock_config

        with patch("consoul.pricing.calculate_cost") as mock_calc:
            mock_calc.return_value = {"total_cost": 0.05}

            result = service._calculate_cost({"input_tokens": 100, "output_tokens": 50})

            assert result["total_cost"] == 0.05
            mock_calc.assert_called_once_with(
                model_name="gpt-4o", input_tokens=100, output_tokens=50
            )

    def test_calculate_cost_without_config(self, service):
        """Test _calculate_cost() without config."""
        service.config = None

        result = service._calculate_cost({"input_tokens": 100, "output_tokens": 50})

        assert result == {"total_cost": 0.0}

    def test_calculate_cost_missing_tokens(self, service, mock_config):
        """Test _calculate_cost() with missing token counts."""
        service.config = mock_config

        with patch("consoul.pricing.calculate_cost") as mock_calc:
            mock_calc.return_value = {"total_cost": 0.0}

            service._calculate_cost({})

            # Should default to 0 tokens
            mock_calc.assert_called_once_with(
                model_name="gpt-4o", input_tokens=0, output_tokens=0
            )

    def test_calculate_cost_none_metadata(self, service, mock_config):
        """Test _calculate_cost() with None values in metadata."""
        service.config = mock_config

        with patch("consoul.pricing.calculate_cost") as mock_calc:
            mock_calc.return_value = {"total_cost": 0.0}

            service._calculate_cost({"input_tokens": None, "output_tokens": None})

            # dict.get() returns None if value is None (not the default)
            mock_calc.assert_called_once_with(
                model_name="gpt-4o", input_tokens=None, output_tokens=None
            )


# =============================================================================
# Test: Attachment Error Handling
# =============================================================================


class TestAttachmentErrorHandling:
    """Test error handling for attachment loading and processing."""

    @pytest.mark.asyncio
    async def test_send_message_attachment_file_not_found(self, service, tmp_path):
        """Test attachment with non-existent file path."""
        from consoul.sdk.models import Attachment

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        # Non-existent file
        attachments = [Attachment(path="/nonexistent/path/file.txt", type="code")]

        async for _ in service.send_message("Test", attachments=attachments):
            pass

        # Should handle gracefully - message still sent
        service.conversation.add_user_message_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_attachment_permission_error(self, service, tmp_path):
        """Test attachment with unreadable file."""
        from consoul.sdk.models import Attachment

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        # Create file and mock read to raise permission error
        test_file = tmp_path / "restricted.txt"
        test_file.write_text("content")

        with patch("pathlib.Path.read_text") as mock_read:
            mock_read.side_effect = PermissionError("Access denied")

            attachments = [Attachment(path=str(test_file), type="code")]

            async for _ in service.send_message("Test", attachments=attachments):
                pass

            # Should handle gracefully
            service.conversation.add_user_message_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_attachment_encoding_error(self, service, tmp_path):
        """Test attachment with invalid UTF-8 encoding."""
        from consoul.sdk.models import Attachment

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        # Create binary file
        binary_file = tmp_path / "binary.dat"
        binary_file.write_bytes(b"\x80\x81\x82\x83")

        attachments = [Attachment(path=str(binary_file), type="code")]

        # Should handle encoding errors gracefully
        async for _ in service.send_message("Test", attachments=attachments):
            pass

        service.conversation.add_user_message_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_multimodal_message_invalid_mime_type(self, service, tmp_path):
        """Test _create_multimodal_message() with invalid MIME type."""
        service.config = Mock()
        service.config.current_model = "gpt-4o"

        # Create text file (not an image)
        text_file = tmp_path / "test.txt"
        text_file.write_text("Not an image")

        with pytest.raises(ValueError, match="Invalid MIME type"):
            service._create_multimodal_message("Test", [text_file])

    @pytest.mark.asyncio
    async def test_create_multimodal_message_no_config(self, service, tmp_path):
        """Test _create_multimodal_message() without config."""
        service.config = None

        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"fake image")

        with pytest.raises(ValueError, match="Config not available"):
            service._create_multimodal_message("Test", [image_file])

    @pytest.mark.asyncio
    async def test_send_message_multimodal_creation_error(self, service, tmp_path):
        """Test multimodal message creation error fallback."""
        service.config = Mock()
        service.config.current_model = "gpt-4o"
        # Need to set max_tokens for trimming logic
        model_config = service.config.get_current_model_config()
        model_config.max_tokens = 4096
        service.conversation.max_tokens = 8000
        # Mock get_trimmed_messages to return empty list
        service.conversation.get_trimmed_messages = Mock(return_value=[])

        async def mock_astream(messages):
            chunk = Mock()
            chunk.content = "OK"
            chunk.response_metadata = {}
            yield chunk

        service.model.astream = mock_astream

        from consoul.sdk.models import Attachment

        # Create image that will fail to process
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"fake")

        with patch.object(
            service, "_create_multimodal_message", side_effect=RuntimeError("Failed")
        ):
            attachments = [Attachment(path=str(image_file), type="image")]

            async for _ in service.send_message("Test", attachments=attachments):
                pass

            # Should fall back to text-only message
            service.conversation.add_user_message_async.assert_called_once()


# =============================================================================
# Test: Helper Method Edge Cases
# =============================================================================


class TestHelperMethodEdgeCases:
    """Test edge cases in helper methods."""

    def test_has_multimodal_content_empty_messages(self, service):
        """Test _has_multimodal_content() with empty message list."""
        result = service._has_multimodal_content([])

        assert result is False

    def test_has_multimodal_content_string_content(self, service):
        """Test _has_multimodal_content() with string content."""
        msg = Mock()
        msg.content = "Plain text message"

        result = service._has_multimodal_content([msg])

        assert result is False

    def test_has_multimodal_content_text_blocks_only(self, service):
        """Test _has_multimodal_content() with text blocks only."""
        msg = Mock()
        msg.content = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
        ]

        result = service._has_multimodal_content([msg])

        assert result is False

    def test_has_multimodal_content_with_image(self, service):
        """Test _has_multimodal_content() with image block."""
        msg = Mock()
        msg.content = [
            {"type": "text", "text": "Look at this"},
            {"type": "image", "data": "base64data"},
        ]

        result = service._has_multimodal_content([msg])

        assert result is True

    def test_has_multimodal_content_with_image_url(self, service):
        """Test _has_multimodal_content() with image_url block."""
        msg = Mock()
        msg.content = [
            {"type": "text", "text": "Check this"},
            {"type": "image_url", "url": "https://example.com/image.png"},
        ]

        result = service._has_multimodal_content([msg])

        assert result is True

    def test_normalize_chunk_content_with_none(self, service):
        """Test _normalize_chunk_content() with None."""
        result = service._normalize_chunk_content(None)

        assert result == ""

    def test_normalize_chunk_content_with_string(self, service):
        """Test _normalize_chunk_content() with string."""
        result = service._normalize_chunk_content("Hello world")

        assert result == "Hello world"

    def test_normalize_chunk_content_with_text_blocks(self, service):
        """Test _normalize_chunk_content() with text blocks."""
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": " world"},
        ]

        result = service._normalize_chunk_content(content)

        assert result == "Hello world"

    def test_normalize_chunk_content_with_mixed_blocks(self, service):
        """Test _normalize_chunk_content() with mixed block types."""
        content = [
            {"type": "text", "text": "Before"},
            {"type": "tool_use", "id": "123"},
            {"type": "text", "text": "After"},
        ]

        result = service._normalize_chunk_content(content)

        assert result == "BeforeAfter"

    def test_normalize_chunk_content_with_string_list(self, service):
        """Test _normalize_chunk_content() with list of strings."""
        content = ["Hello", " ", "world"]

        result = service._normalize_chunk_content(content)

        assert result == "Hello world"

    def test_normalize_chunk_content_with_other_type(self, service):
        """Test _normalize_chunk_content() with other types."""
        result = service._normalize_chunk_content(12345)

        assert result == "12345"


# =============================================================================
# Test: Session Resumption (SOUL-355)
# =============================================================================


class TestSessionResumption:
    """Tests for session resumption via session_id parameter."""

    @patch("consoul.ai.tools.audit.StructuredAuditLogger")
    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_passes_session_id_to_conversation_history(
        self, mock_history_class, mock_get_chat_model, mock_audit_logger, mock_config
    ):
        """Test from_config() passes session_id to ConversationHistory constructor."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history.messages = []
        mock_history_class.return_value = mock_history

        ConversationService.from_config(
            config=mock_config,
            session_id="test-session-123",
        )

        # Verify ConversationHistory was called with session_id
        mock_history_class.assert_called_once()
        call_kwargs = mock_history_class.call_args[1]
        assert call_kwargs["session_id"] == "test-session-123"

    @patch("consoul.ai.tools.audit.StructuredAuditLogger")
    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_from_config_without_session_id_passes_none(
        self, mock_history_class, mock_get_chat_model, mock_audit_logger, mock_config
    ):
        """Test from_config() without session_id passes None to ConversationHistory."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history.messages = []
        mock_history_class.return_value = mock_history

        ConversationService.from_config(config=mock_config)

        # Verify ConversationHistory was called with session_id=None
        mock_history_class.assert_called_once()
        call_kwargs = mock_history_class.call_args[1]
        assert call_kwargs["session_id"] is None

    @patch("consoul.ai.tools.audit.StructuredAuditLogger")
    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_resumed_session_has_loaded_messages(
        self, mock_history_class, mock_get_chat_model, mock_audit_logger, mock_config
    ):
        """Test resumed session contains pre-loaded messages from database."""
        from langchain_core.messages import AIMessage, HumanMessage

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Simulate conversation with pre-loaded messages
        mock_history = Mock()
        mock_history.messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
        ]
        mock_history_class.return_value = mock_history

        service = ConversationService.from_config(
            config=mock_config,
            session_id="existing-session",
        )

        # Verify the conversation has the pre-loaded messages
        assert len(service.conversation.messages) == 3
        assert service.conversation.messages[0].content == "Hello"
        assert service.conversation.messages[1].content == "Hi there!"
        assert service.conversation.messages[2].content == "How are you?"

    @patch("consoul.ai.tools.audit.StructuredAuditLogger")
    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_resumed_session_does_not_add_duplicate_system_prompt(
        self, mock_history_class, mock_get_chat_model, mock_audit_logger, mock_config
    ):
        """Test resumed session does NOT add a new system prompt (it's already in DB)."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history.messages = []
        mock_history_class.return_value = mock_history

        ConversationService.from_config(
            config=mock_config,
            session_id="existing-session",
        )

        # Verify add_system_message was NOT called when resuming
        mock_history.add_system_message.assert_not_called()

    @patch("consoul.ai.tools.audit.StructuredAuditLogger")
    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.ConversationHistory")
    def test_resumed_session_preserves_base_prompt_for_dynamic_context(
        self, mock_history_class, mock_get_chat_model, mock_audit_logger, mock_config
    ):
        """Test resumed session preserves base_prompt for dynamic context providers."""
        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model
        mock_history = Mock()
        mock_history.messages = []
        mock_history_class.return_value = mock_history

        service = ConversationService.from_config(
            config=mock_config,
            session_id="existing-session",
        )

        # Verify base_prompt is preserved (from profile's system_prompt)
        # This is needed for dynamic context providers to work after resumption
        assert service.base_prompt == "You are a helpful assistant."

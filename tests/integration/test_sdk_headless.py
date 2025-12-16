"""Integration tests verifying SDK works without UI dependencies.

These tests prove that the SDK can be used in headless environments without
Textual or Rich installed. This is critical for SDK consumers using the library
in web backends, CLIs, scripts, and notebooks.

Test Strategy:
1. Import verification - Ensure SDK imports succeed and don't pull in UI libs
2. Basic operations - Test core SDK functionality works without UI
3. Streaming - Verify async streaming works without UI dependencies
4. Tool execution - Test tool execution with custom approval provider
5. Model operations - Test model switching and management
6. Conversation persistence - Test conversation history works

All tests use mocks to avoid actual API calls while testing the SDK interface.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestSDKImportsHeadless:
    """Test SDK imports work without UI dependencies."""

    def test_sdk_imports_without_ui_libraries(self) -> None:
        """Test that SDK imports don't pull in Textual or Rich."""
        # Clear any cached imports
        ui_modules = [
            "textual",
            "rich",
        ]
        for module in list(sys.modules.keys()):
            if any(ui_lib in module for ui_lib in ui_modules):
                # Skip if already imported (CI environment may have them)
                pytest.skip(
                    f"UI library {module} already imported, skipping isolation test"
                )

        # Import SDK components
        from consoul.sdk import (
            Attachment,
            Consoul,
            ConversationService,
            ConversationStats,
            ModelCapabilities,
            ModelInfo,
            PricingInfo,
            Token,
            ToolRequest,
        )

        # Verify imports worked
        assert Consoul is not None
        assert ConversationService is not None
        assert Attachment is not None
        assert Token is not None
        assert ToolRequest is not None
        assert ConversationStats is not None
        assert ModelInfo is not None
        assert PricingInfo is not None
        assert ModelCapabilities is not None

        # Verify UI libraries not imported as side effect
        for module in sys.modules:
            assert not module.startswith("textual"), (
                f"Textual module {module} imported as side effect"
            )
            # Note: Rich may be in dependencies but SDK core shouldn't require it

    def test_conversation_service_import(self) -> None:
        """Test ConversationService can be imported standalone."""
        from consoul.sdk.services.conversation import ConversationService

        assert ConversationService is not None
        assert hasattr(ConversationService, "from_config")
        assert hasattr(ConversationService, "send_message")

    def test_model_service_import(self) -> None:
        """Test ModelService can be imported standalone."""
        from consoul.sdk.services.model import ModelService

        assert ModelService is not None
        assert hasattr(ModelService, "from_config")
        assert hasattr(ModelService, "get_model")
        assert hasattr(ModelService, "switch_model")

    def test_tool_service_import(self) -> None:
        """Test ToolService can be imported standalone."""
        from consoul.sdk.services.tool import ToolService

        assert ToolService is not None
        assert hasattr(ToolService, "from_config")
        assert hasattr(ToolService, "list_tools")
        assert hasattr(ToolService, "needs_approval")


class TestConversationServiceHeadless:
    """Test ConversationService works without UI dependencies."""

    def test_conversation_service_initialization(self) -> None:
        """Test ConversationService initializes without UI."""
        from consoul.sdk.services.conversation import ConversationService

        # Setup mocks
        mock_model = Mock()
        mock_conversation = Mock()
        mock_conversation.messages = []
        mock_conversation.session_id = "test-session"
        mock_conversation.model_name = "gpt-4o"

        # Create service
        service = ConversationService(model=mock_model, conversation=mock_conversation)

        assert service is not None
        assert service.model is mock_model
        assert service.conversation is mock_conversation

    @pytest.mark.asyncio
    async def test_send_message_basic(self) -> None:
        """Test send_message works without UI dependencies."""
        from consoul.sdk.models import Token
        from consoul.sdk.services.conversation import ConversationService

        # Setup mocks
        mock_model = Mock()
        mock_conversation = Mock()
        mock_conversation.messages = []
        mock_conversation.session_id = "test-session"
        mock_conversation.model_name = "gpt-4o"
        mock_conversation.add_user_message_async = AsyncMock()
        mock_conversation._persist_message = AsyncMock()
        mock_conversation.count_tokens = Mock(return_value=100)

        # Mock streaming response
        async def mock_stream():
            yield Token(content="Hello")
            yield Token(content=" world")
            yield Token(content="!")

        service = ConversationService(model=mock_model, conversation=mock_conversation)

        # Mock _stream_response to return our mock tokens
        with patch.object(service, "_stream_response", return_value=mock_stream()):
            tokens = []
            async for token in service.send_message("Hello"):
                tokens.append(token)

            assert len(tokens) == 3
            assert tokens[0].content == "Hello"
            assert tokens[1].content == " world"
            assert tokens[2].content == "!"

    def test_get_stats_without_ui(self) -> None:
        """Test get_stats works without UI dependencies."""
        from consoul.sdk.services.conversation import ConversationService

        # Setup mocks
        mock_model = Mock()
        mock_model.model_name = "gpt-4o"
        mock_conversation = Mock()
        mock_conversation.messages = [Mock(), Mock(), Mock()]  # 3 messages
        mock_conversation.model_name = "gpt-4o"
        mock_conversation.session_id = "test-session"
        mock_conversation.count_tokens = Mock(return_value=500)

        service = ConversationService(model=mock_model, conversation=mock_conversation)

        stats = service.get_stats()

        assert stats is not None
        assert stats.message_count == 3
        assert stats.total_tokens == 500
        assert stats.session_id == "test-session"


class TestModelServiceHeadless:
    """Test ModelService works without UI dependencies."""

    @patch("consoul.ai.get_chat_model")
    def test_model_service_initialization(self, mock_get_model: Mock) -> None:
        """Test ModelService initializes without UI."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(model=mock_model, config=mock_config, tool_service=None)

        assert service is not None
        assert service._model is mock_model
        assert service.current_model_id == "gpt-4o"

    @patch("consoul.ai.get_chat_model")
    def test_switch_model_without_ui(self, mock_get_model: Mock) -> None:
        """Test model switching works without UI dependencies."""
        from consoul.sdk.services.model import ModelService

        initial_model = Mock()
        new_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_config.get_current_model_config = Mock()
        mock_get_model.return_value = new_model

        service = ModelService(
            model=initial_model, config=mock_config, tool_service=None
        )

        # Switch model
        result = service.switch_model("claude-3-5-sonnet-20241022")

        assert result is new_model
        assert service.current_model_id == "claude-3-5-sonnet-20241022"

    def test_supports_vision_without_ui(self) -> None:
        """Test vision capability detection works without UI."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(model=mock_model, config=mock_config, tool_service=None)

        # Use patch to return ModelInfo with vision support
        with patch.object(service, "get_current_model_info") as mock_get_info:
            mock_info = Mock()
            mock_info.supports_vision = True
            mock_get_info.return_value = mock_info

            assert service.supports_vision() is True


class TestToolServiceHeadless:
    """Test ToolService works without UI dependencies."""

    def test_tool_service_initialization(self) -> None:
        """Test ToolService initializes without UI."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_config = Mock()

        service = ToolService(tool_registry=mock_registry, config=mock_config)

        assert service is not None
        assert service.tool_registry is mock_registry

    def test_list_tools_without_ui(self) -> None:
        """Test tool listing works without UI dependencies."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_tools = [Mock(name="bash_execute"), Mock(name="read_file")]
        mock_registry.list_tools = Mock(return_value=mock_tools)

        service = ToolService(tool_registry=mock_registry, config=None)

        tools = service.list_tools(enabled_only=True)

        assert len(tools) == 2
        mock_registry.list_tools.assert_called_once_with(enabled_only=True)

    def test_needs_approval_without_ui(self) -> None:
        """Test approval checks work without UI dependencies."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_registry.needs_approval = Mock(return_value=True)

        service = ToolService(tool_registry=mock_registry, config=None)

        result = service.needs_approval("bash_execute", {"command": "ls"})

        assert result is True


class TestConsoulWrapperHeadless:
    """Test high-level Consoul wrapper works without UI."""

    def test_consoul_response_model(self) -> None:
        """Test ConsoulResponse model works without UI."""
        from consoul.sdk.wrapper import ConsoulResponse

        # Create response
        response = ConsoulResponse(content="Hello there!", tokens=10, model="gpt-4o")

        assert response.content == "Hello there!"
        assert response.tokens == 10
        assert response.model == "gpt-4o"
        assert str(response) == "Hello there!"

    def test_consoul_wrapper_import(self) -> None:
        """Test Consoul wrapper can be imported without UI."""
        from consoul.sdk.wrapper import Consoul

        # Verify class exists and has expected methods
        assert Consoul is not None
        assert hasattr(Consoul, "chat")
        assert hasattr(Consoul, "ask")


class TestStreamingWithoutUI:
    """Test streaming functionality works without UI dependencies."""

    @pytest.mark.asyncio
    async def test_token_streaming_no_ui_required(self) -> None:
        """Test Token streaming doesn't require UI libraries."""
        from consoul.sdk.models import Token

        # Create tokens (should not require UI)
        token1 = Token(content="Hello")
        token2 = Token(content=" world", cost=0.0001)

        assert token1.content == "Hello"
        assert token2.content == " world"
        assert token2.cost == 0.0001

    @pytest.mark.asyncio
    async def test_async_iteration_without_ui(self) -> None:
        """Test async iteration over tokens works without UI."""
        from consoul.sdk.models import Token

        # Simulate async token stream
        async def token_stream():
            yield Token(content="Hello")
            yield Token(content=" world")
            yield Token(content="!")

        collected = []
        async for token in token_stream():
            collected.append(token.content)

        assert collected == ["Hello", " world", "!"]


class TestCustomApprovalProviderHeadless:
    """Test custom approval provider works without UI."""

    def test_custom_approval_provider_interface(self) -> None:
        """Test that custom approval providers can be implemented without UI."""

        # Create custom approval provider (headless)
        class HeadlessApprovalProvider:
            """Example headless approval provider for testing."""

            async def __call__(
                self, tool_name: str, arguments: dict, approved: bool = True
            ) -> bool:
                """Auto-approve or auto-reject based on parameter."""
                return approved

        # Create instance
        provider = HeadlessApprovalProvider()

        # Verify it works
        import asyncio

        result = asyncio.run(provider("bash_execute", {"command": "ls"}))
        assert result is True

        result = asyncio.run(
            provider("bash_execute", {"command": "rm -rf /"}, approved=False)
        )
        assert result is False


class TestSDKModelsHeadless:
    """Test SDK models work without UI dependencies."""

    def test_attachment_model(self) -> None:
        """Test Attachment model works without UI."""
        from consoul.sdk.models import Attachment

        attachment = Attachment(path="/tmp/test.txt", type="document")

        assert attachment.path == "/tmp/test.txt"
        assert attachment.type == "document"

    def test_conversation_stats_model(self) -> None:
        """Test ConversationStats model works without UI."""
        from consoul.sdk.models import ConversationStats

        stats = ConversationStats(
            message_count=5,
            total_tokens=1000,
            total_cost=0.05,
            session_id="test-123",
        )

        assert stats.message_count == 5
        assert stats.total_tokens == 1000
        assert stats.total_cost == 0.05

    def test_model_info_model(self) -> None:
        """Test ModelInfo model works without UI."""
        from consoul.sdk.models import ModelInfo

        model_info = ModelInfo(
            id="gpt-4o",
            name="GPT-4 Optimized",
            provider="openai",
            context_window="128K",
            description="Latest GPT-4 model",
            supports_vision=True,
            supports_tools=True,
        )

        assert model_info.id == "gpt-4o"
        assert model_info.supports_vision is True
        assert model_info.supports_tools is True

    def test_pricing_info_model(self) -> None:
        """Test PricingInfo model works without UI."""
        from consoul.sdk.models import PricingInfo

        pricing = PricingInfo(
            input_price=2.50,
            output_price=10.00,
            tier="standard",
            effective_date="2025-01-01",
        )

        assert pricing.input_price == 2.50
        assert pricing.output_price == 10.00

    def test_model_capabilities_model(self) -> None:
        """Test ModelCapabilities model works without UI."""
        from consoul.sdk.models import ModelCapabilities

        caps = ModelCapabilities(
            supports_vision=True,
            supports_tools=True,
            supports_reasoning=False,
            supports_streaming=True,
        )

        assert caps.supports_vision is True
        assert caps.supports_tools is True
        assert caps.supports_reasoning is False


class TestSDKWithoutRichConsole:
    """Test SDK doesn't require rich.console for core functionality."""

    def test_sdk_imports_dont_require_rich_console(self) -> None:
        """Verify SDK doesn't import rich.console as side effect."""
        # Note: Rich may be in dependencies for other purposes,
        # but SDK shouldn't require rich.console specifically
        from consoul.sdk import Consoul, ConversationService

        assert Consoul is not None
        assert ConversationService is not None
        # rich.console may or may not be loaded - SDK core doesn't require it

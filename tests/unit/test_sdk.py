"""Unit tests for Consoul SDK."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.tools import tool

from consoul import Consoul, ConsoulResponse
from consoul.ai.tools import RiskLevel


class TestConsoulResponse:
    """Test ConsoulResponse class."""

    def test_init(self) -> None:
        """Test ConsoulResponse initialization."""
        response = ConsoulResponse(
            content="Hello, world!",
            tokens=100,
            model="claude-3-5-sonnet-20241022",
        )
        assert response.content == "Hello, world!"
        assert response.tokens == 100
        assert response.model == "claude-3-5-sonnet-20241022"

    def test_init_defaults(self) -> None:
        """Test ConsoulResponse with default values."""
        response = ConsoulResponse(content="Hello")
        assert response.content == "Hello"
        assert response.tokens == 0
        assert response.model == ""

    def test_str(self) -> None:
        """Test string representation returns content."""
        response = ConsoulResponse(content="Test content", tokens=50)
        assert str(response) == "Test content"

    def test_repr(self) -> None:
        """Test repr shows detailed information."""
        response = ConsoulResponse(
            content="A" * 100,
            tokens=75,
            model="gpt-4o",
        )
        repr_str = repr(response)
        assert "ConsoulResponse" in repr_str
        assert "tokens=75" in repr_str
        assert "model='gpt-4o'" in repr_str
        # Check truncation
        assert len(repr_str) < 150


class TestConsoulInit:
    """Test Consoul initialization."""

    def test_init_invalid_temperature(self) -> None:
        """Test that invalid temperature raises ValueError."""
        with pytest.raises(
            ValueError, match=r"Temperature must be between 0\.0 and 2\.0"
        ):
            Consoul(temperature=3.0)

        with pytest.raises(
            ValueError, match=r"Temperature must be between 0\.0 and 2\.0"
        ):
            Consoul(temperature=-1.0)


class TestConsoulChat:
    """Test Consoul chat/ask methods use basic property tests."""

    def test_chat_and_ask_are_callable(self) -> None:
        """Test that Consoul has chat and ask methods."""
        # We can't easily test full functionality without real API keys
        # So just verify the class has these methods
        assert hasattr(Consoul, "chat")
        assert callable(Consoul.chat)
        assert hasattr(Consoul, "ask")
        assert callable(Consoul.ask)

    def test_clear_is_callable(self) -> None:
        """Test that Consoul has clear method."""
        assert hasattr(Consoul, "clear")
        assert callable(Consoul.clear)


class TestConsoulProperties:
    """Test Consoul has introspection properties."""

    def test_has_settings_property(self) -> None:
        """Test that Consoul class has settings property."""
        assert hasattr(Consoul, "settings")

    def test_has_last_request_property(self) -> None:
        """Test that Consoul class has last_request property."""
        assert hasattr(Consoul, "last_request")

    def test_has_last_cost_property(self) -> None:
        """Test that Consoul class has last_cost property."""
        assert hasattr(Consoul, "last_cost")


class TestConsoulToolSpecification:
    """Test tool specification functionality."""

    @patch("consoul.sdk.get_chat_model")
    def test_tools_disabled_with_false(self, mock_get_model: Mock) -> None:
        """Test that tools=False disables all tools."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        console = Consoul(tools=False, persist=False)

        assert console.tools_spec is False
        assert console.registry is None
        assert console.tools_enabled is False

    @patch("consoul.sdk.get_chat_model")
    def test_tools_disabled_with_none(self, mock_get_model: Mock) -> None:
        """Test that tools=None disables all tools."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        console = Consoul(tools=None, persist=False)

        assert console.tools_spec is None
        assert console.registry is None
        assert console.tools_enabled is False

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_enabled_with_true(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test that tools=True enables all tools (backward compatible)."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        console = Consoul(tools=True, persist=False)

        assert console.tools_spec is True
        assert console.tools_enabled is True
        assert mock_registry.register.call_count == 13  # All 13 tools in catalog

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_by_name_list(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test specifying tools by name in a list."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        console = Consoul(tools=["bash", "grep"], persist=False)

        assert console.tools_spec == ["bash", "grep"]
        assert mock_registry.register.call_count == 2

        # Verify the right tools were registered
        calls = mock_registry.register.call_args_list
        registered_names = {call.kwargs["tool"].name for call in calls}
        assert "bash_execute" in registered_names
        assert "grep_search" in registered_names

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_by_risk_level_safe(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test specifying tools by risk level (safe)."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        console = Consoul(tools="safe", persist=False)

        assert console.tools_spec == "safe"

        # Verify only safe tools were registered
        calls = mock_registry.register.call_args_list
        for call in calls:
            assert call.kwargs["risk_level"] == RiskLevel.SAFE

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_by_risk_level_caution(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test specifying tools by risk level (caution)."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        console = Consoul(tools="caution", persist=False)

        assert console.tools_spec == "caution"

        # Verify safe + caution tools were registered
        calls = mock_registry.register.call_args_list
        risk_levels = {call.kwargs["risk_level"] for call in calls}
        assert RiskLevel.SAFE in risk_levels
        assert RiskLevel.CAUTION in risk_levels
        assert RiskLevel.DANGEROUS not in risk_levels

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_custom_basetool(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test specifying custom BaseTool instance."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Create a custom tool
        @tool
        def my_custom_tool(query: str) -> str:
            """Custom tool for testing."""
            return f"Result: {query}"

        console = Consoul(tools=[my_custom_tool], persist=False)

        assert console.tools_spec == [my_custom_tool]
        assert mock_registry.register.call_count == 1

        # Verify custom tool was registered with CAUTION level
        call = mock_registry.register.call_args
        assert call.kwargs["tool"] == my_custom_tool
        assert call.kwargs["risk_level"] == RiskLevel.CAUTION

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_mixed_custom_and_builtin(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test mixing custom tools with built-in tool names."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Create a custom tool
        @tool
        def my_tool(x: int) -> int:
            """Double the input."""
            return x * 2

        Consoul(tools=[my_tool, "bash", "grep"], persist=False)

        assert mock_registry.register.call_count == 3

        # Verify mixed tools were registered
        calls = mock_registry.register.call_args_list
        tool_names = {call.kwargs["tool"].name for call in calls}
        assert "my_tool" in tool_names
        assert "bash_execute" in tool_names
        assert "grep_search" in tool_names

    @patch("consoul.sdk.get_chat_model")
    def test_tools_invalid_name_raises_error(self, mock_get_model: Mock) -> None:
        """Test that invalid tool name raises ValueError."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        with pytest.raises(ValueError, match="Unknown tool or category 'invalid_tool'"):
            Consoul(tools=["invalid_tool"], persist=False)

    @patch("consoul.sdk.get_chat_model")
    def test_tools_invalid_type_raises_error(self, mock_get_model: Mock) -> None:
        """Test that invalid tool type raises ValueError."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        with pytest.raises(ValueError, match="Invalid tools parameter type"):
            Consoul(tools=123, persist=False)  # type: ignore

    @patch("consoul.sdk.get_chat_model")
    def test_tools_empty_list(self, mock_get_model: Mock) -> None:
        """Test that empty list disables tools."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        console = Consoul(tools=[], persist=False)

        assert console.tools_spec == []
        assert console.registry is None
        assert console.tools_enabled is False

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_single_string_name(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test specifying a single tool as string."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        console = Consoul(tools="bash", persist=False)

        assert console.tools_spec == "bash"
        assert console.tools_enabled is True
        assert mock_registry.register.call_count == 1

        # Verify bash tool was registered
        call = mock_registry.register.call_args
        assert call.kwargs["tool"].name == "bash_execute"

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    def test_tools_enabled_accessible_in_settings(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test that tools_enabled is accessible via settings property."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Test with tools enabled
        console = Consoul(tools=["bash"], persist=False)
        settings = console.settings
        assert settings["tools_enabled"] is True

        # Test with tools disabled
        console_no_tools = Consoul(tools=False, persist=False)
        settings_no_tools = console_no_tools.settings
        assert settings_no_tools["tools_enabled"] is False


class TestConsoulTokenUsage:
    """Test token usage tracking from usage_metadata."""

    @patch("consoul.sdk.get_chat_model")
    def test_last_cost_with_usage_metadata(self, mock_get_model: Mock) -> None:
        """Test that last_cost extracts usage_metadata when available."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Create mock response with usage_metadata
        mock_response = AIMessage(
            content="Test response",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )
        mock_model.invoke.return_value = mock_response

        console = Consoul(model="claude-3-5-haiku-20241022", tools=False, persist=False)
        console.chat("Test message")

        cost = console.last_cost
        assert cost["input_tokens"] == 100
        assert cost["output_tokens"] == 50
        assert cost["total_tokens"] == 150
        assert cost["source"] == "usage_metadata"
        assert cost["estimated_cost"] > 0  # Should use accurate pricing
        assert cost["model"] == "claude-3-5-haiku-20241022"

    @patch("consoul.sdk.get_chat_model")
    def test_last_cost_fallback_without_metadata(self, mock_get_model: Mock) -> None:
        """Test that last_cost falls back when usage_metadata unavailable."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Create response WITHOUT usage_metadata
        mock_response = AIMessage(content="Test response")
        mock_model.invoke.return_value = mock_response

        console = Consoul(model="claude-3-5-haiku-20241022", tools=False, persist=False)

        # Mock history.count_tokens() for fallback calculation
        console.history.count_tokens = Mock(side_effect=[0, 100])  # before, after

        console.chat("Test message")

        cost = console.last_cost
        assert cost["source"] == "approximation"
        assert cost["input_tokens"] > 0  # Fallback calculation
        assert cost["output_tokens"] > 0
        assert cost["total_tokens"] > 0
        assert (
            cost["estimated_cost"] > 0
        )  # Should use accurate pricing even with approximated tokens

    @patch("consoul.sdk.get_chat_model")
    def test_last_cost_before_any_requests(self, mock_get_model: Mock) -> None:
        """Test last_cost returns zeros before any chat."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        console = Consoul(tools=False, persist=False)
        cost = console.last_cost

        assert cost["input_tokens"] == 0
        assert cost["output_tokens"] == 0
        assert cost["total_tokens"] == 0
        assert cost["estimated_cost"] == 0.0
        assert cost["source"] == "none"

    @patch("consoul.sdk.get_chat_model")
    def test_last_cost_uses_metadata_total_tokens(self, mock_get_model: Mock) -> None:
        """Test that total_tokens from metadata is used directly."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Metadata with all fields
        mock_response = AIMessage(
            content="Test",
            usage_metadata={
                "input_tokens": 75,
                "output_tokens": 25,
                "total_tokens": 100,
            },
        )
        mock_model.invoke.return_value = mock_response

        console = Consoul(tools=False, persist=False)

        # Mock history.count_tokens() (not used in this path but needs to be callable)
        console.history.count_tokens = Mock(return_value=0)

        console.chat("Test")

        cost = console.last_cost
        assert cost["input_tokens"] == 75
        assert cost["output_tokens"] == 25
        assert cost["total_tokens"] == 100
        assert cost["source"] == "usage_metadata"

    @patch("consoul.sdk.get_chat_model")
    def test_last_cost_handles_none_metadata(self, mock_get_model: Mock) -> None:
        """Test that last_cost handles None usage_metadata gracefully."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Response with usage_metadata = None
        mock_response = AIMessage(content="Test", usage_metadata=None)
        mock_model.invoke.return_value = mock_response

        console = Consoul(tools=False, persist=False)

        # Mock history.count_tokens() for fallback calculation
        console.history.count_tokens = Mock(side_effect=[0, 50])  # before, after

        console.chat("Test")

        cost = console.last_cost
        assert cost["source"] == "approximation"  # Falls back
        assert cost["total_tokens"] > 0


class TestConsoulToolDiscovery:
    """Test tool discovery functionality."""

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    @patch("consoul.sdk.discover_tools_from_directory")
    def test_discover_tools_disabled_by_default(
        self,
        mock_discover: Mock,
        mock_registry_class: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test that tool discovery is disabled by default."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        Consoul(tools=["bash"], persist=False)

        # discover_tools_from_directory should NOT be called
        mock_discover.assert_not_called()

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    @patch("consoul.sdk.discover_tools_from_directory")
    def test_discover_tools_when_enabled(
        self,
        mock_discover: Mock,
        mock_registry_class: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test that discover_tools=True enables discovery."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Mock discovered tools
        @tool
        def discovered_tool(x: str) -> str:
            """Discovered tool."""
            return x

        mock_discover.return_value = [(discovered_tool, RiskLevel.CAUTION)]

        Consoul(tools=["bash"], discover_tools=True, persist=False)

        # discover_tools_from_directory should be called once
        mock_discover.assert_called_once()

        # Verify it was called with correct path
        call_args = mock_discover.call_args
        assert str(call_args[0][0]).endswith(".consoul/tools")
        assert call_args[1]["recursive"] is True

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    @patch("consoul.sdk.discover_tools_from_directory")
    def test_discover_tools_combined_with_builtin(
        self,
        mock_discover: Mock,
        mock_registry_class: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test that discovered tools are combined with built-in tools."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Mock discovered tools
        @tool
        def custom_tool_1(x: str) -> str:
            """Custom tool 1."""
            return x

        @tool
        def custom_tool_2(y: int) -> int:
            """Custom tool 2."""
            return y

        mock_discover.return_value = [
            (custom_tool_1, RiskLevel.CAUTION),
            (custom_tool_2, RiskLevel.CAUTION),
        ]

        Consoul(tools=["bash", "grep"], discover_tools=True, persist=False)

        # Should have registered 4 tools: bash, grep, custom_tool_1, custom_tool_2
        assert mock_registry.register.call_count == 4

        # Verify tool names
        calls = mock_registry.register.call_args_list
        registered_names = {call.kwargs["tool"].name for call in calls}
        assert "bash_execute" in registered_names
        assert "grep_search" in registered_names
        assert "custom_tool_1" in registered_names
        assert "custom_tool_2" in registered_names

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.ToolRegistry")
    @patch("consoul.sdk.discover_tools_from_directory")
    def test_discover_tools_with_tools_true(
        self,
        mock_discover: Mock,
        mock_registry_class: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test discovery with tools=True (all built-in tools)."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Mock one discovered tool
        @tool
        def my_tool(x: str) -> str:
            """My tool."""
            return x

        mock_discover.return_value = [(my_tool, RiskLevel.CAUTION)]

        Consoul(tools=True, discover_tools=True, persist=False)

        # Should have registered 14 tools: 13 built-in + 1 discovered
        assert mock_registry.register.call_count == 14

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.discover_tools_from_directory")
    def test_discover_tools_only_no_builtin(
        self,
        mock_discover: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test discovery with tools=False (only discovered tools)."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Mock discovered tools
        @tool
        def only_discovered(x: str) -> str:
            """Only discovered."""
            return x

        mock_discover.return_value = [(only_discovered, RiskLevel.CAUTION)]

        console = Consoul(tools=False, discover_tools=True, persist=False)

        # Should have enabled tools from discovery
        assert console.tools_enabled is True
        mock_discover.assert_called_once()

    @patch("consoul.sdk.get_chat_model")
    @patch("consoul.sdk.discover_tools_from_directory")
    def test_discover_tools_empty_directory(
        self,
        mock_discover: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test discovery with empty directory (no tools found)."""
        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Mock empty discovery
        mock_discover.return_value = []

        console = Consoul(tools=False, discover_tools=True, persist=False)

        # Should have disabled tools since nothing was discovered
        assert console.tools_enabled is False
        mock_discover.assert_called_once()


class TestConsoulApprovalProvider:
    """Test custom approval provider functionality."""

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.ToolRegistry")
    def test_custom_approval_provider(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test that custom approval provider is passed to ToolRegistry."""
        from consoul.ai.tools.approval import ToolApprovalRequest, ToolApprovalResponse

        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Create mock approval provider
        class MockApprovalProvider:
            async def request_approval(
                self, request: ToolApprovalRequest
            ) -> ToolApprovalResponse:
                return ToolApprovalResponse(approved=True)

        provider = MockApprovalProvider()
        console = Consoul(tools=True, approval_provider=provider, persist=False)

        # Verify ToolRegistry was created with custom provider
        assert console.tools_enabled is True
        mock_registry_class.assert_called_once()

        # Get the call arguments
        call_kwargs = mock_registry_class.call_args.kwargs
        assert call_kwargs["approval_provider"] == provider

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.ToolRegistry")
    @patch("consoul.sdk.wrapper.CliApprovalProvider")
    def test_default_approval_provider(
        self,
        mock_cli_provider_class: Mock,
        mock_registry_class: Mock,
        mock_get_model: Mock,
    ) -> None:
        """Test that CliApprovalProvider is used by default."""
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        mock_cli_provider = Mock()
        mock_cli_provider_class.return_value = mock_cli_provider

        # Create Consoul without approval_provider parameter
        console = Consoul(tools=True, persist=False)

        # Verify CliApprovalProvider was instantiated
        mock_cli_provider_class.assert_called_once_with(show_arguments=True)

        # Verify it was passed to ToolRegistry
        assert console.tools_enabled is True
        call_kwargs = mock_registry_class.call_args.kwargs
        assert call_kwargs["approval_provider"] == mock_cli_provider

    @patch("consoul.sdk.wrapper.get_chat_model")
    def test_approval_provider_with_tools_disabled(self, mock_get_model: Mock) -> None:
        """Test that approval_provider is ignored when tools are disabled."""
        from consoul.ai.tools.approval import ToolApprovalRequest, ToolApprovalResponse

        mock_model = Mock()
        mock_get_model.return_value = mock_model

        # Create mock approval provider
        class MockApprovalProvider:
            async def request_approval(
                self, request: ToolApprovalRequest
            ) -> ToolApprovalResponse:
                return ToolApprovalResponse(approved=True)

        provider = MockApprovalProvider()

        # Should not raise error even with custom provider
        console = Consoul(tools=False, approval_provider=provider, persist=False)

        # Verify tools are disabled and registry was not created
        assert console.tools_enabled is False
        assert console.registry is None
        assert console.approval_provider == provider  # Stored but not used

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.ToolRegistry")
    def test_web_approval_provider_integration(
        self, mock_registry_class: Mock, mock_get_model: Mock
    ) -> None:
        """Test integration with WebApprovalProvider example."""
        from examples.sdk.web_approval_provider import WebApprovalProvider

        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_get_model.return_value = mock_model

        mock_registry = Mock()
        mock_registry.bind_to_model.return_value = mock_model_with_tools
        mock_registry_class.return_value = mock_registry

        # Create WebApprovalProvider instance
        web_provider = WebApprovalProvider(
            approval_url="http://localhost:8080/approve",
            auth_token="test-token",
            timeout=60,
        )

        console = Consoul(
            tools=["bash", "grep"], approval_provider=web_provider, persist=False
        )

        # Verify web provider was passed to registry
        assert console.tools_enabled is True
        call_kwargs = mock_registry_class.call_args.kwargs
        assert call_kwargs["approval_provider"] == web_provider

        # Verify tools were registered
        assert mock_registry.register.call_count == 2

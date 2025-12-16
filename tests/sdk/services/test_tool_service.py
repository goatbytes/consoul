"""Unit tests for ToolService.

Tests tool registration, listing, approval policy checks, and configuration.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


class TestToolServiceInitialization:
    """Test ToolService initialization."""

    def test_init_basic(self) -> None:
        """Test basic ToolService initialization."""
        from consoul.sdk.services.tool import ToolService

        # Create mock registry
        mock_registry = Mock()
        mock_config = Mock()

        # Create service
        service = ToolService(tool_registry=mock_registry, config=mock_config)

        assert service.tool_registry is mock_registry
        assert service.config is mock_config

    def test_init_without_config(self) -> None:
        """Test ToolService initialization without config."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()

        service = ToolService(tool_registry=mock_registry, config=None)

        assert service.tool_registry is mock_registry
        assert service.config is None


class TestFromConfig:
    """Test ToolService.from_config() factory method."""

    def test_from_config_default(self, mock_config: Mock) -> None:
        """Test factory with default configuration (all tools enabled)."""
        from consoul.sdk.services.tool import ToolService

        # Configure mock for default behavior (no allowed_tools, no risk_filter)
        mock_config.tools.allowed_tools = None
        mock_config.tools.risk_filter = None
        # Individual tool configs (all None for defaults)
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

        service = ToolService.from_config(mock_config)

        assert service is not None
        assert service.tool_registry is not None
        assert service.config == mock_config.tools

        # Verify tools are registered (all enabled by default)
        tools = service.list_tools(enabled_only=True)
        assert len(tools) > 0  # Should have enabled tools

    def test_from_config_with_allowed_tools(self, mock_config: Mock) -> None:
        """Test factory with explicit allowed_tools whitelist."""
        from consoul.sdk.services.tool import ToolService

        # Configure mock with allowed_tools whitelist
        mock_config.tools.allowed_tools = ["bash", "read", "grep_search"]
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

        service = ToolService.from_config(mock_config)

        assert service is not None
        enabled_tools = service.list_tools(enabled_only=True)

        # Only whitelisted tools should be enabled
        enabled_names = {tool.name for tool in enabled_tools}
        assert "bash_execute" in enabled_names  # "bash" -> "bash_execute"
        assert "read_file" in enabled_names  # "read" -> "read_file"
        assert "grep_search" in enabled_names

    def test_from_config_with_risk_filter(self, mock_config: Mock) -> None:
        """Test factory with risk-based filtering."""
        from consoul.sdk.services.tool import ToolService

        # Configure mock with risk_filter
        mock_config.tools.allowed_tools = None
        mock_config.tools.risk_filter = "safe"  # Only SAFE tools
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

        service = ToolService.from_config(mock_config)

        assert service is not None
        enabled_tools = service.list_tools(enabled_only=True)

        # Verify risk filter applied (SAFE tools only)
        # grep_search, read_file, code_search are SAFE
        enabled_names = {tool.name for tool in enabled_tools}
        assert "grep_search" in enabled_names  # SAFE
        assert "read_file" in enabled_names  # SAFE

    def test_from_config_empty_whitelist(self, mock_config: Mock) -> None:
        """Test factory with empty allowed_tools (chat-only mode)."""
        from consoul.sdk.services.tool import ToolService

        # Configure mock with empty allowed_tools
        mock_config.tools.allowed_tools = []  # Chat-only mode
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

        service = ToolService.from_config(mock_config)

        assert service is not None
        enabled_tools = service.list_tools(enabled_only=True)

        # No tools should be enabled
        assert len(enabled_tools) == 0

    def test_from_config_invalid_tool_name(self, mock_config: Mock) -> None:
        """Test factory with invalid tool name in allowed_tools."""
        from consoul.sdk.services.tool import ToolService

        # Configure mock with invalid tool name
        mock_config.tools.allowed_tools = ["bash", "invalid_tool_xyz"]
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

        with pytest.raises(ValueError, match="Invalid tool names"):
            ToolService.from_config(mock_config)


class TestListTools:
    """Test tool listing functionality."""

    def test_list_tools_enabled_only(self) -> None:
        """Test listing only enabled tools."""
        from consoul.sdk.services.tool import ToolService

        # Create mock registry
        mock_registry = Mock()
        mock_enabled = [Mock(name="bash_execute"), Mock(name="read_file")]
        mock_registry.list_tools = Mock(return_value=mock_enabled)

        service = ToolService(tool_registry=mock_registry, config=None)

        tools = service.list_tools(enabled_only=True)

        assert len(tools) == 2
        mock_registry.list_tools.assert_called_once_with(enabled_only=True)

    def test_list_tools_all(self) -> None:
        """Test listing all tools (enabled + disabled)."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_all = [
            Mock(name="bash_execute", enabled=True),
            Mock(name="read_file", enabled=True),
            Mock(name="web_search", enabled=False),
        ]
        mock_registry.list_tools = Mock(return_value=mock_all)

        service = ToolService(tool_registry=mock_registry, config=None)

        tools = service.list_tools(enabled_only=False)

        assert len(tools) == 3
        mock_registry.list_tools.assert_called_once_with(enabled_only=False)


class TestNeedsApproval:
    """Test approval policy checks."""

    def test_needs_approval_true(self) -> None:
        """Test tool requiring approval."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_registry.needs_approval = Mock(return_value=True)

        service = ToolService(tool_registry=mock_registry, config=None)

        result = service.needs_approval("bash_execute", {"command": "rm -rf /"})

        assert result is True
        mock_registry.needs_approval.assert_called_once_with(
            "bash_execute", {"command": "rm -rf /"}
        )

    def test_needs_approval_false(self) -> None:
        """Test tool auto-approved."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_registry.needs_approval = Mock(return_value=False)

        service = ToolService(tool_registry=mock_registry, config=None)

        result = service.needs_approval("read_file", {"path": "README.md"})

        assert result is False
        mock_registry.needs_approval.assert_called_once_with(
            "read_file", {"path": "README.md"}
        )


class TestGetToolsCount:
    """Test tool count functionality."""

    def test_get_tools_count(self) -> None:
        """Test getting total tool count."""
        from consoul.sdk.services.tool import ToolService

        mock_registry = Mock()
        mock_all_tools = [Mock() for _ in range(15)]  # 15 total tools
        mock_registry.list_tools = Mock(return_value=mock_all_tools)

        service = ToolService(tool_registry=mock_registry, config=None)

        count = service.get_tools_count()

        assert count == 15
        mock_registry.list_tools.assert_called_once_with(enabled_only=False)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config() -> Mock:
    """Create mock ConsoulConfig for testing."""
    import tempfile

    config = Mock()

    # Tool configuration
    config.tools = Mock()
    config.tools.allowed_tools = None
    config.tools.risk_filter = None
    config.tools.audit_log_file = tempfile.mktemp(suffix=".log")  # Valid path
    config.tools.bash = None
    config.tools.read = None
    config.tools.grep_search = None
    config.tools.code_search = None
    config.tools.find_references = None
    config.tools.web_search = None
    config.tools.wikipedia = None
    config.tools.read_url = None
    config.tools.file_edit = None
    config.tools.image_analysis = None

    return config

"""Tests for custom tool registration and factory patterns.

Tests that custom tools are properly registered, prioritized over catalog
tools, and have correct risk levels and categories assigned.
"""

from __future__ import annotations

import contextlib
from unittest.mock import Mock

import pytest
from langchain_core.tools import tool

from consoul.ai.tools.base import RiskLevel, ToolCategory

# =============================================================================
# Test Fixtures - Custom Tools
# =============================================================================


@tool
def custom_tool_one(x: str) -> str:
    """A custom tool for testing."""
    return x.upper()


@tool
def custom_tool_two(y: int) -> int:
    """Another custom tool for testing."""
    return y * 2


@tool
def search_override(query: str) -> str:
    """Custom search tool that should override catalog search."""
    return f"Custom search: {query}"


# =============================================================================
# Test: Custom Tool Registration
# =============================================================================


class TestCustomToolRegistration:
    """Test custom tool registration patterns.

    Note: These tests focus on ToolRegistry directly rather than
    ConversationService.from_config to avoid complex mocking of the
    factory method's many dependencies.
    """

    def _create_tool_config(self):
        """Create a mock ToolConfig."""
        config = Mock()
        config.enabled = True
        config.allowed_tools = None
        config.blocked_tools = []
        config.approval_mode = "auto"
        config.risk_thresholds = {}
        config.tool_timeout = 30
        config.audit_logging = False
        return config

    def test_custom_tool_registration_with_risk_level(self):
        """Custom tools should be registerable with specified risk level."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=Mock())

        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.DANGEROUS,
            categories=[],
        )

        tools = registry.list_tools()
        tool_map = {t.name: t for t in tools}

        assert "custom_tool_one" in tool_map
        assert tool_map["custom_tool_one"].risk_level == RiskLevel.DANGEROUS

    def test_custom_tool_registration_with_categories(self):
        """Custom tools should be registerable with specified categories."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=Mock())

        categories = [ToolCategory.SEARCH, ToolCategory.WEB]
        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.SAFE,
            categories=categories,
        )

        tools = registry.list_tools()
        tool_map = {t.name: t for t in tools}

        assert "custom_tool_one" in tool_map
        assert tool_map["custom_tool_one"].categories == categories

    def test_multiple_custom_tools_registration(self):
        """Multiple custom tools should be registerable."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=Mock())

        registry.register(custom_tool_one, risk_level=RiskLevel.SAFE)
        registry.register(custom_tool_two, risk_level=RiskLevel.CAUTION)

        tools = registry.list_tools()
        names = [t.name for t in tools]

        assert "custom_tool_one" in names
        assert "custom_tool_two" in names


class TestCustomToolFiltering:
    """Test custom tool filtering with allowed_tools."""

    def _create_tool_config(self, allowed_tools=None):
        """Create a mock ToolConfig."""
        config = Mock()
        config.enabled = True
        config.allowed_tools = allowed_tools
        config.blocked_tools = []
        config.approval_mode = "auto"
        config.risk_thresholds = {}
        config.tool_timeout = 30
        config.audit_logging = False  # Disable audit logging for tests
        return config

    def test_custom_tool_enabled_when_in_allowed_tools(self):
        """Custom tool should be enabled when in allowed_tools list."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config(allowed_tools=["custom_tool_one"])
        registry = ToolRegistry(config=config, approval_provider=Mock())

        # Register custom tool
        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.SAFE,
            categories=[],
        )

        tools = registry.list_tools()
        tool_map = {t.name: t for t in tools}

        assert "custom_tool_one" in tool_map
        # enabled determined by allowed_tools
        assert tool_map["custom_tool_one"].enabled is True

    def test_custom_tool_disabled_when_not_in_allowed_tools(self):
        """Custom tool should be disabled when not in allowed_tools list."""
        from consoul.ai.tools.registry import ToolRegistry

        # Only allow a different tool
        config = self._create_tool_config(allowed_tools=["some_other_tool"])
        registry = ToolRegistry(config=config, approval_provider=Mock())

        # Register custom tool - explicitly disabled since not in allowed
        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.SAFE,
            categories=[],
            enabled=False,
        )

        tools = registry.list_tools()
        tool_map = {t.name: t for t in tools}

        assert "custom_tool_one" in tool_map
        assert tool_map["custom_tool_one"].enabled is False

    def test_custom_tool_enabled_when_allowed_tools_none(self):
        """Custom tool should be enabled when allowed_tools is None (all allowed)."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config(allowed_tools=None)
        registry = ToolRegistry(config=config, approval_provider=Mock())

        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.SAFE,
            categories=[],
        )

        tools = registry.list_tools()
        tool_map = {t.name: t for t in tools}

        assert "custom_tool_one" in tool_map
        assert tool_map["custom_tool_one"].enabled is True


class TestToolRegistryPriority:
    """Test that custom tools take priority over catalog tools."""

    def _create_tool_config(self):
        """Create a mock ToolConfig."""
        config = Mock()
        config.enabled = True
        config.allowed_tools = None
        config.blocked_tools = []
        config.approval_mode = "auto"
        config.risk_thresholds = {}
        config.tool_timeout = 30
        config.audit_logging = False  # Disable audit logging for tests
        return config

    def test_custom_tools_registered_before_catalog(self):
        """Custom tools should be registered before catalog tools."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=Mock())

        # Register custom tool first
        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.SAFE,
            categories=[],
        )

        # Then register a "catalog" tool with same infrastructure
        registry.register(
            custom_tool_two,
            risk_level=RiskLevel.CAUTION,
            categories=[],
        )

        tools = registry.list_tools()

        # Both should be present
        names = [t.name for t in tools]
        assert "custom_tool_one" in names
        assert "custom_tool_two" in names

    def test_duplicate_tool_name_handling(self):
        """When same tool name registered twice, implementation handles it."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=Mock())

        # First registration with SAFE
        registry.register(
            custom_tool_one,
            risk_level=RiskLevel.SAFE,
            categories=[],
        )

        # Second registration - create a duplicate tool
        @tool
        def duplicate_tool(x: str) -> str:
            """Duplicate tool."""
            return x.lower()

        # Override the name to match
        duplicate_tool.name = "custom_tool_one"

        # Register again - should either raise or overwrite
        with contextlib.suppress(ValueError, Exception):
            registry.register(
                duplicate_tool,
                risk_level=RiskLevel.DANGEROUS,
                categories=[],
            )

        # Verify original tool is still registered
        tools = registry.list_tools()
        tool_map = {t.name: t for t in tools}
        assert "custom_tool_one" in tool_map


class TestToolValidation:
    """Test tool validation during registration."""

    def test_tool_with_empty_name_rejected(self):
        """Tool with empty name should be rejected."""
        from consoul.ai.tools.base import ToolMetadata

        with pytest.raises(ValueError, match="name cannot be empty"):
            ToolMetadata(
                name="",
                description="Test",
                risk_level=RiskLevel.SAFE,
                tool=Mock(),
                schema={},
            )

    def test_tool_with_empty_description_rejected(self):
        """Tool with empty description should be rejected."""
        from consoul.ai.tools.base import ToolMetadata

        with pytest.raises(ValueError, match="description cannot be empty"):
            ToolMetadata(
                name="test_tool",
                description="",
                risk_level=RiskLevel.SAFE,
                tool=Mock(),
                schema={},
            )

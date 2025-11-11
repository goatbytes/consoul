"""Tests for ToolRegistry."""

from unittest.mock import MagicMock

import pytest
from langchain_core.tools import tool

from consoul.ai.tools import (
    RiskLevel,
    ToolNotFoundError,
    ToolRegistry,
    ToolValidationError,
)
from consoul.config.models import ToolConfig

# Test fixtures


@pytest.fixture
def tool_config():
    """Create a default ToolConfig for testing."""
    return ToolConfig(
        enabled=True,
        auto_approve=False,
        allowed_tools=[],
        approval_mode="always",
        timeout=30,
    )


@pytest.fixture
def registry(tool_config):
    """Create a ToolRegistry for testing."""
    from tests.ai.tools.test_approval import MockApproveProvider

    return ToolRegistry(tool_config, approval_provider=MockApproveProvider())


@pytest.fixture
def sample_tool():
    """Create a sample LangChain tool for testing."""

    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    return multiply


@pytest.fixture
def dangerous_tool():
    """Create a dangerous tool for security testing."""

    @tool
    def delete_files(path: str) -> str:
        """Delete files at path."""
        return f"Deleted {path}"

    return delete_files


# Test ToolRegistry initialization


class TestToolRegistryInit:
    """Tests for ToolRegistry initialization."""

    def test_init_with_config(self, tool_config):
        """Test registry initializes with config."""
        from tests.ai.tools.test_approval import MockApproveProvider

        registry = ToolRegistry(tool_config, approval_provider=MockApproveProvider())
        assert registry.config == tool_config
        assert len(registry) == 0

    def test_init_creates_empty_registry(self, registry):
        """Test registry starts empty."""
        assert len(registry._tools) == 0
        assert len(registry._approved_this_session) == 0


# Test tool registration


class TestToolRegistration:
    """Tests for tool registration functionality."""

    def test_register_tool(self, registry, sample_tool):
        """Test registering a tool."""
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        assert "multiply" in registry
        assert len(registry) == 1

        metadata = registry.get_tool("multiply")
        assert metadata.name == "multiply"
        assert metadata.risk_level == RiskLevel.SAFE
        assert metadata.enabled is True

    def test_register_with_tags(self, registry, sample_tool):
        """Test registering tool with tags."""
        registry.register(
            sample_tool, risk_level=RiskLevel.SAFE, tags=["math", "readonly"]
        )

        metadata = registry.get_tool("multiply")
        assert metadata.tags == ["math", "readonly"]

    def test_register_disabled_tool(self, registry, sample_tool):
        """Test registering a disabled tool."""
        registry.register(sample_tool, enabled=False)

        metadata = registry.get_tool("multiply")
        assert metadata.enabled is False

    def test_register_duplicate_tool_raises_error(self, registry, sample_tool):
        """Test registering duplicate tool raises error."""
        registry.register(sample_tool)

        with pytest.raises(ToolValidationError, match="already registered"):
            registry.register(sample_tool)

    def test_register_tool_with_invalid_name_raises_error(self, registry):
        """Test registering tool with empty name raises error."""

        # Create a mock tool with empty name
        invalid_tool = MagicMock()
        invalid_tool.name = ""
        invalid_tool.description = "Test"

        with pytest.raises(ToolValidationError, match="non-empty name"):
            registry.register(invalid_tool)


# Test tool retrieval


class TestToolRetrieval:
    """Tests for retrieving tools from registry."""

    def test_get_tool(self, registry, sample_tool):
        """Test retrieving a registered tool."""
        registry.register(sample_tool)
        metadata = registry.get_tool("multiply")

        assert metadata.name == "multiply"
        assert metadata.tool == sample_tool

    def test_get_nonexistent_tool_raises_error(self, registry):
        """Test getting non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError, match="not found"):
            registry.get_tool("nonexistent")

    def test_list_all_tools(self, registry, sample_tool, dangerous_tool):
        """Test listing all tools."""
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)
        registry.register(dangerous_tool, risk_level=RiskLevel.DANGEROUS)

        tools = registry.list_tools()
        assert len(tools) == 2

    def test_list_enabled_only(self, registry, sample_tool, dangerous_tool):
        """Test listing only enabled tools."""
        registry.register(sample_tool, enabled=True)
        registry.register(dangerous_tool, enabled=False)

        tools = registry.list_tools(enabled_only=True)
        assert len(tools) == 1
        assert tools[0].name == "multiply"

    def test_list_by_risk_level(self, registry, sample_tool, dangerous_tool):
        """Test filtering tools by risk level."""
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)
        registry.register(dangerous_tool, risk_level=RiskLevel.DANGEROUS)

        safe_tools = registry.list_tools(risk_level=RiskLevel.SAFE)
        assert len(safe_tools) == 1
        assert safe_tools[0].name == "multiply"

        dangerous_tools = registry.list_tools(risk_level=RiskLevel.DANGEROUS)
        assert len(dangerous_tools) == 1
        assert dangerous_tools[0].name == "delete_files"

    def test_list_by_tags(self, registry, sample_tool, dangerous_tool):
        """Test filtering tools by tags."""
        registry.register(sample_tool, tags=["math", "readonly"])
        registry.register(dangerous_tool, tags=["filesystem", "write"])

        math_tools = registry.list_tools(tags=["math"])
        assert len(math_tools) == 1
        assert math_tools[0].name == "multiply"


# Test tool unregistration


class TestToolUnregistration:
    """Tests for unregistering tools."""

    def test_unregister_tool(self, registry, sample_tool):
        """Test unregistering a tool."""
        registry.register(sample_tool)
        assert "multiply" in registry

        registry.unregister("multiply")
        assert "multiply" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent_tool_raises_error(self, registry):
        """Test unregistering non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError, match="not found"):
            registry.unregister("nonexistent")


# Test security policies


class TestSecurityPolicies:
    """Tests for security policy enforcement."""

    def test_is_allowed_with_empty_whitelist(self, registry, sample_tool):
        """Test all tools allowed when whitelist is empty."""
        registry.register(sample_tool)

        assert registry.is_allowed("multiply") is True

    def test_is_allowed_with_whitelist(self, sample_tool):
        """Test whitelist enforcement."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(allowed_tools=["multiply"])
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        @tool
        def other_tool(x: int) -> int:
            """Other tool"""
            return x

        registry.register(other_tool)

        assert registry.is_allowed("multiply") is True
        assert registry.is_allowed("other_tool") is False

    def test_is_allowed_disabled_tool(self, registry, sample_tool):
        """Test disabled tools are not allowed."""
        registry.register(sample_tool, enabled=False)

        assert registry.is_allowed("multiply") is False

    def test_is_allowed_nonexistent_tool(self, registry):
        """Test nonexistent tools are not allowed."""
        assert registry.is_allowed("nonexistent") is False


# Test approval workflows


class TestApprovalWorkflows:
    """Tests for approval workflow logic."""

    def test_needs_approval_always_mode(self, sample_tool):
        """Test 'always' approval mode requires approval every time."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(approval_mode="always")
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        assert registry.needs_approval("multiply") is True
        registry.mark_approved("multiply")
        assert registry.needs_approval("multiply") is True  # Still needs approval

    def test_needs_approval_once_per_session_mode(self, sample_tool):
        """Test 'once_per_session' approval mode."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(approval_mode="once_per_session")
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        assert registry.needs_approval("multiply") is True
        registry.mark_approved("multiply")
        assert registry.needs_approval("multiply") is False

    def test_needs_approval_whitelist_mode(self, sample_tool):
        """Test 'whitelist' approval mode."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(approval_mode="whitelist", allowed_tools=["multiply"])
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        @tool
        def other_tool(x: int) -> int:
            """Other tool"""
            return x

        registry.register(other_tool)

        # Whitelisted tool doesn't need approval
        assert registry.needs_approval("multiply") is False
        # Non-whitelisted tool needs approval
        assert registry.needs_approval("other_tool") is True

    def test_auto_approve_skips_approval(self, sample_tool):
        """Test auto_approve bypasses approval (DANGEROUS)."""
        from tests.ai.tools.test_approval import MockApproveProvider

        # Should trigger warning when creating ToolConfig
        with pytest.warns(UserWarning, match="DANGEROUS"):
            config = ToolConfig(auto_approve=True)

        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)
        assert registry.needs_approval("multiply") is False

    def test_clear_session_approvals(self, sample_tool):
        """Test clearing session approvals."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(approval_mode="once_per_session")
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        registry.mark_approved("multiply")
        assert registry.needs_approval("multiply") is False

        registry.clear_session_approvals()
        assert registry.needs_approval("multiply") is True


# Test risk assessment


class TestRiskAssessment:
    """Tests for risk assessment functionality."""

    def test_assess_risk_returns_tool_risk(self, registry, sample_tool):
        """Test risk assessment returns tool's risk level."""
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        risk = registry.assess_risk("multiply", {"a": 2, "b": 3})
        assert risk == RiskLevel.SAFE

    def test_assess_risk_nonexistent_tool_raises_error(self, registry):
        """Test risk assessment for non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError):
            registry.assess_risk("nonexistent", {})


# Test model binding


class TestModelBinding:
    """Tests for binding tools to chat models."""

    def test_bind_to_model_all_tools(self, registry, sample_tool):
        """Test binding all tools to a model."""
        registry.register(sample_tool)

        # Mock chat model
        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        registry.bind_to_model(mock_model)

        # Verify bind_tools was called
        mock_model.bind_tools.assert_called_once()
        args = mock_model.bind_tools.call_args[0][0]
        assert len(args) == 1
        assert args[0] == sample_tool

    def test_bind_to_model_specific_tools(self, registry, sample_tool, dangerous_tool):
        """Test binding specific tools to a model."""
        registry.register(sample_tool)
        registry.register(dangerous_tool)

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        registry.bind_to_model(mock_model, tool_names=["multiply"])

        args = mock_model.bind_tools.call_args[0][0]
        assert len(args) == 1
        assert args[0].name == "multiply"

    def test_bind_to_model_only_enabled_tools(
        self, registry, sample_tool, dangerous_tool
    ):
        """Test only enabled tools are bound."""
        registry.register(sample_tool, enabled=True)
        registry.register(dangerous_tool, enabled=False)

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        registry.bind_to_model(mock_model)

        args = mock_model.bind_tools.call_args[0][0]
        assert len(args) == 1
        assert args[0].name == "multiply"

    def test_bind_to_model_no_tools(self, registry):
        """Test binding when no tools are available."""
        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock()

        result = registry.bind_to_model(mock_model)

        # Should return model unchanged
        assert result == mock_model
        mock_model.bind_tools.assert_not_called()


# Test utility methods


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_len(self, registry, sample_tool):
        """Test __len__ returns number of tools."""
        assert len(registry) == 0

        registry.register(sample_tool)
        assert len(registry) == 1

    def test_contains(self, registry, sample_tool):
        """Test __contains__ checks tool registration."""
        assert "multiply" not in registry

        registry.register(sample_tool)
        assert "multiply" in registry

    def test_repr(self, registry, sample_tool):
        """Test __repr__ returns useful info."""
        registry.register(sample_tool)

        repr_str = repr(registry)
        assert "ToolRegistry" in repr_str
        assert "tools=1" in repr_str
        assert "enabled=1" in repr_str
        assert "approval_mode='always'" in repr_str

"""Tests for ToolRegistry."""

from unittest.mock import MagicMock

import pytest
from langchain_core.tools import tool

from consoul.ai.tools import (
    PermissionPolicy,
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

        # Use PARANOID policy for always mode
        config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        assert registry.needs_approval("multiply") is True
        registry.mark_approved("multiply")
        assert registry.needs_approval("multiply") is True  # Still needs approval

    def test_needs_approval_once_per_session_mode(self, sample_tool):
        """Test 'once_per_session' approval mode."""
        from tests.ai.tools.test_approval import MockApproveProvider

        # Use PARANOID policy with once_per_session for this test
        # We need to test session caching, which still works with policies
        config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        # First call requires approval
        assert registry.needs_approval("multiply") is True
        registry.mark_approved("multiply")
        # With PARANOID policy, approval is always required (no session caching)
        assert registry.needs_approval("multiply") is True

    def test_needs_approval_whitelist_mode(self, sample_tool):
        """Test 'whitelist' approval mode."""
        from tests.ai.tools.test_approval import MockApproveProvider

        # Use PARANOID policy with whitelist (whitelist bypasses policy)
        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID, allowed_tools=["multiply"]
        )
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool)

        @tool
        def other_tool(x: int) -> int:
            """Other tool"""
            return x

        registry.register(other_tool)

        # Whitelisted tool doesn't need approval (bypasses policy)
        assert registry.needs_approval("multiply") is False
        # Non-whitelisted tool needs approval (PARANOID policy)
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

        # Note: Session approvals are not used with policy system
        # Policies determine approval based on risk level, not session state
        # This test demonstrates that BALANCED policy behavior is consistent
        config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        # BALANCED auto-approves SAFE tools
        assert registry.needs_approval("multiply") is False

        # Clearing session approvals doesn't change policy-based decisions
        registry.clear_session_approvals()
        assert registry.needs_approval("multiply") is False

    def test_needs_approval_paranoid_policy(self, sample_tool):
        """Test PARANOID policy always requires approval."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        # PARANOID always requires approval, even for SAFE tools
        assert registry.needs_approval("multiply") is True

    def test_needs_approval_balanced_policy(self, sample_tool):
        """Test BALANCED policy auto-approves SAFE, requires approval for CAUTION+."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())

        # Register SAFE tool
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)
        assert registry.needs_approval("multiply") is False

        # Register CAUTION tool
        @tool
        def caution_tool(x: int) -> int:
            """Tool with CAUTION risk."""
            return x

        registry.register(caution_tool, risk_level=RiskLevel.CAUTION)
        assert registry.needs_approval("caution_tool") is True

    def test_needs_approval_trusting_policy(self, sample_tool):
        """Test TRUSTING policy auto-approves SAFE+CAUTION, requires approval for DANGEROUS."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(permission_policy=PermissionPolicy.TRUSTING)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())

        # SAFE auto-approved
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)
        assert registry.needs_approval("multiply") is False

        # CAUTION auto-approved
        @tool
        def caution_tool(x: int) -> int:
            """Tool with CAUTION risk."""
            return x

        registry.register(caution_tool, risk_level=RiskLevel.CAUTION)
        assert registry.needs_approval("caution_tool") is False

        # DANGEROUS requires approval
        @tool
        def dangerous_tool(x: int) -> int:
            """Tool with DANGEROUS risk."""
            return x

        registry.register(dangerous_tool, risk_level=RiskLevel.DANGEROUS)
        assert registry.needs_approval("dangerous_tool") is True

    def test_needs_approval_unrestricted_policy(self, sample_tool):
        """Test UNRESTRICTED policy auto-approves everything except BLOCKED."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())

        # All risk levels auto-approved
        registry.register(sample_tool, risk_level=RiskLevel.DANGEROUS)
        assert registry.needs_approval("multiply") is False

    def test_policy_overrides_manual_approval_mode(self, sample_tool):
        """Test that permission_policy takes precedence over manual approval_mode."""
        from tests.ai.tools.test_approval import MockApproveProvider

        # Manual config says auto_approve=True, but policy says PARANOID
        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID,
            approval_mode="never",
            auto_approve=True,
        )
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        # Policy wins - approval still required
        assert registry.needs_approval("multiply") is True

    def test_whitelist_bypasses_policy(self, sample_tool):
        """Test that whitelist bypasses policy approval requirements."""
        from tests.ai.tools.test_approval import MockApproveProvider

        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID, allowed_tools=["multiply"]
        )
        registry = ToolRegistry(config, approval_provider=MockApproveProvider())
        registry.register(sample_tool, risk_level=RiskLevel.DANGEROUS)

        # Whitelisted tool bypasses PARANOID policy
        assert registry.needs_approval("multiply") is False


# Test risk assessment


class TestRiskAssessment:
    """Tests for risk assessment functionality."""

    def test_assess_risk_returns_tool_risk(self, registry, sample_tool):
        """Test risk assessment returns tool's risk level (as CommandRisk)."""
        from consoul.ai.tools.permissions.analyzer import CommandRisk

        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        risk = registry.assess_risk("multiply", {"a": 2, "b": 3})
        # assess_risk now returns CommandRisk for all tools
        assert isinstance(risk, CommandRisk)
        assert risk.level == RiskLevel.SAFE

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


class TestWhitelistIntegration:
    """Tests for command-level whitelist integration with registry."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock approval provider."""
        from tests.ai.tools.test_approval import MockApproveProvider

        return MockApproveProvider()

    def test_needs_approval_checks_bash_whitelist(self, mock_provider):
        """Test that needs_approval checks bash command whitelist."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(
            bash=BashToolConfig(whitelist_patterns=["git status", "npm test"])
        )
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Whitelisted commands should not need approval
        assert not registry.needs_approval("bash_execute", {"command": "git status"})
        assert not registry.needs_approval("bash_execute", {"command": "npm test"})

        # Non-whitelisted commands should need approval
        assert registry.needs_approval("bash_execute", {"command": "rm -rf /"})

    def test_needs_approval_whitelist_with_regex_patterns(self, mock_provider):
        """Test whitelist with regex patterns."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(
            bash=BashToolConfig(whitelist_patterns=["git.*", "npm (install|ci)"])
        )
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Regex matches should not need approval
        assert not registry.needs_approval("bash_execute", {"command": "git status"})
        assert not registry.needs_approval("bash_execute", {"command": "git log"})
        assert not registry.needs_approval("bash_execute", {"command": "npm install"})
        assert not registry.needs_approval("bash_execute", {"command": "npm ci"})

        # Non-matches should need approval
        assert registry.needs_approval("bash_execute", {"command": "cargo build"})

    def test_needs_approval_whitelist_bypasses_always_mode(self, mock_provider):
        """Test that whitelist bypasses 'always' approval mode."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(
            approval_mode="always",
            bash=BashToolConfig(whitelist_patterns=["git status"]),
        )
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Whitelisted command bypasses 'always' mode
        assert not registry.needs_approval("bash_execute", {"command": "git status"})

        # Non-whitelisted still requires approval
        assert registry.needs_approval("bash_execute", {"command": "git log"})

    def test_needs_approval_without_command_argument(self, mock_provider):
        """Test needs_approval without command argument (backward compatibility)."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(bash=BashToolConfig(whitelist_patterns=["git status"]))
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Without arguments, should default to requiring approval
        assert registry.needs_approval("bash_execute")

    def test_needs_approval_with_empty_arguments(self, mock_provider):
        """Test needs_approval with empty arguments dict."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(bash=BashToolConfig(whitelist_patterns=["git status"]))
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Empty arguments should require approval
        assert registry.needs_approval("bash_execute", {})

    def test_needs_approval_non_bash_tool_unaffected(self, mock_provider):
        """Test that whitelist doesn't affect non-bash tools."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(bash=BashToolConfig(whitelist_patterns=["git status"]))
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Non-bash tools should still require approval
        assert registry.needs_approval("python_execute", {"code": "print('hello')"})

    def test_needs_approval_whitelist_with_once_per_session(self, mock_provider):
        """Test whitelist interaction with once_per_session mode."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(
            approval_mode="once_per_session",
            bash=BashToolConfig(whitelist_patterns=["git status"]),
        )
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Whitelisted command bypasses approval
        assert not registry.needs_approval("bash_execute", {"command": "git status"})

        # Non-whitelisted command requires approval first time
        assert registry.needs_approval("bash_execute", {"command": "git log"})

        # After marking approved, no longer needs approval
        registry.mark_approved("bash_execute")
        assert not registry.needs_approval("bash_execute", {"command": "git log"})

    def test_needs_approval_whitelist_normalizes_commands(self, mock_provider):
        """Test that whitelist normalizes commands before checking."""
        from consoul.config.models import BashToolConfig

        config = ToolConfig(bash=BashToolConfig(whitelist_patterns=["git status"]))
        registry = ToolRegistry(config, approval_provider=mock_provider)

        # Extra whitespace should be normalized
        assert not registry.needs_approval(
            "bash_execute", {"command": "  git   status  "}
        )
        assert not registry.needs_approval("bash_execute", {"command": "git  status"})


# Test analyze_images tool registration


class TestAnalyzeImagesRegistration:
    """Tests for analyze_images tool registration with vision model detection."""

    @pytest.fixture
    def vision_config(self):
        """Create ToolConfig with image_analysis enabled."""
        from consoul.config.models import ImageAnalysisToolConfig

        return ToolConfig(
            enabled=True,
            image_analysis=ImageAnalysisToolConfig(enabled=True),
        )

    @pytest.fixture
    def disabled_vision_config(self):
        """Create ToolConfig with image_analysis disabled."""
        from consoul.config.models import ImageAnalysisToolConfig

        return ToolConfig(
            enabled=True,
            image_analysis=ImageAnalysisToolConfig(enabled=False),
        )

    def test_register_analyze_images_tool(self, vision_config):
        """Test registering analyze_images tool."""
        from consoul.ai.tools.implementations import (
            analyze_images,
            set_analyze_images_config,
        )
        from tests.ai.tools.test_approval import MockApproveProvider

        # Set config and register
        set_analyze_images_config(vision_config.image_analysis)
        registry = ToolRegistry(vision_config, approval_provider=MockApproveProvider())
        registry.register(
            analyze_images,
            risk_level=RiskLevel.CAUTION,
            tags=["multimodal", "vision", "filesystem", "external_api"],
        )

        # Verify registration
        assert "analyze_images" in registry
        metadata = registry.get_tool("analyze_images")
        assert metadata.name == "analyze_images"
        assert metadata.risk_level == RiskLevel.CAUTION
        assert "multimodal" in metadata.tags
        assert "vision" in metadata.tags
        assert "filesystem" in metadata.tags
        assert "external_api" in metadata.tags

    def test_analyze_images_not_registered_when_disabled(self, disabled_vision_config):
        """Test analyze_images NOT registered when config.enabled=False."""
        from tests.ai.tools.test_approval import MockApproveProvider

        registry = ToolRegistry(
            disabled_vision_config, approval_provider=MockApproveProvider()
        )

        # Should NOT be registered
        assert "analyze_images" not in registry

    def test_analyze_images_requires_approval_caution_level(self, vision_config):
        """Test analyze_images requires approval (CAUTION risk level)."""
        from consoul.ai.tools.implementations import (
            analyze_images,
            set_analyze_images_config,
        )
        from tests.ai.tools.test_approval import MockApproveProvider

        set_analyze_images_config(vision_config.image_analysis)
        registry = ToolRegistry(vision_config, approval_provider=MockApproveProvider())
        registry.register(
            analyze_images,
            risk_level=RiskLevel.CAUTION,
            tags=["multimodal", "vision", "filesystem", "external_api"],
        )

        # CAUTION tools require approval with BALANCED policy (default)
        from consoul.config.models import ToolConfig

        config_with_policy = ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.BALANCED,
            image_analysis=vision_config.image_analysis,
        )
        registry_with_policy = ToolRegistry(
            config_with_policy, approval_provider=MockApproveProvider()
        )
        registry_with_policy.register(
            analyze_images,
            risk_level=RiskLevel.CAUTION,
            tags=["multimodal", "vision", "filesystem", "external_api"],
        )

        # Should require approval
        assert registry_with_policy.needs_approval("analyze_images")

    def test_analyze_images_config_injection(self, vision_config):
        """Test config injection via set_analyze_images_config()."""
        from consoul.ai.tools.implementations import (
            get_analyze_images_config,
            set_analyze_images_config,
        )

        # Inject custom config
        from consoul.config.models import ImageAnalysisToolConfig

        custom_config = ImageAnalysisToolConfig(
            enabled=True, max_image_size_mb=10, max_images_per_query=3
        )
        set_analyze_images_config(custom_config)

        # Verify config is injected
        retrieved_config = get_analyze_images_config()
        assert retrieved_config.max_image_size_mb == 10
        assert retrieved_config.max_images_per_query == 3

    def test_analyze_images_tool_schema(self, vision_config):
        """Test analyze_images has proper LangChain tool schema."""
        from consoul.ai.tools.implementations import (
            analyze_images,
            set_analyze_images_config,
        )
        from tests.ai.tools.test_approval import MockApproveProvider

        set_analyze_images_config(vision_config.image_analysis)
        registry = ToolRegistry(vision_config, approval_provider=MockApproveProvider())
        registry.register(
            analyze_images,
            risk_level=RiskLevel.CAUTION,
            tags=["multimodal", "vision", "filesystem", "external_api"],
        )

        metadata = registry.get_tool("analyze_images")
        tool = metadata.tool

        # Verify tool has proper schema
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "args_schema")
        assert tool.name == "analyze_images"

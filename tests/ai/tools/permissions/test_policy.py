"""Tests for permission policy system.

Tests PolicyResolver, PolicySettings, and PermissionPolicy integration
with ToolConfig and needs_approval() logic.
"""

import warnings

from consoul.ai.tools.base import RiskLevel
from consoul.ai.tools.permissions.policy import (
    PermissionPolicy,
    PolicyResolver,
    PolicySettings,
)
from consoul.config.models import BashToolConfig, ToolConfig


class TestPermissionPolicy:
    """Test PermissionPolicy enum values."""

    def test_policy_values(self):
        """Test that policy enum has expected values."""
        assert PermissionPolicy.PARANOID.value == "paranoid"
        assert PermissionPolicy.BALANCED.value == "balanced"
        assert PermissionPolicy.TRUSTING.value == "trusting"
        assert PermissionPolicy.UNRESTRICTED.value == "unrestricted"

    def test_policy_string_comparison(self):
        """Test that policies can be compared as strings."""
        assert PermissionPolicy.BALANCED == "balanced"
        assert PermissionPolicy.PARANOID != "balanced"


class TestPolicySettings:
    """Test PolicySettings dataclass."""

    def test_policy_settings_creation(self):
        """Test creating PolicySettings instance."""
        settings = PolicySettings(
            approval_mode="risk_based",
            auto_approve=False,
            risk_threshold=RiskLevel.SAFE,
            description="Test policy",
        )
        assert settings.approval_mode == "risk_based"
        assert settings.auto_approve is False
        assert settings.risk_threshold == RiskLevel.SAFE
        assert settings.description == "Test policy"


class TestPolicyResolver:
    """Test PolicyResolver behavior."""

    def test_paranoid_policy_settings(self):
        """Test PARANOID policy resolves to always require approval."""
        config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        assert settings.approval_mode == "always"
        assert settings.auto_approve is False
        assert settings.risk_threshold == RiskLevel.SAFE
        assert "Maximum security" in settings.description

    def test_balanced_policy_settings(self):
        """Test BALANCED policy resolves to risk-based with SAFE threshold."""
        config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        assert settings.approval_mode == "risk_based"
        assert settings.auto_approve is False
        assert settings.risk_threshold == RiskLevel.SAFE
        assert "Recommended default" in settings.description

    def test_trusting_policy_settings(self):
        """Test TRUSTING policy resolves to risk-based with CAUTION threshold."""
        config = ToolConfig(permission_policy=PermissionPolicy.TRUSTING)
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        assert settings.approval_mode == "risk_based"
        assert settings.auto_approve is False
        assert settings.risk_threshold == RiskLevel.CAUTION
        assert "Convenience-focused" in settings.description

    def test_unrestricted_policy_settings(self):
        """Test UNRESTRICTED policy resolves to never require approval."""
        config = ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        assert settings.approval_mode == "never"
        assert settings.auto_approve is True
        assert settings.risk_threshold == RiskLevel.DANGEROUS
        assert "DANGEROUS" in settings.description

    def test_default_policy_is_balanced(self):
        """Test that default ToolConfig uses BALANCED policy."""
        # When permission_policy is not specified, validator sets it to BALANCED
        config = ToolConfig()
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        assert config.permission_policy == PermissionPolicy.BALANCED
        assert settings.approval_mode == "risk_based"
        assert settings.auto_approve is False
        assert settings.risk_threshold == RiskLevel.SAFE
        assert "Recommended default" in settings.description

    def test_should_require_approval_paranoid(self):
        """Test PARANOID policy always requires approval."""
        config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
        resolver = PolicyResolver(config)

        # All risk levels require approval in PARANOID mode
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is True
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is True
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is True

    def test_should_require_approval_balanced(self):
        """Test BALANCED policy auto-approves SAFE, requires approval for CAUTION+."""
        config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        resolver = PolicyResolver(config)

        # SAFE auto-approved, CAUTION+ require approval
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is True
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is True

    def test_should_require_approval_trusting(self):
        """Test TRUSTING policy auto-approves SAFE+CAUTION, requires approval for DANGEROUS+."""
        config = ToolConfig(permission_policy=PermissionPolicy.TRUSTING)
        resolver = PolicyResolver(config)

        # SAFE+CAUTION auto-approved, DANGEROUS+ require approval
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is False
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is True

    def test_should_require_approval_unrestricted(self):
        """Test UNRESTRICTED policy auto-approves everything except BLOCKED."""
        config = ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)
        resolver = PolicyResolver(config)

        # Everything auto-approved except BLOCKED
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is False
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is False
        assert resolver.should_require_approval("bash", RiskLevel.BLOCKED) is True

    def test_should_require_approval_blocked_always_requires(self):
        """Test BLOCKED commands always require approval regardless of policy."""
        for policy in PermissionPolicy:
            config = ToolConfig(permission_policy=policy)
            resolver = PolicyResolver(config)
            assert resolver.should_require_approval("bash", RiskLevel.BLOCKED) is True

    def test_whitelist_bypasses_policy(self):
        """Test that whitelisted tools bypass policy approval requirements."""
        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID,
            allowed_tools=["bash_execute"],
        )
        resolver = PolicyResolver(config)

        # Whitelisted tool bypasses PARANOID policy
        assert resolver.should_require_approval("bash_execute", RiskLevel.SAFE) is False

    def test_bash_whitelist_bypasses_policy(self):
        """Test that whitelisted bash commands bypass policy requirements."""
        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID,
            bash=BashToolConfig(whitelist_patterns=["git status"]),
        )
        resolver = PolicyResolver(config)

        # Whitelisted command bypasses policy
        assert (
            resolver.should_require_approval(
                "bash_execute", RiskLevel.DANGEROUS, {"command": "git status"}
            )
            is False
        )

    def test_validate_policy_paranoid_safe(self):
        """Test PARANOID policy validation produces no warnings."""
        config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
        resolver = PolicyResolver(config)
        warnings_list = resolver.validate_policy()

        assert len(warnings_list) == 0

    def test_validate_policy_balanced_safe(self):
        """Test BALANCED policy validation produces no warnings."""
        config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        resolver = PolicyResolver(config)
        warnings_list = resolver.validate_policy()

        assert len(warnings_list) == 0

    def test_validate_policy_trusting_safe(self):
        """Test TRUSTING policy validation produces no warnings."""
        config = ToolConfig(permission_policy=PermissionPolicy.TRUSTING)
        resolver = PolicyResolver(config)
        warnings_list = resolver.validate_policy()

        assert len(warnings_list) == 0

    def test_validate_policy_unrestricted_dangerous(self):
        """Test UNRESTRICTED policy validation produces warnings."""
        config = ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)
        resolver = PolicyResolver(config)
        warnings_list = resolver.validate_policy()

        assert len(warnings_list) > 0
        assert any("UNRESTRICTED" in w for w in warnings_list)
        assert any("DANGEROUS" in w for w in warnings_list)

    def test_validate_policy_auto_approve_with_policy(self):
        """Test that auto_approve field is ignored when policy is set."""
        # Even with auto_approve=True, policy settings take precedence
        config = ToolConfig(
            permission_policy=PermissionPolicy.BALANCED, auto_approve=True
        )
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        # Policy overrides manual auto_approve setting
        assert settings.auto_approve is False
        assert settings.approval_mode == "risk_based"


class TestToolConfigValidation:
    """Test ToolConfig validation for permission policies."""

    def test_unrestricted_policy_warning(self):
        """Test that UNRESTRICTED policy triggers a warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)

            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "UNRESTRICTED" in str(w[0].message)
            assert "DANGEROUS" in str(w[0].message)

    def test_balanced_policy_no_warning(self):
        """Test that BALANCED policy does not trigger warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ToolConfig(permission_policy=PermissionPolicy.BALANCED)

            assert len(w) == 0

    def test_paranoid_policy_no_warning(self):
        """Test that PARANOID policy does not trigger warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ToolConfig(permission_policy=PermissionPolicy.PARANOID)

            assert len(w) == 0


class TestPolicyIntegration:
    """Test policy integration scenarios."""

    def test_policy_overrides_manual_approval_mode(self):
        """Test that permission_policy takes precedence over manual approval_mode."""
        # Manual config says "never", but policy says "always"
        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID,
            approval_mode="never",
            auto_approve=True,
        )
        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        # Policy wins
        assert settings.approval_mode == "always"
        assert settings.auto_approve is False

    def test_risk_based_mode_risk_comparison(self):
        """Test risk-based mode correctly compares risk levels."""
        config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        resolver = PolicyResolver(config)

        # BALANCED has risk_threshold=SAFE (0)
        # Risk values: SAFE=0, CAUTION=1, DANGEROUS=2, BLOCKED=3
        assert (
            resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        )  # 0 <= 0
        assert (
            resolver.should_require_approval("bash", RiskLevel.CAUTION) is True
        )  # 1 > 0
        assert (
            resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is True
        )  # 2 > 0

    def test_default_config_uses_balanced(self):
        """Test that default ToolConfig uses BALANCED policy."""
        config = ToolConfig()
        assert config.permission_policy == PermissionPolicy.BALANCED

        resolver = PolicyResolver(config)
        settings = resolver.get_effective_settings()

        assert settings.approval_mode == "risk_based"
        assert settings.risk_threshold == RiskLevel.SAFE
        assert "Recommended default" in settings.description

    def test_whitelist_highest_priority(self):
        """Test that whitelist has highest priority over all policies."""
        # PARANOID policy + whitelisted tool = auto-approved
        config = ToolConfig(
            permission_policy=PermissionPolicy.PARANOID,
            allowed_tools=["bash_execute"],
        )
        resolver = PolicyResolver(config)

        # Even DANGEROUS commands are auto-approved if whitelisted
        assert (
            resolver.should_require_approval("bash_execute", RiskLevel.DANGEROUS)
            is False
        )

    def test_blocked_overrides_whitelist(self):
        """Test that BLOCKED commands cannot be bypassed by whitelist."""
        config = ToolConfig(
            permission_policy=PermissionPolicy.UNRESTRICTED,
            allowed_tools=["bash_execute"],
        )
        resolver = PolicyResolver(config)

        # BLOCKED always requires approval (actually blocked)
        # Note: In practice, BLOCKED commands would be rejected, not approved
        assert (
            resolver.should_require_approval("bash_execute", RiskLevel.BLOCKED) is True
        )


class TestPolicyUsageExamples:
    """Test policy system through realistic usage scenarios."""

    def test_production_environment_setup(self):
        """Test recommended production environment configuration."""
        config = ToolConfig(
            permission_policy=PermissionPolicy.BALANCED,
            bash=BashToolConfig(
                whitelist_patterns=[
                    "git status",
                    "git log",
                    "ls",
                    "cat",
                ]
            ),
        )
        resolver = PolicyResolver(config)

        # SAFE commands auto-approved
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False

        # CAUTION+ require approval
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is True

        # Whitelisted commands bypass policy
        assert (
            resolver.should_require_approval(
                "bash_execute", RiskLevel.SAFE, {"command": "git status"}
            )
            is False
        )

    def test_development_environment_setup(self):
        """Test convenient development environment configuration."""
        config = ToolConfig(permission_policy=PermissionPolicy.TRUSTING)
        resolver = PolicyResolver(config)

        # SAFE+CAUTION auto-approved for convenience
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is False

        # DANGEROUS still requires approval
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is True

    def test_testing_environment_setup(self):
        """Test unrestricted testing environment (CI/CD)."""
        config = ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)
        resolver = PolicyResolver(config)

        # Everything auto-approved (except BLOCKED)
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is False
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is False

    def test_policy_system_defaults(self):
        """Test that default ToolConfig has sensible policy defaults."""
        # Default config should use BALANCED policy
        config = ToolConfig()
        resolver = PolicyResolver(config)

        # Default is BALANCED policy
        assert config.permission_policy == PermissionPolicy.BALANCED

        # BALANCED auto-approves SAFE, requires approval for CAUTION+
        assert resolver.should_require_approval("bash", RiskLevel.SAFE) is False
        assert resolver.should_require_approval("bash", RiskLevel.CAUTION) is True
        assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS) is True

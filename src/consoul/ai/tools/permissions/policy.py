"""Permission policy system for tool execution.

Provides predefined permission policies (PARANOID/BALANCED/TRUSTING/UNRESTRICTED)
that combine approval behavior, risk-based decisions, and whitelist management
into cohesive, user-friendly security configurations.

Example:
    >>> from consoul.ai.tools.permissions import PermissionPolicy, PolicyResolver
    >>> from consoul.config.models import ToolConfig
    >>>
    >>> # Use predefined policy
    >>> config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
    >>> resolver = PolicyResolver(config)
    >>> settings = resolver.get_effective_settings()
    >>> assert settings.approval_mode == "risk_based"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.ai.tools.base import RiskLevel
    from consoul.config.models import ToolConfig

__all__ = ["PermissionPolicy", "PolicyResolver", "PolicySettings"]


class PermissionPolicy(str, Enum):
    """Predefined permission policies for tool execution.

    Each policy defines a security posture that combines approval behavior,
    risk thresholds, and auto-approval settings into a cohesive configuration.

    Policy Comparison:
        ┌──────────────┬──────┬─────────┬───────────┬─────────┬──────────────────┐
        │ Policy       │ SAFE │ CAUTION │ DANGEROUS │ BLOCKED │ Use Case         │
        ├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
        │ PARANOID     │ ⚠️   │ ⚠️      │ ⚠️        │ ❌      │ Production, max  │
        │              │      │         │           │         │ security         │
        ├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
        │ BALANCED ⭐  │ ✅   │ ⚠️      │ ⚠️        │ ❌      │ Recommended      │
        │              │      │         │           │         │ default          │
        ├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
        │ TRUSTING     │ ✅   │ ✅      │ ⚠️        │ ❌      │ Development,     │
        │              │      │         │           │         │ convenience      │
        ├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
        │ UNRESTRICTED │ ✅   │ ✅      │ ✅        │ ❌      │ Testing only,    │
        │              │      │         │           │         │ DANGEROUS        │
        └──────────────┴──────┴─────────┴───────────┴─────────┴──────────────────┘

        Legend: ✅ Auto-approve  ⚠️ Require approval  ❌ Always blocked

    Attributes:
        PARANOID: Maximum security - approve every command individually
        BALANCED: Recommended default - auto-approve SAFE, prompt for CAUTION+
        TRUSTING: Convenience-focused - auto-approve SAFE+CAUTION, prompt DANGEROUS+
        UNRESTRICTED: Minimal restrictions - auto-approve all except BLOCKED (DANGEROUS)

    Example:
        >>> policy = PermissionPolicy.BALANCED
        >>> print(policy.value)
        'balanced'
    """

    PARANOID = "paranoid"
    BALANCED = "balanced"
    TRUSTING = "trusting"
    UNRESTRICTED = "unrestricted"


@dataclass
class PolicySettings:
    """Resolved policy settings for tool execution approval.

    Represents the effective configuration derived from a permission policy,
    combining approval mode, risk thresholds, and auto-approval behavior.

    Attributes:
        approval_mode: When to request approval ('always', 'risk_based', 'once_per_session', 'never')
        auto_approve: Whether to auto-approve tools without prompting (DANGEROUS)
        risk_threshold: Maximum risk level that can be auto-approved (if mode supports it)
        description: Human-readable description of the policy behavior

    Example:
        >>> from consoul.ai.tools.base import RiskLevel
        >>> settings = PolicySettings(
        ...     approval_mode="risk_based",
        ...     auto_approve=False,
        ...     risk_threshold=RiskLevel.SAFE,
        ...     description="Auto-approve SAFE commands only"
        ... )
    """

    approval_mode: str
    auto_approve: bool
    risk_threshold: RiskLevel
    description: str


class PolicyResolver:
    """Resolves permission policies into effective approval settings.

    Combines policy presets with whitelist patterns and per-tool overrides
    to determine the final approval behavior for tool execution.

    Priority Order (highest to lowest):
        1. Blocklist (BLOCKED commands never approved)
        2. Whitelist (explicit user trust bypasses policy)
        3. Policy (preset behavior)
        4. Manual settings (backward compatibility)

    Example:
        >>> from consoul.config.models import ToolConfig
        >>> config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
        >>> resolver = PolicyResolver(config)
        >>> settings = resolver.get_effective_settings()
        >>> assert settings.approval_mode == "risk_based"
    """

    def __init__(self, config: ToolConfig) -> None:
        """Initialize policy resolver with tool configuration.

        Args:
            config: ToolConfig containing policy and approval settings
        """
        self.config = config

    def get_effective_settings(self) -> PolicySettings:
        """Get effective policy settings after resolving policy and overrides.

        Returns:
            PolicySettings with resolved approval configuration

        Example:
            >>> config = ToolConfig(permission_policy=PermissionPolicy.PARANOID)
            >>> resolver = PolicyResolver(config)
            >>> settings = resolver.get_effective_settings()
            >>> assert settings.approval_mode == "always"
        """
        # If no policy set, use manual settings (backward compatibility)
        if (
            not hasattr(self.config, "permission_policy")
            or self.config.permission_policy is None
        ):
            return self._settings_from_manual_config()

        # Get settings for the policy
        return self._settings_for_policy(self.config.permission_policy)

    def _settings_from_manual_config(self) -> PolicySettings:
        """Create PolicySettings from manual ToolConfig settings.

        Returns:
            PolicySettings derived from existing manual configuration

        Example:
            >>> config = ToolConfig(approval_mode="always", auto_approve=False)
            >>> resolver = PolicyResolver(config)
            >>> settings = resolver._settings_from_manual_config()
            >>> assert settings.approval_mode == "always"
        """
        from consoul.ai.tools.base import RiskLevel

        # Derive risk threshold from approval_mode
        # For manual configs, we treat anything beyond approval_mode as DANGEROUS threshold
        risk_threshold = RiskLevel.DANGEROUS

        return PolicySettings(
            approval_mode=self.config.approval_mode,
            auto_approve=self.config.auto_approve,
            risk_threshold=risk_threshold,
            description="Manual configuration (no policy set)",
        )

    def _settings_for_policy(self, policy: PermissionPolicy) -> PolicySettings:
        """Get PolicySettings for a specific permission policy.

        Args:
            policy: The PermissionPolicy to get settings for

        Returns:
            PolicySettings configured for the specified policy

        Example:
            >>> resolver = PolicyResolver(ToolConfig())
            >>> settings = resolver._settings_for_policy(PermissionPolicy.BALANCED)
            >>> assert settings.approval_mode == "risk_based"
        """
        from consoul.ai.tools.base import RiskLevel

        if policy == PermissionPolicy.PARANOID:
            return PolicySettings(
                approval_mode="always",
                auto_approve=False,
                risk_threshold=RiskLevel.SAFE,
                description="Approve every command individually. Maximum security.",
            )
        elif policy == PermissionPolicy.BALANCED:
            return PolicySettings(
                approval_mode="risk_based",
                auto_approve=False,
                risk_threshold=RiskLevel.SAFE,
                description="Auto-approve SAFE commands, prompt for CAUTION+. Recommended default.",
            )
        elif policy == PermissionPolicy.TRUSTING:
            return PolicySettings(
                approval_mode="risk_based",
                auto_approve=False,
                risk_threshold=RiskLevel.CAUTION,
                description="Auto-approve SAFE and CAUTION, prompt for DANGEROUS. Convenience-focused.",
            )
        elif policy == PermissionPolicy.UNRESTRICTED:
            return PolicySettings(
                approval_mode="never",
                auto_approve=True,
                risk_threshold=RiskLevel.DANGEROUS,
                description="Auto-approve everything except BLOCKED. DANGEROUS - testing only.",
            )
        else:
            # Fallback to BALANCED if unknown policy
            return self._settings_for_policy(PermissionPolicy.BALANCED)

    def validate_policy(self) -> list[str]:
        """Validate policy configuration and return warnings for dangerous settings.

        Returns:
            List of warning messages (empty if configuration is safe)

        Example:
            >>> config = ToolConfig(permission_policy=PermissionPolicy.UNRESTRICTED)
            >>> resolver = PolicyResolver(config)
            >>> warnings = resolver.validate_policy()
            >>> assert len(warnings) > 0
            >>> assert "UNRESTRICTED" in warnings[0]
        """
        warnings: list[str] = []

        # Check if policy is set
        if (
            not hasattr(self.config, "permission_policy")
            or self.config.permission_policy is None
        ):
            # Manual config - check for dangerous settings
            if self.config.auto_approve:
                warnings.append(
                    "auto_approve=True is DANGEROUS and disables user approval. "
                    "Consider using BALANCED or TRUSTING policy instead."
                )
            return warnings

        settings = self.get_effective_settings()

        # Warn about UNRESTRICTED policy
        if self.config.permission_policy == PermissionPolicy.UNRESTRICTED:
            warnings.append(
                "UNRESTRICTED policy is DANGEROUS and should ONLY be used in testing environments. "
                "All tool executions will be auto-approved without user confirmation."
            )

        # Warn if auto_approve is True (regardless of policy)
        if settings.auto_approve:
            warnings.append(
                f"Policy '{self.config.permission_policy.value}' enables auto_approve=True. "
                "Ensure this is intentional and appropriate for your environment."
            )

        return warnings

    def should_require_approval(
        self,
        tool_name: str,
        risk_level: RiskLevel,
        arguments: dict[str, Any] | None = None,
    ) -> bool:
        """Determine if tool execution requires approval based on policy.

        This method combines policy settings, risk assessment, and whitelist
        checking to make the final approval decision.

        Args:
            tool_name: Name of the tool being executed
            risk_level: Risk level from CommandAnalyzer or tool metadata
            arguments: Optional tool arguments (for whitelist checking)

        Returns:
            True if approval is required, False if auto-approved

        Example:
            >>> from consoul.ai.tools.base import RiskLevel
            >>> config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
            >>> resolver = PolicyResolver(config)
            >>> # SAFE command should be auto-approved
            >>> assert not resolver.should_require_approval("bash", RiskLevel.SAFE)
            >>> # DANGEROUS command should require approval
            >>> assert resolver.should_require_approval("bash", RiskLevel.DANGEROUS)
        """
        from consoul.ai.tools.base import RiskLevel

        # BLOCKED commands always require approval (actually blocked, not approved)
        if risk_level == RiskLevel.BLOCKED:
            return True

        # Check whitelist (bypasses policy)
        if self._is_whitelisted(tool_name, arguments):
            return False

        settings = self.get_effective_settings()

        # Handle 'never' mode (UNRESTRICTED policy)
        if settings.approval_mode == "never":
            return False  # Auto-approve everything (except BLOCKED above)

        # Handle 'always' mode (PARANOID policy)
        if settings.approval_mode == "always":
            return True  # Always require approval

        # Handle 'risk_based' mode (BALANCED and TRUSTING policies)
        if settings.approval_mode == "risk_based":
            # Compare risk levels: require approval if tool risk > threshold
            # SAFE=0, CAUTION=1, DANGEROUS=2, BLOCKED=3
            risk_values = {"safe": 0, "caution": 1, "dangerous": 2, "blocked": 3}
            tool_risk_value = risk_values.get(risk_level.value, 3)
            threshold_value = risk_values.get(settings.risk_threshold.value, 0)
            return tool_risk_value > threshold_value

        # For other modes (once_per_session, whitelist), require approval by default
        # These are handled by the registry's session caching logic
        return True

    def _is_whitelisted(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> bool:
        """Check if tool/command is whitelisted.

        Args:
            tool_name: Name of the tool
            arguments: Optional tool arguments

        Returns:
            True if whitelisted, False otherwise
        """
        # Check tool-level whitelist
        if self.config.allowed_tools and tool_name in self.config.allowed_tools:
            return True

        # Check bash command-level whitelist
        if tool_name == "bash_execute" and arguments and "command" in arguments:
            from consoul.ai.tools.implementations.bash import is_whitelisted

            return is_whitelisted(arguments["command"], self.config.bash)

        return False

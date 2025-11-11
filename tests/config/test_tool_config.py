"""Tests for ToolConfig in ConsoulConfig."""

import pytest

from consoul.config.models import ConsoulConfig, ProfileConfig, ToolConfig


class TestToolConfig:
    """Tests for ToolConfig model."""

    def test_default_tool_config(self):
        """Test ToolConfig defaults."""
        config = ToolConfig()

        assert config.enabled is True
        assert config.auto_approve is False
        assert config.allowed_tools == []
        assert config.approval_mode == "always"
        assert config.timeout == 30

    def test_tool_config_with_whitelist(self):
        """Test ToolConfig with allowed tools whitelist."""
        config = ToolConfig(
            enabled=True,
            allowed_tools=["bash", "python"],
            approval_mode="whitelist",
        )

        assert config.allowed_tools == ["bash", "python"]
        assert config.approval_mode == "whitelist"

    def test_tool_config_timeout_validation(self):
        """Test timeout must be positive and within limits."""
        # Valid timeout
        config = ToolConfig(timeout=60)
        assert config.timeout == 60

        # Timeout too small
        with pytest.raises(ValueError, match="greater than 0"):
            ToolConfig(timeout=0)

        with pytest.raises(ValueError, match="greater than 0"):
            ToolConfig(timeout=-1)

        # Timeout too large
        with pytest.raises(ValueError, match="less than or equal to 600"):
            ToolConfig(timeout=601)

    def test_tool_config_auto_approve_warning(self):
        """Test auto_approve triggers security warning."""
        with pytest.warns(UserWarning, match="DANGEROUS"):
            config = ToolConfig(auto_approve=True)

        assert config.auto_approve is True

    def test_tool_config_approval_mode_validation(self):
        """Test approval_mode must be valid literal."""
        # Valid modes
        for mode in ["always", "once_per_session", "whitelist"]:
            config = ToolConfig(approval_mode=mode)
            assert config.approval_mode == mode

        # Invalid mode
        with pytest.raises(ValueError):
            ToolConfig(approval_mode="invalid")

    def test_tool_config_in_consoul_config(self):
        """Test ToolConfig integrates with ConsoulConfig."""
        # Create a minimal ConsoulConfig with tools
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(name="default", description="Default profile")
            },
            active_profile="default",
            tools=ToolConfig(
                enabled=True,
                timeout=45,
                allowed_tools=["bash"],
            ),
        )

        assert config.tools.enabled is True
        assert config.tools.timeout == 45
        assert config.tools.allowed_tools == ["bash"]

    def test_tool_config_default_in_consoul_config(self):
        """Test ToolConfig uses defaults in ConsoulConfig."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(name="default", description="Default profile")
            },
            active_profile="default",
        )

        # tools field should use default ToolConfig
        assert config.tools.enabled is True
        assert config.tools.auto_approve is False
        assert config.tools.timeout == 30

    def test_tool_config_serialization(self):
        """Test ToolConfig serialization."""
        config = ToolConfig(
            enabled=True,
            allowed_tools=["bash", "python"],
            timeout=60,
        )

        # Serialize to dict
        data = config.model_dump()

        assert data["enabled"] is True
        assert data["allowed_tools"] == ["bash", "python"]
        assert data["timeout"] == 60
        assert data["auto_approve"] is False

    def test_tool_config_deserialization(self):
        """Test ToolConfig deserialization."""
        data = {
            "enabled": False,
            "allowed_tools": ["python"],
            "approval_mode": "once_per_session",
            "timeout": 45,
        }

        config = ToolConfig(**data)

        assert config.enabled is False
        assert config.allowed_tools == ["python"]
        assert config.approval_mode == "once_per_session"
        assert config.timeout == 45

    def test_tool_config_extra_fields_forbidden(self):
        """Test ToolConfig rejects unknown fields."""
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            ToolConfig(unknown_field="value")

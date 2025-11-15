"""Tests for ToolConfig in ConsoulConfig."""

import pytest

from consoul.config.models import (
    ConsoulConfig,
    FileEditToolConfig,
    ProfileConfig,
    ReadToolConfig,
    ToolConfig,
)


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


class TestReadToolConfig:
    """Tests for ReadToolConfig model."""

    def test_default_read_config(self):
        """Test ReadToolConfig defaults."""
        config = ReadToolConfig()

        assert config.max_lines_default == 2000
        assert config.max_line_length == 2000
        assert config.max_output_chars == 40000
        assert config.enable_pdf is True
        assert config.pdf_max_pages == 50
        assert len(config.allowed_extensions) > 0
        assert ".py" in config.allowed_extensions
        assert ".pdf" in config.allowed_extensions
        assert len(config.blocked_paths) > 0
        assert "/etc/shadow" in config.blocked_paths

    def test_read_config_custom_values(self):
        """Test ReadToolConfig with custom values."""
        config = ReadToolConfig(
            max_lines_default=1000,
            max_line_length=1000,
            max_output_chars=20000,
            enable_pdf=False,
            pdf_max_pages=25,
        )

        assert config.max_lines_default == 1000
        assert config.max_line_length == 1000
        assert config.max_output_chars == 20000
        assert config.enable_pdf is False
        assert config.pdf_max_pages == 25

    def test_read_config_validation_positive_integers(self):
        """Test that limits must be positive."""
        # max_lines_default must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            ReadToolConfig(max_lines_default=0)

        with pytest.raises(ValueError, match="greater than 0"):
            ReadToolConfig(max_lines_default=-1)

        # max_line_length must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            ReadToolConfig(max_line_length=0)

        # max_output_chars must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            ReadToolConfig(max_output_chars=-100)

        # pdf_max_pages must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            ReadToolConfig(pdf_max_pages=0)

    def test_read_config_max_lines_upper_limit(self):
        """Test max_lines_default has reasonable upper limit."""
        # Should allow up to 10000
        config = ReadToolConfig(max_lines_default=10000)
        assert config.max_lines_default == 10000

        # Should reject over 10000
        with pytest.raises(ValueError, match="less than or equal to 10000"):
            ReadToolConfig(max_lines_default=10001)

    def test_read_config_pdf_max_pages_upper_limit(self):
        """Test pdf_max_pages has reasonable upper limit."""
        # Should allow up to 500
        config = ReadToolConfig(pdf_max_pages=500)
        assert config.pdf_max_pages == 500

        # Should reject over 500
        with pytest.raises(ValueError, match="less than or equal to 500"):
            ReadToolConfig(pdf_max_pages=501)

    def test_read_config_custom_extensions(self):
        """Test custom allowed extensions."""
        config = ReadToolConfig(allowed_extensions=[".txt", ".md", ".custom"])

        assert config.allowed_extensions == [".txt", ".md", ".custom"]

    def test_read_config_custom_blocked_paths(self):
        """Test custom blocked paths."""
        config = ReadToolConfig(blocked_paths=["/custom/blocked", "/another/path"])

        assert config.blocked_paths == ["/custom/blocked", "/another/path"]

    def test_read_config_in_tool_config(self):
        """Test ReadToolConfig integrates with ToolConfig."""
        tool_config = ToolConfig(
            enabled=True, read=ReadToolConfig(max_lines_default=1500)
        )

        assert tool_config.read.max_lines_default == 1500
        assert tool_config.read.enable_pdf is True

    def test_read_config_default_in_tool_config(self):
        """Test ToolConfig uses ReadToolConfig defaults."""
        tool_config = ToolConfig()

        assert tool_config.read.max_lines_default == 2000
        assert tool_config.read.max_line_length == 2000
        assert tool_config.read.enable_pdf is True

    def test_read_config_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            ReadToolConfig(invalid_field="value")


class TestFileEditToolConfig:
    """Tests for FileEditToolConfig model."""

    def test_default_file_edit_config(self):
        """Test FileEditToolConfig defaults."""
        config = FileEditToolConfig()

        assert config.max_edits == 50
        assert config.max_payload_bytes == 1048576  # 1MB
        assert config.default_encoding == "utf-8"
        assert config.allow_overwrite is False
        assert config.timeout == 30
        assert len(config.allowed_extensions) > 0
        assert ".py" in config.allowed_extensions
        assert ".md" in config.allowed_extensions
        assert len(config.blocked_paths) > 0
        assert "/etc/shadow" in config.blocked_paths
        assert "/etc/passwd" in config.blocked_paths

    def test_file_edit_config_custom_values(self):
        """Test FileEditToolConfig with custom values."""
        config = FileEditToolConfig(
            max_edits=25,
            max_payload_bytes=524288,  # 512KB
            default_encoding="latin-1",
            allow_overwrite=True,
            timeout=60,
        )

        assert config.max_edits == 25
        assert config.max_payload_bytes == 524288
        assert config.default_encoding == "latin-1"
        assert config.allow_overwrite is True
        assert config.timeout == 60

    def test_file_edit_config_validation_positive_integers(self):
        """Test that limits must be positive."""
        # max_edits must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            FileEditToolConfig(max_edits=0)

        with pytest.raises(ValueError, match="greater than 0"):
            FileEditToolConfig(max_edits=-1)

        # max_payload_bytes must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            FileEditToolConfig(max_payload_bytes=0)

        with pytest.raises(ValueError, match="greater than 0"):
            FileEditToolConfig(max_payload_bytes=-100)

        # timeout must be positive
        with pytest.raises(ValueError, match="greater than 0"):
            FileEditToolConfig(timeout=0)

        with pytest.raises(ValueError, match="greater than 0"):
            FileEditToolConfig(timeout=-1)

    def test_file_edit_config_max_edits_limits(self):
        """Test max_edits has reasonable upper limit."""
        # Should allow 1-100
        config = FileEditToolConfig(max_edits=1)
        assert config.max_edits == 1

        config = FileEditToolConfig(max_edits=100)
        assert config.max_edits == 100

        # Should reject over 100
        with pytest.raises(ValueError, match="less than or equal to 100"):
            FileEditToolConfig(max_edits=101)

    def test_file_edit_config_timeout_limits(self):
        """Test timeout has reasonable upper limit."""
        # Should allow up to 600 seconds (10 minutes)
        config = FileEditToolConfig(timeout=600)
        assert config.timeout == 600

        # Should reject over 600
        with pytest.raises(ValueError, match="less than or equal to 600"):
            FileEditToolConfig(timeout=601)

    def test_file_edit_config_custom_extensions(self):
        """Test custom allowed extensions."""
        config = FileEditToolConfig(allowed_extensions=[".py", ".md", ".custom"])

        assert config.allowed_extensions == [".py", ".md", ".custom"]

    def test_file_edit_config_custom_blocked_paths(self):
        """Test custom blocked paths."""
        config = FileEditToolConfig(blocked_paths=["/custom/blocked", "/another/path"])

        assert config.blocked_paths == ["/custom/blocked", "/another/path"]

    def test_file_edit_config_in_tool_config(self):
        """Test FileEditToolConfig integrates with ToolConfig."""
        tool_config = ToolConfig(
            enabled=True, file_edit=FileEditToolConfig(max_edits=25, timeout=60)
        )

        assert tool_config.file_edit.max_edits == 25
        assert tool_config.file_edit.timeout == 60
        assert tool_config.file_edit.allow_overwrite is False

    def test_file_edit_config_default_in_tool_config(self):
        """Test ToolConfig uses FileEditToolConfig defaults."""
        tool_config = ToolConfig()

        assert tool_config.file_edit.max_edits == 50
        assert tool_config.file_edit.max_payload_bytes == 1048576
        assert tool_config.file_edit.default_encoding == "utf-8"
        assert tool_config.file_edit.allow_overwrite is False

    def test_file_edit_config_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            FileEditToolConfig(invalid_field="value")

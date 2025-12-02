"""Tests for --temperature and --max-tokens global flags."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from consoul.__main__ import cli


@pytest.fixture
def runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestTemperatureFlag:
    """Tests for --temperature flag validation and usage."""

    def test_temperature_below_minimum(self, runner):
        """Test temperature below minimum fails validation."""
        result = runner.invoke(cli, ["--temperature", "-0.1", "ask", "test"])

        assert result.exit_code != 0
        # Click validation should fail before trying to run
        assert (
            "Invalid value" in result.output or "temperature" in result.output.lower()
        )

    def test_temperature_above_maximum(self, runner):
        """Test temperature above maximum fails validation."""
        result = runner.invoke(cli, ["--temperature", "2.1", "ask", "test"])

        assert result.exit_code != 0
        assert (
            "Invalid value" in result.output or "temperature" in result.output.lower()
        )

    def test_temperature_invalid_format(self, runner):
        """Test non-numeric temperature fails validation."""
        result = runner.invoke(cli, ["--temperature", "high", "ask", "test"])

        assert result.exit_code != 0
        assert (
            "Invalid value" in result.output
            or "not a valid float" in result.output.lower()
        )


class TestMaxTokensFlag:
    """Tests for --max-tokens flag validation and usage."""

    def test_max_tokens_zero(self, runner):
        """Test max-tokens of zero fails validation."""
        result = runner.invoke(cli, ["--max-tokens", "0", "ask", "test"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "max" in result.output.lower()

    def test_max_tokens_negative(self, runner):
        """Test negative max-tokens fails validation."""
        result = runner.invoke(cli, ["--max-tokens", "-100", "ask", "test"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "max" in result.output.lower()

    def test_max_tokens_invalid_format(self, runner):
        """Test non-numeric max-tokens fails validation."""
        result = runner.invoke(cli, ["--max-tokens", "lots", "ask", "test"])

        assert result.exit_code != 0
        assert (
            "Invalid value" in result.output
            or "not a valid integer" in result.output.lower()
        )


class TestCombinedParameters:
    """Tests for using both flags together."""

    def test_both_invalid_flags(self, runner):
        """Test using both invalid temperature and max-tokens."""
        result = runner.invoke(
            cli,
            ["--temperature", "3.0", "--max-tokens", "-1", "ask", "test"],
        )

        assert result.exit_code != 0
        # Should fail on first invalid parameter
        assert "Invalid value" in result.output


class TestFlagPositioning:
    """Tests for correct flag positioning (global vs command-specific)."""

    def test_temperature_after_command_fails(self, runner):
        """Test temperature fails when placed after command."""
        # This should fail because --temperature is a global flag
        result = runner.invoke(cli, ["ask", "--temperature", "0.5", "test"])

        # Should fail with unrecognized option error
        assert result.exit_code != 0
        assert (
            "no such option" in result.output.lower()
            or "unrecognized" in result.output.lower()
        )

    def test_max_tokens_after_command_fails(self, runner):
        """Test max-tokens fails when placed after command."""
        # This should fail because --max-tokens is a global flag
        result = runner.invoke(cli, ["ask", "--max-tokens", "1000", "test"])

        # Should fail with unrecognized option error
        assert result.exit_code != 0
        assert (
            "no such option" in result.output.lower()
            or "unrecognized" in result.output.lower()
        )

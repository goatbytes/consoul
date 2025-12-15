"""Tests for system prompt building functionality."""

import pytest

from consoul.ai.prompt_builder import build_enhanced_system_prompt, build_system_prompt
from consoul.ai.tools import ToolRegistry


@pytest.fixture
def mock_tool_registry(mocker):
    """Create a mock tool registry with sample tools."""
    registry = mocker.Mock(spec=ToolRegistry)

    # Mock tool metadata
    tool_metadata = mocker.Mock()
    tool_metadata.name = "bash_execute"
    tool_metadata.description = "Execute bash commands"
    tool_metadata.risk_level = mocker.Mock()
    tool_metadata.risk_level.value = "caution"
    tool_metadata.categories = []

    registry.list_tools.return_value = [tool_metadata]
    return registry


class TestBuildSystemPrompt:
    """Tests for build_system_prompt() function."""

    def test_none_base_prompt(self):
        """Test that None base_prompt returns None."""
        result = build_system_prompt(None, None)
        assert result is None

    def test_marker_replacement(self, mock_tool_registry):
        """Test {AVAILABLE_TOOLS} marker is replaced."""
        prompt = "Assistant\n\n{AVAILABLE_TOOLS}\n\nEnd"
        result = build_system_prompt(prompt, mock_tool_registry)

        assert "{AVAILABLE_TOOLS}" not in result
        assert "# Available Tools" in result
        assert "bash_execute" in result

    def test_auto_append_enabled_default(self, mock_tool_registry):
        """Test auto-append is enabled by default."""
        prompt = "My AI assistant"
        result = build_system_prompt(prompt, mock_tool_registry)

        assert "# Available Tools" in result
        assert "bash_execute" in result

    def test_auto_append_disabled(self, mock_tool_registry):
        """Test auto_append_tools=False prevents appending."""
        prompt = "My AI assistant"
        result = build_system_prompt(
            prompt, mock_tool_registry, auto_append_tools=False
        )

        assert result == "My AI assistant"
        assert "# Available Tools" not in result

    def test_marker_works_with_auto_append_false(self, mock_tool_registry):
        """Test marker still works when auto_append_tools=False."""
        prompt = "Assistant {AVAILABLE_TOOLS} End"
        result = build_system_prompt(
            prompt, mock_tool_registry, auto_append_tools=False
        )

        assert "{AVAILABLE_TOOLS}" not in result
        assert "# Available Tools" in result

    def test_no_tools_no_append(self):
        """Test no tools means no append."""
        prompt = "My AI assistant"
        result = build_system_prompt(prompt, None)

        assert result == "My AI assistant"

    def test_marker_with_no_tools(self):
        """Test marker with no tools shows no-tools message."""
        prompt = "Assistant\n\n{AVAILABLE_TOOLS}"
        result = build_system_prompt(prompt, None)

        assert "{AVAILABLE_TOOLS}" not in result
        assert "NO tools available" in result


class TestBuildEnhancedSystemPrompt:
    """Tests for build_enhanced_system_prompt() function."""

    def test_none_base_prompt(self):
        """Test that None base_prompt returns None."""
        result = build_enhanced_system_prompt(None)
        assert result is None

    def test_all_features_disabled(self, mock_tool_registry):
        """Test SDK use case - all injections disabled."""
        prompt = "Clean prompt"
        result = build_enhanced_system_prompt(
            prompt,
            tool_registry=mock_tool_registry,
            include_env_context=False,
            include_git_context=False,
            auto_append_tools=False,
        )

        assert result == "Clean prompt"
        assert "Working Directory" not in result
        assert "# Available Tools" not in result

    def test_env_context_injection(self, mocker):
        """Test environment context is injected."""
        # Mock get_environment_context at import location
        mocker.patch(
            "consoul.ai.environment.get_environment_context",
            return_value="Working Directory: /test",
        )

        prompt = "My prompt"
        result = build_enhanced_system_prompt(
            prompt,
            include_env_context=True,
            include_git_context=False,
            auto_append_tools=False,
        )

        assert "Working Directory: /test" in result
        assert "My prompt" in result

    def test_tool_docs_with_marker(self, mock_tool_registry):
        """Test tool docs with {AVAILABLE_TOOLS} marker."""
        prompt = "Prompt {AVAILABLE_TOOLS} End"
        result = build_enhanced_system_prompt(
            prompt,
            tool_registry=mock_tool_registry,
            include_env_context=False,
            include_git_context=False,
        )

        assert "{AVAILABLE_TOOLS}" not in result
        assert "# Available Tools" in result
        assert "bash_execute" in result

    def test_tool_docs_auto_append(self, mock_tool_registry):
        """Test tool docs auto-append (default behavior)."""
        prompt = "My prompt"
        result = build_enhanced_system_prompt(
            prompt,
            tool_registry=mock_tool_registry,
            include_env_context=False,
            include_git_context=False,
            auto_append_tools=True,
        )

        assert "# Available Tools" in result
        assert "bash_execute" in result

    def test_combined_env_and_tools(self, mock_tool_registry, mocker):
        """Test environment context + tool docs."""
        mocker.patch(
            "consoul.ai.environment.get_environment_context",
            return_value="Working Directory: /test",
        )

        prompt = "Prompt"
        result = build_enhanced_system_prompt(
            prompt,
            tool_registry=mock_tool_registry,
            include_env_context=True,
            include_git_context=False,
            auto_append_tools=True,
        )

        assert "Working Directory: /test" in result
        assert "Prompt" in result
        assert "# Available Tools" in result

    def test_defaults_preserve_cli_tui_behavior(self, mock_tool_registry, mocker):
        """Test all defaults enabled (CLI/TUI behavior)."""
        mocker.patch(
            "consoul.ai.environment.get_environment_context",
            return_value="Working Directory: /test",
        )

        prompt = "Assistant"
        result = build_enhanced_system_prompt(
            prompt,
            tool_registry=mock_tool_registry,
        )

        # Should have env context + tool docs
        assert "Working Directory: /test" in result
        assert "# Available Tools" in result

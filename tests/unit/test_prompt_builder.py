"""Tests for flexible system prompt builder (SOUL-287)."""

from unittest.mock import Mock, patch

from consoul.ai.prompt_builder import build_enhanced_system_prompt


class TestGranularEnvironmentContext:
    """Test granular environment context controls."""

    @patch("consoul.ai.environment.get_environment_context")
    def test_granular_os_only(self, mock_get_env):
        """Test including only OS information."""
        mock_get_env.return_value = "## Environment\n- OS: macOS 15.2"

        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            include_os_info=True,
        )

        mock_get_env.assert_called_once_with(
            include_os=True,
            include_shell=False,
            include_directory=False,
            include_datetime=False,
            include_git=False,
        )
        assert "macOS" in prompt

    @patch("consoul.ai.environment.get_environment_context")
    def test_granular_os_and_datetime(self, mock_get_env):
        """Test including OS and datetime only."""
        mock_get_env.return_value = "## Environment\n- OS: macOS\n- Date: 2025-12-16"

        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            include_os_info=True,
            include_datetime_info=True,
        )

        mock_get_env.assert_called_once_with(
            include_os=True,
            include_shell=False,
            include_directory=False,
            include_datetime=True,
            include_git=False,
        )
        assert "macOS" in prompt
        assert "2025-12-16" in prompt

    @patch("consoul.ai.environment.get_environment_context")
    def test_granular_no_context(self, mock_get_env):
        """Test with no environment context (profile-free SDK default)."""
        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
        )

        # get_environment_context should NOT be called when all flags are False
        mock_get_env.assert_not_called()
        assert prompt == "You are an assistant."

    @patch("consoul.ai.environment.get_environment_context")
    def test_granular_git_only(self, mock_get_env):
        """Test including only git information."""
        mock_get_env.return_value = "## Git Repository\n- Branch: main"

        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            include_git_info=True,
        )

        mock_get_env.assert_called_once_with(
            include_os=False,
            include_shell=False,
            include_directory=False,
            include_datetime=False,
            include_git=True,
        )
        assert "Branch: main" in prompt


class TestLegacyBackwardCompatibility:
    """Test backward compatibility with legacy parameters."""

    @patch("consoul.ai.environment.get_environment_context")
    def test_legacy_include_env_context_true(self, mock_get_env):
        """Test legacy include_env_context=True enables all system flags."""
        mock_get_env.return_value = "## Environment\n- OS: macOS\n- Shell: zsh"

        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            include_env_context=True,
        )

        # Legacy parameter should be passed through
        mock_get_env.assert_called_once_with(
            include_system_info=True,
            include_git_info=None,
        )
        assert "Environment" in prompt

    @patch("consoul.ai.environment.get_environment_context")
    def test_legacy_include_git_context_true(self, mock_get_env):
        """Test legacy include_git_context=True."""
        mock_get_env.return_value = "## Git Repository\n- Branch: develop"

        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            include_git_context=True,
        )

        mock_get_env.assert_called_once_with(
            include_system_info=None,
            include_git_info=True,
        )
        assert "Git Repository" in prompt

    @patch("consoul.ai.environment.get_environment_context")
    def test_legacy_both_true(self, mock_get_env):
        """Test legacy parameters both True (CLI/TUI default)."""
        mock_get_env.return_value = (
            "## Environment\n- OS: macOS\n\n## Git Repository\n- Branch: main"
        )

        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            include_env_context=True,
            include_git_context=True,
        )

        mock_get_env.assert_called_once_with(
            include_system_info=True,
            include_git_info=True,
        )
        assert "Environment" in prompt
        assert "Git Repository" in prompt

    @patch("consoul.ai.environment.get_environment_context")
    def test_legacy_overrides_granular(self, mock_get_env):
        """Test that legacy parameters take precedence over granular flags."""
        mock_get_env.return_value = "## Environment"

        # Even though granular flags are set, legacy should take precedence
        build_enhanced_system_prompt(
            "You are an assistant.",
            include_os_info=True,  # This should be ignored
            include_env_context=False,  # Legacy takes precedence
        )

        mock_get_env.assert_called_once_with(
            include_system_info=False,
            include_git_info=None,
        )


class TestCustomContextSections:
    """Test custom context sections for domain-specific applications."""

    def test_single_custom_section(self):
        """Test single custom context section."""
        prompt = build_enhanced_system_prompt(
            "You are a legal assistant.",
            context_sections={"jurisdiction": "California workers' compensation law"},
        )

        assert "# Jurisdiction" in prompt
        assert "California workers' compensation law" in prompt
        assert "You are a legal assistant." in prompt

    def test_multiple_custom_sections(self):
        """Test multiple custom context sections."""
        prompt = build_enhanced_system_prompt(
            "You are a medical assistant.",
            context_sections={
                "patient_demographics": "Age: 45, Gender: M",
                "medical_history": "Hypertension, Type 2 Diabetes",
                "current_medications": "Metformin, Lisinopril",
            },
        )

        assert "# Patient Demographics" in prompt
        assert "Age: 45" in prompt
        assert "# Medical History" in prompt
        assert "Hypertension" in prompt
        assert "# Current Medications" in prompt
        assert "Metformin" in prompt

    def test_custom_sections_title_formatting(self):
        """Test that custom section keys are properly title-cased."""
        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            context_sections={
                "case_law_precedents": "Recent case law...",
                "client_info": "Construction industry",
            },
        )

        # Underscores should be replaced with spaces and title-cased
        assert "# Case Law Precedents" in prompt
        assert "# Client Info" in prompt

    @patch("consoul.ai.environment.get_environment_context")
    def test_custom_sections_with_environment(self, mock_get_env):
        """Test custom sections combined with environment context."""
        mock_get_env.return_value = "## Environment\n- OS: macOS"

        prompt = build_enhanced_system_prompt(
            "You are a legal assistant.",
            include_os_info=True,
            context_sections={"jurisdiction": "California law"},
        )

        # Environment should come first
        assert prompt.index("## Environment") < prompt.index("# Jurisdiction")
        assert prompt.index("# Jurisdiction") < prompt.index(
            "You are a legal assistant"
        )

    def test_empty_custom_sections(self):
        """Test with empty custom sections dict."""
        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            context_sections={},
        )

        assert prompt == "You are an assistant."

    def test_custom_sections_ordering(self):
        """Test that custom sections maintain order (Python 3.7+ dict ordering)."""
        prompt = build_enhanced_system_prompt(
            "You are an assistant.",
            context_sections={
                "first": "First section",
                "second": "Second section",
                "third": "Third section",
            },
        )

        # Sections should appear in the order they were defined
        first_idx = prompt.index("# First")
        second_idx = prompt.index("# Second")
        third_idx = prompt.index("# Third")

        assert first_idx < second_idx < third_idx


class TestToolDocumentation:
    """Test tool documentation control with granular context."""

    def test_no_tools_no_context(self):
        """Test minimal prompt with no tools, no context."""
        prompt = build_enhanced_system_prompt(
            "You are a chat assistant.",
            auto_append_tools=False,
        )

        assert prompt == "You are a chat assistant."
        assert "# Available Tools" not in prompt

    def test_tools_with_granular_context(self):
        """Test tools with selective environment context."""
        mock_registry = Mock()
        mock_registry.list_tools.return_value = []

        with patch("consoul.ai.environment.get_environment_context") as mock_get_env:
            mock_get_env.return_value = "## Environment\n- OS: macOS"

            prompt = build_enhanced_system_prompt(
                "You are an assistant.",
                tool_registry=mock_registry,
                include_os_info=True,
                auto_append_tools=True,
            )

            assert "## Environment" in prompt
            assert "OS: macOS" in prompt


class TestDomainSpecificUsagePatterns:
    """Test real-world domain-specific usage patterns."""

    def test_legal_ai_pattern(self):
        """Test legal AI usage pattern with case law context."""
        prompt = build_enhanced_system_prompt(
            "You are a workers' compensation legal assistant for California.",
            context_sections={
                "jurisdiction": "California workers' compensation law",
                "case_law": "Recent precedents from 2024: Case A vs Company B...",
                "client_background": "Construction industry, injured worker claims",
            },
            include_os_info=False,  # No environment noise
            include_git_info=False,  # No git context
            auto_append_tools=False,  # Chat-only mode
        )

        assert "# Jurisdiction" in prompt
        assert "California workers' compensation law" in prompt
        assert "# Case Law" in prompt
        assert "# Client Background" in prompt
        assert "Working Directory:" not in prompt  # No env noise
        assert "# Available Tools" not in prompt  # No tools

    def test_medical_chatbot_pattern(self):
        """Test medical chatbot with patient context and timestamp."""
        with patch("consoul.ai.environment.get_environment_context") as mock_get_env:
            mock_get_env.return_value = "## Environment\n- Date: 2025-12-16 14:30 PST"

            prompt = build_enhanced_system_prompt(
                "You are a medical assistant providing patient care guidance.",
                context_sections={
                    "patient_demographics": "Age: 45, Gender: M, Weight: 180lbs",
                    "medical_history": "Hypertension (2020), Type 2 Diabetes (2022)",
                    "current_medications": "Metformin 500mg BID, Lisinopril 10mg QD",
                },
                include_datetime_info=True,  # Timestamp for medical records
                include_os_info=False,
                include_directory_info=False,
                auto_append_tools=False,
            )

            assert "# Patient Demographics" in prompt
            assert "# Medical History" in prompt
            assert "# Current Medications" in prompt
            assert "Date: 2025-12-16" in prompt  # Timestamp included
            assert "Working Directory:" not in prompt

    def test_customer_support_pattern(self):
        """Test customer support bot with product context."""
        prompt = build_enhanced_system_prompt(
            "You are a customer support agent for TechCorp.",
            context_sections={
                "customer_tier": "Premium",
                "product_line": "Enterprise Software Suite",
                "common_issues": "License activation, SSO integration, API rate limits",
            },
            auto_append_tools=False,
        )

        assert "# Customer Tier" in prompt
        assert "Premium" in prompt
        assert "# Product Line" in prompt
        assert "# Common Issues" in prompt

"""Integration tests for tool filtering with ToolService."""

import pytest

from consoul.ai.tools.base import RiskLevel, ToolCategory
from consoul.sdk.models import ToolFilter
from consoul.sdk.services.tool import ToolService


class TestToolServiceFiltering:
    """Test ToolService with ToolFilter integration."""

    @pytest.fixture
    def tool_service(self):
        """Create ToolService with all tools registered."""
        from consoul.config import load_config

        config = load_config()
        return ToolService.from_config(config)

    def test_apply_filter_with_deny_list(self, tool_service):
        """Test apply_filter() with deny list."""
        # Create filter that denies bash
        filter = ToolFilter(deny=["bash_execute"])

        # Apply filter
        filtered_service = tool_service.apply_filter(filter)

        # Check that bash_execute is not in filtered tools
        filtered_tools = filtered_service.list_tools(enabled_only=True)
        tool_names = [meta.name for meta in filtered_tools]

        assert "bash_execute" not in tool_names
        assert "grep_search" in tool_names  # Other tools still present

    def test_apply_filter_with_allow_list(self, tool_service):
        """Test apply_filter() with allow list."""
        # Create filter that only allows specific tools
        filter = ToolFilter(allow=["grep_search", "web_search"])

        # Apply filter
        filtered_service = tool_service.apply_filter(filter)

        # Check that only allowed tools are present
        filtered_tools = filtered_service.list_tools(enabled_only=True)
        tool_names = [meta.name for meta in filtered_tools]

        assert tool_names == ["grep_search", "web_search"] or set(tool_names) == {
            "grep_search",
            "web_search",
        }
        assert "bash_execute" not in tool_names

    def test_apply_filter_with_risk_level(self, tool_service):
        """Test apply_filter() with risk level."""
        # Create filter that only allows SAFE tools
        filter = ToolFilter(risk_level=RiskLevel.SAFE)

        # Apply filter
        filtered_service = tool_service.apply_filter(filter)

        # Check that only SAFE tools are present
        filtered_tools = filtered_service.list_tools(enabled_only=True)

        for tool_meta in filtered_tools:
            assert tool_meta.risk_level == RiskLevel.SAFE

    def test_get_filtered_tools(self, tool_service):
        """Test get_filtered_tools() method."""
        # Create filter
        filter = ToolFilter(deny=["bash_execute"], risk_level=RiskLevel.SAFE)

        # Get filtered tools
        filtered_tools = tool_service.get_filtered_tools(filter)
        tool_names = [meta.name for meta in filtered_tools]

        # Bash should be denied
        assert "bash_execute" not in tool_names

        # All remaining tools should be SAFE
        for tool_meta in filtered_tools:
            assert tool_meta.risk_level == RiskLevel.SAFE

    def test_filtered_service_maintains_config(self, tool_service):
        """Test that filtered service maintains original config."""
        filter = ToolFilter(deny=["bash_execute"])

        filtered_service = tool_service.apply_filter(filter)

        # Config should be preserved
        assert filtered_service.config == tool_service.config

    def test_filtered_service_maintains_providers(self, tool_service):
        """Test that filtered service maintains approval provider and audit logger."""
        filter = ToolFilter(deny=["bash_execute"])

        filtered_service = tool_service.apply_filter(filter)

        # Providers should be preserved
        assert (
            filtered_service.tool_registry.approval_provider
            == tool_service.tool_registry.approval_provider
        )
        assert (
            filtered_service.tool_registry.audit_logger
            == tool_service.tool_registry.audit_logger
        )


class TestToolFilteringUseCases:
    """Test real-world tool filtering scenarios."""

    def test_legal_industry_deployment(self):
        """Test legal industry filter (document analysis only)."""
        from consoul.config import load_config

        config = load_config()
        service = ToolService.from_config(config)

        # Legal filter: only safe search tools, no bash/filesystem
        legal_filter = ToolFilter(
            allow=["web_search", "grep_search", "read_url"],
            deny=["bash_execute", "file_edit", "create_file"],
            risk_level=RiskLevel.SAFE,
        )

        filtered_service = service.apply_filter(legal_filter)
        filtered_tools = filtered_service.list_tools(enabled_only=True)
        tool_names = [meta.name for meta in filtered_tools]

        # Only allowed tools present
        for tool_name in tool_names:
            assert tool_name in ["web_search", "grep_search", "read_url"]

        # Dangerous tools blocked
        assert "bash_execute" not in tool_names
        assert "file_edit" not in tool_names

    def test_readonly_session(self):
        """Test read-only session filter."""
        from consoul.config import load_config

        config = load_config()
        service = ToolService.from_config(config)

        # Read-only filter: max safety, no write/execute
        readonly_filter = ToolFilter(
            risk_level=RiskLevel.SAFE,
            deny=["bash_execute", "file_edit", "create_file", "delete_file"],
        )

        filtered_service = service.apply_filter(readonly_filter)
        filtered_tools = filtered_service.list_tools(enabled_only=True)

        # All tools should be SAFE
        for tool_meta in filtered_tools:
            assert tool_meta.risk_level == RiskLevel.SAFE

        # No write/execute tools
        tool_names = [meta.name for meta in filtered_tools]
        assert "bash_execute" not in tool_names
        assert "file_edit" not in tool_names

    def test_research_session(self):
        """Test research session filter (web + search only)."""
        from consoul.config import load_config

        config = load_config()
        service = ToolService.from_config(config)

        # Research filter: search and web categories only
        research_filter = ToolFilter(
            categories=[ToolCategory.SEARCH, ToolCategory.WEB],
            deny=["bash_execute"],
        )

        filtered_service = service.apply_filter(research_filter)
        filtered_tools = filtered_service.list_tools(enabled_only=True)

        # All tools should have SEARCH or WEB category
        for tool_meta in filtered_tools:
            if tool_meta.categories:
                has_allowed_category = any(
                    cat in [ToolCategory.SEARCH, ToolCategory.WEB]
                    for cat in tool_meta.categories
                )
                assert has_allowed_category

        # Bash should be denied
        tool_names = [meta.name for meta in filtered_tools]
        assert "bash_execute" not in tool_names


class TestToolFilteringWithConversationService:
    """Test tool filtering integrated with ConversationService."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for testing."""
        from consoul.config import load_config

        return load_config()

    def test_conversation_service_with_filter(self, mock_config):
        """Test ConversationService accepts tool_filter parameter."""
        from consoul.ai.tools.providers import CliApprovalProvider
        from consoul.sdk.models import ToolFilter
        from consoul.sdk.services.conversation import ConversationService

        # Create filter
        filter = ToolFilter(deny=["bash_execute"], risk_level=RiskLevel.SAFE)

        # Create service with filter
        service = ConversationService.from_config(
            config=mock_config,
            tool_filter=filter,
            approval_provider=CliApprovalProvider(),  # Required for tool registry
        )

        # Check that filter was applied
        assert service.tool_filter == filter

        # Check that filtered tools are available
        if service.tool_registry:
            filtered_tools = service.tool_registry.list_tools(enabled_only=True)
            tool_names = [meta.name for meta in filtered_tools]

            # Bash should be blocked
            assert "bash_execute" not in tool_names

            # All tools should be SAFE
            for tool_meta in filtered_tools:
                assert tool_meta.risk_level == RiskLevel.SAFE

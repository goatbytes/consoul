"""Unit tests for ToolFilter dataclass."""

import pytest

from consoul.ai.tools.base import RiskLevel, ToolCategory
from consoul.sdk.models import ToolFilter


class TestToolFilterValidation:
    """Test ToolFilter validation."""

    def test_valid_filter_creation(self):
        """Test creating valid ToolFilter instances."""
        # Empty filter (no restrictions)
        filter1 = ToolFilter()
        assert filter1.allow is None
        assert filter1.deny is None
        assert filter1.risk_level is None
        assert filter1.categories is None

        # Filter with allow list
        filter2 = ToolFilter(allow=["bash_execute", "grep_search"])
        assert filter2.allow == ["bash_execute", "grep_search"]

        # Filter with deny list
        filter3 = ToolFilter(deny=["bash_execute"])
        assert filter3.deny == ["bash_execute"]

        # Filter with risk level
        filter4 = ToolFilter(risk_level=RiskLevel.SAFE)
        assert filter4.risk_level == RiskLevel.SAFE

        # Filter with categories
        filter5 = ToolFilter(categories=[ToolCategory.SEARCH, ToolCategory.WEB])
        assert filter5.categories == [ToolCategory.SEARCH, ToolCategory.WEB]

    def test_invalid_risk_level(self):
        """Test validation of risk_level parameter."""
        with pytest.raises(ValueError, match="risk_level must be RiskLevel enum"):
            ToolFilter(risk_level="safe")  # type: ignore

    def test_invalid_categories(self):
        """Test validation of categories parameter."""
        with pytest.raises(ValueError, match="categories must be a list"):
            ToolFilter(categories="search")  # type: ignore

        with pytest.raises(
            ValueError, match="All categories must be ToolCategory enum"
        ):
            ToolFilter(categories=["search"])  # type: ignore

    def test_invalid_allow_list(self):
        """Test validation of allow parameter."""
        with pytest.raises(ValueError, match="allow must be a list"):
            ToolFilter(allow="bash_execute")  # type: ignore

    def test_invalid_deny_list(self):
        """Test validation of deny parameter."""
        with pytest.raises(ValueError, match="deny must be a list"):
            ToolFilter(deny="bash_execute")  # type: ignore

    def test_overlapping_allow_deny_warning(self):
        """Test warning for overlapping allow/deny lists."""
        with pytest.warns(UserWarning, match="overlapping allow/deny lists"):
            ToolFilter(
                allow=["bash_execute", "grep_search"],
                deny=["bash_execute"],  # Overlaps with allow
            )


class TestToolFilterLogic:
    """Test ToolFilter.is_tool_allowed() logic."""

    def test_deny_list_blocks_tool(self):
        """Test deny list takes highest priority."""
        filter = ToolFilter(deny=["bash_execute"])
        allowed, reason = filter.is_tool_allowed(
            tool_name="bash_execute",
            tool_risk=RiskLevel.CAUTION,
        )
        assert not allowed
        assert "denied by filter" in reason

    def test_allow_list_permits_tool(self):
        """Test allow list permits specified tools."""
        filter = ToolFilter(allow=["grep_search", "web_search"])

        # Tool in allow list
        allowed, reason = filter.is_tool_allowed(
            tool_name="grep_search",
            tool_risk=RiskLevel.SAFE,
        )
        assert allowed
        assert reason is None

        # Tool not in allow list
        allowed, reason = filter.is_tool_allowed(
            tool_name="bash_execute",
            tool_risk=RiskLevel.CAUTION,
        )
        assert not allowed
        assert "not in allow list" in reason

    def test_deny_overrides_allow(self):
        """Test deny list takes precedence over allow list."""
        filter = ToolFilter(
            allow=["bash_execute", "grep_search"],
            deny=["bash_execute"],
        )

        # Denied tool (even though in allow list)
        allowed, reason = filter.is_tool_allowed(
            tool_name="bash_execute",
            tool_risk=RiskLevel.CAUTION,
        )
        assert not allowed
        assert "denied by filter" in reason

        # Allowed tool
        allowed, reason = filter.is_tool_allowed(
            tool_name="grep_search",
            tool_risk=RiskLevel.SAFE,
        )
        assert allowed

    def test_risk_level_filtering(self):
        """Test risk level filtering."""
        filter = ToolFilter(risk_level=RiskLevel.SAFE)

        # SAFE tool allowed
        allowed, reason = filter.is_tool_allowed(
            tool_name="grep_search",
            tool_risk=RiskLevel.SAFE,
        )
        assert allowed
        assert reason is None

        # CAUTION tool blocked (exceeds SAFE)
        allowed, reason = filter.is_tool_allowed(
            tool_name="bash_execute",
            tool_risk=RiskLevel.CAUTION,
        )
        assert not allowed
        assert "risk level" in reason
        assert "exceeds maximum" in reason

        # DANGEROUS tool blocked
        allowed, reason = filter.is_tool_allowed(
            tool_name="dangerous_tool",
            tool_risk=RiskLevel.DANGEROUS,
        )
        assert not allowed

    def test_category_filtering(self):
        """Test category filtering."""
        filter = ToolFilter(categories=[ToolCategory.SEARCH, ToolCategory.WEB])

        # Tool with allowed category
        allowed, reason = filter.is_tool_allowed(
            tool_name="grep_search",
            tool_risk=RiskLevel.SAFE,
            tool_categories=[ToolCategory.SEARCH],
        )
        assert allowed
        assert reason is None

        # Tool with non-allowed category
        allowed, reason = filter.is_tool_allowed(
            tool_name="bash_execute",
            tool_risk=RiskLevel.CAUTION,
            tool_categories=[ToolCategory.EXECUTE],
        )
        assert not allowed
        assert "categories not in allowed list" in reason

    def test_category_filtering_blocks_uncategorized_tools(self):
        """Test that category filter blocks tools without category metadata."""
        filter = ToolFilter(categories=[ToolCategory.SEARCH, ToolCategory.WEB])

        # Tool with no categories should be blocked when category filter is active
        allowed, reason = filter.is_tool_allowed(
            tool_name="uncategorized_tool",
            tool_risk=RiskLevel.SAFE,
            tool_categories=None,  # No categories
        )
        assert not allowed
        assert "no category metadata" in reason

        # Empty categories list should also be blocked
        allowed, reason = filter.is_tool_allowed(
            tool_name="empty_categories_tool",
            tool_risk=RiskLevel.SAFE,
            tool_categories=[],  # Empty list
        )
        assert not allowed
        assert "no category metadata" in reason

    def test_combined_filters(self):
        """Test combination of multiple filter criteria."""
        filter = ToolFilter(
            deny=["dangerous_bash"],
            allow=["grep_search", "web_search", "bash_execute"],
            risk_level=RiskLevel.CAUTION,
            categories=[ToolCategory.SEARCH, ToolCategory.WEB, ToolCategory.EXECUTE],
        )

        # Denied tool (highest priority)
        allowed, _ = filter.is_tool_allowed(
            tool_name="dangerous_bash",
            tool_risk=RiskLevel.SAFE,
            tool_categories=[ToolCategory.EXECUTE],
        )
        assert not allowed

        # Not in allow list
        allowed, _ = filter.is_tool_allowed(
            tool_name="file_edit",
            tool_risk=RiskLevel.SAFE,
            tool_categories=[ToolCategory.FILE_EDIT],
        )
        assert not allowed

        # Exceeds risk level
        allowed, _ = filter.is_tool_allowed(
            tool_name="bash_execute",
            tool_risk=RiskLevel.DANGEROUS,
            tool_categories=[ToolCategory.EXECUTE],
        )
        assert not allowed

        # Wrong category
        allowed, _ = filter.is_tool_allowed(
            tool_name="web_search",
            tool_risk=RiskLevel.SAFE,
            tool_categories=[ToolCategory.FILE_EDIT],  # Wrong category
        )
        assert not allowed

        # Passes all checks
        allowed, reason = filter.is_tool_allowed(
            tool_name="grep_search",
            tool_risk=RiskLevel.SAFE,
            tool_categories=[ToolCategory.SEARCH],
        )
        assert allowed
        assert reason is None


class TestToolFilterUseCases:
    """Test real-world use cases for ToolFilter."""

    def test_legal_industry_filter(self):
        """Test filter for legal industry (document analysis only)."""
        legal_filter = ToolFilter(
            allow=["web_search", "grep_search", "read_url"],
            deny=["bash_execute", "file_edit", "create_file"],
            risk_level=RiskLevel.SAFE,
        )

        # Safe search tools allowed
        assert legal_filter.is_tool_allowed("web_search", RiskLevel.SAFE)[0]
        assert legal_filter.is_tool_allowed("grep_search", RiskLevel.SAFE)[0]

        # Bash explicitly denied
        assert not legal_filter.is_tool_allowed("bash_execute", RiskLevel.CAUTION)[0]

        # File operations denied
        assert not legal_filter.is_tool_allowed("file_edit", RiskLevel.CAUTION)[0]

    def test_readonly_session_filter(self):
        """Test filter for read-only session (maximum safety)."""
        readonly_filter = ToolFilter(
            risk_level=RiskLevel.SAFE,
            deny=["bash_execute", "file_edit", "create_file", "delete_file"],
        )

        # Safe read tools allowed
        assert readonly_filter.is_tool_allowed("grep_search", RiskLevel.SAFE)[0]

        # Any write/execute tool blocked
        assert not readonly_filter.is_tool_allowed("bash_execute", RiskLevel.CAUTION)[0]
        assert not readonly_filter.is_tool_allowed("file_edit", RiskLevel.CAUTION)[0]

    def test_research_session_filter(self):
        """Test filter for research session (web + search, no execution)."""
        research_filter = ToolFilter(
            categories=[ToolCategory.SEARCH, ToolCategory.WEB],
            deny=["bash_execute"],
        )

        # Search tools allowed
        assert research_filter.is_tool_allowed(
            "grep_search",
            RiskLevel.SAFE,
            tool_categories=[ToolCategory.SEARCH],
        )[0]

        # Web tools allowed
        assert research_filter.is_tool_allowed(
            "web_search",
            RiskLevel.SAFE,
            tool_categories=[ToolCategory.WEB],
        )[0]

        # Execution tools blocked
        assert not research_filter.is_tool_allowed(
            "bash_execute",
            RiskLevel.CAUTION,
            tool_categories=[ToolCategory.EXECUTE],
        )[0]

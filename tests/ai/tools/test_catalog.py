"""Tests for tool catalog module."""

from consoul.ai.tools.base import RiskLevel
from consoul.ai.tools.catalog import (
    TOOL_ALIASES,
    TOOL_CATALOG,
    get_all_tool_names,
    get_tool_by_name,
    get_tools_by_risk_level,
    validate_tool_name,
)


class TestToolCatalog:
    """Test tool catalog data structure."""

    def test_catalog_not_empty(self) -> None:
        """Test that catalog has tools."""
        assert len(TOOL_CATALOG) > 0

    def test_catalog_structure(self) -> None:
        """Test that catalog entries have correct structure."""
        for name, (tool, risk_level) in TOOL_CATALOG.items():
            assert isinstance(name, str)
            assert hasattr(tool, "name")
            assert hasattr(tool, "run")
            assert isinstance(risk_level, RiskLevel)

    def test_expected_tools_present(self) -> None:
        """Test that expected tools are in catalog."""
        expected_tools = [
            "bash",
            "grep",
            "code_search",
            "find_references",
            "create_file",
            "edit_lines",
            "edit_replace",
            "append_file",
            "delete_file",
        ]

        for tool_name in expected_tools:
            assert tool_name in TOOL_CATALOG, f"Expected tool '{tool_name}' not found"


class TestGetToolByName:
    """Test get_tool_by_name function."""

    def test_get_bash_tool(self) -> None:
        """Test getting bash tool by name."""
        result = get_tool_by_name("bash")
        assert result is not None
        tool, risk_level = result
        assert tool.name == "bash_execute"
        assert risk_level == RiskLevel.CAUTION

    def test_get_grep_tool(self) -> None:
        """Test getting grep tool by name."""
        result = get_tool_by_name("grep")
        assert result is not None
        tool, risk_level = result
        assert tool.name == "grep_search"
        assert risk_level == RiskLevel.SAFE

    def test_get_tool_by_alias(self) -> None:
        """Test getting tool by alias name."""
        for alias, canonical in TOOL_ALIASES.items():
            result = get_tool_by_name(alias)
            assert result is not None, f"Alias '{alias}' should resolve"
            tool, _ = result
            expected_result = TOOL_CATALOG[canonical]
            assert tool == expected_result[0]

    def test_get_invalid_tool(self) -> None:
        """Test getting non-existent tool returns None."""
        result = get_tool_by_name("nonexistent_tool")
        assert result is None

    def test_case_sensitive(self) -> None:
        """Test that tool names are case-sensitive."""
        result = get_tool_by_name("BASH")
        assert result is None


class TestGetToolsByRiskLevel:
    """Test get_tools_by_risk_level function."""

    def test_safe_tools_only(self) -> None:
        """Test getting only safe tools."""
        tools = get_tools_by_risk_level("safe")
        assert len(tools) > 0
        for _, risk_level in tools:
            assert risk_level == RiskLevel.SAFE

    def test_caution_includes_safe(self) -> None:
        """Test that caution level includes safe tools."""
        safe_tools = get_tools_by_risk_level("safe")
        caution_tools = get_tools_by_risk_level("caution")

        assert len(caution_tools) > len(safe_tools)

        # All safe tools should be in caution list (compare by name)
        safe_tool_names = {tool.name for tool, _ in safe_tools}
        caution_tool_names = {tool.name for tool, _ in caution_tools}
        assert safe_tool_names.issubset(caution_tool_names)

    def test_dangerous_includes_all(self) -> None:
        """Test that dangerous level includes all tools."""
        dangerous_tools = get_tools_by_risk_level("dangerous")
        all_tools_in_catalog = list(TOOL_CATALOG.values())

        assert len(dangerous_tools) == len(all_tools_in_catalog)

    def test_risk_level_enum(self) -> None:
        """Test using RiskLevel enum instead of string."""
        tools = get_tools_by_risk_level(RiskLevel.SAFE)
        assert len(tools) > 0
        for _, risk_level in tools:
            assert risk_level == RiskLevel.SAFE

    def test_specific_risk_levels(self) -> None:
        """Test that tools are categorized correctly."""
        safe_tools = get_tools_by_risk_level("safe")
        caution_tools = get_tools_by_risk_level("caution")
        dangerous_tools = get_tools_by_risk_level("dangerous")

        # Verify expected tools at each level
        safe_names = {tool.name for tool, _ in safe_tools}
        assert "grep_search" in safe_names
        assert "code_search" in safe_names
        assert "find_references" in safe_names

        caution_names = {tool.name for tool, _ in caution_tools}
        assert "bash_execute" in caution_names
        assert "create_file" in caution_names

        dangerous_names = {tool.name for tool, _ in dangerous_tools}
        assert "delete_file" in dangerous_names


class TestGetAllToolNames:
    """Test get_all_tool_names function."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        names = get_all_tool_names()
        assert isinstance(names, list)

    def test_names_are_strings(self) -> None:
        """Test that all names are strings."""
        names = get_all_tool_names()
        assert all(isinstance(name, str) for name in names)

    def test_list_is_sorted(self) -> None:
        """Test that list is sorted alphabetically."""
        names = get_all_tool_names()
        assert names == sorted(names)

    def test_matches_catalog_keys(self) -> None:
        """Test that names match catalog keys."""
        names = get_all_tool_names()
        catalog_keys = sorted(TOOL_CATALOG.keys())
        assert names == catalog_keys


class TestValidateToolName:
    """Test validate_tool_name function."""

    def test_valid_tool_names(self) -> None:
        """Test that all catalog tools are valid."""
        for tool_name in TOOL_CATALOG:
            assert validate_tool_name(tool_name) is True

    def test_valid_aliases(self) -> None:
        """Test that all aliases are valid."""
        for alias in TOOL_ALIASES:
            assert validate_tool_name(alias) is True

    def test_invalid_tool_name(self) -> None:
        """Test that invalid names return False."""
        assert validate_tool_name("nonexistent") is False
        assert validate_tool_name("") is False
        assert validate_tool_name("BASH") is False  # Case-sensitive

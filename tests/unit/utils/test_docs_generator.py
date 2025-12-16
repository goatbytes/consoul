"""Unit tests for docs_generator module."""

from __future__ import annotations

import pytest

from consoul.utils.docs_generator import parse_command_schema


class TestParseCommandSchema:
    """Test parse_command_schema function with various edge cases."""

    @pytest.fixture
    def base_command_schema(self) -> dict:
        """Base schema structure for testing."""
        return {
            "type": "command",
            "name": "test",
            "description": "Test command",
            "arguments": [],
            "options": [],
        }

    @pytest.fixture
    def group_schema(self) -> dict:
        """Schema for a command group."""
        return {
            "type": "group",
            "name": "consoul",
            "description": "Main command group",
            "commands": [],
            "arguments": [],
            "options": [],
        }

    def test_empty_command_name(self, group_schema: dict) -> None:
        """Test handling of empty command name - should not raise IndexError."""
        group_schema["commands"] = [
            {
                "type": "command",
                "name": "",  # Empty string
                "description": "Empty name command",
                "arguments": [],
                "options": [],
            }
        ]

        # Should not raise IndexError
        result = parse_command_schema(group_schema)

        # Should return the commands
        assert len(result) > 0
        # The subcommand should have empty name as fallback
        assert result[0]["commands"][0]["name"] == ""

    def test_whitespace_only_command_name(self, group_schema: dict) -> None:
        """Test handling of whitespace-only command names."""
        test_cases = ["   ", "\t", "\n", " \t\n "]

        for whitespace in test_cases:
            group_schema["commands"] = [
                {
                    "type": "command",
                    "name": whitespace,
                    "description": "Whitespace command",
                    "arguments": [],
                    "options": [],
                }
            ]

            # Should not raise IndexError
            result = parse_command_schema(group_schema)

            # Should return the commands
            assert len(result) > 0
            # Should fallback to the original whitespace string
            assert result[0]["commands"][0]["name"] == whitespace

    def test_single_word_command_name(self, group_schema: dict) -> None:
        """Test extraction of single-word command name."""
        group_schema["commands"] = [
            {
                "type": "command",
                "name": "chat",
                "description": "Chat command",
                "arguments": [],
                "options": [],
            }
        ]

        result = parse_command_schema(group_schema)

        # Should extract single word correctly
        assert result[0]["commands"][0]["name"] == "chat"

    def test_multi_word_command_name(self, group_schema: dict) -> None:
        """Test extraction of last word from multi-word command path."""
        test_cases = [
            ("consoul chat", "chat"),
            ("consoul tui start", "start"),
            ("a b c", "c"),
            ("one two", "two"),
        ]

        for full_name, expected_name in test_cases:
            group_schema["commands"] = [
                {
                    "type": "command",
                    "name": full_name,
                    "description": "Multi-word command",
                    "arguments": [],
                    "options": [],
                }
            ]

            result = parse_command_schema(group_schema)

            # Should extract last word
            assert result[0]["commands"][0]["name"] == expected_name

    def test_normal_subcommand_structure(self) -> None:
        """Test typical command group with subcommands."""
        schema = {
            "type": "application",
            "name": "consoul",
            "commands": [
                {
                    "type": "group",
                    "name": "consoul",
                    "description": "AI-powered terminal assistant",
                    "commands": [
                        {
                            "type": "command",
                            "name": "consoul chat",
                            "description": "Start chat mode",
                            "arguments": [],
                            "options": [],
                        },
                        {
                            "type": "command",
                            "name": "consoul tui",
                            "description": "Start TUI mode",
                            "arguments": [],
                            "options": [],
                        },
                    ],
                    "arguments": [],
                    "options": [],
                }
            ],
        }

        result = parse_command_schema(schema)

        # Should have the main group command
        assert len(result) >= 1
        assert result[0]["name"] == "consoul"
        assert result[0]["type"] == "group"

        # Should have subcommands with extracted names
        subcommands = result[0]["commands"]
        assert len(subcommands) == 2
        assert subcommands[0]["name"] == "chat"
        assert subcommands[1]["name"] == "tui"

    def test_nested_groups(self) -> None:
        """Test handling of nested command groups."""
        schema = {
            "type": "application",
            "name": "app",
            "commands": [
                {
                    "type": "group",
                    "name": "parent",
                    "description": "Parent group",
                    "commands": [
                        {
                            "type": "group",
                            "name": "parent child",
                            "description": "Child group",
                            "commands": [
                                {
                                    "type": "command",
                                    "name": "parent child grandchild",
                                    "description": "Grandchild command",
                                    "arguments": [],
                                    "options": [],
                                }
                            ],
                            "arguments": [],
                            "options": [],
                        }
                    ],
                    "arguments": [],
                    "options": [],
                }
            ],
        }

        # Should not raise IndexError even with deep nesting
        result = parse_command_schema(schema)

        # Should process all levels
        assert len(result) >= 1

    def test_single_command_schema(self, base_command_schema: dict) -> None:
        """Test parsing a single command (not a group)."""
        result = parse_command_schema(base_command_schema)

        assert len(result) == 1
        assert result[0]["name"] == "test"
        assert result[0]["type"] == "command"
        assert result[0]["description"] == "Test command"

    def test_preserves_command_metadata(self, group_schema: dict) -> None:
        """Test that command metadata is preserved correctly."""
        group_schema["commands"] = [
            {
                "type": "command",
                "name": "consoul test",
                "description": "Test description",
                "arguments": [{"name": "arg1"}],
                "options": [{"name": "--option1"}],
            }
        ]

        result = parse_command_schema(group_schema)

        subcommand = result[0]["commands"][0]
        assert subcommand["description"] == "Test description"
        assert subcommand["arguments"] == [{"name": "arg1"}]
        assert subcommand["options"] == [{"name": "--option1"}]

    def test_empty_commands_list(self) -> None:
        """Test handling of group with no subcommands."""
        schema = {
            "type": "group",
            "name": "empty-group",
            "description": "Group with no commands",
            "commands": [],
            "arguments": [],
            "options": [],
        }

        result = parse_command_schema(schema)

        assert len(result) == 1
        assert result[0]["commands"] == []

"""Test grep_search tool implementation."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.ai.tools.implementations.grep_search import (
    _build_grep_command,
    _build_ripgrep_command,
    _detect_ripgrep,
    _execute_search,
    _parse_grep_output,
    _parse_ripgrep_output,
    get_grep_search_config,
    grep_search,
    set_grep_search_config,
)
from consoul.config.models import GrepSearchToolConfig


class TestRipgrepDetection:
    """Test ripgrep detection logic."""

    def test_detect_ripgrep_available(self) -> None:
        """Test ripgrep detection when rg is available."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = _detect_ripgrep()

            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["rg", "--version"]

    def test_detect_ripgrep_unavailable(self) -> None:
        """Test ripgrep detection when rg is not available."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = _detect_ripgrep()

            assert result is False

    def test_detect_ripgrep_timeout(self) -> None:
        """Test ripgrep detection handles timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("rg", 2)

            result = _detect_ripgrep()

            assert result is False


class TestCommandBuilding:
    """Test command building for ripgrep and grep."""

    def test_build_ripgrep_basic(self) -> None:
        """Test basic ripgrep command building."""
        cmd = _build_ripgrep_command("def main", "src/")

        assert cmd == ["rg", "--json", "def main", "src/"]

    def test_build_ripgrep_with_glob(self) -> None:
        """Test ripgrep command with glob pattern."""
        cmd = _build_ripgrep_command("def main", "src/", glob_pattern="*.py")

        assert cmd == ["rg", "--json", "def main", "src/", "--glob", "*.py"]

    def test_build_ripgrep_case_insensitive(self) -> None:
        """Test ripgrep command with case insensitive search."""
        cmd = _build_ripgrep_command("def main", "src/", case_sensitive=False)

        assert cmd == ["rg", "--json", "def main", "src/", "-i"]

    def test_build_ripgrep_with_context(self) -> None:
        """Test ripgrep command with context lines."""
        cmd = _build_ripgrep_command("def main", "src/", context_lines=2)

        assert cmd == ["rg", "--json", "def main", "src/", "-C", "2"]

    def test_build_ripgrep_all_options(self) -> None:
        """Test ripgrep command with all options."""
        cmd = _build_ripgrep_command(
            pattern="def main",
            path="src/",
            glob_pattern="*.py",
            case_sensitive=False,
            context_lines=3,
        )

        assert cmd == [
            "rg",
            "--json",
            "def main",
            "src/",
            "--glob",
            "*.py",
            "-i",
            "-C",
            "3",
        ]

    def test_build_grep_basic(self) -> None:
        """Test basic grep command building."""
        cmd = _build_grep_command("def main", "src/")

        assert cmd == ["grep", "-rn", "def main", "src/"]

    def test_build_grep_with_glob(self) -> None:
        """Test grep command with glob pattern."""
        cmd = _build_grep_command("def main", "src/", glob_pattern="*.py")

        assert cmd == ["grep", "-rn", "def main", "src/", "--include", "*.py"]

    def test_build_grep_case_insensitive(self) -> None:
        """Test grep command with case insensitive search."""
        cmd = _build_grep_command("def main", "src/", case_sensitive=False)

        assert cmd == ["grep", "-rn", "def main", "src/", "-i"]

    def test_build_grep_with_context(self) -> None:
        """Test grep command with context lines."""
        cmd = _build_grep_command("def main", "src/", context_lines=2)

        assert cmd == ["grep", "-rn", "def main", "src/", "-C", "2"]

    def test_build_grep_all_options(self) -> None:
        """Test grep command with all options."""
        cmd = _build_grep_command(
            pattern="def main",
            path="src/",
            glob_pattern="*.py",
            case_sensitive=False,
            context_lines=3,
        )

        assert cmd == [
            "grep",
            "-rn",
            "def main",
            "src/",
            "--include",
            "*.py",
            "-i",
            "-C",
            "3",
        ]


class TestRipgrepOutputParsing:
    """Test ripgrep JSON output parsing."""

    def test_parse_ripgrep_single_match(self) -> None:
        """Test parsing single ripgrep match."""
        output = json.dumps(
            {
                "type": "match",
                "data": {
                    "path": {"text": "src/main.py"},
                    "line_number": 10,
                    "lines": {"text": "def main():\n"},
                },
            }
        )

        results = _parse_ripgrep_output(output)

        assert len(results) == 1
        assert results[0]["file"] == "src/main.py"
        assert results[0]["line"] == 10
        assert results[0]["text"] == "def main():"
        assert results[0]["context_before"] == []
        assert results[0]["context_after"] == []

    def test_parse_ripgrep_with_context(self) -> None:
        """Test parsing ripgrep match with context."""
        match_entry = {
            "type": "match",
            "data": {
                "path": {"text": "src/utils.py"},
                "line_number": 42,
                "lines": {"text": "    result = calculate()\n"},
            },
        }

        context_before = {
            "type": "context",
            "data": {
                "lines": {"text": "def process():\n"},
            },
        }

        context_after = {
            "type": "context",
            "data": {
                "lines": {"text": "    return result\n"},
            },
        }

        output = "\n".join(
            [
                json.dumps(context_before),
                json.dumps(match_entry),
                json.dumps(context_after),
            ]
        )

        results = _parse_ripgrep_output(output)

        assert len(results) == 1
        assert results[0]["file"] == "src/utils.py"
        assert results[0]["line"] == 42
        assert results[0]["text"] == "    result = calculate()"
        assert results[0]["context_before"] == ["def process():"]
        assert results[0]["context_after"] == ["    return result"]

    def test_parse_ripgrep_multiple_matches(self) -> None:
        """Test parsing multiple ripgrep matches."""
        match1 = {
            "type": "match",
            "data": {
                "path": {"text": "src/foo.py"},
                "line_number": 1,
                "lines": {"text": "def foo():\n"},
            },
        }

        match2 = {
            "type": "match",
            "data": {
                "path": {"text": "src/bar.py"},
                "line_number": 2,
                "lines": {"text": "def bar():\n"},
            },
        }

        output = "\n".join([json.dumps(match1), json.dumps(match2)])

        results = _parse_ripgrep_output(output)

        assert len(results) == 2
        assert results[0]["file"] == "src/foo.py"
        assert results[1]["file"] == "src/bar.py"

    def test_parse_ripgrep_empty_output(self) -> None:
        """Test parsing empty ripgrep output."""
        results = _parse_ripgrep_output("")

        assert results == []

    def test_parse_ripgrep_malformed_json(self) -> None:
        """Test parsing malformed JSON is skipped."""
        output = "not json\n" + json.dumps(
            {
                "type": "match",
                "data": {
                    "path": {"text": "file.py"},
                    "line_number": 1,
                    "lines": {"text": "code\n"},
                },
            }
        )

        results = _parse_ripgrep_output(output)

        # Should skip malformed line but parse valid JSON
        assert len(results) == 1
        assert results[0]["file"] == "file.py"


class TestGrepOutputParsing:
    """Test grep line-based output parsing."""

    def test_parse_grep_single_match(self) -> None:
        """Test parsing single grep match."""
        output = "src/main.py:10:def main():"

        results = _parse_grep_output(output)

        assert len(results) == 1
        assert results[0]["file"] == "src/main.py"
        assert results[0]["line"] == 10
        assert results[0]["text"] == "def main():"
        assert results[0]["context_before"] == []
        assert results[0]["context_after"] == []

    def test_parse_grep_with_context(self) -> None:
        """Test parsing grep match with context."""
        output = """src/utils.py-40-def process():
src/utils.py-41-    # Comment
src/utils.py:42:    result = calculate()
src/utils.py-43-    return result"""

        results = _parse_grep_output(output, context_lines=2)

        assert len(results) == 1
        assert results[0]["file"] == "src/utils.py"
        assert results[0]["line"] == 42
        assert results[0]["text"] == "    result = calculate()"
        assert results[0]["context_before"] == ["def process():", "    # Comment"]
        assert results[0]["context_after"] == ["    return result"]

    def test_parse_grep_multiple_matches(self) -> None:
        """Test parsing multiple grep matches."""
        output = """src/foo.py:1:def foo():
--
src/bar.py:2:def bar():"""

        results = _parse_grep_output(output)

        assert len(results) == 2
        assert results[0]["file"] == "src/foo.py"
        assert results[0]["line"] == 1
        assert results[1]["file"] == "src/bar.py"
        assert results[1]["line"] == 2

    def test_parse_grep_empty_output(self) -> None:
        """Test parsing empty grep output."""
        results = _parse_grep_output("")

        assert results == []


class TestSearchExecution:
    """Test search execution with ripgrep and grep."""

    def test_execute_search_ripgrep(self) -> None:
        """Test search execution with ripgrep."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._detect_ripgrep",
            ) as mock_detect,
            patch("subprocess.run") as mock_run,
        ):
            mock_detect.return_value = True

            rg_output = json.dumps(
                {
                    "type": "match",
                    "data": {
                        "path": {"text": "test.py"},
                        "line_number": 1,
                        "lines": {"text": "match\n"},
                    },
                }
            )

            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=rg_output,
                stderr="",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / "test.py"
                test_file.write_text("match")

                results = _execute_search("match", tmpdir)

                assert len(results) == 1
                assert results[0]["file"] == "test.py"
                assert results[0]["line"] == 1

    def test_execute_search_grep_fallback(self) -> None:
        """Test search execution falls back to grep."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._detect_ripgrep",
            ) as mock_detect,
            patch("subprocess.run") as mock_run,
        ):
            mock_detect.return_value = False

            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test.py:1:match",
                stderr="",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / "test.py"
                test_file.write_text("match")

                results = _execute_search("match", tmpdir)

                assert len(results) == 1
                assert results[0]["file"] == "test.py"
                assert results[0]["line"] == 1

    def test_execute_search_no_matches(self) -> None:
        """Test search with no matches (exit code 1)."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._detect_ripgrep",
            ) as mock_detect,
            patch("subprocess.run") as mock_run,
        ):
            mock_detect.return_value = True

            mock_run.return_value = MagicMock(
                returncode=1,  # No matches
                stdout="",
                stderr="",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                results = _execute_search("nonexistent", tmpdir)

                assert results == []

    def test_execute_search_invalid_path(self) -> None:
        """Test search with invalid path raises error."""
        with pytest.raises(ToolExecutionError) as exc_info:
            _execute_search("pattern", "/nonexistent/path")

        assert "does not exist" in str(exc_info.value)

    def test_execute_search_timeout(self) -> None:
        """Test search timeout raises error."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._detect_ripgrep",
            ) as mock_detect,
            patch("subprocess.run") as mock_run,
        ):
            mock_detect.return_value = True
            mock_run.side_effect = subprocess.TimeoutExpired("rg", 30)

            with (
                tempfile.TemporaryDirectory() as tmpdir,
                pytest.raises(ToolExecutionError) as exc_info,
            ):
                _execute_search("pattern", tmpdir)

            assert "timed out" in str(exc_info.value).lower()

    def test_execute_search_command_error(self) -> None:
        """Test search command error raises ToolExecutionError."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._detect_ripgrep",
            ) as mock_detect,
            patch("subprocess.run") as mock_run,
        ):
            mock_detect.return_value = True

            mock_run.return_value = MagicMock(
                returncode=2,  # Error
                stdout="",
                stderr="Error message",
            )

            with (
                tempfile.TemporaryDirectory() as tmpdir,
                pytest.raises(ToolExecutionError) as exc_info,
            ):
                _execute_search("pattern", tmpdir)

            assert "failed" in str(exc_info.value).lower()


class TestGrepSearchTool:
    """Test grep_search tool function."""

    def test_grep_search_basic(self) -> None:
        """Test basic grep_search usage."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._execute_search",
            ) as mock_execute,
        ):
            mock_execute.return_value = [
                {
                    "file": "test.py",
                    "line": 1,
                    "text": "match",
                    "context_before": [],
                    "context_after": [],
                }
            ]

            result = grep_search.invoke({"pattern": "pattern", "path": "src/"})

            parsed = json.loads(result)
            assert len(parsed) == 1
            assert parsed[0]["file"] == "test.py"
            assert parsed[0]["line"] == 1

    def test_grep_search_with_options(self) -> None:
        """Test grep_search with all options."""
        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._execute_search",
            ) as mock_execute,
        ):
            mock_execute.return_value = []

            grep_search.invoke(
                {
                    "pattern": "def main",
                    "path": "src/",
                    "glob_pattern": "*.py",
                    "case_sensitive": False,
                    "context_lines": 2,
                    "timeout": 60,
                }
            )

            mock_execute.assert_called_once_with(
                pattern="def main",
                path="src/",
                glob_pattern="*.py",
                case_sensitive=False,
                context_lines=2,
                timeout=60,
            )

    def test_grep_search_uses_config_timeout(self) -> None:
        """Test grep_search uses config timeout when not specified."""
        config = GrepSearchToolConfig(timeout=45)
        set_grep_search_config(config)

        with (
            patch(
                "consoul.ai.tools.implementations.grep_search._execute_search",
            ) as mock_execute,
        ):
            mock_execute.return_value = []

            grep_search.invoke({"pattern": "pattern"})

            # Should use config timeout
            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs["timeout"] == 45


class TestConfig:
    """Test configuration management."""

    def test_set_get_config(self) -> None:
        """Test setting and getting config."""
        config = GrepSearchToolConfig(timeout=60)
        set_grep_search_config(config)

        retrieved = get_grep_search_config()

        assert retrieved.timeout == 60

    def test_get_config_default(self) -> None:
        """Test getting default config when not set."""
        # Reset to None
        set_grep_search_config(None)  # type: ignore[arg-type]

        config = get_grep_search_config()

        assert isinstance(config, GrepSearchToolConfig)
        assert config.timeout == 30  # Default

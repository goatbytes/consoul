"""Tests for read file tool implementation."""

import pytest

from consoul.ai.tools.implementations.read import (
    _format_with_line_numbers,
    _is_binary_file,
    _is_pdf_file,
    _read_with_encoding_fallback,
    _validate_extension,
    _validate_path,
    read_file,
)
from consoul.config.models import ReadToolConfig


class TestFormatWithLineNumbers:
    """Tests for line numbering formatting."""

    def test_format_simple_lines(self):
        """Test basic line numbering."""
        lines = ["hello\n", "world\n"]
        result, total_chars, truncated = _format_with_line_numbers(lines)

        assert result == "     1\thello\n     2\tworld"
        assert total_chars == 25  # len("     1\thello\n     2\tworld")
        assert truncated is False

    def test_format_with_offset(self):
        """Test line numbering with custom start."""
        lines = ["line100\n", "line101\n"]
        result, total_chars, truncated = _format_with_line_numbers(
            lines, start_line=100
        )

        assert result == "   100\tline100\n   101\tline101"
        assert total_chars == 29  # len("   100\tline100\n   101\tline101")
        assert truncated is False

    def test_format_strips_newlines(self):
        """Test that trailing newlines are stripped."""
        lines = ["hello\r\n", "world\n", "test\r"]
        result, total_chars, truncated = _format_with_line_numbers(lines)

        assert result == "     1\thello\n     2\tworld\n     3\ttest"
        assert total_chars == 37  # len("     1\thello\n     2\tworld\n     3\ttest")
        assert truncated is False

    def test_format_empty_list(self):
        """Test formatting empty line list."""
        result, total_chars, truncated = _format_with_line_numbers([])
        assert result == ""
        assert total_chars == 0
        assert truncated is False

    def test_format_single_line(self):
        """Test formatting single line."""
        result, total_chars, truncated = _format_with_line_numbers(["test\n"])
        assert result == "     1\ttest"
        assert total_chars == 11  # len("     1\ttest")
        assert truncated is False


class TestIsBinaryFile:
    """Tests for binary file detection."""

    def test_text_file_not_binary(self, tmp_path):
        """Test that text files are not detected as binary."""
        file_path = tmp_path / "text.txt"
        file_path.write_text("Hello, world!")

        assert not _is_binary_file(file_path)

    def test_binary_file_detected(self, tmp_path):
        """Test that binary files with null bytes are detected."""
        file_path = tmp_path / "binary.dat"
        file_path.write_bytes(b"Hello\x00World")

        assert _is_binary_file(file_path)

    def test_empty_file_not_binary(self, tmp_path):
        """Test that empty files are not detected as binary."""
        file_path = tmp_path / "empty.txt"
        file_path.touch()

        assert not _is_binary_file(file_path)

    def test_nonexistent_file_not_binary(self, tmp_path):
        """Test that nonexistent files return False."""
        file_path = tmp_path / "nonexistent.txt"

        assert not _is_binary_file(file_path)


class TestValidatePath:
    """Tests for path validation."""

    def test_valid_path(self, tmp_path):
        """Test that valid file paths pass validation."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        config = ReadToolConfig()
        result = _validate_path(str(file_path), config)

        assert result == file_path.resolve()

    def test_nonexistent_file_raises(self, tmp_path):
        """Test that nonexistent files raise ValueError."""
        file_path = tmp_path / "nonexistent.txt"
        config = ReadToolConfig()

        with pytest.raises(ValueError, match="File not found"):
            _validate_path(str(file_path), config)

    def test_directory_raises(self, tmp_path):
        """Test that directories raise ValueError."""
        config = ReadToolConfig()

        with pytest.raises(ValueError, match="Cannot read directory"):
            _validate_path(str(tmp_path), config)

    def test_path_traversal_raises(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        config = ReadToolConfig()
        malicious_path = str(file_path.parent / ".." / file_path.name)

        with pytest.raises(ValueError, match="Path traversal"):
            _validate_path(malicious_path, config)

    def test_blocked_path_raises(self, tmp_path):
        """Test that blocked paths raise ValueError."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        # Add parent dir to blocked paths
        config = ReadToolConfig(blocked_paths=[str(tmp_path)])

        with pytest.raises(ValueError, match="not allowed"):
            _validate_path(str(file_path), config)

    def test_default_blocked_paths(self):
        """Test that default blocked paths are enforced."""
        config = ReadToolConfig()

        # Default blocked paths include /etc/shadow
        with pytest.raises(ValueError, match="not allowed"):
            _validate_path("/etc/shadow", config)


class TestValidateExtension:
    """Tests for extension validation."""

    def test_allowed_extension_passes(self, tmp_path):
        """Test that allowed extensions pass validation."""
        file_path = tmp_path / "test.py"
        file_path.touch()

        config = ReadToolConfig(allowed_extensions=[".py", ".txt"])
        _validate_extension(file_path, config)  # Should not raise

    def test_disallowed_extension_raises(self, tmp_path):
        """Test that disallowed extensions raise ValueError."""
        file_path = tmp_path / "test.exe"
        file_path.touch()

        config = ReadToolConfig(allowed_extensions=[".py", ".txt"])

        with pytest.raises(ValueError, match="not allowed"):
            _validate_extension(file_path, config)

    def test_empty_allowed_list_allows_all(self, tmp_path):
        """Test that empty allowed_extensions list allows all."""
        file_path = tmp_path / "test.anything"
        file_path.touch()

        config = ReadToolConfig(allowed_extensions=[])
        _validate_extension(file_path, config)  # Should not raise

    def test_case_insensitive_extension(self, tmp_path):
        """Test that extension matching is case-insensitive."""
        file_path = tmp_path / "test.PY"
        file_path.touch()

        config = ReadToolConfig(allowed_extensions=[".py"])
        _validate_extension(file_path, config)  # Should not raise


class TestReadWithEncodingFallback:
    """Tests for encoding fallback."""

    def test_utf8_file(self, tmp_path):
        """Test reading UTF-8 file."""
        file_path = tmp_path / "utf8.txt"
        file_path.write_text("Hello, 世界!", encoding="utf-8")

        result = _read_with_encoding_fallback(file_path)

        assert result == "Hello, 世界!"

    def test_utf8_with_bom(self, tmp_path):
        """Test reading UTF-8 file with BOM."""
        file_path = tmp_path / "utf8bom.txt"
        # Write bytes with BOM directly
        file_path.write_bytes(b"\xef\xbb\xbfHello, world!")

        result = _read_with_encoding_fallback(file_path)

        # UTF-8 will successfully read BOM (but not strip it)
        # This is acceptable behavior - the content is still readable
        assert "Hello, world!" in result

    def test_latin1_fallback(self, tmp_path):
        """Test fallback to Latin-1 encoding."""
        file_path = tmp_path / "latin1.txt"
        # Write with Latin-1 encoding (contains chars not valid in UTF-8)
        file_path.write_bytes(b"Hello, \xe9cole!")  # é in Latin-1

        result = _read_with_encoding_fallback(file_path)

        assert "cole" in result  # Should decode somehow


class TestReadFile:
    """Tests for read_file tool function."""

    def test_read_simple_file(self, tmp_path):
        """Test reading a simple text file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("line1\nline2\nline3\n")

        result = read_file.invoke({"file_path": str(file_path)})

        assert "     1\tline1" in result
        assert "     2\tline2" in result
        assert "     3\tline3" in result

    def test_read_with_offset(self, tmp_path):
        """Test reading with offset parameter."""
        file_path = tmp_path / "test.txt"
        content = "\n".join([f"line{i}" for i in range(1, 11)])
        file_path.write_text(content)

        result = read_file.invoke(
            {"file_path": str(file_path), "offset": 5, "limit": 3}
        )

        assert "     5\tline5" in result
        assert "     6\tline6" in result
        assert "     7\tline7" in result
        assert "line1" not in result
        assert "line10" not in result

    def test_read_with_limit_only(self, tmp_path):
        """Test reading with limit parameter only."""
        file_path = tmp_path / "test.txt"
        content = "\n".join([f"line{i}" for i in range(1, 11)])
        file_path.write_text(content)

        result = read_file.invoke({"file_path": str(file_path), "limit": 3})

        assert "     1\tline1" in result
        assert "     2\tline2" in result
        assert "     3\tline3" in result
        assert "line4" not in result

    def test_read_offset_beyond_file(self, tmp_path):
        """Test that offset beyond file length returns error."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("line1\nline2\n")

        result = read_file.invoke({"file_path": str(file_path), "offset": 100})

        assert "❌" in result
        assert "exceeds file length" in result

    def test_read_empty_file(self, tmp_path):
        """Test reading empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.touch()

        result = read_file.invoke({"file_path": str(file_path)})

        assert result == "[File is empty]"

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading nonexistent file."""
        result = read_file.invoke({"file_path": str(tmp_path / "nonexistent.txt")})

        assert "❌" in result
        assert "File not found" in result

    def test_read_binary_file(self, tmp_path):
        """Test reading binary file returns error."""
        # Use .bin extension which is not in allowed_extensions
        file_path = tmp_path / "binary.bin"
        file_path.write_bytes(b"Hello\x00World")

        result = read_file.invoke({"file_path": str(file_path)})

        assert "❌" in result
        # Should be blocked by extension or binary detection
        assert "not allowed" in result or "Unsupported binary file" in result

    def test_read_directory(self, tmp_path):
        """Test that reading directory returns error."""
        result = read_file.invoke({"file_path": str(tmp_path)})

        assert "❌" in result
        assert "Cannot read directory" in result

    def test_read_blocked_path(self):
        """Test that reading blocked path returns error."""
        result = read_file.invoke({"file_path": "/etc/shadow"})

        assert "❌" in result
        assert "not allowed" in result

    def test_read_disallowed_extension(self, tmp_path):
        """Test that disallowed extension returns error."""
        file_path = tmp_path / "test.exe"
        file_path.write_text("content")

        result = read_file.invoke({"file_path": str(file_path)})

        assert "❌" in result
        assert "not allowed" in result

    def test_read_utf8_file(self, tmp_path):
        """Test reading UTF-8 file with unicode."""
        file_path = tmp_path / "utf8.txt"
        file_path.write_text("Hello, 世界!\nこんにちは\n")

        result = read_file.invoke({"file_path": str(file_path)})

        assert "     1\tHello, 世界!" in result
        assert "     2\tこんにちは" in result

    def test_read_preserves_line_numbers_with_offset(self, tmp_path):
        """Test that line numbers are preserved (not reset) with offset."""
        file_path = tmp_path / "test.txt"
        content = "\n".join([f"line{i}" for i in range(1, 101)])
        file_path.write_text(content)

        result = read_file.invoke(
            {"file_path": str(file_path), "offset": 50, "limit": 5}
        )

        # Line numbers should be 50-54, not 1-5
        assert "    50\tline50" in result
        assert "    51\tline51" in result
        assert "     1\t" not in result  # Should NOT restart at 1

    def test_read_file_without_trailing_newline(self, tmp_path):
        """Test reading file without trailing newline."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("line1\nline2")  # No trailing newline

        result = read_file.invoke({"file_path": str(file_path)})

        assert "     1\tline1" in result
        assert "     2\tline2" in result

    def test_read_single_line_file(self, tmp_path):
        """Test reading single-line file."""
        file_path = tmp_path / "single.txt"
        file_path.write_text("single line")

        result = read_file.invoke({"file_path": str(file_path)})

        assert result == "     1\tsingle line"

    def test_read_file_with_blank_lines(self, tmp_path):
        """Test reading file with blank lines."""
        file_path = tmp_path / "blank.txt"
        file_path.write_text("line1\n\nline3\n")

        result = read_file.invoke({"file_path": str(file_path)})

        assert "     1\tline1" in result
        assert "     2\t" in result  # Blank line
        assert "     3\tline3" in result

    def test_read_applies_default_limit_with_offset(self, tmp_path):
        """Test that max_lines_default is applied when offset but no limit."""
        file_path = tmp_path / "large.txt"
        # Create file with 5000 lines
        content = "\n".join([f"line{i}" for i in range(1, 5001)])
        file_path.write_text(content)

        # Offset without limit should use config.max_lines_default (2000)
        result = read_file.invoke({"file_path": str(file_path), "offset": 1})

        # Should have lines 1-2000
        assert "     1\tline1" in result
        assert "  2000\tline2000" in result
        # Should NOT have line 2001
        assert "line2001" not in result

    def test_read_handles_path_traversal_attempt(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        # Try to read with .. in path
        malicious_path = str(file_path.parent / ".." / file_path.name)
        result = read_file.invoke({"file_path": malicious_path})

        assert "❌" in result
        assert "Path traversal" in result

    def test_read_windows_line_endings(self, tmp_path):
        """Test reading file with Windows line endings."""
        file_path = tmp_path / "windows.txt"
        file_path.write_text("line1\r\nline2\r\nline3\r\n")

        result = read_file.invoke({"file_path": str(file_path)})

        assert "     1\tline1" in result
        assert "     2\tline2" in result
        assert "     3\tline3" in result
        # Should not have \r in output
        assert "\r" not in result

    def test_read_mixed_line_endings(self, tmp_path):
        """Test reading file with mixed line endings."""
        file_path = tmp_path / "mixed.txt"
        # Mix of \n, \r\n, and \r
        file_path.write_bytes(b"line1\nline2\r\nline3\rline4")

        result = read_file.invoke({"file_path": str(file_path)})

        # Should handle gracefully
        assert "line1" in result
        assert "line2" in result

    def test_read_large_file_applies_default_limit(self, tmp_path):
        """Test that reading large file without offset/limit applies max_lines_default.

        Regression test for bug where max_lines_default was only applied with offset,
        allowing large files to stream entirely and burst LLM context.
        """
        from consoul.ai.tools.implementations.read import set_read_config

        # Create file with 3000 lines
        file_path = tmp_path / "large.txt"
        content = "\n".join([f"line{i}" for i in range(1, 3001)])
        file_path.write_text(content)

        # Set max_lines_default to 100
        config = ReadToolConfig(max_lines_default=100)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should only contain first 100 lines
            assert "     1\tline1" in result
            assert "   100\tline100" in result
            assert "   101\tline101" not in result
            assert "  3000\tline3000" not in result

            # Should have truncation message
            assert "Output limited to 100 lines" in result
            assert "file has 3000 total lines" in result
            assert "Use offset/limit parameters to read more" in result
        finally:
            # Reset config
            set_read_config(ReadToolConfig())

    def test_read_extensionless_file(self, tmp_path):
        """Test reading extensionless files like Dockerfile, Makefile, LICENSE.

        Regression test for bug where Path.suffix='' never matched allowed_extensions,
        rejecting common text files like Dockerfile.
        """
        # Create extensionless file
        file_path = tmp_path / "Dockerfile"
        file_path.write_text("FROM python:3.12\nRUN pip install consoul")

        result = read_file.invoke({"file_path": str(file_path)})

        # Should succeed ('' is in default allowed_extensions)
        assert "     1\tFROM python:3.12" in result
        assert "     2\tRUN pip install consoul" in result

    def test_read_case_insensitive_extension_config(self, tmp_path):
        """Test extension matching is case-insensitive.

        Regression test for bug where config=[".TXT"] rejected .txt files
        because suffix.lower() didn't match verbatim config values.
        """
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world")

        # Config with uppercase extension
        config = ReadToolConfig(allowed_extensions=[".TXT", ".MD"])
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should succeed despite case mismatch
            assert "     1\thello world" in result
        finally:
            # Reset config
            set_read_config(ReadToolConfig())

    def test_read_long_line_truncated(self, tmp_path):
        """Test that lines exceeding max_line_length are truncated.

        Regression test for SOUL-82: Very long lines (minified JS, logs)
        should be truncated to prevent context overflow.
        """
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "long_line.txt"
        # Create line with 3000 characters
        long_line = "x" * 3000
        file_path.write_text(f"short line\n{long_line}\nanother short line")

        # Use default config (max_line_length=2000)
        config = ReadToolConfig()
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # First line should be intact
            assert "     1\tshort line" in result
            # Second line should be truncated with indicator
            assert "     2\t" + "x" * 2000 + " …[line truncated]" in result
            # Third line should be intact
            assert "     3\tanother short line" in result
        finally:
            set_read_config(ReadToolConfig())

    def test_read_multiple_long_lines(self, tmp_path):
        """Test that multiple long lines are all truncated."""
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "multiple_long.txt"
        content = "\n".join(["y" * 2500 for _ in range(5)])
        file_path.write_text(content)

        config = ReadToolConfig(max_line_length=2000)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # All lines should be truncated
            for i in range(1, 6):
                assert f"     {i}\t" + "y" * 2000 + " …[line truncated]" in result
        finally:
            set_read_config(ReadToolConfig())

    def test_read_large_output_truncated(self, tmp_path):
        """Test that total output exceeding max_output_chars is truncated."""
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "large_output.txt"
        # Create file that will produce ~50000 chars of output
        lines = [f"line{i:04d}" + "z" * 100 for i in range(400)]
        file_path.write_text("\n".join(lines))

        config = ReadToolConfig(max_output_chars=10000, max_lines_default=500)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should be truncated
            assert len(result) < 10500  # Some buffer for truncation message
            assert "…[output truncated - use offset/limit to read more]" in result
        finally:
            set_read_config(ReadToolConfig())

    def test_read_exact_line_length(self, tmp_path):
        """Test that line exactly at max_line_length is not truncated."""
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "exact_line.txt"
        exact_line = "a" * 2000  # Exactly at limit
        file_path.write_text(exact_line)

        config = ReadToolConfig(max_line_length=2000)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should NOT be truncated
            assert "…[line truncated]" not in result
            assert "a" * 2000 in result
        finally:
            set_read_config(ReadToolConfig())

    def test_read_exact_output_length(self, tmp_path):
        """Test that output exactly at max_output_chars is not truncated."""
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "exact_output.txt"
        # Calculate to get exactly at output limit
        # Format: "     1\t<content>\n" = 8 chars overhead per line
        line_length = 50
        num_lines = (5000 - 1) // (8 + line_length + 1)  # -1 for final newline
        content = "\n".join(
            [f"b{i:04d}" + "c" * (line_length - 5) for i in range(num_lines)]
        )
        file_path.write_text(content)

        config = ReadToolConfig(max_output_chars=5000, max_lines_default=1000)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should NOT be truncated (at or under limit)
            assert "…[output truncated" not in result
        finally:
            set_read_config(ReadToolConfig())

    def test_read_minified_javascript(self, tmp_path):
        """Test real-world case: minified JavaScript with very long lines."""
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "minified.js"
        # Simulate minified JS - single very long line
        minified = "(function(){var a=1;var b=2;var c=3;" * 200  # ~8000 chars
        file_path.write_text(minified)

        config = ReadToolConfig(max_line_length=2000)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should be truncated
            assert "…[line truncated]" in result
            # Should have exactly 2000 chars of content + indicator
            assert result.count("(function(){var a=1;var b=2;var c=3;") < 100
        finally:
            set_read_config(ReadToolConfig())

    def test_read_empty_file_still_works(self, tmp_path):
        """Verify empty file handling unchanged by SOUL-82."""
        file_path = tmp_path / "empty.txt"
        file_path.touch()

        result = read_file.invoke({"file_path": str(file_path)})

        # Should still return the empty file message
        assert result == "[File is empty]"

    def test_read_exact_limit_no_truncation(self, tmp_path):
        """Regression test: file exactly at max_output_chars should not be truncated.

        Tests the bug fix where total_chars was overcounting by 1, causing files
        exactly at the limit to be incorrectly truncated.
        """
        from consoul.ai.tools.implementations.read import set_read_config

        file_path = tmp_path / "tiny.txt"
        file_path.write_text("abc\n")

        # Output will be "     1\tabc" (11 chars)
        config = ReadToolConfig(max_output_chars=11, max_lines_default=1000)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": str(file_path)})

            # Should NOT be truncated
            assert result == "     1\tabc"
            assert "…[output truncated" not in result
        finally:
            set_read_config(ReadToolConfig())


class TestPDFReading:
    """Tests for PDF file reading functionality.

    Note: These tests require the optional pypdf dependency.
    Install with: pip install consoul[pdf] or poetry install --extras pdf
    """

    @pytest.fixture(autouse=True)
    def require_pypdf(self):
        """Skip all PDF tests if pypdf is not installed."""
        pytest.importorskip(
            "pypdf", reason="pypdf not installed (pip install consoul[pdf])"
        )

    @pytest.fixture
    def pdf_path(self):
        """Return path to test PDF file."""
        from pathlib import Path

        pdf = Path(
            ".local/read_tool/Designing a Comprehensive __Read__ Tool for Consoul AI Agent.pdf"
        )
        if not pdf.exists():
            pytest.skip("Test PDF not found")
        return str(pdf)

    @pytest.fixture
    def mock_pdf(self, tmp_path, monkeypatch):
        """Create a mock PDF file for testing."""
        # Create a simple PDF-like file (not a real PDF, for basic tests)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\nTest content")
        return pdf_file

    def test_read_pdf_basic(self, pdf_path):
        """Test basic PDF reading."""
        result = read_file.invoke({"file_path": pdf_path})

        # Should contain page markers
        assert "=== Page 1 ===" in result
        # Should have some content
        assert len(result) > 100

    def test_read_pdf_with_page_range(self, pdf_path):
        """Test PDF reading with page range."""
        result = read_file.invoke(
            {"file_path": pdf_path, "start_page": 1, "end_page": 2}
        )

        # Should contain pages 1 and 2
        assert "=== Page 1 ===" in result
        assert "=== Page 2 ===" in result
        # Should not contain page 3
        assert "=== Page 3 ===" not in result

    def test_read_pdf_single_page(self, pdf_path):
        """Test reading single PDF page."""
        result = read_file.invoke(
            {"file_path": pdf_path, "start_page": 2, "end_page": 2}
        )

        # Should only contain page 2
        assert "=== Page 2 ===" in result
        assert "=== Page 1 ===" not in result
        assert "=== Page 3 ===" not in result

    def test_read_pdf_start_page_only(self, pdf_path):
        """Test PDF reading with only start_page specified."""
        result = read_file.invoke({"file_path": pdf_path, "start_page": 2})

        # Should start from page 2
        assert "=== Page 2 ===" in result
        assert "=== Page 1 ===" not in result

    def test_read_pdf_disabled(self, pdf_path):
        """Test PDF reading when disabled in config."""
        from consoul.ai.tools.implementations.read import set_read_config

        # Disable PDF reading
        config = ReadToolConfig(enable_pdf=False)
        set_read_config(config)

        try:
            result = read_file.invoke({"file_path": pdf_path})

            assert "PDF reading is disabled" in result
            assert "❌" in result
        finally:
            # Reset config
            set_read_config(ReadToolConfig())

    def test_read_pdf_max_pages_limit(self, pdf_path):
        """Test PDF max pages limit enforcement."""
        from consoul.ai.tools.implementations.read import set_read_config

        # Set max pages to 2
        config = ReadToolConfig(pdf_max_pages=2)
        set_read_config(config)

        try:
            # Try to read more than 2 pages
            result = read_file.invoke(
                {"file_path": pdf_path, "start_page": 1, "end_page": 10}
            )

            # Should limit to 2 pages
            assert "=== Page 1 ===" in result
            assert "=== Page 2 ===" in result
            assert "=== Page 3 ===" not in result
            # Should have note about limiting
            assert "limited to 2 pages" in result.lower()
        finally:
            # Reset config
            set_read_config(ReadToolConfig())

    def test_read_pdf_invalid_page_range(self, pdf_path):
        """Test PDF reading with invalid page range."""
        # Start page > end page
        result = read_file.invoke(
            {"file_path": pdf_path, "start_page": 5, "end_page": 2}
        )

        assert "❌" in result
        assert "must be >=" in result

    def test_read_pdf_page_exceeds_length(self, pdf_path):
        """Test PDF reading with start page exceeding PDF length."""
        result = read_file.invoke({"file_path": pdf_path, "start_page": 1000})

        assert "❌" in result
        assert "exceeds PDF length" in result

    def test_read_pdf_missing_pypdf(self, mock_pdf, monkeypatch):
        """Test error when pypdf is not installed."""
        # Mock import to fail
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("No module named 'pypdf'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = read_file.invoke({"file_path": str(mock_pdf)})

        assert "❌" in result
        assert "pypdf" in result.lower()
        assert "pip install consoul[pdf]" in result

    def test_read_pdf_text_params_ignored(self, pdf_path):
        """Test that text file params are ignored for PDFs."""
        # offset and limit should be ignored for PDFs
        result = read_file.invoke({"file_path": pdf_path, "offset": 10, "limit": 5})

        # Should still read PDF normally (not apply text file params)
        assert "=== Page 1 ===" in result

    def test_is_pdf_file(self):
        """Test PDF file detection."""
        from pathlib import Path

        assert _is_pdf_file(Path("test.pdf"))
        assert _is_pdf_file(Path("test.PDF"))
        assert _is_pdf_file(Path("path/to/file.pdf"))
        assert not _is_pdf_file(Path("test.txt"))
        assert not _is_pdf_file(Path("test.pdf.txt"))
        assert not _is_pdf_file(Path("testpdf"))

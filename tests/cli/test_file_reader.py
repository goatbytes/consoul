"""Tests for file reading and formatting functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from consoul.cli.file_reader import (
    expand_glob_pattern,
    format_files_context,
    read_file_content,
)


class TestReadFileContent:
    """Tests for read_file_content function."""

    def test_read_simple_file(self, tmp_path: Path) -> None:
        """Test reading a simple text file."""
        file_path = tmp_path / "test.txt"
        content = "line 1\nline 2\nline 3"
        file_path.write_text(content)

        result = read_file_content(file_path, include_line_numbers=False)
        assert result == content

    def test_read_file_with_line_numbers(self, tmp_path: Path) -> None:
        """Test reading file with line numbers."""
        file_path = tmp_path / "test.py"
        content = "def foo():\n    pass\n    return True"
        file_path.write_text(content)

        result = read_file_content(file_path, include_line_numbers=True)

        # Should have line numbers
        assert "1→def foo():" in result
        assert "2→    pass" in result
        assert "3→    return True" in result

    def test_file_size_limit(self, tmp_path: Path) -> None:
        """Test file size limit enforcement."""
        file_path = tmp_path / "large.txt"
        # Create file larger than 1KB
        content = "x" * 2000
        file_path.write_text(content)

        with pytest.raises(ValueError, match="exceeds size limit"):
            read_file_content(file_path, max_size=1000)

    def test_binary_file_rejection(self, tmp_path: Path) -> None:
        """Test binary files are rejected."""
        file_path = tmp_path / "binary.bin"
        # Write binary content with null bytes
        file_path.write_bytes(b"test\x00binary\x00content")

        with pytest.raises(ValueError, match="Binary files are not supported"):
            read_file_content(file_path)

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test error on nonexistent file."""
        file_path = tmp_path / "nonexistent.txt"

        with pytest.raises(ValueError, match="File not found"):
            read_file_content(file_path)

    def test_directory_rejection(self, tmp_path: Path) -> None:
        """Test directories are rejected."""
        dir_path = tmp_path / "testdir"
        dir_path.mkdir()

        with pytest.raises(ValueError, match="Path is not a file"):
            read_file_content(dir_path)

    def test_utf8_encoding(self, tmp_path: Path) -> None:
        """Test UTF-8 encoding is handled."""
        file_path = tmp_path / "utf8.txt"
        content = "Hello 世界 🌍"
        file_path.write_text(content, encoding="utf-8")

        result = read_file_content(file_path, include_line_numbers=False)
        assert result == content


class TestPDFSupport:
    """Tests for PDF file reading."""

    def test_read_simple_pdf(self, tmp_path: Path) -> None:
        """Test reading a simple PDF file."""
        pytest.importorskip("pypdf")
        import pypdf

        # Create a simple PDF
        file_path = tmp_path / "test.pdf"
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=200, height=200)

        # PDFs created programmatically may not have extractable text
        # So we'll just test that it doesn't raise an error
        with open(file_path, "wb") as f:
            writer.write(f)

        # Should not raise an error for PDFs
        result = read_file_content(file_path)
        assert isinstance(result, str)
        assert "Page 1" in result

    def test_pdf_missing_library(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test graceful error when pypdf is not installed."""
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"%PDF-1.4\n")  # Minimal PDF header

        # Mock pypdf import failure
        import sys

        monkeypatch.setitem(sys.modules, "pypdf", None)

        with pytest.raises(ValueError, match="PDF support requires 'pypdf' library"):
            read_file_content(file_path)

    def test_pdf_with_text(self, tmp_path: Path) -> None:
        """Test reading PDF with actual text content."""
        pytest.importorskip("pypdf")
        pytest.importorskip("reportlab")

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        # Create PDF with text using reportlab
        file_path = tmp_path / "with_text.pdf"
        c = canvas.Canvas(str(file_path), pagesize=letter)
        c.drawString(100, 750, "Hello from page 1")
        c.showPage()
        c.drawString(100, 750, "Hello from page 2")
        c.save()

        result = read_file_content(file_path)

        # Should contain page markers and text
        assert "=== Page 1 ===" in result
        assert "=== Page 2 ===" in result
        assert "Hello from page 1" in result
        assert "Hello from page 2" in result

    def test_pdf_page_limit(self, tmp_path: Path) -> None:
        """Test PDF page limit is enforced."""
        pytest.importorskip("pypdf")
        pytest.importorskip("reportlab")

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        # Create PDF with many pages (more than default limit of 50)
        file_path = tmp_path / "many_pages.pdf"
        c = canvas.Canvas(str(file_path), pagesize=letter)

        # Create 60 pages
        for i in range(60):
            c.drawString(100, 750, f"Page {i + 1}")
            c.showPage()
        c.save()

        result = read_file_content(file_path)

        # Should only read first 50 pages
        assert "=== Page 50 ===" in result
        assert "=== Page 51 ===" not in result
        assert "Truncated: showing 50 of 60 pages" in result

    def test_empty_pdf(self, tmp_path: Path) -> None:
        """Test reading PDF with no pages."""
        pytest.importorskip("pypdf")
        import pypdf

        file_path = tmp_path / "empty.pdf"
        writer = pypdf.PdfWriter()

        with open(file_path, "wb") as f:
            writer.write(f)

        result = read_file_content(file_path)
        assert "no pages" in result.lower()

    def test_pdf_glob_pattern(self, tmp_path: Path) -> None:
        """Test glob pattern matches PDF files."""
        pytest.importorskip("pypdf")
        import pypdf

        # Create multiple PDFs
        for i in range(3):
            file_path = tmp_path / f"doc{i}.pdf"
            writer = pypdf.PdfWriter()
            writer.add_blank_page(width=200, height=200)
            with open(file_path, "wb") as f:
                writer.write(f)

        # Expand glob pattern for PDFs
        pattern = str(tmp_path / "*.pdf")
        files = expand_glob_pattern(pattern)

        assert len(files) == 3
        assert all(f.suffix == ".pdf" for f in files)


class TestExpandGlobPattern:
    """Tests for expand_glob_pattern function."""

    def test_simple_glob(self, tmp_path: Path) -> None:
        """Test simple glob pattern."""
        # Create test files
        (tmp_path / "test1.py").write_text("content")
        (tmp_path / "test2.py").write_text("content")
        (tmp_path / "test.txt").write_text("content")

        import os

        os.chdir(tmp_path)

        result = expand_glob_pattern("*.py")

        assert len(result) == 2
        assert all(f.suffix == ".py" for f in result)
        # Should be sorted
        assert result[0].name < result[1].name

    def test_recursive_glob(self, tmp_path: Path) -> None:
        """Test recursive ** glob pattern."""
        # Create nested structure
        (tmp_path / "test1.py").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test2.py").write_text("content")

        import os

        os.chdir(tmp_path)

        result = expand_glob_pattern("**/*.py")

        assert len(result) == 2

    def test_no_matches(self, tmp_path: Path) -> None:
        """Test pattern with no matches returns empty list."""
        import os

        os.chdir(tmp_path)

        result = expand_glob_pattern("*.xyz")

        assert result == []

    def test_file_count_limit(self, tmp_path: Path) -> None:
        """Test file count limit enforcement."""
        # Create many files
        for i in range(60):
            (tmp_path / f"test{i}.txt").write_text("content")

        import os

        os.chdir(tmp_path)

        with pytest.raises(ValueError, match="matched 60 files"):
            expand_glob_pattern("*.txt", max_files=50)

    def test_filters_directories(self, tmp_path: Path) -> None:
        """Test directories are filtered out."""
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "dir").mkdir()

        import os

        os.chdir(tmp_path)

        result = expand_glob_pattern("*")

        # Should only include files, not directories
        assert len(result) == 1
        assert result[0].name == "file.txt"


class TestFormatFilesContext:
    """Tests for format_files_context function."""

    def test_single_file(self, tmp_path: Path) -> None:
        """Test formatting single file."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def foo():\n    pass")

        result = format_files_context([file_path])

        assert f'<file path="{file_path}">' in result
        assert "</file>" in result
        assert "def foo():" in result

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Test formatting multiple files."""
        file1 = tmp_path / "test1.py"
        file1.write_text("content1")
        file2 = tmp_path / "test2.py"
        file2.write_text("content2")

        result = format_files_context([file1, file2])

        assert f'<file path="{file1}">' in result
        assert f'<file path="{file2}">' in result
        assert "content1" in result
        assert "content2" in result
        # Files should be separated by blank line between blocks
        assert "</file>\n\n<file" in result

    def test_empty_file_list(self, tmp_path: Path) -> None:
        """Test empty file list returns empty string."""
        result = format_files_context([])

        assert result == ""

    def test_total_size_limit(self, tmp_path: Path) -> None:
        """Test total size limit across multiple files."""
        # Create files that together exceed limit
        file1 = tmp_path / "test1.txt"
        file1.write_text("x" * 3000)
        file2 = tmp_path / "test2.txt"
        file2.write_text("x" * 3000)

        with pytest.raises(ValueError, match="Total file content exceeds size limit"):
            format_files_context([file1, file2], max_total_size=5000)

    def test_propagates_read_errors(self, tmp_path: Path) -> None:
        """Test read errors are propagated with context."""
        # Create file that will fail size check
        file_path = tmp_path / "large.txt"
        file_path.write_text("x" * 200_000)

        with pytest.raises(ValueError, match="Error reading"):
            format_files_context([file_path], max_total_size=500_000)

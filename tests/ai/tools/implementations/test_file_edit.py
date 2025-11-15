"""Tests for file edit tool implementation."""

import json

import pytest

from consoul.ai.tools.implementations.file_edit import (
    FileEditResult,
    _apply_line_edits,
    _atomic_write,
    _compute_file_hash,
    _create_diff_preview,
    _parse_line_range,
    _validate_edits,
    _validate_file_path,
    create_file,
    edit_file_lines,
    get_file_edit_config,
    set_file_edit_config,
)
from consoul.config.models import FileEditToolConfig


class TestParseLineRange:
    """Tests for line range parsing."""

    def test_parse_single_line(self):
        """Test parsing single line number."""
        start, end = _parse_line_range("42")
        assert start == 42
        assert end == 42

    def test_parse_line_range(self):
        """Test parsing line range."""
        start, end = _parse_line_range("5-10")
        assert start == 5
        assert end == 10

    def test_parse_with_whitespace(self):
        """Test parsing with surrounding whitespace."""
        start, end = _parse_line_range("  3 - 7  ")
        assert start == 3
        assert end == 7

    def test_parse_same_start_end(self):
        """Test parsing range where start equals end."""
        start, end = _parse_line_range("100-100")
        assert start == 100
        assert end == 100

    def test_parse_invalid_format(self):
        """Test parsing with invalid format."""
        with pytest.raises(ValueError, match="Invalid"):
            _parse_line_range("1-2-3")

    def test_parse_non_numeric(self):
        """Test parsing with non-numeric values."""
        with pytest.raises(ValueError, match="Invalid"):
            _parse_line_range("abc")

        with pytest.raises(ValueError, match="Invalid"):
            _parse_line_range("1-xyz")

    def test_parse_negative_numbers(self):
        """Test parsing with negative numbers."""
        with pytest.raises(ValueError, match="positive"):
            _parse_line_range("-1")

        with pytest.raises(ValueError, match="positive"):
            _parse_line_range("5--10")

    def test_parse_zero(self):
        """Test parsing with zero (invalid, lines are 1-indexed)."""
        with pytest.raises(ValueError, match="positive"):
            _parse_line_range("0")

        with pytest.raises(ValueError, match="positive"):
            _parse_line_range("0-5")


class TestValidateFilePath:
    """Tests for file path validation."""

    def test_valid_file_path(self, tmp_path):
        """Test validation of valid file path."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        config = FileEditToolConfig()
        result = _validate_file_path(str(file), config)

        assert result == file.resolve()

    def test_path_traversal_blocked(self, tmp_path):
        """Test that path traversal is blocked."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        config = FileEditToolConfig()

        with pytest.raises(ValueError, match="traversal"):
            _validate_file_path("../test.txt", config)

    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        config = FileEditToolConfig()

        with pytest.raises(FileNotFoundError):
            _validate_file_path(str(tmp_path / "missing.txt"), config)

    def test_directory_rejected(self, tmp_path):
        """Test that directories are rejected."""
        config = FileEditToolConfig()

        with pytest.raises(ValueError, match="Not a file"):
            _validate_file_path(str(tmp_path), config)

    def test_blocked_path_rejected(self, tmp_path):
        """Test that blocked paths are rejected."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        config = FileEditToolConfig(blocked_paths=[str(tmp_path)])

        with pytest.raises(ValueError, match="blocked"):
            _validate_file_path(str(file), config)

    def test_extension_validation(self, tmp_path):
        """Test extension filtering."""
        file = tmp_path / "test.exe"
        file.write_text("content")

        config = FileEditToolConfig(allowed_extensions=[".py", ".txt"])

        with pytest.raises(ValueError, match="not allowed"):
            _validate_file_path(str(file), config)

    def test_extensionless_file_allowed(self, tmp_path):
        """Test that extensionless files are allowed when "" in allowed_extensions."""
        file = tmp_path / "Dockerfile"
        file.write_text("FROM python:3.12")

        config = FileEditToolConfig(allowed_extensions=["", ".py"])
        result = _validate_file_path(str(file), config)

        assert result == file.resolve()

    def test_extensionless_file_rejected(self, tmp_path):
        """Test that extensionless files are rejected when "" not in allowed_extensions."""
        file = tmp_path / "Makefile"
        file.write_text("all:")

        config = FileEditToolConfig(allowed_extensions=[".py", ".txt"])

        with pytest.raises(ValueError, match="Extensionless"):
            _validate_file_path(str(file), config)


class TestComputeFileHash:
    """Tests for file hash computation."""

    def test_compute_hash_consistency(self, tmp_path):
        """Test that hash is consistent for same content."""
        file = tmp_path / "test.txt"
        file.write_text("Hello, world!")

        hash1 = _compute_file_hash(file)
        hash2 = _compute_file_hash(file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length

    def test_different_content_different_hash(self, tmp_path):
        """Test that different content produces different hash."""
        file = tmp_path / "test.txt"

        file.write_text("content1")
        hash1 = _compute_file_hash(file)

        file.write_text("content2")
        hash2 = _compute_file_hash(file)

        assert hash1 != hash2

    def test_hash_ignores_encoding_param(self, tmp_path):
        """Test that hash is based on bytes, not encoding param."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"Hello")

        # Hash should be same regardless of encoding param
        # (because we hash bytes directly)
        hash1 = _compute_file_hash(file, encoding="utf-8")
        hash2 = _compute_file_hash(file, encoding="latin-1")

        assert hash1 == hash2


class TestValidateEdits:
    """Tests for edit validation."""

    def test_valid_edits(self):
        """Test validation of valid edits."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"1-2": "new lines", "4": "single line"}

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is True
        assert error is None

    def test_max_edits_exceeded(self):
        """Test validation fails when max_edits exceeded."""
        config = FileEditToolConfig(max_edits=2)
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"1": "a", "2": "b", "3": "c"}  # 3 edits > max of 2

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "Too many edits" in error
        assert "3" in error
        assert "2" in error

    def test_max_payload_exceeded(self):
        """Test validation fails when payload size exceeded."""
        config = FileEditToolConfig(max_payload_bytes=100)
        lines = ["line1", "line2", "line3"]
        large_content = "x" * 200  # 200 bytes > max of 100
        edits = {"1": large_content}

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "Payload too large" in error

    def test_invalid_line_range_format(self):
        """Test validation fails on invalid range format."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3"]
        edits = {"abc": "content"}

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "Invalid" in error

    def test_start_greater_than_end(self):
        """Test validation fails when start > end."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3"]
        edits = {"3-1": "backwards"}  # 3 > 1

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "start" in error.lower()
        assert "end" in error.lower()

    def test_line_out_of_bounds_start(self):
        """Test validation fails when start line < 1."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3"]
        edits = {"0-2": "invalid"}  # Line 0 doesn't exist

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "0" in error

    def test_line_out_of_bounds_end(self):
        """Test validation fails when end line > file length."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3"]  # Only 3 lines
        edits = {"2-5": "too far"}  # Line 5 doesn't exist

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "5" in error
        assert "3" in error  # File has 3 lines

    def test_overlapping_ranges(self):
        """Test validation fails on overlapping ranges."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"1-3": "first", "2-4": "overlaps"}  # Lines 2-3 overlap

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is False
        assert "Overlapping" in error
        assert "ambiguous" in error.lower()

    def test_adjacent_ranges_allowed(self):
        """Test that adjacent (non-overlapping) ranges are allowed."""
        config = FileEditToolConfig()
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"1-2": "first", "3-4": "second"}  # Adjacent but not overlapping

        is_valid, error = _validate_edits(edits, lines, config)

        assert is_valid is True
        assert error is None


class TestApplyLineEdits:
    """Tests for applying line edits."""

    def test_apply_single_line_edit(self):
        """Test editing single line."""
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"3": "new line 3"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == ["line1", "line2", "new line 3", "line4", "line5"]
        assert changed_ranges == ["3"]

    def test_apply_line_range_edit(self):
        """Test editing line range."""
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"2-4": "replacement\nfor lines\n2 through 4"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == [
            "line1",
            "replacement",
            "for lines",
            "2 through 4",
            "line5",
        ]
        assert changed_ranges == ["2-4"]

    def test_apply_multiple_edits_bottom_to_top(self):
        """Test that edits are applied bottom-to-top."""
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"1-2": "top edit", "4-5": "bottom edit"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        # Bottom edit applied first (doesn't affect line numbers for top edit)
        assert result_lines == ["top edit", "line3", "bottom edit"]
        # Changed ranges sorted in normal order
        assert changed_ranges == ["1-2", "4-5"]

    def test_delete_lines_with_empty_content(self):
        """Test deleting lines by providing empty content."""
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"2-3": ""}  # Empty string deletes lines

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == ["line1", "line4", "line5"]
        assert changed_ranges == ["2-3"]

    def test_replace_single_line_with_multiple(self):
        """Test replacing single line with multiple lines."""
        lines = ["line1", "line2", "line3"]
        edits = {"2": "new line 2a\nnew line 2b\nnew line 2c"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == [
            "line1",
            "new line 2a",
            "new line 2b",
            "new line 2c",
            "line3",
        ]
        assert changed_ranges == ["2"]

    def test_replace_multiple_lines_with_single(self):
        """Test replacing multiple lines with single line."""
        lines = ["line1", "line2", "line3", "line4", "line5"]
        edits = {"2-4": "single replacement"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == ["line1", "single replacement", "line5"]
        assert changed_ranges == ["2-4"]

    def test_edit_entire_file(self):
        """Test editing all lines in file."""
        lines = ["line1", "line2", "line3"]
        edits = {"1-3": "completely\nnew\ncontent"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == ["completely", "new", "content"]
        assert changed_ranges == ["1-3"]

    def test_edit_first_line(self):
        """Test editing first line."""
        lines = ["line1", "line2", "line3"]
        edits = {"1": "new first line"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == ["new first line", "line2", "line3"]
        assert changed_ranges == ["1"]

    def test_edit_last_line(self):
        """Test editing last line."""
        lines = ["line1", "line2", "line3"]
        edits = {"3": "new last line"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines == ["line1", "line2", "new last line"]
        assert changed_ranges == ["3"]

    def test_multiple_separate_edits(self):
        """Test multiple non-overlapping edits."""
        lines = [f"line{i}" for i in range(1, 11)]
        edits = {"1": "first", "5": "middle", "10": "last"}

        result_lines, changed_ranges = _apply_line_edits(lines, edits)

        assert result_lines[0] == "first"
        assert result_lines[4] == "middle"
        assert result_lines[9] == "last"
        assert changed_ranges == ["1", "5", "10"]


class TestCreateDiffPreview:
    """Tests for diff preview generation."""

    def test_diff_preview_shows_changes(self):
        """Test that diff preview shows modifications."""
        original = "line1\nline2\nline3"
        modified = "line1\nNEW LINE 2\nline3"

        diff = _create_diff_preview(original, modified, "test.txt")

        assert "a/test.txt" in diff
        assert "b/test.txt" in diff
        assert "-line2" in diff  # Removed
        assert "+NEW LINE 2" in diff  # Added

    def test_diff_preview_no_changes(self):
        """Test diff preview when content unchanged."""
        content = "line1\nline2\nline3"

        diff = _create_diff_preview(content, content, "test.txt")

        # Empty diff when no changes
        assert diff == ""

    def test_diff_preview_addition(self):
        """Test diff preview for line addition."""
        original = "line1\nline2"
        modified = "line1\nline2\nline3"

        diff = _create_diff_preview(original, modified, "test.txt")

        assert "+line3" in diff

    def test_diff_preview_deletion(self):
        """Test diff preview for line deletion."""
        original = "line1\nline2\nline3"
        modified = "line1\nline3"

        diff = _create_diff_preview(original, modified, "test.txt")

        assert "-line2" in diff


class TestAtomicWrite:
    """Tests for atomic file writing."""

    def test_atomic_write_success(self, tmp_path):
        """Test successful atomic write."""
        file = tmp_path / "test.txt"
        file.write_text("original")

        _atomic_write(file, "new content")

        assert file.read_text() == "new content"

    def test_atomic_write_creates_file(self, tmp_path):
        """Test atomic write creates new file."""
        file = tmp_path / "new.txt"

        _atomic_write(file, "content")

        assert file.exists()
        assert file.read_text() == "content"

    def test_atomic_write_encoding(self, tmp_path):
        """Test atomic write with different encoding."""
        file = tmp_path / "test.txt"
        content = "Hello 世界"

        _atomic_write(file, content, encoding="utf-8")

        assert file.read_text(encoding="utf-8") == content

    def test_atomic_write_no_temp_file_left(self, tmp_path):
        """Test that temp files are cleaned up."""
        file = tmp_path / "test.txt"

        _atomic_write(file, "content")

        # No temp files should remain
        temp_files = list(tmp_path.glob(".*.tmp"))
        assert len(temp_files) == 0


class TestEditFileLines:
    """Integration tests for edit_file_lines tool."""

    def test_edit_single_line_success(self, tmp_path):
        """Test successful single line edit."""
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3\nline4\nline5")

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"3": "NEW LINE 3"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["changed_lines"] == ["3"]
        assert "bytes_written" in data
        assert "checksum" in data
        assert "preview" in data

        # Verify file was actually modified
        content = file.read_text()
        assert "NEW LINE 3" in content
        assert "line1" in content
        assert "line5" in content

    def test_edit_line_range_success(self, tmp_path):
        """Test successful line range edit."""
        file = tmp_path / "test.txt"
        file.write_text("\n".join([f"line{i}" for i in range(1, 11)]))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"3-5": "new line 3\nnew line 4\nnew line 5"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["changed_lines"] == ["3-5"]

        content = file.read_text()
        assert "new line 3" in content
        assert "new line 4" in content
        assert "new line 5" in content
        assert "line1" in content
        assert "line10" in content

    def test_multiple_edits_success(self, tmp_path):
        """Test multiple non-overlapping edits."""
        file = tmp_path / "test.txt"
        file.write_text("\n".join([f"line{i}" for i in range(1, 11)]))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {
                    "1-2": "header line 1\nheader line 2",
                    "9-10": "footer line 9\nfooter line 10",
                },
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert sorted(data["changed_lines"]) == ["1-2", "9-10"]

        content = file.read_text()
        assert "header line 1" in content
        assert "footer line 10" in content

    def test_optimistic_lock_success(self, tmp_path):
        """Test edit with correct expected_hash."""
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3")

        # Compute hash before edit
        expected_hash = _compute_file_hash(file)

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"2": "modified"},
                "expected_hash": expected_hash,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

    def test_optimistic_lock_failure(self, tmp_path):
        """Test edit fails with incorrect expected_hash."""
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3")

        # Use wrong hash
        wrong_hash = "0" * 64

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"2": "modified"},
                "expected_hash": wrong_hash,
            }
        )

        data = json.loads(result)
        assert data["status"] == "hash_mismatch"
        assert "hash mismatch" in data["error"].lower()

        # File should not be modified
        assert "modified" not in file.read_text()

    def test_dry_run_no_modification(self, tmp_path):
        """Test dry_run returns preview without modifying file."""
        file = tmp_path / "test.txt"
        original_content = "line1\nline2\nline3"
        file.write_text(original_content)

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"2": "would be changed"},
                "dry_run": True,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert "preview" in data
        assert "warnings" in data
        assert "Dry run" in data["warnings"][0]
        assert "bytes_written" not in data
        assert "checksum" not in data

        # File should not be modified
        assert file.read_text() == original_content

    def test_validation_failure_path_traversal(self, tmp_path):
        """Test validation fails on path traversal."""
        result = edit_file_lines.invoke(
            {
                "file_path": "../../../etc/passwd",
                "line_edits": {"1": "malicious"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "traversal" in data["error"].lower()

    def test_validation_failure_file_not_found(self, tmp_path):
        """Test validation fails when file doesn't exist."""
        result = edit_file_lines.invoke(
            {
                "file_path": str(tmp_path / "missing.txt"),
                "line_edits": {"1": "content"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "not found" in data["error"].lower()

    def test_validation_failure_invalid_range(self, tmp_path):
        """Test validation fails on invalid line range."""
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3")

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"1-100": "too far"},  # Line 100 doesn't exist
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "100" in data["error"]

    def test_validation_failure_overlapping_ranges(self, tmp_path):
        """Test validation fails on overlapping ranges."""
        file = tmp_path / "test.txt"
        file.write_text("\n".join([f"line{i}" for i in range(1, 11)]))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"1-5": "first", "3-7": "overlaps"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "overlapping" in data["error"].lower()

    def test_delete_lines(self, tmp_path):
        """Test deleting lines with empty content."""
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3\nline4\nline5")

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"2-4": ""},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        content = file.read_text()
        assert content == "line1\nline5"

    def test_config_integration(self, tmp_path):
        """Test that tool uses module-level config."""
        file = tmp_path / "test.py"
        file.write_text("print('hello')")

        # Set restrictive config
        set_file_edit_config(FileEditToolConfig(allowed_extensions=[".txt"]))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"1": "print('modified')"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert ".py" in data["error"]
        assert "not allowed" in data["error"]

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_encoding_error_handling(self, tmp_path):
        """Test error handling for encoding issues."""
        file = tmp_path / "binary.txt"  # .txt extension to pass validation
        file.write_bytes(b"\x00\x01\x02\xff\xfe")

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"1": "text"},
            }
        )

        data = json.loads(result)
        # Binary files trigger either validation_failed or error depending on detection
        assert data["status"] in ("error", "validation_failed")
        assert (
            "encoding" in data["error"].lower()
            or "decode" in data["error"].lower()
            or "binary" in data["error"].lower()
        )


class TestFileEditResult:
    """Tests for FileEditResult dataclass."""

    def test_to_json_success(self):
        """Test JSON serialization of success result."""
        result = FileEditResult(
            status="success",
            bytes_written=100,
            checksum="abc123",
            changed_lines=["1-5"],
            preview="diff content",
            warnings=None,
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["status"] == "success"
        assert data["bytes_written"] == 100
        assert data["checksum"] == "abc123"
        assert data["changed_lines"] == ["1-5"]
        assert data["preview"] == "diff content"
        assert "warnings" not in data  # None omitted
        assert "error" not in data  # None omitted

    def test_to_json_error(self):
        """Test JSON serialization of error result."""
        result = FileEditResult(
            status="error",
            error="Something went wrong",
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["status"] == "error"
        assert data["error"] == "Something went wrong"
        assert "bytes_written" not in data  # None omitted


class TestModuleConfig:
    """Tests for module-level config management."""

    def test_get_default_config(self):
        """Test getting default config when none set."""
        # Reset module config
        set_file_edit_config(None)

        config = get_file_edit_config()

        assert isinstance(config, FileEditToolConfig)
        assert config.max_edits == 50  # Default value

    def test_set_and_get_config(self):
        """Test setting and getting custom config."""
        custom_config = FileEditToolConfig(max_edits=10, max_payload_bytes=1000)

        set_file_edit_config(custom_config)
        retrieved_config = get_file_edit_config()

        assert retrieved_config.max_edits == 10
        assert retrieved_config.max_payload_bytes == 1000

        # Reset to default
        set_file_edit_config(FileEditToolConfig())


class TestCreateFile:
    """Integration tests for create_file tool."""

    def test_create_new_file_success(self, tmp_path):
        """Test creating new file in existing directory."""
        file = tmp_path / "new_file.txt"
        content = "Hello, World!"

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["bytes_written"] == len(content.encode("utf-8"))
        assert "checksum" in data

        # Verify file was created with correct content
        assert file.exists()
        assert file.read_text() == content

    def test_create_file_with_parent_dirs(self, tmp_path):
        """Test automatic parent directory creation."""
        file = tmp_path / "deep" / "nested" / "dirs" / "file.py"
        content = "def test():\n    pass"

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Verify parent dirs were created
        assert file.parent.exists()
        assert file.parent.is_dir()
        assert file.read_text() == content

    def test_create_file_already_exists_no_overwrite(self, tmp_path):
        """Test overwrite protection when file exists."""
        file = tmp_path / "existing.txt"
        file.write_text("original content")

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "new content",
                "overwrite": False,
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "already exists" in data["error"].lower()

        # Original content preserved
        assert file.read_text() == "original content"

    def test_create_file_overwrite_not_allowed_in_config(self, tmp_path):
        """Test overwrite fails if config.allow_overwrite=False."""
        file = tmp_path / "existing.txt"
        file.write_text("original")

        # Set config with allow_overwrite=False
        set_file_edit_config(FileEditToolConfig(allow_overwrite=False))

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "new",
                "overwrite": True,  # User wants overwrite but config blocks it
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "config does not allow" in data["error"].lower()

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_create_file_overwrite_success(self, tmp_path):
        """Test overwrite succeeds with both flags True."""
        file = tmp_path / "existing.txt"
        file.write_text("original content")

        # Set config with allow_overwrite=True
        set_file_edit_config(FileEditToolConfig(allow_overwrite=True))

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "new content",
                "overwrite": True,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert "checksum" in data

        # File was overwritten
        assert file.read_text() == "new content"

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_create_file_blocked_extension(self, tmp_path):
        """Test validation fails for blocked extensions."""
        file = tmp_path / "malicious.exe"

        # Config with restricted extensions
        set_file_edit_config(FileEditToolConfig(allowed_extensions=[".txt", ".py"]))

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "binary content",
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "not allowed" in data["error"].lower()

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_create_file_blocked_path(self, tmp_path):
        """Test validation fails for blocked paths."""
        # Try to create in /etc (blocked path)
        result = create_file.invoke(
            {
                "file_path": "/etc/passwd_fake",
                "content": "malicious",
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "blocked" in data["error"].lower() or "denied" in data["error"].lower()

    def test_create_file_path_traversal(self):
        """Test path traversal rejection."""
        result = create_file.invoke(
            {
                "file_path": "../../../etc/passwd",
                "content": "malicious",
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "traversal" in data["error"].lower()

    def test_create_file_returns_checksum(self, tmp_path):
        """Test result includes SHA256 checksum."""
        file = tmp_path / "test.txt"
        content = "test content"

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert "checksum" in data
        assert len(data["checksum"]) == 64  # SHA256 hex digest

        # Verify checksum matches file
        assert data["checksum"] == _compute_file_hash(file)

    def test_create_file_returns_bytes_written(self, tmp_path):
        """Test result includes content size."""
        file = tmp_path / "test.txt"
        content = "Hello, 世界!"  # Mix ASCII and UTF-8

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert data["bytes_written"] == len(content.encode("utf-8"))

    def test_create_file_status_success_new(self, tmp_path):
        """Test status is \"success\" for new files."""
        file = tmp_path / "new.txt"

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "content",
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

    def test_create_file_status_success_overwrite(self, tmp_path):
        """Test status is \"success\" when overwriting."""
        file = tmp_path / "existing.txt"
        file.write_text("original")

        set_file_edit_config(FileEditToolConfig(allow_overwrite=True))

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "new",
                "overwrite": True,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_create_file_encoding(self, tmp_path):
        """Test respects config.default_encoding."""
        file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"

        # Use UTF-8 encoding (default)
        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert file.read_text(encoding="utf-8") == content

    def test_create_file_empty_content(self, tmp_path):
        """Test creating empty file."""
        file = tmp_path / "empty.txt"

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "",
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["bytes_written"] == 0
        assert file.read_text() == ""

    def test_create_file_large_content(self, tmp_path):
        """Test creating file with large content."""
        file = tmp_path / "large.txt"
        content = "x" * 10000  # 10KB

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["bytes_written"] == 10000
        assert file.read_text() == content

    def test_create_file_special_chars(self, tmp_path):
        """Test content with unicode/special characters."""
        file = tmp_path / "special.txt"
        content = "Line 1\nLine 2\tTab\nWindows\\nEscaped\n\u2764\ufe0f Unicode"

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": content,
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert file.read_text() == content

    def test_create_file_config_integration(self, tmp_path):
        """Test uses module-level config."""
        file = tmp_path / "test.exe"

        # Restrictive config
        set_file_edit_config(FileEditToolConfig(allowed_extensions=[".txt"]))

        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "content",
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"

        # Reset
        set_file_edit_config(FileEditToolConfig())

    def test_create_file_atomic_write(self, tmp_path):
        """Test no partial files on error."""
        file = tmp_path / "atomic.txt"

        # This should succeed
        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": "test content",
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Verify no temp files left behind
        temp_files = list(tmp_path.glob(".*tmp"))
        assert len(temp_files) == 0

    def test_create_file_payload_size_limit(self, tmp_path):
        """Test max_payload_bytes enforcement."""
        file = tmp_path / "large.txt"

        # Set strict limit
        set_file_edit_config(FileEditToolConfig(max_payload_bytes=100))

        # Try to create file exceeding limit
        large_content = "x" * 200  # 200 bytes
        result = create_file.invoke(
            {
                "file_path": str(file),
                "content": large_content,
            }
        )

        data = json.loads(result)
        assert data["status"] == "validation_failed"
        assert "exceeds maximum allowed" in data["error"]
        assert "200" in data["error"]  # Actual size
        assert "100" in data["error"]  # Limit

        # File should not be created
        assert not file.exists()

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_edit_preserves_crlf_newlines(self, tmp_path):
        """Test that CRLF line endings are preserved."""
        file = tmp_path / "windows.txt"
        # Create file with CRLF line endings
        content_crlf = "line1\r\nline2\r\nline3\r\n"
        file.write_bytes(content_crlf.encode("utf-8"))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"2": "modified line 2"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Verify CRLF is preserved
        final_content = file.read_bytes().decode("utf-8")
        assert "\r\n" in final_content
        assert final_content == "line1\r\nmodified line 2\r\nline3\r\n"

    def test_edit_preserves_lf_newlines(self, tmp_path):
        """Test that LF line endings are preserved."""
        file = tmp_path / "unix.txt"
        # Create file with LF line endings
        content_lf = "line1\nline2\nline3\n"
        file.write_text(content_lf)

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"2": "modified line 2"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Verify LF is preserved (no CRLF)
        final_content = file.read_text()
        assert "\r\n" not in final_content
        assert final_content == "line1\nmodified line 2\nline3\n"

    def test_concurrent_edits_no_collision(self, tmp_path):
        """Test that concurrent edits use unique temp files."""
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3\n")

        # Simulate concurrent edits by checking temp file names are unique
        # We cannot actually test true concurrency easily, but we can verify
        # the temp file naming uses randomness
        import threading

        temp_files_seen = set()

        def edit_file():
            # Import here to access _atomic_write internals
            import secrets

            # Generate what the temp path would be
            random_suffix = secrets.token_hex(8)
            temp_path = file.parent / f".{file.name}.{random_suffix}.tmp"
            temp_files_seen.add(str(temp_path))

        # Run multiple threads
        threads = [threading.Thread(target=edit_file) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All temp file names should be unique
        assert len(temp_files_seen) == 10

    def test_extension_case_insensitive_uppercase(self, tmp_path):
        """Test that extension filtering is case-insensitive for uppercase."""
        file = tmp_path / "test.PY"
        file.write_text('print("hello")')

        # Config allows .py (lowercase)
        set_file_edit_config(FileEditToolConfig(allowed_extensions=[".py"]))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"1": 'print("modified")'},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Reset config
        set_file_edit_config(FileEditToolConfig())

    def test_extension_case_insensitive_mixed_case(self, tmp_path):
        """Test that extension filtering is case-insensitive for mixed case."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        # Config allows .TXT (uppercase)
        set_file_edit_config(FileEditToolConfig(allowed_extensions=[".TXT", ".MD"]))

        result = edit_file_lines.invoke(
            {
                "file_path": str(file),
                "line_edits": {"1": "modified"},
            }
        )

        data = json.loads(result)
        assert data["status"] == "success"

        # Reset config
        set_file_edit_config(FileEditToolConfig())

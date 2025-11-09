"""Tests for security utilities."""

from pathlib import Path

import pytest

from consoul.utils.security import (
    check_env_file_in_gitignore,
    mask_api_key,
    warn_if_env_not_ignored,
)


class TestCheckEnvFileInGitignore:
    """Tests for check_env_file_in_gitignore function."""

    def test_no_gitignore_returns_false(self, tmp_path: Path):
        """Test that missing .gitignore returns False."""
        assert not check_env_file_in_gitignore(tmp_path)

    def test_env_in_gitignore_returns_true(self, tmp_path: Path):
        """Test that .env in .gitignore returns True."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")

        assert check_env_file_in_gitignore(tmp_path)

    def test_env_local_in_gitignore_returns_true(self, tmp_path: Path):
        """Test that .env.local in .gitignore returns True."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env.local\n")

        assert check_env_file_in_gitignore(tmp_path)

    def test_env_glob_in_gitignore_returns_true(self, tmp_path: Path):
        """Test that .env* glob pattern in .gitignore returns True."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env*\n")

        assert check_env_file_in_gitignore(tmp_path)

    def test_env_with_comments(self, tmp_path: Path):
        """Test that .env with inline comment is detected."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env  # Environment variables\n")

        assert check_env_file_in_gitignore(tmp_path)

    def test_env_not_in_gitignore_returns_false(self, tmp_path: Path):
        """Test that .gitignore without .env returns False."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n")

        assert not check_env_file_in_gitignore(tmp_path)

    def test_commented_env_returns_false(self, tmp_path: Path):
        """Test that commented .env line returns False."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# .env\n*.pyc\n")

        assert not check_env_file_in_gitignore(tmp_path)

    def test_uses_current_dir_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that function uses current directory when project_root is None."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")

        monkeypatch.chdir(tmp_path)
        assert check_env_file_in_gitignore()

    def test_handles_read_error_gracefully(self, tmp_path: Path):
        """Test that read errors return False gracefully."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")
        # Make file unreadable
        gitignore.chmod(0o000)

        try:
            # Should not raise, should return False
            assert not check_env_file_in_gitignore(tmp_path)
        finally:
            # Restore permissions for cleanup
            gitignore.chmod(0o644)


class TestWarnIfEnvNotIgnored:
    """Tests for warn_if_env_not_ignored function."""

    def test_no_warning_when_env_file_missing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        """Test that no warning is printed when .env file doesn't exist."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")

        warn_if_env_not_ignored(tmp_path)

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_no_warning_when_env_in_gitignore(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        """Test that no warning is printed when .env is in .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")

        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret\n")

        warn_if_env_not_ignored(tmp_path)

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_warning_when_env_not_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        """Test that warning is printed when .env exists but not in .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")

        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret\n")

        warn_if_env_not_ignored(tmp_path)

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert ".env" in captured.err
        assert "gitignore" in captured.err.lower()

    def test_uses_current_dir_by_default(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        """Test that function uses current directory when project_root is None."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret\n")

        monkeypatch.chdir(tmp_path)
        warn_if_env_not_ignored()

        captured = capsys.readouterr()
        assert "WARNING" in captured.err


class TestMaskApiKey:
    """Tests for mask_api_key function."""

    def test_mask_long_key(self):
        """Test masking a long API key."""
        key = "sk-ant-1234567890abcdefghijklmnop"
        masked = mask_api_key(key)

        assert masked == "sk-a...mnop"
        assert len(masked) < len(key)

    def test_mask_medium_key(self):
        """Test masking a medium-length API key."""
        key = "abcd1234efgh5678"
        masked = mask_api_key(key)

        assert masked == "abcd...5678"

    def test_mask_short_key(self):
        """Test masking a short API key."""
        key = "short"
        masked = mask_api_key(key)

        assert masked == "****"

    def test_mask_very_short_key(self):
        """Test masking a very short API key."""
        key = "abc"
        masked = mask_api_key(key)

        assert masked == "***"

    def test_mask_empty_key(self):
        """Test masking an empty key."""
        masked = mask_api_key("")

        assert masked == ""

    def test_mask_with_custom_show_chars(self):
        """Test masking with custom number of characters to show."""
        key = "1234567890abcdefghij"
        masked = mask_api_key(key, show_chars=6)

        assert masked == "123456...efghij"

    def test_mask_preserves_prefix(self):
        """Test that common API key prefixes are preserved."""
        keys = [
            ("sk-ant-1234567890abcdef", "sk-a...cdef"),
            ("sk-proj-1234567890abcdef", "sk-p...cdef"),
        ]

        for key, expected in keys:
            assert mask_api_key(key) == expected

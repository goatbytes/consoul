"""Tests for WhitelistManager - bash command whitelisting."""

import re

import pytest

from consoul.ai.tools.permissions.whitelist import WhitelistManager, WhitelistPattern


class TestWhitelistPattern:
    """Tests for WhitelistPattern dataclass."""

    def test_exact_pattern_matches_exact_command(self):
        """Test that exact pattern matches exact command."""
        pattern = WhitelistPattern("git status", pattern_type="exact")
        assert pattern.matches("git status")
        assert not pattern.matches("git log")
        assert not pattern.matches("git status --short")

    def test_regex_pattern_matches_multiple_commands(self):
        """Test that regex pattern matches multiple commands."""
        pattern = WhitelistPattern("git.*", pattern_type="regex")
        assert pattern.matches("git status")
        assert pattern.matches("git log")
        assert pattern.matches("git diff")
        assert not pattern.matches("npm install")

    def test_regex_pattern_with_alternatives(self):
        """Test regex pattern with alternatives (or operator)."""
        pattern = WhitelistPattern("git (status|log|diff)", pattern_type="regex")
        assert pattern.matches("git status")
        assert pattern.matches("git log")
        assert pattern.matches("git diff")
        assert not pattern.matches("git push")
        assert not pattern.matches("git commit")

    def test_invalid_regex_raises_error(self):
        """Test that invalid regex pattern raises ValueError."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            WhitelistPattern("git[", pattern_type="regex")  # Unclosed bracket

    def test_exact_pattern_has_no_compiled(self):
        """Test that exact patterns don't compile regex."""
        pattern = WhitelistPattern("git status", pattern_type="exact")
        assert pattern.compiled is None

    def test_regex_pattern_has_compiled(self):
        """Test that regex patterns compile pattern."""
        pattern = WhitelistPattern("git.*", pattern_type="regex")
        assert pattern.compiled is not None
        assert isinstance(pattern.compiled, re.Pattern)

    def test_pattern_case_insensitive(self):
        """Test that regex patterns are case-insensitive."""
        pattern = WhitelistPattern("git.*", pattern_type="regex")
        assert pattern.matches("git status")
        assert pattern.matches("GIT STATUS")
        assert pattern.matches("Git Status")


class TestWhitelistManager:
    """Tests for WhitelistManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a WhitelistManager with temporary storage."""
        storage_path = tmp_path / "whitelist.yaml"
        return WhitelistManager(storage_path=storage_path)

    def test_add_exact_pattern(self, manager):
        """Test adding exact match pattern."""
        pattern = manager.add_pattern("git status", description="Safe command")
        assert pattern.pattern == "git status"
        assert pattern.pattern_type == "exact"
        assert pattern.description == "Safe command"
        assert len(manager.get_patterns()) == 1

    def test_add_regex_pattern(self, manager):
        """Test adding regex pattern."""
        pattern = manager.add_pattern(
            "git.*", pattern_type="regex", description="All git commands"
        )
        assert pattern.pattern == "git.*"
        assert pattern.pattern_type == "regex"
        assert len(manager.get_patterns()) == 1

    def test_add_duplicate_pattern_returns_existing(self, manager):
        """Test that adding duplicate pattern returns existing pattern."""
        pattern1 = manager.add_pattern("git status")
        pattern2 = manager.add_pattern("git status")
        assert pattern1 is pattern2
        assert len(manager.get_patterns()) == 1

    def test_add_empty_pattern_raises_error(self, manager):
        """Test that adding empty pattern raises ValueError."""
        with pytest.raises(ValueError, match="Pattern cannot be empty"):
            manager.add_pattern("")
        with pytest.raises(ValueError, match="Pattern cannot be empty"):
            manager.add_pattern("   ")

    def test_remove_existing_pattern(self, manager):
        """Test removing existing pattern."""
        manager.add_pattern("git status")
        assert len(manager.get_patterns()) == 1
        assert manager.remove_pattern("git status")
        assert len(manager.get_patterns()) == 0

    def test_remove_nonexistent_pattern_returns_false(self, manager):
        """Test that removing non-existent pattern returns False."""
        assert not manager.remove_pattern("git status")

    def test_is_whitelisted_exact_match(self, manager):
        """Test whitelisting with exact match."""
        manager.add_pattern("git status")
        assert manager.is_whitelisted("git status")
        assert not manager.is_whitelisted("git log")

    def test_is_whitelisted_regex_match(self, manager):
        """Test whitelisting with regex pattern."""
        manager.add_pattern("git.*", pattern_type="regex")
        assert manager.is_whitelisted("git status")
        assert manager.is_whitelisted("git log")
        assert manager.is_whitelisted("git diff")
        assert not manager.is_whitelisted("npm install")

    def test_is_whitelisted_normalizes_whitespace(self, manager):
        """Test that whitespace is normalized before matching."""
        manager.add_pattern("git status")
        assert manager.is_whitelisted("  git   status  ")
        assert manager.is_whitelisted("git  status")

    def test_is_whitelisted_handles_quotes(self, manager):
        """Test that quotes are handled consistently."""
        manager.add_pattern("echo hello world")
        assert manager.is_whitelisted("echo 'hello world'")
        assert manager.is_whitelisted('echo "hello world"')

    def test_is_whitelisted_with_multiple_patterns(self, manager):
        """Test whitelisting with multiple patterns."""
        manager.add_pattern("git status")
        manager.add_pattern("npm test")
        manager.add_pattern("cargo.*", pattern_type="regex")

        assert manager.is_whitelisted("git status")
        assert manager.is_whitelisted("npm test")
        assert manager.is_whitelisted("cargo build")
        assert manager.is_whitelisted("cargo test")
        assert not manager.is_whitelisted("rm -rf /")

    def test_is_whitelisted_caches_results(self, manager):
        """Test that is_whitelisted caches results for performance."""
        manager.add_pattern("git status")

        # First call - should cache
        assert manager.is_whitelisted("git status")
        # Second call - should use cache
        assert manager.is_whitelisted("git status")

        # Check cache is populated
        assert len(manager._pattern_cache) > 0

    def test_clear_removes_all_patterns(self, manager):
        """Test that clear removes all patterns."""
        manager.add_pattern("git status")
        manager.add_pattern("npm test")
        assert len(manager.get_patterns()) == 2

        manager.clear()
        assert len(manager.get_patterns()) == 0
        assert not manager.is_whitelisted("git status")

    def test_clear_clears_cache(self, manager):
        """Test that clear also clears the cache."""
        manager.add_pattern("git status")
        manager.is_whitelisted("git status")  # Populate cache

        manager.clear()
        assert len(manager._pattern_cache) == 0

    def test_get_patterns_returns_copy(self, manager):
        """Test that get_patterns returns a copy, not original list."""
        manager.add_pattern("git status")
        patterns1 = manager.get_patterns()
        patterns2 = manager.get_patterns()

        assert patterns1 is not patterns2
        assert patterns1 == patterns2


class TestWhitelistPersistence:
    """Tests for whitelist save/load functionality."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a WhitelistManager with temporary storage."""
        storage_path = tmp_path / "whitelist.yaml"
        return WhitelistManager(storage_path=storage_path)

    def test_save_creates_yaml_file(self, manager):
        """Test that save creates YAML file."""
        manager.add_pattern("git status")
        manager.save()

        assert manager.storage_path.exists()
        assert manager.storage_path.is_file()

    def test_save_creates_parent_directory(self, tmp_path):
        """Test that save creates parent directories."""
        storage_path = tmp_path / "nested" / "dir" / "whitelist.yaml"
        manager = WhitelistManager(storage_path=storage_path)
        manager.add_pattern("git status")
        manager.save()

        assert storage_path.exists()
        assert storage_path.parent.exists()

    def test_save_sets_secure_permissions(self, manager):
        """Test that save sets file permissions to 600."""
        manager.add_pattern("git status")
        manager.save()

        # Check permissions are 600 (user read/write only)
        stat = manager.storage_path.stat()
        assert oct(stat.st_mode)[-3:] == "600"

    def test_load_restores_exact_patterns(self, manager):
        """Test that load restores exact match patterns."""
        manager.add_pattern("git status", description="Safe git command")
        manager.add_pattern("npm test", description="Run tests")
        manager.save()

        # Create new manager and load
        new_manager = WhitelistManager(storage_path=manager.storage_path)
        new_manager.load()

        patterns = new_manager.get_patterns()
        assert len(patterns) == 2
        assert new_manager.is_whitelisted("git status")
        assert new_manager.is_whitelisted("npm test")

    def test_load_restores_regex_patterns(self, manager):
        """Test that load restores regex patterns."""
        manager.add_pattern("git.*", pattern_type="regex", description="All git")
        manager.add_pattern("npm (install|ci)", pattern_type="regex")
        manager.save()

        # Create new manager and load
        new_manager = WhitelistManager(storage_path=manager.storage_path)
        new_manager.load()

        assert new_manager.is_whitelisted("git status")
        assert new_manager.is_whitelisted("npm install")
        assert new_manager.is_whitelisted("npm ci")

    def test_load_from_nonexistent_file_is_noop(self, tmp_path):
        """Test that loading from non-existent file doesn't error."""
        storage_path = tmp_path / "nonexistent.yaml"
        manager = WhitelistManager(storage_path=storage_path)
        manager.load()  # Should not raise
        assert len(manager.get_patterns()) == 0

    def test_save_load_roundtrip(self, manager):
        """Test that save/load roundtrip preserves all data."""
        manager.add_pattern("git status", description="Git status command")
        manager.add_pattern(
            "git.*", pattern_type="regex", description="All git commands"
        )
        manager.add_pattern("npm test")
        manager.save()

        # Create new manager and load
        new_manager = WhitelistManager(storage_path=manager.storage_path)
        new_manager.load()

        # Check all patterns restored
        patterns = new_manager.get_patterns()
        assert len(patterns) == 3

        # Check exact pattern details
        exact_patterns = [p for p in patterns if p.pattern_type == "exact"]
        assert len(exact_patterns) == 2

        regex_patterns = [p for p in patterns if p.pattern_type == "regex"]
        assert len(regex_patterns) == 1

    def test_load_skips_invalid_patterns(self, manager):
        """Test that load skips invalid patterns but continues."""
        # Manually create file with invalid pattern
        manager.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.storage_path.open("w") as f:
            f.write("version: 1\n")
            f.write("patterns:\n")
            f.write("  - pattern: 'git['\n")  # Invalid regex
            f.write("    pattern_type: regex\n")
            f.write("  - pattern: 'git status'\n")  # Valid
            f.write("    pattern_type: exact\n")

        with pytest.warns(UserWarning, match="Skipping invalid whitelist pattern"):
            manager.load()

        # Should load valid pattern, skip invalid
        patterns = manager.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].pattern == "git status"

    def test_load_auto_loads_on_init(self, manager):
        """Test that existing whitelist is auto-loaded on init."""
        manager.add_pattern("git status")
        manager.save()

        # Create new manager with same path
        new_manager = WhitelistManager(storage_path=manager.storage_path)

        # Should auto-load existing whitelist
        assert new_manager.is_whitelisted("git status")


class TestWhitelistNormalization:
    """Tests for command normalization."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a WhitelistManager with temporary storage."""
        return WhitelistManager(storage_path=tmp_path / "whitelist.yaml")

    def test_normalize_collapses_whitespace(self, manager):
        """Test that multiple spaces are collapsed to single space."""
        normalized1 = manager._normalize_command("ls  -la")
        normalized2 = manager._normalize_command("ls -la")
        assert normalized1 == normalized2 == "ls -la"

    def test_normalize_strips_leading_trailing_whitespace(self, manager):
        """Test that leading/trailing whitespace is removed."""
        normalized = manager._normalize_command("  ls -la  ")
        assert normalized == "ls -la"

    def test_normalize_handles_single_quotes(self, manager):
        """Test normalization with single quotes."""
        # shlex removes quotes and joins tokens
        normalized = manager._normalize_command("echo 'hello world'")
        assert normalized == "echo hello world"

    def test_normalize_handles_double_quotes(self, manager):
        """Test normalization with double quotes."""
        # shlex removes quotes and joins tokens
        normalized = manager._normalize_command('echo "hello world"')
        assert normalized == "echo hello world"

    def test_normalize_handles_unclosed_quotes_gracefully(self, manager):
        """Test that unclosed quotes fall back to simple normalization."""
        # Should not raise error, just do simple normalization
        normalized = manager._normalize_command('echo "unclosed quote')
        assert "echo" in normalized

    def test_normalize_handles_complex_command(self, manager):
        """Test normalization with complex command."""
        command = "git commit -m 'feat: add feature' --no-verify"
        normalized = manager._normalize_command(command)
        assert "git" in normalized
        assert "commit" in normalized


class TestWhitelistEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a WhitelistManager with temporary storage."""
        return WhitelistManager(storage_path=tmp_path / "whitelist.yaml")

    def test_empty_whitelist_rejects_all(self, manager):
        """Test that empty whitelist rejects all commands."""
        assert not manager.is_whitelisted("git status")
        assert not manager.is_whitelisted("npm test")
        assert not manager.is_whitelisted("ls -la")

    def test_whitelist_with_special_regex_characters(self, manager):
        """Test patterns with regex special characters."""
        # Exact match should work with special characters
        manager.add_pattern("git log --pretty=format:'%h %s'")
        assert manager.is_whitelisted("git log --pretty=format:'%h %s'")

    def test_regex_pattern_with_dollar_sign(self, manager):
        """Test regex pattern with end-of-string anchor."""
        manager.add_pattern("^git status$", pattern_type="regex")
        assert manager.is_whitelisted("git status")
        assert not manager.is_whitelisted("git status --short")

    def test_add_pattern_clears_cache(self, manager):
        """Test that adding pattern clears cache."""
        manager.add_pattern("git status")
        manager.is_whitelisted("git status")  # Populate cache

        manager.add_pattern("npm test")  # Should clear cache
        assert len(manager._pattern_cache) == 0

    def test_remove_pattern_clears_cache(self, manager):
        """Test that removing pattern clears cache."""
        manager.add_pattern("git status")
        manager.is_whitelisted("git status")  # Populate cache

        manager.remove_pattern("git status")  # Should clear cache
        assert len(manager._pattern_cache) == 0

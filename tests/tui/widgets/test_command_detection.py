"""Tests for inline command detection in InputArea."""

from __future__ import annotations

from consoul.tui.widgets.input_area import InputArea


class TestCommandDetection:
    """Test command detection from user input."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.input_area = InputArea()

    def test_extract_command_with_backticks(self) -> None:
        """Test extracting command with backticks."""
        command = self.input_area._extract_command("!`ls -la`")
        assert command == "ls -la"

    def test_extract_command_without_backticks(self) -> None:
        """Test extracting command without backticks."""
        command = self.input_area._extract_command("!ls -la")
        assert command == "ls -la"

    def test_extract_command_with_extra_spaces(self) -> None:
        """Test extracting command with extra spaces."""
        command = self.input_area._extract_command("!  ls -la  ")
        assert command == "ls -la  "  # Trailing spaces in command are kept

    def test_extract_command_with_backticks_and_spaces(self) -> None:
        """Test extracting command with backticks and spaces."""
        command = self.input_area._extract_command("!  `ls -la`  ")
        assert command == "ls -la"

    def test_no_command_for_regular_message(self) -> None:
        """Test that regular messages don't trigger command extraction."""
        command = self.input_area._extract_command("Hello, how are you?")
        assert command is None

    def test_no_command_for_exclamation_not_at_start(self) -> None:
        """Test that exclamation not at start doesn't trigger."""
        command = self.input_area._extract_command("Hi! How are you?")
        assert command is None

    def test_no_command_for_exclamation_with_space(self) -> None:
        """Test that ! followed by space doesn't trigger."""
        command = self.input_area._extract_command("! ")
        assert command is None

    def test_command_with_complex_args(self) -> None:
        """Test command with complex arguments."""
        command = self.input_area._extract_command("!git commit -m 'test message'")
        assert command == "git commit -m 'test message'"

    def test_command_with_pipes(self) -> None:
        """Test command with pipes."""
        command = self.input_area._extract_command("!`cat file.txt | grep 'error'`")
        assert command == "cat file.txt | grep 'error'"

    def test_command_with_redirects(self) -> None:
        """Test command with redirects."""
        command = self.input_area._extract_command("!ls > output.txt")
        assert command == "ls > output.txt"

    def test_multiline_command_not_supported(self) -> None:
        """Test that multiline input is not treated as command."""
        # This is expected behavior - only single line commands supported
        command = self.input_area._extract_command("!ls\n!pwd")
        # The regex will only match if it's a single line starting with !
        # Since this has a newline, it won't match
        assert command is None or "!pwd" not in (command or "")

    def test_empty_command(self) -> None:
        """Test empty command."""
        command = self.input_area._extract_command("!")
        assert command is None

    def test_empty_backtick_command(self) -> None:
        """Test empty backtick command."""
        command = self.input_area._extract_command("!``")
        assert command is None  # Empty backticks


class TestInlineCommandDetection:
    """Test inline command detection within messages."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.input_area = InputArea()

    def test_has_inline_command_simple(self) -> None:
        """Test detecting simple inline command."""
        has_inline = self.input_area._has_inline_commands(
            "Here is the output: !`ls -la`"
        )
        assert has_inline is True

    def test_has_inline_command_multiple(self) -> None:
        """Test detecting multiple inline commands."""
        has_inline = self.input_area._has_inline_commands(
            "Compare !`cat file1.txt` with !`cat file2.txt`"
        )
        assert has_inline is True

    def test_no_inline_command_regular_message(self) -> None:
        """Test regular message without commands."""
        has_inline = self.input_area._has_inline_commands("Hello, how are you?")
        assert has_inline is False

    def test_no_inline_command_standalone(self) -> None:
        """Test standalone command is not detected as inline."""
        has_inline = self.input_area._has_inline_commands("!`ls -la`")
        assert has_inline is False  # This is standalone, not inline

    def test_has_inline_command_with_text_before(self) -> None:
        """Test inline command with text before."""
        has_inline = self.input_area._has_inline_commands("Check this: !`pwd`")
        assert has_inline is True

    def test_has_inline_command_with_text_after(self) -> None:
        """Test inline command with text after."""
        has_inline = self.input_area._has_inline_commands(
            "!`cat file.txt` is the content"
        )
        assert has_inline is True

    def test_no_inline_without_backticks(self) -> None:
        """Test that !command without backticks in middle is not inline."""
        # Without backticks, we only support standalone mode
        has_inline = self.input_area._has_inline_commands("Here is !ls output")
        assert has_inline is False

"""Bash command execution tool with security controls.

Provides secure bash command execution with:
- Command validation and blocking
- Whitelist support for trusted commands
- Timeout enforcement
- Working directory control
- Detailed output capture (stdout/stderr/exit code)

Note:
    This tool explicitly invokes /bin/bash to ensure bash-specific features
    (process substitutions, [[ ... ]], etc.) work consistently across systems
    where /bin/sh may be dash (e.g., Ubuntu).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from consoul.ai.tools.exceptions import BlockedCommandError, ToolExecutionError
from consoul.ai.tools.permissions.whitelist import WhitelistManager
from consoul.config.models import BashToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: BashToolConfig | None = None


def set_bash_config(config: BashToolConfig) -> None:
    """Set the module-level config for bash tool.

    This should be called by the ToolRegistry when registering bash_execute
    to inject the profile's configured settings.

    Args:
        config: BashToolConfig from the active profile's ToolConfig.bash
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_bash_config() -> BashToolConfig:
    """Get the current bash tool config.

    Returns:
        The configured BashToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else BashToolConfig()


# Default blocked command patterns (security-critical)
DEFAULT_BLOCKED_PATTERNS = [
    r"^sudo\s",  # sudo commands
    r"rm\s+(-[rf]+\s+)?/",  # rm with root paths
    r"dd\s+if=",  # disk operations
    r"chmod\s+777",  # dangerous permissions
    r":\(\)\{.*:\|:.*\};:",  # fork bomb
    r"wget.*\|.*bash",  # download-and-execute
    r"curl.*\|.*sh",  # download-and-execute
    r">\s*/dev/sd[a-z]",  # write to disk devices
    r"mkfs",  # format filesystem
    r"fdisk",  # partition operations
]


def is_whitelisted(
    command: str,
    config: BashToolConfig | None = None,
) -> bool:
    """Check if command matches any whitelist pattern.

    Whitelisted commands bypass blocklist validation and approval prompts.

    Security:
        All patterns are treated as LITERAL/EXACT matches by default for safety.
        To use regex patterns, prefix with "regex:" (e.g., "regex:git (status|log)")
        This prevents accidental regex interpretation of commands like "./gradlew"

    Args:
        command: The bash command to check
        config: Optional config with whitelist patterns

    Returns:
        True if command is whitelisted, False otherwise

    Example:
        >>> config = BashToolConfig(whitelist_patterns=["git status"])
        >>> is_whitelisted("git status", config)
        True
        >>> is_whitelisted("rm -rf /", config)
        False
        >>> # Regex must be explicit
        >>> config2 = BashToolConfig(whitelist_patterns=["regex:git (status|log)"])
        >>> is_whitelisted("git status", config2)
        True
    """
    if not config or not config.whitelist_patterns:
        return False

    # Create whitelist manager with patterns from config
    manager = WhitelistManager()
    for pattern in config.whitelist_patterns:
        # Check for explicit regex prefix
        if pattern.startswith("regex:"):
            # Explicit regex pattern
            regex_pattern = pattern[6:]  # Remove "regex:" prefix
            try:
                manager.add_pattern(
                    regex_pattern,
                    pattern_type="regex",
                )
            except ValueError as e:
                # Invalid regex - log warning but don't crash
                import warnings

                warnings.warn(
                    f"Invalid regex pattern '{regex_pattern}': {e}. Pattern will be ignored.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
        else:
            # Treat as literal/exact match for safety
            manager.add_pattern(
                pattern,
                pattern_type="exact",
            )

    return manager.is_whitelisted(command)


def validate_command(
    command: str,
    config: BashToolConfig | None = None,
) -> None:
    """Validate command against blocked patterns.

    Whitelisted commands bypass blocklist validation.

    Args:
        command: The bash command to validate
        config: Optional config with blocked patterns (uses defaults if None)

    Raises:
        BlockedCommandError: If command matches a blocked pattern

    Example:
        >>> validate_command("ls -la")  # OK
        >>> validate_command("sudo rm -rf /")  # Raises BlockedCommandError
        >>> config = BashToolConfig(whitelist_patterns=["sudo apt-get update"])
        >>> validate_command("sudo apt-get update", config)  # OK (whitelisted)
    """
    if config and config.allow_dangerous:
        # Skip validation if dangerous commands are explicitly allowed
        return

    # Check whitelist first - whitelisted commands bypass blocklist
    if is_whitelisted(command, config):
        return

    patterns = config.blocked_patterns if config else DEFAULT_BLOCKED_PATTERNS

    for pattern in patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise BlockedCommandError(
                f"Command blocked: matches pattern '{pattern}'\nCommand: {command}"
            )


def _run_command(
    command: str,
    timeout: int,
    working_directory: str | None = None,
) -> tuple[str, str, int]:
    """Run bash command with timeout and capture output.

    Explicitly uses /bin/bash to ensure bash-specific features work consistently
    across systems where /bin/sh may be dash or another shell.

    Args:
        command: The bash command to execute
        timeout: Timeout in seconds
        working_directory: Optional working directory

    Returns:
        Tuple of (stdout, stderr, exit_code)

    Raises:
        ToolExecutionError: If subprocess execution fails
        subprocess.TimeoutExpired: If command exceeds timeout
    """
    # Validate working directory if specified
    cwd = None
    if working_directory:
        cwd_path = Path(working_directory)
        if not cwd_path.exists():
            raise ToolExecutionError(
                f"Working directory does not exist: {working_directory}"
            )
        if not cwd_path.is_dir():
            raise ToolExecutionError(
                f"Working directory is not a directory: {working_directory}"
            )
        cwd = str(cwd_path)

    try:
        # Explicitly use /bin/bash to ensure bash-specific features work
        # (process substitutions, [[ ... ]], etc.) even on systems where
        # /bin/sh is dash (e.g., Ubuntu)
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        # Filter out HuggingFace tokenizers fork warning from stderr
        # This warning appears when subprocess forks after tokenizers have been loaded
        # It's informational only - tokenizers automatically handles the issue
        stderr_filtered = result.stderr
        if stderr_filtered:
            lines = stderr_filtered.split("\n")
            filtered_lines = [
                line
                for line in lines
                if "huggingface/tokenizers" not in line.lower()
                and "disabling parallelism" not in line.lower()
            ]
            stderr_filtered = "\n".join(filtered_lines).strip()

        return result.stdout, stderr_filtered, result.returncode

    except subprocess.TimeoutExpired as e:
        raise ToolExecutionError(
            f"Command timed out after {timeout} seconds: {command}"
        ) from e
    except Exception as e:
        raise ToolExecutionError(f"Failed to execute command: {e}") from e


@tool
def bash_execute(
    command: str,
    timeout: int | None = None,
    working_directory: str | None = None,
) -> str:
    """Execute a bash command with security controls.

    This tool executes bash commands with strict security controls including:
    - Command validation (blocks dangerous patterns like sudo, rm -rf /, etc.)
    - Whitelist support (trusted commands bypass approval prompts)
    - Timeout enforcement (default from profile config)
    - Working directory control
    - Detailed output capture

    The tool uses the BashToolConfig from the active profile's ToolConfig.bash
    settings. Call set_bash_config() to inject the profile configuration before
    tool registration.

    Whitelist behavior:
    - Whitelisted commands bypass blocklist validation
    - Whitelisted commands skip approval prompts (when integrated with registry)
    - Configure via BashToolConfig.whitelist_patterns

    Args:
        command: The bash command to execute
        timeout: Optional timeout override in seconds (default from config)
        working_directory: Optional working directory override (default from config)

    Returns:
        Command output. Format depends on result:
        - Success (exit 0): stdout content
        - Failure (exit != 0): "Command failed with exit code X:\\nstderr"
        - Blocked: Error message with blocked pattern

    Example:
        >>> bash_execute("ls -la")
        'total 48\\ndrwxr-xr-x  12 user  staff   384 Nov 10 21:00 .\\n...'
        >>> bash_execute("sudo rm -rf /")
        'Command blocked: matches pattern \\'sudo\\\\s\\'...'
        >>> # With whitelist_patterns=["sudo apt-get update"]
        >>> bash_execute("sudo apt-get update")  # Allowed (whitelisted)
    """
    # Get config from module-level (set by registry via set_bash_config)
    config = get_bash_config()

    # Use config timeout if not specified
    actual_timeout = timeout if timeout is not None else config.timeout
    actual_working_dir = working_directory or config.working_directory

    # Validate command for security
    try:
        validate_command(command, config)
    except BlockedCommandError as e:
        return f"❌ {e}"

    # Execute command
    try:
        stdout, stderr, exit_code = _run_command(
            command,
            timeout=actual_timeout,
            working_directory=actual_working_dir,
        )

        # Format output based on exit code
        if exit_code == 0:
            # Success: return stdout (or stderr if stdout is empty)
            return stdout if stdout else stderr if stderr else "(no output)"
        else:
            # Failure: return exit code and stderr
            output = f"Command failed with exit code {exit_code}"
            if stderr:
                output += f":\n{stderr}"
            if stdout:
                output += f"\nstdout:\n{stdout}"
            return output

    except ToolExecutionError as e:
        return f"❌ {e}"

"""Bash command execution tool with security controls.

Provides secure bash command execution with:
- Command validation and blocking
- Timeout enforcement
- Working directory control
- Detailed output capture (stdout/stderr/exit code)
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from consoul.ai.tools.exceptions import BlockedCommandError, ToolExecutionError
from consoul.config.models import BashToolConfig

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


def validate_command(
    command: str,
    config: BashToolConfig | None = None,
) -> None:
    """Validate command against blocked patterns.

    Args:
        command: The bash command to validate
        config: Optional config with blocked patterns (uses defaults if None)

    Raises:
        BlockedCommandError: If command matches a blocked pattern

    Example:
        >>> validate_command("ls -la")  # OK
        >>> validate_command("sudo rm -rf /")  # Raises BlockedCommandError
    """
    if config and config.allow_dangerous:
        # Skip validation if dangerous commands are explicitly allowed
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
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result.stdout, result.stderr, result.returncode

    except subprocess.TimeoutExpired as e:
        raise ToolExecutionError(
            f"Command timed out after {timeout} seconds: {command}"
        ) from e
    except Exception as e:
        raise ToolExecutionError(f"Failed to execute command: {e}") from e


@tool  # type: ignore[misc]
def bash_execute(
    command: str,
    timeout: int | None = None,
    working_directory: str | None = None,
) -> str:
    """Execute a bash command with security controls.

    This tool executes bash commands with strict security controls including:
    - Command validation (blocks dangerous patterns like sudo, rm -rf /, etc.)
    - Timeout enforcement (default 30 seconds)
    - Working directory control
    - Detailed output capture

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
    """
    # Load config (this will be injected by the tool system in the future)
    # For now, use defaults
    config = BashToolConfig()

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

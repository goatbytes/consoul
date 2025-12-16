"""Command execution utilities for TUI.

Provides handlers for executing shell commands inline and as standalone
command executions with proper output handling, timeout management, and
error handling.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

__all__ = [
    "CommandExecutionHandler",
    "InlineCommandInfo",
]


@dataclass
class InlineCommandInfo:
    """Information about an inline command to be executed."""

    placeholder: str  # Full pattern like !`command`
    command: str  # The actual command to execute


class CommandExecutionHandler:
    """Handler for command execution operations.

    Provides methods for:
    - Executing shell commands with timeout
    - Injecting command output into messages
    - Detecting and parsing inline commands
    - Substituting inline commands with their output
    """

    def __init__(
        self,
        timeout: int = 30,
        max_output_lines: int = 1000,
        max_inline_output_chars: int = 10000,
    ):
        """Initialize command execution handler.

        Args:
            timeout: Command execution timeout in seconds (default: 30)
            max_output_lines: Maximum lines for command output before truncation
            max_inline_output_chars: Maximum characters for inline command output
        """
        self.timeout = timeout
        self.max_output_lines = max_output_lines
        self.max_inline_output_chars = max_inline_output_chars

    async def execute_command(
        self,
        command: str,
        cwd: Path | None = None,
        run_in_thread: Callable[..., Any] | None = None,
    ) -> tuple[str, str, int, float]:
        """Execute a shell command and return output.

        Args:
            command: Command to execute
            cwd: Working directory (default: current directory)
            run_in_thread: Optional async function to run subprocess in thread

        Returns:
            Tuple of (stdout, stderr, exit_code, execution_time)

        Raises:
            subprocess.TimeoutExpired: If command exceeds timeout
            Exception: For other execution failures
        """
        start_time = time.time()
        working_dir = cwd or Path.cwd()

        logger.info(f"[COMMAND_EXEC] Executing: {command}")

        try:
            if run_in_thread:
                # Run in thread to avoid blocking async event loop
                result = await run_in_thread(
                    subprocess.run,
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=working_dir,
                )
            else:
                # Synchronous execution
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=working_dir,
                )

            execution_time = time.time() - start_time
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode

            # Truncate stdout if too long
            stdout = self._truncate_output(stdout)

            logger.info(
                f"[COMMAND_EXEC] Completed with exit code {exit_code} "
                f"in {execution_time:.2f}s"
            )

            return stdout, stderr, exit_code, execution_time

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.warning(f"[COMMAND_EXEC] Command timed out: {command}")
            raise

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[COMMAND_EXEC] Execution failed: {e}", exc_info=True)
            raise

    def _truncate_output(self, output: str) -> str:
        """Truncate output if it exceeds maximum lines.

        Args:
            output: Command output to truncate

        Returns:
            Truncated output with ellipsis if needed
        """
        if not output:
            return output

        lines = output.split("\n")
        if len(lines) <= self.max_output_lines:
            return output

        # Keep first 50 and last 50 lines
        first = lines[:50]
        last = lines[-50:]
        truncated = [
            *first,
            f"\n... truncated {len(lines) - 100} lines ...\n",
            *last,
        ]
        return "\n".join(truncated)

    def inject_command_output(self, message: str, command: str, output: str) -> str:
        """Inject command output into message with shell_command tags.

        Args:
            message: Original user message
            command: Command that was executed
            output: Command output to inject

        Returns:
            Message with command output prepended in shell_command tags
        """
        prefix = f"""<shell_command>
Command: {command}
Output:
{output}
</shell_command>

"""
        logger.info("[COMMAND_INJECT] Injected command output into message")
        return prefix + message

    def detect_inline_commands(self, message: str) -> list[InlineCommandInfo]:
        """Detect inline commands in message using !`command` pattern.

        Args:
            message: Message text to scan for inline commands

        Returns:
            List of InlineCommandInfo objects for detected commands
        """
        pattern = r"!\s*`([^`]+)`"
        matches = list(re.finditer(pattern, message))

        commands = []
        for match in matches:
            command = match.group(1)
            placeholder = match.group(0)
            commands.append(InlineCommandInfo(placeholder, command))

        logger.info(f"[INLINE_COMMAND] Detected {len(commands)} inline commands")
        return commands

    async def substitute_inline_commands(
        self,
        message: str,
        run_in_thread: Callable[..., Any] | None = None,
    ) -> str:
        """Execute inline commands and substitute with their output.

        Args:
            message: Message containing inline commands
            run_in_thread: Optional async function to run subprocess in thread

        Returns:
            Message with all inline commands replaced by their output
        """
        commands = self.detect_inline_commands(message)

        if not commands:
            return message

        # Execute each command and build replacement map
        replacements = {}
        for cmd_info in commands:
            logger.info(f"[INLINE_COMMAND] Executing: {cmd_info.command}")

            try:
                stdout, stderr, exit_code, _ = await self.execute_command(
                    cmd_info.command, run_in_thread=run_in_thread
                )

                # Build output
                output = stdout.strip() if stdout else ""
                if stderr:
                    output += f"\n[stderr: {stderr.strip()}]"

                if exit_code != 0:
                    output = f"[Command failed with exit code {exit_code}]\n{output}"

                # Truncate if too long
                if len(output) > self.max_inline_output_chars:
                    output = (
                        output[: self.max_inline_output_chars]
                        + "\n... (output truncated)"
                    )

                replacements[cmd_info.placeholder] = output

            except subprocess.TimeoutExpired:
                replacements[cmd_info.placeholder] = (
                    f"[Command timed out after {self.timeout} seconds]"
                )
                logger.warning(f"[INLINE_COMMAND] Timeout: {cmd_info.command}")

            except Exception as e:
                replacements[cmd_info.placeholder] = f"[Command failed: {e}]"
                logger.error(f"[INLINE_COMMAND] Error: {e}", exc_info=True)

        # Replace all command patterns with their output
        processed_message = message
        for placeholder, output in replacements.items():
            processed_message = processed_message.replace(placeholder, output)

        logger.info(f"[INLINE_COMMAND] Processed {len(replacements)} commands")
        return processed_message

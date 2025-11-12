"""Command risk analyzer for dynamic bash command assessment.

Provides intelligent, pattern-based risk analysis that classifies bash commands
as SAFE, CAUTION, DANGEROUS, or BLOCKED based on their potential impact.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

from consoul.ai.tools.base import RiskLevel

__all__ = ["CommandAnalyzer", "CommandRisk"]


@dataclass
class CommandRisk:
    """Risk assessment result for a command.

    Attributes:
        level: Risk classification (SAFE, CAUTION, DANGEROUS, BLOCKED)
        reason: Human-readable explanation of the risk assessment
        matched_pattern: Regex pattern that matched (if any)
        suggestions: Optional safer alternatives or recommendations
    """

    level: RiskLevel
    reason: str
    matched_pattern: str | None = None
    suggestions: list[str] = field(default_factory=list)


class CommandAnalyzer:
    """Analyzes bash commands to assess security risk dynamically.

    Uses pattern-based analysis to classify commands by their potential impact:
    - SAFE: Read-only operations with minimal risk
    - CAUTION: Operations that modify state but are generally safe
    - DANGEROUS: Operations with potential for data loss or system damage
    - BLOCKED: Explicitly prohibited operations (sudo, rm -rf /, etc.)

    The analyzer considers:
    - Base command name
    - Command flags and arguments
    - File paths and patterns
    - Combinations of operations (pipes, redirects)

    Example:
        >>> analyzer = CommandAnalyzer()
        >>> risk = analyzer.analyze_command("ls -la")
        >>> assert risk.level == RiskLevel.SAFE
        >>> risk = analyzer.analyze_command("rm -rf /")
        >>> assert risk.level == RiskLevel.BLOCKED
    """

    def __init__(self) -> None:
        """Initialize command analyzer with compiled patterns."""
        self._safe_patterns = self._compile_safe_patterns()
        self._caution_patterns = self._compile_caution_patterns()
        self._dangerous_patterns = self._compile_dangerous_patterns()
        self._blocked_patterns = self._compile_blocked_patterns()

    def analyze_command(self, command: str) -> CommandRisk:
        """Analyze a bash command and assess its risk level.

        Args:
            command: The bash command string to analyze

        Returns:
            CommandRisk with level, reason, and optional suggestions

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> risk = analyzer.analyze_command("git status")
            >>> assert risk.level == RiskLevel.SAFE
            >>> assert "read-only" in risk.reason.lower()
        """
        if not command or not command.strip():
            return CommandRisk(
                level=RiskLevel.SAFE,
                reason="Empty command (no-op)",
            )

        # Normalize whitespace
        command = command.strip()

        # Check BLOCKED patterns first (highest priority)
        for pattern in self._blocked_patterns:
            if pattern.search(command):
                return CommandRisk(
                    level=RiskLevel.BLOCKED,
                    reason=f"Command matches blocked pattern: {pattern.pattern}",
                    matched_pattern=pattern.pattern,
                    suggestions=[
                        "This command is explicitly prohibited for security reasons",
                        "Consider using safer alternatives or request admin assistance",
                    ],
                )

        # Extract base command for analysis
        try:
            base_cmd = self._extract_base_command(command)
        except Exception:
            # If we can't parse it, treat as dangerous
            return CommandRisk(
                level=RiskLevel.DANGEROUS,
                reason="Unable to parse command structure",
                suggestions=["Complex command structure - manual review recommended"],
            )

        # Check for DANGEROUS patterns
        for pattern in self._dangerous_patterns:
            if pattern.search(command):
                return CommandRisk(
                    level=RiskLevel.DANGEROUS,
                    reason=f"Command matches dangerous pattern: {pattern.pattern}",
                    matched_pattern=pattern.pattern,
                    suggestions=["Verify command carefully before execution"],
                )

        # Check if command has dangerous flags/arguments
        if self._has_dangerous_flags(command, base_cmd):
            return CommandRisk(
                level=RiskLevel.DANGEROUS,
                reason=f"Command '{base_cmd}' with potentially destructive flags",
                suggestions=["Review flags and target paths carefully"],
            )

        # Check if this is a read-only operation first (base command check)
        # But also check for redirects that would make it a write operation
        if self._is_read_only_operation(command, base_cmd):
            # Even though the base command is read-only, check for redirects
            if self._has_output_redirect(command):
                if self._targets_sensitive_path(command):
                    return CommandRisk(
                        level=RiskLevel.BLOCKED,
                        reason=f"Output redirection to system file: {base_cmd}",
                        suggestions=["Redirecting to system files is prohibited"],
                    )
                return CommandRisk(
                    level=RiskLevel.CAUTION,
                    reason=f"Output redirection: {base_cmd}",
                    suggestions=["Review redirect target path"],
                )
            return CommandRisk(
                level=RiskLevel.SAFE,
                reason=f"Read-only operation: {base_cmd}",
            )

        # Handle commands with output redirects
        # This includes echo/printf and read-only commands like cat that are redirected
        read_only_cmds = {
            "cat",
            "less",
            "more",
            "head",
            "tail",
            "grep",
            "egrep",
            "fgrep",
        }
        display_cmds = {"echo", "printf"}

        if base_cmd in display_cmds or (
            base_cmd in read_only_cmds and self._has_output_redirect(command)
        ):
            if self._has_output_redirect(command):
                # Check if redirect targets a sensitive path
                if self._targets_sensitive_path(command):
                    return CommandRisk(
                        level=RiskLevel.BLOCKED,
                        reason=f"Output redirection to system file: {base_cmd}",
                        suggestions=["Redirecting to system files is prohibited"],
                    )
                return CommandRisk(
                    level=RiskLevel.CAUTION,
                    reason=f"Output redirection: {base_cmd}",
                    suggestions=["Review redirect target path"],
                )
            # display commands without redirects are safe
            if base_cmd in display_cmds:
                return CommandRisk(
                    level=RiskLevel.SAFE,
                    reason=f"Display command without redirection: {base_cmd}",
                )

        # Handle rm separately - check for system paths regardless of flags
        if base_cmd == "rm":
            if self._rm_targets_system_path(command):
                return CommandRisk(
                    level=RiskLevel.BLOCKED,
                    reason="Removing system files is prohibited",
                    suggestions=[
                        "System paths (/etc, /var, /usr, etc.) cannot be deleted",
                        "Request admin assistance if needed",
                    ],
                )
            # Check for dangerous recursive removal (both -r and -f together, or wildcards)
            if re.search(r"rm\s+.*-[rf]*r[rf]*", command) and re.search(
                r"rm\s+.*-[rf]*f[rf]*", command
            ):
                return CommandRisk(
                    level=RiskLevel.DANGEROUS,
                    reason="Recursive/forced file removal",
                    suggestions=["Verify paths carefully before removal"],
                )
            # Check for wildcards with -f
            if "-f" in command and "*" in command:
                return CommandRisk(
                    level=RiskLevel.DANGEROUS,
                    reason="Forced file removal with wildcards",
                    suggestions=["Verify paths carefully before removal"],
                )
            # Single file removal is caution (including with -f or -i flags)
            return CommandRisk(
                level=RiskLevel.CAUTION,
                reason="File removal operation",
                suggestions=["Verify file path before removal"],
            )

        # Check for SAFE patterns (matches full command or base command)
        for pattern in self._safe_patterns:
            # Try matching full command or just the base command
            if pattern.search(command) or pattern.search(base_cmd):
                return CommandRisk(
                    level=RiskLevel.SAFE,
                    reason="Read-only or informational command",
                    matched_pattern=pattern.pattern,
                )

        # Check for CAUTION patterns
        for pattern in self._caution_patterns:
            if pattern.search(command) or pattern.search(base_cmd):
                return CommandRisk(
                    level=RiskLevel.CAUTION,
                    reason="Command modifies filesystem but is generally safe",
                    matched_pattern=pattern.pattern,
                )

        # Default to CAUTION for unknown commands
        return CommandRisk(
            level=RiskLevel.CAUTION,
            reason=f"Unknown command: {base_cmd} - defaulting to caution",
            suggestions=["Verify command behavior before execution"],
        )

    def _extract_base_command(self, command: str) -> str:
        """Extract the base command name from a command string.

        Args:
            command: Full command string

        Returns:
            Base command name (first non-assignment token)

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> analyzer._extract_base_command("ls -la /tmp")
            'ls'
            >>> analyzer._extract_base_command("FOO=bar ls -la")
            'ls'
        """
        # Handle pipes - analyze first command in pipeline
        if "|" in command:
            command = command.split("|")[0].strip()

        # Parse with shlex to handle quoting
        try:
            tokens = shlex.split(command)
            if tokens:
                # Skip environment variable assignments (FOO=bar)
                # and find first actual command
                for token in tokens:
                    # Skip flags
                    if token.startswith("-"):
                        continue
                    # Skip environment variable assignments
                    if "=" in token:
                        # Check if it's an assignment (VAR=value) vs comparison
                        parts = token.split("=", 1)
                        if len(parts) == 2 and parts[0].isidentifier():
                            # This is an env var assignment, skip it
                            continue
                    # Found the actual command
                    return token
        except ValueError:
            # Shlex parsing failed, fall back to simple split
            pass

        # Fallback: simple whitespace split, skipping assignments
        parts = command.split()
        for part in parts:
            if not part.startswith("-") and "=" not in part:
                return part

        return parts[0] if parts else ""

    def _has_dangerous_flags(self, command: str, base_cmd: str) -> bool:
        """Check if command has potentially dangerous flags or arguments.

        Args:
            command: Full command string
            base_cmd: Base command name

        Returns:
            True if command has dangerous flags

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> analyzer._has_dangerous_flags("rm -rf /", "rm")
            True
            >>> analyzer._has_dangerous_flags("rm file.txt", "rm")
            False
        """
        # rm with recursive force flags
        if base_cmd == "rm" and re.search(r"rm\s+.*-[rf]+", command):
            # Check if targeting root or system paths
            if re.search(r"rm\s+.*-[rf]+.*\s+/($|\s)", command):
                return True
            if re.search(r"rm\s+.*-[rf]+.*(etc|var|usr|sys|boot|lib)/", command):
                return True
            # rm -rf with wildcards is dangerous
            if "*" in command and "-r" in command:
                return True

        # chmod with 777 or recursive dangerous permissions
        if base_cmd == "chmod":
            if "777" in command or "666" in command:
                return True
            if "-R" in command and re.search(r"chmod.*-R.*\s+/", command):
                return True

        # chown recursive on system paths
        if (
            base_cmd == "chown"
            and "-R" in command
            and re.search(r"chown.*-R.*/(etc|var|usr|sys)", command)
        ):
            return True

        # kill -9 (SIGKILL)
        return base_cmd in ("kill", "killall", "pkill") and (
            "-9" in command or "SIGKILL" in command
        )

    def _is_read_only_operation(self, command: str, base_cmd: str) -> bool:
        """Check if command is a read-only operation.

        Args:
            command: Full command string
            base_cmd: Base command name

        Returns:
            True if command only reads data without modification

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> analyzer._is_read_only_operation("cat file.txt", "cat")
            True
            >>> analyzer._is_read_only_operation("cat file.txt > output.txt", "cat")
            False
        """
        # Common read-only commands
        read_only_commands = {
            "cat",
            "less",
            "more",
            "head",
            "tail",
            "grep",
            "egrep",
            "fgrep",
            "find",
            "locate",
            "which",
            "whereis",
            "file",
            "stat",
            "wc",
            "diff",
            "cmp",
            "md5sum",
            "sha256sum",
            "sha1sum",
        }

        # Check if command uses redirection (which makes it a write operation)
        if base_cmd in read_only_commands:
            # Look for output redirects: >, >>, or | tee
            # We need to be careful with quoted strings and escaped characters
            # Simple approach: check for redirect operators outside of quotes
            return not self._has_output_redirect(command)

        return False

    def _has_output_redirect(self, command: str) -> bool:
        """Check if command contains output redirection operators.

        Args:
            command: Full command string

        Returns:
            True if command has output redirection (>, >>, | tee)

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> analyzer._has_output_redirect("cat file.txt > output.txt")
            True
            >>> analyzer._has_output_redirect("cat file.txt")
            False
        """
        # Try to parse with shlex to handle quoting properly
        try:
            # Check for common redirect patterns
            # Match > or >> followed by a path (not inside quotes)
            if re.search(r'(?<!["\'])>+(?!["\'])', command):
                return True
            # Match | tee (pipe to tee is a write operation)
            if re.search(r"\|\s*tee\b", command):
                return True
        except Exception:
            # If we can't parse, be conservative - assume it has redirect
            # if we see redirect chars
            if ">" in command or "| tee" in command:
                return True

        return False

    def _targets_sensitive_path(self, command: str) -> bool:
        """Check if command redirects to a sensitive system path.

        Args:
            command: Full command string

        Returns:
            True if command targets sensitive paths like /etc, ~/.ssh, etc.

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> analyzer._targets_sensitive_path("echo foo > /etc/passwd")
            True
            >>> analyzer._targets_sensitive_path("echo foo > output.txt")
            False
        """
        # Extract redirect target
        redirect_match = re.search(r">+\s*([^\s;|&]+)", command)
        if redirect_match:
            target = redirect_match.group(1).strip()
            # Check for sensitive paths
            sensitive_patterns = [
                r"^/etc/",
                r"^/var/",
                r"^/usr/",
                r"^/sys/",
                r"^/boot/",
                r"^/lib/",
                r"^/dev/",
                r"^/proc/",
                r"^/root/",
                r"^~?/.ssh/",
                r"^~?/.bash",
                r"^~?/.zsh",
                r"^~?/.profile",
            ]
            for pattern in sensitive_patterns:
                if re.search(pattern, target):
                    return True
        return False

    def _rm_targets_system_path(self, command: str) -> bool:
        """Check if rm command targets system paths.

        Args:
            command: Full rm command string

        Returns:
            True if command targets system paths regardless of flags

        Example:
            >>> analyzer = CommandAnalyzer()
            >>> analyzer._rm_targets_system_path("rm /etc/passwd")
            True
            >>> analyzer._rm_targets_system_path("rm -rf /etc")
            True
            >>> analyzer._rm_targets_system_path("rm file.txt")
            False
        """
        # System path patterns that should always be blocked
        system_patterns = [
            r"\s+/etc(/|$|\s)",
            r"\s+/var(/|$|\s)",
            r"\s+/usr(/|$|\s)",
            r"\s+/sys(/|$|\s)",
            r"\s+/boot(/|$|\s)",
            r"\s+/lib(/|$|\s)",
            r"\s+/bin(/|$|\s)",
            r"\s+/sbin(/|$|\s)",
            r"\s+/dev(/|$|\s)",
            r"\s+/proc(/|$|\s)",
            # Also check for exact root
            r"\s+/($|\s)",
        ]
        return any(re.search(pattern, command) for pattern in system_patterns)

    def _compile_safe_patterns(self) -> list[re.Pattern[str]]:
        """Compile regex patterns for SAFE commands.

        Returns:
            List of compiled patterns matching safe operations
        """
        patterns = [
            # Filesystem navigation and listing
            r"^ls(\s|$)",
            r"^pwd(\s|$)",
            r"^cd(\s|$)",
            # Environment
            r"^env(\s|$)",
            r"^export\s+\w+=",  # Setting env vars
            # Help and documentation
            r"^man(\s|$)",
            r"^help(\s|$)",
            r"^which(\s|$)",
            r"^type(\s|$)",
            r"^whereis(\s|$)",
            # Git read-only operations
            r"^git\s+(status|log|diff|show|branch|remote|config\s+--list)",
            # Package info (read-only)
            r"^(npm|pip|cargo|gem)\s+(list|show|info|search|--version)",
            # System info
            r"^(uname|hostname|whoami|uptime|date)(\s|$)",
            # Process info (read-only)
            r"^(ps|top|htop|pgrep)(\s|$)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _compile_caution_patterns(self) -> list[re.Pattern[str]]:
        """Compile regex patterns for CAUTION commands.

        Returns:
            List of compiled patterns matching caution-level operations
        """
        patterns = [
            # File operations (non-destructive)
            r"^mkdir(\s|$)",
            r"^touch(\s|$)",
            r"^cp(\s|$)",
            r"^mv(\s|$)",
            r"^ln(\s|$)",
            # Note: rm is now handled separately in analyze_command
            # to check for system paths regardless of flags
            # Safe permissions
            r"^chmod\s+[0-7]{3}\s+[^/]",  # chmod octal on non-root paths
            # Git modifications
            r"^git\s+(add|commit|stash|checkout|merge|pull|fetch)",
            # Package operations (modifying)
            r"^(npm|pip|cargo|gem)\s+(install|update|uninstall)",
            # Archive operations
            r"^(tar|zip|unzip|gzip|gunzip)(\s|$)",
            # Text editing
            r"^(sed|awk)\s+",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _compile_dangerous_patterns(self) -> list[re.Pattern[str]]:
        """Compile regex patterns for DANGEROUS commands.

        Returns:
            List of compiled patterns matching dangerous operations
        """
        patterns = [
            # Destructive rm operations (not hitting blocked patterns)
            r"rm\s+.*-[rf].*\*",  # rm with wildcards
            r"rm\s+-rf\s+(?!/($|\s)|/etc|/var|/usr|/sys|/boot)",  # rm -rf but not system paths
            # Disk operations
            r"^dd(\s|$)",
            # System operations
            r"^(reboot|shutdown|halt|poweroff)(\s|$)",
            r"^systemctl\s+(stop|restart|disable)",
            r"^service\s+\w+\s+(stop|restart)",
            # Process killing
            r"^(kill|killall|pkill)\s+-9",
            r"^kill\s+.*SIGKILL",
            # Permissions (777/666 specifically, not system paths with -R)
            r"chmod\s+(777|666)\s+[^/]",  # chmod 777/666 on non-root paths
            r"chmod\s+-R.*/(etc|var|usr|sys)",
            # Network dangerous
            r"^iptables(\s|$)",
            r"^ip\s+link\s+delete",
            # Git destructive
            r"^git\s+(reset\s+--hard|clean\s+-[fxd]|push\s+--force)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _compile_blocked_patterns(self) -> list[re.Pattern[str]]:
        """Compile regex patterns for BLOCKED commands.

        Returns:
            List of compiled patterns matching blocked operations
        """
        # Reuse DEFAULT_BLOCKED_PATTERNS from bash.py
        patterns = [
            r"^sudo\s",  # sudo commands
            r"rm\s+(-[rf]+\s+)?/($|\s)",  # rm with root paths
            r"dd\s+if=",  # disk operations
            r":\(\)\{.*:\|:.*\};:",  # fork bomb
            r"wget.*\|.*bash",  # download-and-execute
            r"curl.*\|.*sh",  # download-and-execute
            r">\s*/dev/sd[a-z]",  # write to disk devices
            r"^mkfs",  # format filesystem (match at start)
            r"^fdisk",  # partition operations (match at start)
            r"^parted",  # partition operations (match at start)
            # Additional blocks for system paths (with or without wildcards)
            r"rm\s+.*-[rf]+.*/etc",  # rm -rf /etc
            r"rm\s+.*-[rf]+.*/var",  # rm -rf /var
            r"rm\s+.*-[rf]+.*/usr",  # rm -rf /usr
            r"rm\s+.*-[rf]+.*/sys",  # rm -rf /sys
            r"rm\s+.*-[rf]+.*/boot",  # rm -rf /boot
            r"rm\s+.*-[rf]+.*/lib",  # rm -rf /lib
            # Wildcard root deletions
            r"rm\s+.*-[rf]+.*\s+/\*",  # rm -rf /*
            r"rm\s+.*-[rf]+.*/etc/\*",  # rm -rf /etc/*
            r"rm\s+.*-[rf]+.*/var/\*",  # rm -rf /var/*
            r"rm\s+.*-[rf]+.*/usr/\*",  # rm -rf /usr/*
            r"rm\s+.*-[rf]+.*/sys/\*",  # rm -rf /sys/*
            r"rm\s+.*-[rf]+.*/boot/\*",  # rm -rf /boot/*
            r"rm\s+.*-[rf]+.*/lib/\*",  # rm -rf /lib/*
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

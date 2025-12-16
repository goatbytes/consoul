"""Gira integration for release tracking."""

from __future__ import annotations

import re
import subprocess


def create_release_ticket(version: str, epic: str = "EPIC-010") -> str | None:
    """
    Create Gira ticket for release.

    Args:
        version: Version number
        epic: Epic ID to link to

    Returns:
        Ticket ID or None if creation fails
    """
    cmd = [
        "gira",
        "ticket",
        "create",
        f"Release Consoul v{version}",
        "--type",
        "task",
        "--priority",
        "high",
        "--epic",
        epic,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            # Parse ticket ID from output: "Created ticket SOUL-XXX"
            match = re.search(r"SOUL-(\d+)", result.stdout)
            if match:
                return f"SOUL-{match.group(1)}"

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def update_ticket(ticket_id: str, version: str, status: str = "done") -> bool:
    """
    Update release ticket with completion status.

    Args:
        ticket_id: Ticket ID (e.g., "SOUL-284")
        version: Version number
        status: Final status

    Returns:
        True if successful
    """
    comment = f"""Successfully released v{version}!

✅ Version bumped
✅ CHANGELOG updated
✅ Tests passed
✅ Documentation published
✅ Git tagged and pushed
✅ GitHub release created
✅ PyPI published"""

    try:
        # Add comment
        subprocess.run(
            ["gira", "comment", "add", ticket_id, "-c", comment],
            capture_output=True,
            check=False,
        )

        # Move to done
        subprocess.run(
            ["gira", "ticket", "move", ticket_id, status, "--force"],
            capture_output=True,
            check=False,
        )

        return True

    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

"""Approval provider implementations.

Example providers for different environments:
- CliApprovalProvider: Command-line approval with input()
- AutoApproveProvider: Auto-approve all (TESTING ONLY - never use in production)

Future providers (implemented in other tickets):
- TuiApprovalProvider: Textual TUI modal (see SOUL-59)
- WebApprovalProvider: HTTP-based approval (for web apps)
"""

from consoul.ai.tools.providers.cli import CliApprovalProvider

__all__ = ["CliApprovalProvider"]

"""Approval provider implementations.

Example providers for different environments:
- CliApprovalProvider: Command-line approval with input()
- PolicyBasedApprovalProvider: Non-blocking policy-based approval for backends

Future providers (implemented in other tickets):
- TuiApprovalProvider: Textual TUI modal (see SOUL-59)
- WebApprovalProvider: HTTP-based approval (for web apps)
"""

from consoul.ai.tools.providers.cli import CliApprovalProvider
from consoul.ai.tools.providers.policy import PolicyBasedApprovalProvider

__all__ = ["CliApprovalProvider", "PolicyBasedApprovalProvider"]

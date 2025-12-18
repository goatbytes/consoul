"""Built-in configuration profiles for Consoul.

DEPRECATED: This module has been moved to consoul.tui.profiles as of v0.5.0
and will be removed in v1.0.0.

Profiles are a TUI/CLI convenience feature, not a core SDK requirement.
For SDK usage, use explicit parameters (model, system_prompt, temperature, etc.)
instead of profiles.

Import from consoul.tui.profiles instead:
    from consoul.tui.profiles import get_builtin_profiles

See migration guide: https://docs.consoul.ai/migration/profiles
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.config.models import ConsoulConfig

# Emit deprecation warning when module is imported
warnings.warn(
    "consoul.config.profiles is deprecated as of v0.5.0 and will be removed in v1.0.0. "
    "Profiles have been moved to consoul.tui.profiles as they are a TUI/CLI convenience feature, "
    "not a core SDK requirement. Import from consoul.tui.profiles instead:\n\n"
    "  from consoul.tui.profiles import get_builtin_profiles\n\n"
    "For SDK usage, use explicit parameters (model, system_prompt, temperature) "
    "instead of profiles. See migration guide: https://docs.consoul.ai/migration/profiles",
    DeprecationWarning,
    stacklevel=2,
)


# Wrapper functions to maintain original API signatures
# Import lazily to avoid circular dependencies
def get_builtin_profiles() -> dict[str, dict[str, Any]]:
    """Get all built-in configuration profiles.

    DEPRECATED: Import from consoul.tui.profiles instead.

    Returns:
        Dictionary mapping profile names to their configuration dictionaries.
    """
    from consoul.tui.profiles import get_builtin_profiles as _get_builtin_profiles

    return _get_builtin_profiles()


def list_available_profiles(config: ConsoulConfig) -> list[str]:
    """List all available profile names (built-in + custom).

    DEPRECATED: Import from consoul.tui.profiles instead.

    Args:
        config: ConsoulConfig instance to check for custom profiles.

    Returns:
        Sorted list of profile names.
    """
    from consoul.tui.profiles import list_available_profiles as _list_available_profiles

    return _list_available_profiles(config.profiles)  # type: ignore[arg-type]


def get_profile_description(profile_name: str, config: ConsoulConfig) -> str:
    """Get description for a profile.

    DEPRECATED: Import from consoul.tui.profiles instead.

    Args:
        profile_name: Name of the profile.
        config: ConsoulConfig instance to check for custom profiles.

    Returns:
        Profile description string.
    """
    from consoul.tui.profiles import get_profile_description as _get_profile_description

    return _get_profile_description(profile_name, config.profiles)  # type: ignore[arg-type]


__all__ = [
    "get_builtin_profiles",
    "get_profile_description",
    "list_available_profiles",
]

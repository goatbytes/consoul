"""Backward compatibility shim for consoul.config.profiles (deprecated).

⚠️ **DEPRECATED**: This module has been moved to consoul.tui.profiles in v0.5.0.

This compatibility shim ensures existing imports continue to work:
- `from consoul.config.profiles import ProfileConfig` ✅
- `from consoul.config.profiles import get_builtin_profiles` ✅
- `from consoul.config.profiles import get_profile_description` ✅
- `from consoul.config.profiles import list_available_profiles` ✅

**Migration Path:**
```python
# Old (deprecated, still works)
from consoul.config.profiles import ProfileConfig, get_builtin_profiles

# New (recommended)
from consoul.tui.profiles import ProfileConfig, get_builtin_profiles
```

**Why the move?**
Profiles are a TUI/CLI convenience feature, not a core SDK requirement.
The SDK is now profile-free (v0.5.0+), with profiles exclusive to TUI/CLI usage.

This shim will be removed in v1.0.0.
"""

import warnings

# Re-export everything from the new location
from consoul.tui.profiles import (
    ProfileConfig,
    get_builtin_profiles,
    get_profile_description,
    list_available_profiles,
)

__all__ = [
    "ProfileConfig",
    "get_builtin_profiles",
    "get_profile_description",
    "list_available_profiles",
]

# Emit deprecation warning when module is imported
warnings.warn(
    "consoul.config.profiles is deprecated and will be removed in v1.0.0. "
    "Use consoul.tui.profiles instead. "
    "Profiles are now exclusive to TUI/CLI usage; the SDK is profile-free.",
    DeprecationWarning,
    stacklevel=2,
)

"""macOS-specific fixes for PyTorch/Transformers segfaults.

This module provides workarounds for known segmentation fault issues when
loading HuggingFace models with PyTorch on macOS Apple Silicon.

Root Cause:
    Multiple OpenMP libraries (libomp.dylib) get loaded simultaneously,
    causing segfaults in LayerNorm and other operations.

Solution:
    Set environment variables BEFORE importing torch/transformers.
"""

import os
import platform
from typing import Any


def apply_macos_pytorch_fixes() -> dict[str, str]:
    """Apply environment variables to fix PyTorch segfaults on macOS.

    This must be called BEFORE importing torch or transformers.

    The fixes address:
    1. OpenMP library conflicts (primary cause of segfaults)
    2. MPS (Metal) backend fallback for unsupported operations

    Returns:
        Dict of environment variables that were set.

    Example:
        >>> from consoul.ai.macos_fixes import apply_macos_pytorch_fixes
        >>> applied = apply_macos_pytorch_fixes()
        >>> import torch  # Now safe to import
        >>> from transformers import AutoModelForCausalLM
    """
    if platform.system() != "Darwin":
        return {}

    fixes = {
        # Fix OpenMP conflicts (primary segfault cause)
        # This prevents multiple OpenMP libraries from conflicting
        "OMP_NUM_THREADS": "1",
        "OMP_MAX_ACTIVE_LEVELS": "1",
        # Enable MPS fallback for unsupported operations
        # Automatically uses CPU for operations not supported on Metal GPU
        "PYTORCH_ENABLE_MPS_FALLBACK": "1",
    }

    applied = {}
    for key, value in fixes.items():
        if key not in os.environ:
            os.environ[key] = value
            applied[key] = value

    return applied


def check_pytorch_compatibility() -> dict[str, Any]:
    """Check PyTorch compatibility and return diagnostics.

    This checks if the installed PyTorch version has known issues
    on macOS Apple Silicon.

    Returns:
        Dict with version info and compatibility status.

    Example:
        >>> info = check_pytorch_compatibility()
        >>> if "warning" in info:
        ...     print(info["warning"])
    """
    try:
        import torch
    except ImportError:
        return {"error": "PyTorch not installed"}

    info: dict[str, Any] = {
        "pytorch_version": torch.__version__,
        "mps_available": torch.backends.mps.is_available(),
        "mps_built": torch.backends.mps.is_built(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }

    # Check for known problematic versions
    try:
        from packaging import version

        pt_version = version.parse(torch.__version__.split("+")[0])  # Remove git hash

        if pt_version >= version.parse("2.5.0"):
            info["warning"] = (
                f"⚠️  PyTorch {torch.__version__} has known segfault issues on macOS. "
                f"Recommend downgrading to 2.4.1\n\n"
                f"Fix: Run 'pip install torch==2.4.1' or use 'poetry run consoul tui' "
                f"to use the project's pinned version."
            )
            info["recommended_version"] = "2.4.1"
            info["severity"] = "critical"
        elif pt_version == version.parse("2.2.1"):
            info["warning"] = (
                "⚠️  PyTorch 2.2.1 has known segfault issues. "
                "Recommend upgrading to 2.3.x or 2.4.x"
            )
            info["recommended_version"] = "2.4.1"
            info["severity"] = "high"
        elif pt_version >= version.parse("2.4.0") and pt_version < version.parse(
            "2.5.0"
        ):
            info["status"] = (
                "✅ PyTorch version compatible (may still segfault on some systems)"
            )
            info["severity"] = "low"
        else:
            info["status"] = "✅ PyTorch version compatible"
            info["severity"] = "none"

    except ImportError:
        # packaging not available, skip version check
        pass

    return info

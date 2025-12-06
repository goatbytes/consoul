"""AI provider factory for dynamic model initialization.

This module provides a factory pattern for initializing LangChain chat models
from configuration, with automatic provider detection, API key resolution,
and comprehensive error handling.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any, overload

from langchain.chat_models import init_chat_model
from pydantic import SecretStr  # noqa: TC002  # Used in runtime function signatures

from consoul.ai.exceptions import (
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
    OllamaServiceError,
    ProviderInitializationError,
)
from consoul.config.models import Provider

if TYPE_CHECKING:
    from pathlib import Path

    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.config.models import ModelConfig

# Provider package mapping
PROVIDER_PACKAGES = {
    Provider.OPENAI: "langchain_openai",
    Provider.ANTHROPIC: "langchain_anthropic",
    Provider.GOOGLE: "langchain_google_genai",
    Provider.OLLAMA: "langchain_ollama",
    Provider.HUGGINGFACE: "langchain_huggingface",
    Provider.LLAMACPP: "llama_cpp",  # llama-cpp-python
    Provider.MLX: "mlx_lm",  # Apple's MLX framework
}

# LangChain model_provider names (for init_chat_model)
# Maps our Provider enum to LangChain's expected model_provider parameter
LANGCHAIN_PROVIDER_NAMES = {
    Provider.OPENAI: "openai",
    Provider.ANTHROPIC: "anthropic",
    Provider.GOOGLE: "google_genai",  # LangChain expects "google_genai" not "google"
    Provider.OLLAMA: "ollama",
    Provider.HUGGINGFACE: "huggingface",
}

# Model name patterns for provider detection
# Note: Order matters! HuggingFace patterns (with slashes) must be checked before Ollama
# to prevent "mistralai/" from matching Ollama's "mistral" pattern
PROVIDER_PATTERNS: dict[Provider, list[str]] = {
    Provider.OPENAI: ["gpt-", "o1-", "text-davinci"],
    Provider.ANTHROPIC: ["claude-"],
    Provider.GOOGLE: ["gemini-", "palm-"],
    Provider.HUGGINGFACE: [
        "meta-llama/",
        "mistralai/",
        "google/",
        "openai-community/",
        "microsoft/",
        "facebook/",
        "moonshotai/",
        "Qwen/",
        "tiiuae/",  # Falcon models
        "EleutherAI/",
        "bigscience/",
        "stabilityai/",
    ],
    Provider.OLLAMA: ["llama", "mistral", "phi", "qwen", "codellama"],
}

# Provider documentation URLs
PROVIDER_DOCS = {
    Provider.OPENAI: "https://platform.openai.com/docs/models",
    Provider.ANTHROPIC: "https://docs.anthropic.com/claude/docs/models-overview",
    Provider.GOOGLE: "https://ai.google.dev/models/gemini",
    Provider.OLLAMA: "https://ollama.com/library",
    Provider.HUGGINGFACE: "https://huggingface.co/models",
    Provider.LLAMACPP: "https://github.com/ggml-org/llama.cpp",
    Provider.MLX: "https://huggingface.co/mlx-community",
}

# API key environment variable names
API_KEY_ENV_VARS = {
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    Provider.GOOGLE: "GOOGLE_API_KEY",
    Provider.OLLAMA: None,  # Ollama doesn't require API key
    Provider.HUGGINGFACE: "HUGGINGFACEHUB_API_TOKEN",
    Provider.LLAMACPP: None,  # Llama.cpp doesn't require API key
    Provider.MLX: None,  # MLX doesn't require API key
}


def is_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama service is running locally.

    Args:
        base_url: The base URL for the Ollama service. Defaults to http://localhost:11434.

    Returns:
        True if Ollama is running and accessible, False otherwise.
    """
    try:
        import requests

        response = requests.get(f"{base_url}/api/tags", timeout=2)
        return bool(response.status_code == 200)
    except Exception:
        return False


def get_ollama_models(
    base_url: str = "http://localhost:11434", include_context: bool = False
) -> list[dict[str, Any]]:
    """Get list of available Ollama models.

    Args:
        base_url: The base URL for the Ollama service. Defaults to http://localhost:11434.
        include_context: Whether to fetch context length for each model (slower).

    Returns:
        List of model dicts with 'name', 'size', and optionally 'context_length' keys.
        Sorted by size (smallest first). Returns empty list if Ollama is not running.
    """
    try:
        import requests

        response = requests.get(f"{base_url}/api/tags", timeout=2)
        if response.status_code != 200:
            return []

        data = response.json()
        models = data.get("models", [])

        # Extract model info
        model_list: list[dict[str, Any]] = []
        for m in models:
            model_info: dict[str, Any] = {
                "name": m.get("name", ""),
                "size": m.get("size", 0),
            }

            # Optionally fetch context length from model details
            if include_context:
                try:
                    show_response = requests.post(
                        f"{base_url}/api/show",
                        json={"name": model_info["name"]},
                        timeout=5,
                    )
                    if show_response.status_code == 200:
                        show_data = show_response.json()
                        model_info_data = show_data.get("model_info", {})

                        # Try to find context_length from model_info
                        # Different architectures use different keys
                        context_length = None
                        for key, value in model_info_data.items():
                            if "context_length" in key.lower():
                                context_length = value
                                break

                        if context_length:
                            model_info["context_length"] = context_length
                except Exception:
                    pass  # Skip context fetching if it fails

            model_list.append(model_info)

        # Sort by size (smallest first for faster title generation)
        model_list.sort(key=lambda m: m.get("size", float("inf")))

        return model_list
    except Exception:
        return []


def get_huggingface_local_models() -> list[dict[str, Any]]:
    """Get list of locally cached HuggingFace models.

    Scans the HuggingFace cache directory (~/.cache/huggingface/hub/) and
    returns information about downloaded models.

    Returns:
        List of model dicts with 'name', 'size', and 'revisions' keys.
        Sorted by name. Returns empty list if no models cached or scan fails.

    Example:
        >>> models = get_huggingface_local_models()
        >>> for model in models:
        ...     print(f"{model['name']} ({model['size_gb']:.1f}GB)")
        meta-llama/Llama-3.1-8B-Instruct (8.5GB)
        google/flan-t5-base (1.2GB)
    """
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        # huggingface_hub not installed
        return []

    try:
        # Scan the HuggingFace cache
        cache_info = scan_cache_dir()

        model_list: list[dict[str, Any]] = []
        for repo in cache_info.repos:
            # Only include models (not datasets)
            if repo.repo_type == "model":
                model_info: dict[str, Any] = {
                    "name": repo.repo_id,
                    "size": repo.size_on_disk,
                    "size_gb": repo.size_on_disk / (1024**3),  # Convert to GB
                    "nb_files": repo.nb_files,
                    "revisions": len(list(repo.revisions)),
                }
                model_list.append(model_info)

        # Sort by name alphabetically
        model_list.sort(key=lambda m: m.get("name", "").lower())

        return model_list
    except Exception:
        # Scan failed (cache doesn't exist, permission error, etc.)
        return []


# Cache for GGUF model scan results (with TTL)
_gguf_cache: dict[str, Any] = {"models": None, "timestamp": 0}
_GGUF_CACHE_TTL = 300  # 5 minutes in seconds


def _scan_gguf_models() -> list[dict[str, Any]]:
    """Internal function to scan GGUF models from cache directories.

    This is the actual scanning logic, separated for caching purposes.
    """
    from pathlib import Path

    gguf_models: list[dict[str, Any]] = []

    # Directories to scan for GGUF models
    scan_dirs = [
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / ".lmstudio" / "models",
    ]

    for cache_dir in scan_dirs:
        if not cache_dir.exists():
            continue

        # Search for .gguf files in all repo directories
        for gguf_file in cache_dir.rglob("*.gguf"):
            try:
                # Get actual file size (resolve symlink if needed)
                actual_file = gguf_file.resolve()
                size_bytes = actual_file.stat().st_size
                size_gb = size_bytes / (1024**3)

                # Extract quantization type from filename
                name = gguf_file.name
                quant = "unknown"
                for q in [
                    "IQ4",
                    "IQ3",
                    "Q4",
                    "Q5",
                    "Q8",
                    "Q2",
                    "Q3",
                    "Q6",
                    "F16",
                    "F32",
                ]:
                    if q.lower() in name.lower():
                        quant = q
                        break

                # Get repo name from path
                repo_dir = None
                if cache_dir.name == "hub":
                    # HuggingFace format: models--Org--ModelName
                    for parent in gguf_file.parents:
                        if parent.name.startswith("models--"):
                            repo_dir = parent.name.replace("models--", "").replace(
                                "--", "/"
                            )
                            break
                elif cache_dir.name == "models":
                    # LM Studio format: Org/ModelName/file.gguf
                    # Get the two parent directories (Org/ModelName)
                    parts = gguf_file.relative_to(cache_dir).parts
                    if len(parts) >= 3:
                        repo_dir = f"{parts[0]}/{parts[1]}"
                    elif len(parts) == 2:
                        repo_dir = parts[0]

                model_info: dict[str, Any] = {
                    "name": name,
                    "path": str(gguf_file),
                    "size": size_bytes,
                    "size_gb": size_gb,
                    "quant": quant,
                    "repo": repo_dir or "unknown",
                }
                gguf_models.append(model_info)

            except Exception:
                # Skip files we can't read
                continue

    # Sort by size (smallest first for faster loading)
    gguf_models.sort(key=lambda m: m["size"])

    return gguf_models


def get_gguf_models_from_cache(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Get list of GGUF models from HuggingFace cache and LM Studio.

    Scans both the HuggingFace cache directory and LM Studio models directory
    for .gguf files which can be used with llama.cpp for local model execution.

    Results are cached for 5 minutes to avoid repeated expensive directory scans.

    Args:
        force_refresh: If True, bypass cache and force a fresh scan.

    Returns:
        List of GGUF model dicts with 'name', 'path', 'size_gb', 'quant' keys.
        Sorted by size (smallest first). Returns empty list if no models found.

    Example:
        >>> models = get_gguf_models_from_cache()
        >>> for model in models:
        ...     print(f"{model['name']} ({model['size_gb']:.1f}GB) - {model['quant']}")
        OpenAI-20B-Q4.gguf (11.0GB) - Q4
        Llama-3.1-8B-Q8.gguf (8.5GB) - Q8
    """
    import time

    # Check if cache is valid
    current_time = time.time()
    cache_age = current_time - _gguf_cache["timestamp"]

    if (
        not force_refresh
        and _gguf_cache["models"] is not None
        and cache_age < _GGUF_CACHE_TTL
    ):
        # Return cached results
        cached_models: list[dict[str, Any]] = _gguf_cache["models"]
        return cached_models

    # Perform actual scan
    models = _scan_gguf_models()

    # Update cache
    _gguf_cache["models"] = models
    _gguf_cache["timestamp"] = current_time

    return models


def get_local_mlx_models() -> list[dict[str, Any]]:
    """Scan for locally downloaded MLX models.

    Looks in both ~/.lmstudio/models and ~/.cache/mlx for directories
    containing MLX model files (identified by config.json and .safetensors).

    Returns:
        List of MLX model dicts with 'name', 'path', 'size_gb' keys.
    """
    from pathlib import Path

    mlx_models: list[dict[str, Any]] = []

    # Directories to scan for MLX models
    scan_dirs = [
        Path.home() / ".lmstudio" / "models",
        Path.home() / ".cache" / "mlx",
    ]

    for base_dir in scan_dirs:
        if not base_dir.exists():
            continue

        # Look for directories with safetensors files (MLX format)
        for model_dir in base_dir.rglob("*/"):
            # Check if this looks like an MLX model directory
            has_config = (model_dir / "config.json").exists()
            has_safetensors = any(model_dir.glob("*.safetensors"))

            if has_config and has_safetensors:
                # Get model name from path
                relative_path = model_dir.relative_to(base_dir)
                # For ~/.cache/mlx, convert Org--ModelName back to Org/ModelName
                model_name = str(relative_path).replace("\\", "/").replace("--", "/")

                # Calculate total size
                total_size = sum(
                    f.stat().st_size for f in model_dir.rglob("*") if f.is_file()
                )
                size_gb = total_size / (1024**3)

                mlx_models.append(
                    {
                        "name": model_name,
                        "path": str(model_dir),
                        "size_gb": size_gb,
                    }
                )

    # Sort by name
    mlx_models.sort(key=lambda m: m["name"])

    return mlx_models


def get_mlx_cache_dir() -> Path:
    """Get the MLX cache directory for converted models.

    Returns:
        Path to MLX cache directory (~/.cache/mlx by default)
    """
    from pathlib import Path

    # NOTE: MLX cache directory - future enhancement: make configurable via MLXConfig
    # Currently uses ~/.cache/mlx for model conversions and quantizations
    cache_dir = Path.home() / ".cache" / "mlx"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_convertible_hf_models() -> list[dict[str, Any]]:
    """Get list of local HuggingFace models that can be converted to MLX.

    Scans the HuggingFace cache and returns models that:
    1. Are not already converted to MLX
    2. Have supported architectures for MLX

    Returns:
        List of dicts with 'name', 'size_gb', 'path', 'converted' keys
    """
    hf_models = get_huggingface_local_models()
    mlx_cache = get_mlx_cache_dir()

    convertible = []
    for model in hf_models:
        model_name = model.get("name", "")
        if not model_name:
            continue

        # Check if already converted (exists in MLX cache)
        # MLX models are stored as: ~/.cache/mlx/{org}/{model_name}
        mlx_path = mlx_cache / model_name.replace("/", "--")
        is_converted = mlx_path.exists() and (mlx_path / "config.json").exists()

        convertible.append(
            {
                "name": model_name,
                "size_gb": model.get("size_gb", 0),
                "size": model.get("size", 0),
                "converted": is_converted,
                "mlx_path": str(mlx_path) if is_converted else None,
            }
        )

    return convertible


def convert_hf_to_mlx(
    hf_model_name: str,
    output_dir: str | None = None,
    quantize: bool = True,
    q_bits: int = 4,
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Convert a local HuggingFace model to MLX format.

    Uses mlx_lm.convert to convert PyTorch models to MLX format with
    optional quantization for reduced size and faster inference.

    Args:
        hf_model_name: HuggingFace model identifier (e.g., "Qwen/Qwen3-8B")
        output_dir: Output directory (default: ~/.cache/mlx/{model_name})
        quantize: Whether to apply quantization (default: True for 4-bit)
        q_bits: Quantization bits - 4 or 8 (default: 4)
        progress_callback: Optional callback(line: str) for progress updates

    Returns:
        Dict with 'success', 'output_path', 'error' keys

    Raises:
        MissingDependencyError: If mlx-lm is not installed
        ValueError: If invalid parameters or insufficient disk space
    """
    import shutil
    import subprocess
    from pathlib import Path

    # Validate mlx-lm is installed
    try:
        import mlx_lm  # noqa: F401
    except ImportError as e:
        raise MissingDependencyError(
            "mlx-lm is required for model conversion.\n\n"
            "Install with: pip install mlx-lm\n"
            "Or with Consoul: pip install 'consoul[mlx]'"
        ) from e

    # Validate quantization bits
    if q_bits not in (4, 8):
        raise ValueError(f"Quantization bits must be 4 or 8, got: {q_bits}")

    # Determine output directory
    if output_dir is None:
        mlx_cache = get_mlx_cache_dir()
        # Store as: ~/.cache/mlx/Org--ModelName
        safe_name = hf_model_name.replace("/", "--")
        output_path = mlx_cache / safe_name
    else:
        output_path = Path(output_dir)

    # Check if already exists
    if output_path.exists() and (output_path / "config.json").exists():
        return {
            "success": True,
            "output_path": str(output_path),
            "message": "Model already converted",
            "skipped": True,
        }

    # Check disk space (estimate: need 1.5x model size for conversion workspace)
    hf_models = {m["name"]: m for m in get_huggingface_local_models()}
    model_info = hf_models.get(hf_model_name)
    if model_info:
        model_size_bytes = model_info.get("size", 0)
        required_space = model_size_bytes * 1.5  # Safety margin
        stat = shutil.disk_usage(output_path.parent)
        if stat.free < required_space:
            required_gb = required_space / (1024**3)
            available_gb = stat.free / (1024**3)
            raise ValueError(
                f"Insufficient disk space for conversion.\n"
                f"Required: ~{required_gb:.1f}GB\n"
                f"Available: {available_gb:.1f}GB"
            )

    # Build conversion command
    cmd = [
        "python",
        "-m",
        "mlx_lm",
        "convert",
        "--hf-path",
        hf_model_name,
        "--mlx-path",
        str(output_path),
    ]

    if quantize:
        cmd.extend(["-q", "--q-bits", str(q_bits)])

    # Run conversion
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Stream output for progress
        output_lines = []
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                output_lines.append(line)
                if progress_callback:
                    progress_callback(line)

        returncode = process.wait()

        if returncode == 0:
            return {
                "success": True,
                "output_path": str(output_path),
                "message": "Conversion completed successfully",
                "quantized": quantize,
                "q_bits": q_bits if quantize else None,
            }
        else:
            error_msg = "\n".join(output_lines[-10:])  # Last 10 lines
            return {
                "success": False,
                "error": f"Conversion failed with code {returncode}",
                "details": error_msg,
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Conversion error: {type(e).__name__}",
            "details": str(e),
        }


def find_gguf_for_model(model_name: str) -> str | None:
    """Find a GGUF file in cache for a given model name.

    Args:
        model_name: Model identifier. Can be:
                   - Full file path: "/path/to/model.gguf" (from model picker)
                   - Just repo: "DavidAU/OpenAi-GPT-oss-20b"
                   - Repo + filename: "DavidAU/OpenAi-GPT-oss-20b/model.Q4.gguf"

    Returns:
        Path to GGUF file, or None if not found.
        If only repo is given, prefers smaller quantized versions (Q4 > Q5 > Q8).
    """
    from pathlib import Path

    # If model_name is already a valid file path, return it directly
    if model_name.endswith(".gguf") and Path(model_name).exists():
        return model_name

    gguf_models = get_gguf_models_from_cache()

    # Check if model_name includes filename (has .gguf in it or multiple slashes)
    if "/" in model_name and model_name.count("/") > 1:
        # Format is "repo/filename" - find exact match
        parts = model_name.split("/")
        # Reconstruct: everything before last slash is repo, last part is filename
        repo = "/".join(parts[:-1])
        filename = parts[-1]

        for m in gguf_models:
            if m["repo"] == repo and m["name"] == filename:
                path: str = m["path"]
                return path

        # If exact match not found, fall back to repo-based search
        model_name = repo

    # Filter by model name/repo
    candidates = [m for m in gguf_models if model_name.lower() in m["repo"].lower()]

    if not candidates:
        return None

    # Sort by preference: Q4 > Q5 > Q8 > others
    def quant_priority(model: dict[str, Any]) -> int:
        quant = model["quant"].upper()
        if "Q4" in quant or "IQ4" in quant:
            return 0
        elif "Q5" in quant:
            return 1
        elif "Q8" in quant:
            return 2
        elif "Q6" in quant:
            return 3
        else:
            return 4

    candidates.sort(key=quant_priority)

    best_path: str = candidates[0]["path"]
    return best_path


def select_best_ollama_model(
    base_url: str = "http://localhost:11434",
) -> str | None:
    """Select the best available Ollama model for title generation.

    Preference order:
    1. llama3.2:1b (smallest, fastest)
    2. llama3.2:3b
    3. Any llama3.2 variant
    4. Any llama3 variant
    5. Smallest available model

    Args:
        base_url: The base URL for the Ollama service. Defaults to http://localhost:11434.

    Returns:
        Model name string or None if no models available.
    """
    models = get_ollama_models(base_url)
    if not models:
        return None

    model_names = [m["name"] for m in models]

    # Preference list
    preferred = [
        "llama3.2:1b",
        "llama3.2:3b",
    ]

    # Check preferred models first
    for pref in preferred:
        if pref in model_names:
            return pref

    # Check for any llama3.2 variant
    for name in model_names:
        if "llama3.2" in name.lower():
            return str(name)

    # Check for any llama3 variant
    for name in model_names:
        if "llama3" in name.lower():
            return str(name)

    # Fall back to smallest model
    return models[0]["name"] if models else None


def validate_provider_dependencies(provider: Provider) -> None:
    """Check if required langchain provider package is installed.

    Args:
        provider: The provider to validate.

    Raises:
        MissingDependencyError: If the required package is not installed.
    """
    package_name = PROVIDER_PACKAGES.get(provider)
    if not package_name:
        raise ProviderInitializationError(f"Unknown provider: {provider}")

    # Check if package is installed
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        pip_package = package_name.replace("_", "-")

        # Special message for LlamaCpp with Metal GPU support
        if provider == Provider.LLAMACPP:
            import platform

            install_msg = (
                f"Missing {pip_package} package.\n\n"
                f"To use {provider.value} models, install:\n"
            )

            if platform.system() == "Darwin":
                install_msg += (
                    f"   # macOS with Metal GPU acceleration (recommended):\n"
                    f'   CMAKE_ARGS="-DGGML_METAL=on" pip install {pip_package}\n\n'
                    f"   # Or CPU-only:\n"
                    f"   pip install {pip_package}\n\n"
                    f"   # Or with Poetry:\n"
                    f"   poetry install --extras llamacpp\n"
                )
            else:
                install_msg += (
                    f"   pip install {pip_package}\n\n"
                    f"   # Or with Poetry:\n"
                    f"   poetry install --extras llamacpp\n"
                )

            raise MissingDependencyError(install_msg)

        raise MissingDependencyError(
            f"Missing {pip_package} package.\n\n"
            f"To use {provider.value} models, install:\n"
            f"   pip install {pip_package}\n\n"
            f"Or install all providers:\n"
            f"   pip install consoul[all]"
        )


def get_provider_from_model(model_name: str) -> Provider | None:
    """Detect provider from model name.

    Args:
        model_name: The model name to analyze.

    Returns:
        Detected provider, or None if not recognized.

    Examples:
        >>> get_provider_from_model("gpt-4o")
        Provider.OPENAI
        >>> get_provider_from_model("claude-3-5-sonnet-20241022")
        Provider.ANTHROPIC
        >>> get_provider_from_model("granite4:3b")
        Provider.OLLAMA
    """
    model_lower = model_name.lower()

    # Check if it's an Ollama model FIRST (before checking other patterns)
    # Ollama uses colon-separated tags like "llama3:latest" or "gpt-oss:20b"
    # This must be checked before OpenAI patterns to prevent "gpt-oss:20b" matching "gpt-"
    if ":" in model_name:
        return Provider.OLLAMA

    # Check explicit patterns (OpenAI, Anthropic, Google, HuggingFace)
    for provider, patterns in PROVIDER_PATTERNS.items():
        if provider == Provider.OLLAMA:
            continue  # Handle Ollama separately
        if any(model_lower.startswith(pattern) for pattern in patterns):
            return provider

    # Check known Ollama model prefixes
    # For models without tags like "llama3" or "mistral"
    ollama_patterns = PROVIDER_PATTERNS.get(Provider.OLLAMA, [])
    if any(model_lower.startswith(pattern) for pattern in ollama_patterns):
        return Provider.OLLAMA

    # If still not detected, check if it's an installed Ollama model
    if is_ollama_running():
        try:
            ollama_models = get_ollama_models()
            ollama_model_names = [m.get("name", "") for m in ollama_models]
            # Check exact match or match without tag
            if model_name in ollama_model_names:
                return Provider.OLLAMA
            # Check if it matches any model name without the tag
            base_name = model_name.split(":")[0] if ":" in model_name else model_name
            if any(m.startswith(base_name) for m in ollama_model_names):
                return Provider.OLLAMA
        except Exception:
            # If we can't fetch Ollama models, continue with other detection
            pass

    return None


def build_model_params(model_config: ModelConfig) -> dict[str, Any]:
    """Convert ModelConfig to LangChain init_chat_model parameters.

    Args:
        model_config: The model configuration from profile.

    Returns:
        Dictionary of parameters for init_chat_model.
    """
    from consoul.config.models import (
        AnthropicModelConfig,
        GoogleModelConfig,
        HuggingFaceModelConfig,
        OllamaModelConfig,
        OpenAIModelConfig,
    )

    # Base parameters common to all providers
    params: dict[str, Any] = {
        "model": model_config.model,
        "temperature": model_config.temperature,
    }

    # Add max_tokens if specified
    if model_config.max_tokens is not None:
        params["max_tokens"] = model_config.max_tokens

    # Add stop sequences if specified
    if model_config.stop_sequences:
        params["stop"] = model_config.stop_sequences

    # Add provider-specific parameters
    if isinstance(model_config, OpenAIModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.frequency_penalty is not None:
            params["frequency_penalty"] = model_config.frequency_penalty
        if model_config.presence_penalty is not None:
            params["presence_penalty"] = model_config.presence_penalty
        if model_config.seed is not None:
            params["seed"] = model_config.seed
        if model_config.logit_bias is not None:
            params["logit_bias"] = model_config.logit_bias
        if model_config.response_format is not None:
            params["response_format"] = model_config.response_format
        if model_config.service_tier is not None:
            params["service_tier"] = model_config.service_tier
        # Enable streaming usage metadata for cost calculation via stream_options
        params["model_kwargs"] = {"stream_options": {"include_usage": True}}

    elif isinstance(model_config, AnthropicModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k
        if model_config.thinking is not None:
            params["thinking"] = model_config.thinking
        if model_config.betas is not None:
            params["betas"] = model_config.betas
        if model_config.metadata is not None:
            params["metadata"] = model_config.metadata
        # Enable streaming usage metadata for cost calculation (enabled by default)
        params["stream_usage"] = True

    elif isinstance(model_config, GoogleModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k
        if model_config.candidate_count is not None:
            params["candidate_count"] = model_config.candidate_count
        if model_config.safety_settings is not None:
            params["safety_settings"] = model_config.safety_settings
        if model_config.generation_config is not None:
            params["generation_config"] = model_config.generation_config

    elif isinstance(model_config, OllamaModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k

    elif isinstance(model_config, HuggingFaceModelConfig):
        if model_config.task is not None:
            params["task"] = model_config.task
        if model_config.max_new_tokens is not None:
            params["max_new_tokens"] = model_config.max_new_tokens
        if model_config.do_sample is not None:
            params["do_sample"] = model_config.do_sample
        if model_config.repetition_penalty is not None:
            params["repetition_penalty"] = model_config.repetition_penalty
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k
        if model_config.model_kwargs is not None:
            params["model_kwargs"] = model_config.model_kwargs
        # Local execution parameters
        params["local"] = model_config.local
        if model_config.device is not None:
            params["device"] = model_config.device
        if model_config.quantization is not None:
            params["quantization"] = model_config.quantization

    return params


@overload
def get_chat_model(
    model_config: str,
    api_key: SecretStr | None = None,
    config: Any = None,
    **kwargs: Any,
) -> BaseChatModel: ...


@overload
def get_chat_model(
    model_config: ModelConfig,
    api_key: SecretStr | None = None,
    config: Any = None,
    **kwargs: Any,
) -> BaseChatModel: ...


def get_chat_model(
    model_config: ModelConfig | str,
    api_key: SecretStr | None = None,
    config: Any = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Initialize chat model from configuration with provider detection.

    This function provides a unified interface for initializing LangChain chat
    models from Consoul configuration, handling provider detection, API key
    resolution, dependency validation, and error handling.

    Args:
        model_config: Either a ModelConfig object or a model name string.
            If a string is provided, the provider will be auto-detected.
        api_key: Optional API key override. If None, resolves from config/environment.
        config: Optional ConsoulConfig instance to check for API keys in config.api_keys.
        **kwargs: Additional parameters to pass to init_chat_model.
            For string model names, you can pass temperature, max_tokens, stop_sequences, etc.

    Returns:
        Initialized LangChain chat model ready for use.

    Raises:
        MissingAPIKeyError: If API key is required but not found.
        MissingDependencyError: If provider package is not installed.
        InvalidModelError: If model name is not recognized.
        ProviderInitializationError: If initialization fails for other reasons.

    Examples:
        >>> # Using ModelConfig from config
        >>> from consoul.config import load_config
        >>> config = load_config()
        >>> model_config = config.get_current_model_config()
        >>> chat_model = get_chat_model(model_config)

        >>> # Using model name string with auto-detection
        >>> chat_model = get_chat_model("gpt-4o", temperature=0.7)
        >>> chat_model = get_chat_model("claude-3-5-sonnet-20241022")
    """
    from consoul.config.models import HuggingFaceModelConfig

    # Handle string model names with provider auto-detection
    if isinstance(model_config, str):
        model_name = model_config
        provider = get_provider_from_model(model_name)

        if provider is None:
            raise InvalidModelError(
                f"Could not detect provider for model '{model_name}'.\n\n"
                f"Supported model patterns:\n"
                + "\n".join(
                    f"  - {prov.value}: {', '.join(patterns)}"
                    for prov, patterns in PROVIDER_PATTERNS.items()
                )
                + "\n\nPlease use a recognized model name or pass a ModelConfig object."
            )

        # Create a minimal ModelConfig-like object for parameter building
        from consoul.config.models import (
            AnthropicModelConfig,
            GoogleModelConfig,
            HuggingFaceModelConfig,
            OllamaModelConfig,
            OpenAIModelConfig,
        )

        # Extract common parameters from kwargs
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", None)
        stop_sequences = kwargs.pop("stop_sequences", None)

        # Extract provider-specific parameters to prevent them from leaking to other providers
        # These will only be used if the provider supports them
        top_p = kwargs.pop("top_p", None)
        top_k = kwargs.pop("top_k", None)

        # OpenAI-specific parameters
        frequency_penalty = kwargs.pop("frequency_penalty", None)
        presence_penalty = kwargs.pop("presence_penalty", None)
        seed = kwargs.pop("seed", None)
        logit_bias = kwargs.pop("logit_bias", None)
        response_format = kwargs.pop("response_format", None)

        # Anthropic-specific parameters
        thinking = kwargs.pop("thinking", None)
        betas = kwargs.pop("betas", None)
        metadata = kwargs.pop("metadata", None)

        # Google-specific parameters
        candidate_count = kwargs.pop("candidate_count", None)
        safety_settings = kwargs.pop("safety_settings", None)
        generation_config = kwargs.pop("generation_config", None)

        # HuggingFace-specific parameters
        task = kwargs.pop("task", "text-generation")
        max_new_tokens = kwargs.pop("max_new_tokens", 512)
        do_sample = kwargs.pop("do_sample", True)
        repetition_penalty = kwargs.pop("repetition_penalty", None)
        model_kwargs = kwargs.pop("model_kwargs", None)

        # Build appropriate config based on provider
        if provider == Provider.OPENAI:
            model_config = OpenAIModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                seed=seed,
                logit_bias=logit_bias,
                response_format=response_format,
            )
        elif provider == Provider.ANTHROPIC:
            model_config = AnthropicModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                top_k=top_k,
                thinking=thinking,
                betas=betas,
                metadata=metadata,
            )
        elif provider == Provider.GOOGLE:
            model_config = GoogleModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                top_k=top_k,
                candidate_count=candidate_count,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
        elif provider == Provider.OLLAMA:
            model_config = OllamaModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                top_k=top_k,
            )
        elif provider == Provider.HUGGINGFACE:
            model_config = HuggingFaceModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                task=task,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                repetition_penalty=repetition_penalty,
                top_p=top_p,
                top_k=top_k,
                model_kwargs=model_kwargs,
            )

    # Type narrowing: model_config is ModelConfigUnion (not str)
    if isinstance(model_config, str):
        raise ValueError(f"Invalid model_config type: {type(model_config)}")

    provider = model_config.provider

    # Validate dependencies
    try:
        validate_provider_dependencies(provider)
    except MissingDependencyError:
        raise  # Re-raise with helpful message

    # Check Ollama service availability before attempting initialization
    if provider == Provider.OLLAMA:
        # Get Ollama API base URL from config/env
        from consoul.config.env import get_ollama_api_base

        ollama_base_url = get_ollama_api_base()
        if not ollama_base_url:
            ollama_base_url = "http://localhost:11434"

        if not is_ollama_running(ollama_base_url):
            raise OllamaServiceError(
                f"Ollama service is not running.\n\n"
                f"To use Ollama models:\n"
                f"1. Start Ollama service:\n"
                f"   ollama serve\n\n"
                f"2. Pull the model if not already available:\n"
                f"   ollama pull {model_config.model}\n\n"
                f"3. Verify Ollama is running:\n"
                f"   curl {ollama_base_url}/api/tags\n\n"
                f"Current base URL: {ollama_base_url}\n"
                f"(Set OLLAMA_API_BASE to use a different endpoint)\n\n"
                f"See: {PROVIDER_DOCS.get(Provider.OLLAMA, 'https://ollama.com')}"
            )

    # Resolve API key (if required for this provider)
    resolved_api_key: str | None = None

    # Check if API key is needed for this provider/model combination
    api_key_required = (
        provider != Provider.OLLAMA  # Ollama doesn't need API key
        and provider != Provider.LLAMACPP  # LlamaCpp doesn't need API key
        and provider != Provider.MLX  # MLX doesn't need API key
    )

    # HuggingFace local models don't need API key
    if (
        provider == Provider.HUGGINGFACE
        and isinstance(model_config, HuggingFaceModelConfig)
        and model_config.local
    ):
        api_key_required = False

    if api_key_required:
        if api_key is not None:
            # Explicit override provided
            resolved_api_key = api_key.get_secret_value()
        else:
            # Try multiple sources in order of precedence:
            # 1. config.api_keys (runtime injection)
            # 2. Environment variables / .env files

            # Check config.api_keys first
            if config is not None and hasattr(config, "api_keys"):
                config_key = config.api_keys.get(provider.value)
                if config_key is not None:
                    resolved_api_key = config_key.get_secret_value()

            # Fall back to environment if not found in config
            if resolved_api_key is None:
                from consoul.config.env import get_api_key

                env_api_key = get_api_key(provider)
                if env_api_key is not None:
                    resolved_api_key = env_api_key.get_secret_value()

            # If still not found, raise error
            if resolved_api_key is None:
                env_var = API_KEY_ENV_VARS.get(
                    provider, f"{provider.value.upper()}_API_KEY"
                )
                docs_url = PROVIDER_DOCS.get(provider, "")

                raise MissingAPIKeyError(
                    f"Missing API key for {provider.value}.\n\n"
                    f"Please set your API key using one of these methods:\n\n"
                    f"1. Runtime (ConsoulConfig.api_keys):\n"
                    f"   config.api_keys['{provider.value}'] = SecretStr('your-key')\n\n"
                    f"2. Environment variable:\n"
                    f"   export {env_var}=your-key-here\n\n"
                    f"3. .env file (in project or ~/.consoul/):\n"
                    f"   {env_var}=your-key-here\n\n"
                    + (f"4. Get your key from: {docs_url}\n\n" if docs_url else "")
                    + f"Current provider: {provider.value}\n"
                    f"Current model: {model_config.model}"
                )

    # Build parameters for init_chat_model
    params = build_model_params(model_config)

    # Add provider-specific API key parameter
    if resolved_api_key:
        if provider == Provider.OPENAI:
            params["openai_api_key"] = resolved_api_key
        elif provider == Provider.ANTHROPIC:
            params["anthropic_api_key"] = resolved_api_key
        elif provider == Provider.GOOGLE:
            params["google_api_key"] = resolved_api_key
        elif provider == Provider.HUGGINGFACE:
            params["huggingfacehub_api_token"] = resolved_api_key

    # Add Ollama-specific base_url parameter
    if provider == Provider.OLLAMA:
        from consoul.config.env import get_ollama_api_base

        ollama_base_url = get_ollama_api_base()
        if ollama_base_url:
            params["base_url"] = ollama_base_url

    # Merge with any additional kwargs
    params.update(kwargs)

    # Special handling for LlamaCpp - local GGUF execution
    if provider == Provider.LLAMACPP:
        from langchain_community.chat_models import ChatLlamaCpp

        # Get model path from config or auto-detect
        model_path = getattr(model_config, "model_path", None)
        if not model_path:
            # Auto-detect GGUF in cache
            model_path = find_gguf_for_model(model_config.model)

        if not model_path:
            raise InvalidModelError(
                f"No GGUF model found for '{model_config.model}'.\n\n"
                f"LlamaCpp requires GGUF format models.\n\n"
                f"Options:\n"
                f"1. Download a GGUF model from HuggingFace Hub\n"
                f"2. Convert existing safetensors model to GGUF\n"
                f"3. Specify model_path explicitly in config\n\n"
                f"See LLAMACPP_SOLUTION.md for conversion instructions."
            )

        # Get thread count
        import multiprocessing

        n_threads = getattr(model_config, "n_threads", None)
        if n_threads is None:
            n_threads = multiprocessing.cpu_count() - 1

        # Build ChatLlamaCpp params
        llama_params = {
            "model_path": model_path,
            "n_ctx": getattr(model_config, "n_ctx", 4096),
            "n_gpu_layers": getattr(model_config, "n_gpu_layers", -1),
            "n_batch": getattr(model_config, "n_batch", 512),
            "n_threads": n_threads,
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 512),
            "verbose": False,
        }

        # Add optional parameters if present
        if "top_p" in params:
            llama_params["top_p"] = params["top_p"]
        if "top_k" in params:
            llama_params["top_k"] = params["top_k"]
        if "stop" in params:
            llama_params["stop"] = params["stop"]

        try:
            model = ChatLlamaCpp(**llama_params)

            # Extract and cache the actual n_ctx value from the loaded model
            # The model.client is the underlying llama_cpp.Llama instance
            # which has n_ctx() method that returns the actual context size
            from consoul.ai.context import save_llamacpp_context_length

            try:
                actual_n_ctx = model.client.n_ctx()
                save_llamacpp_context_length(model_path, actual_n_ctx)
            except Exception:
                # Fallback to configured value if extraction fails
                save_llamacpp_context_length(model_path, llama_params["n_ctx"])

            return model  # type: ignore[no-any-return]
        except ImportError as e:
            raise MissingDependencyError(
                f"Failed to import llama-cpp-python: {e}\n\n"
                f"Install with:\n"
                f"  # CPU only:\n"
                f"  pip install llama-cpp-python\n\n"
                f"  # macOS with Metal GPU acceleration (recommended):\n"
                f'  CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python\n\n'
                f"Or with Poetry:\n"
                f"  poetry install --extras llamacpp"
            ) from e
        except Exception as e:
            raise InvalidModelError(
                f"Failed to load GGUF model from '{model_path}'.\n\n"
                f"Error: {e}\n\n"
                f"Verify:\n"
                f"1. File exists and is a valid GGUF model\n"
                f"2. You have enough RAM (model size + ~2GB overhead)\n"
                f"3. Model is not corrupted\n\n"
                f"See LLAMACPP_SOLUTION.md for troubleshooting."
            ) from e

    # Special handling for MLX - Apple Silicon optimized local execution
    if provider == Provider.MLX:
        import logging

        logger = logging.getLogger(__name__)

        # Get model path/ID from config
        model_id = getattr(model_config, "model_path", None) or model_config.model
        logger.info(f"MLX: Loading model from model_id={model_id}")

        # Build MLXChatWrapper params
        mlx_params = {
            "model_id": model_id,
            "max_tokens": getattr(
                model_config, "max_tokens", params.get("max_tokens", 2048)
            ),
            "temperature": getattr(
                model_config, "temp", params.get("temperature", 0.7)
            ),
        }

        # Add optional parameters
        if hasattr(model_config, "top_p"):
            mlx_params["top_p"] = model_config.top_p
        if hasattr(model_config, "repetition_penalty"):
            mlx_params["repetition_penalty"] = model_config.repetition_penalty
        if hasattr(model_config, "repetition_context_size"):
            mlx_params["repetition_context_size"] = model_config.repetition_context_size

        logger.info(f"MLX: mlx_params={mlx_params}")

        try:
            # Load MLX model directly without MLXPipeline (avoids fds_to_keep subprocess errors)
            from consoul.ai.mlx_chat_wrapper import MLXChatWrapper

            logger.info("MLX: Creating MLXChatWrapper with direct mlx_lm.load()...")
            wrapper = MLXChatWrapper(**mlx_params)
            logger.info(
                f"MLX: MLXChatWrapper created successfully, type={type(wrapper)}"
            )
            return wrapper
        except ImportError as e:
            raise MissingDependencyError(
                f"Failed to import MLX: {e}\n\n"
                f"Install with:\n"
                f"  pip install mlx-lm\n\n"
                f"Or with Poetry:\n"
                f"  poetry install --extras mlx\n\n"
                f"Note: MLX requires macOS 15.0+ and Apple Silicon (M-series chips)"
            ) from e
        except RuntimeError as e:
            # Re-raise RuntimeError with clear message (from MLXChatWrapper)
            raise InvalidModelError(str(e)) from e
        except Exception as e:
            error_msg = str(e)

            # Check for common issues
            if "fds_to_keep" in error_msg or "multiprocessing" in error_msg.lower():
                raise InvalidModelError(
                    f"Failed to load MLX model '{model_id}' due to multiprocessing conflict.\n\n"
                    f"This happens when downloading models from HuggingFace in the TUI.\n\n"
                    f"Workaround - Pre-download the model first:\n"
                    f"  python -c \"from mlx_lm import load; load('{model_id}')\"\n\n"
                    f"Or select a locally cached model from ~/.cache/huggingface/hub/\n"
                    f"Or use a local MLX model from ~/.lmstudio/models/"
                ) from e

            raise InvalidModelError(
                f"Failed to load MLX model '{model_id}'.\n\n"
                f"Error: {error_msg}\n\n"
                f"Verify:\n"
                f"1. Model exists on HuggingFace (mlx-community) or locally\n"
                f"2. You have enough RAM for the model\n"
                f"3. Running on Apple Silicon Mac with macOS 15.0+\n\n"
                f"Browse available models: https://huggingface.co/mlx-community"
            ) from e

    # Special handling for HuggingFace - supports both API and local execution
    if provider == Provider.HUGGINGFACE:
        from langchain_huggingface import ChatHuggingFace

        # Check if user wants local execution
        use_local = params.pop("local", False)
        device = params.pop("device", None)
        quantization = params.pop("quantization", None)

        if use_local:
            # Local execution with HuggingFacePipeline
            try:
                from langchain_huggingface import HuggingFacePipeline
            except ImportError as e:
                raise MissingDependencyError(
                    f"Failed to import HuggingFacePipeline: {e}\n\n"
                    f"Install local model support with: pip install 'consoul[huggingface-local]'"
                ) from e

            # Verify required dependencies for local execution
            import importlib.util

            missing_deps = []
            if importlib.util.find_spec("transformers") is None:
                missing_deps.append("transformers")
            if importlib.util.find_spec("torch") is None:
                missing_deps.append("torch")

            if missing_deps:
                raise MissingDependencyError(
                    f"Local HuggingFace execution requires transformers and torch.\n\n"
                    f"Missing: {', '.join(missing_deps)}\n\n"
                    f"Install with: poetry install --extras huggingface-local\n"
                    f"Or: pip install 'consoul[huggingface-local]'"
                )

            # Apply macOS-specific fixes BEFORE importing torch/transformers
            import platform

            if platform.system() == "Darwin":
                # Apply environment variable fixes for OpenMP conflicts
                # This MUST happen before importing torch/transformers
                from consoul.ai.macos_fixes import (
                    apply_macos_pytorch_fixes,
                    check_pytorch_compatibility,
                )

                applied_fixes = apply_macos_pytorch_fixes()
                if applied_fixes:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Applied macOS PyTorch fixes: {', '.join(applied_fixes.keys())}"
                    )

                # Check PyTorch compatibility and warn if issues detected
                compat_info = check_pytorch_compatibility()
                if "warning" in compat_info:
                    import sys
                    import warnings

                    severity = compat_info.get("severity", "high")

                    # For critical issues, print to stderr before attempting to use model
                    if severity == "critical":
                        print("\n" + "=" * 70, file=sys.stderr)
                        print(
                            "CRITICAL: PyTorch Version Incompatibility", file=sys.stderr
                        )
                        print("=" * 70, file=sys.stderr)
                        print(compat_info["warning"], file=sys.stderr)
                        print("\nAlternatives:", file=sys.stderr)
                        print(
                            "  1. Use LlamaCpp models (working, no PyTorch needed)",
                            file=sys.stderr,
                        )
                        print(
                            "  2. Use cloud providers (OpenAI, Anthropic, Google)",
                            file=sys.stderr,
                        )
                        print("  3. Use Ollama for local inference", file=sys.stderr)
                        print("=" * 70 + "\n", file=sys.stderr)

                    warnings.warn(
                        f"{compat_info['warning']}\n\n"
                        "Local HuggingFace execution on macOS may experience segmentation faults. "
                        "Environment variable fixes have been applied. "
                        "See HUGGINGFACE_LOCAL_ISSUES.md for details.",
                        RuntimeWarning,
                        stacklevel=2,
                    )

            # Build pipeline params
            pipeline_params = {
                "model_id": params.pop("model"),
                "task": params.pop("task", "text-generation"),
            }

            # Add pipeline_kwargs for generation parameters
            pipeline_kwargs = {}
            if "temperature" in params:
                pipeline_kwargs["temperature"] = params.pop("temperature")
            if "max_tokens" in params or "max_new_tokens" in params:
                pipeline_kwargs["max_new_tokens"] = params.pop(
                    "max_tokens", params.pop("max_new_tokens", 512)
                )
            if "stop" in params:
                # HuggingFace uses stop_sequences
                pipeline_kwargs["stop_sequences"] = params.pop("stop")
            if "do_sample" in params:
                pipeline_kwargs["do_sample"] = params.pop("do_sample")
            if "repetition_penalty" in params:
                pipeline_kwargs["repetition_penalty"] = params.pop("repetition_penalty")
            if "top_p" in params:
                pipeline_kwargs["top_p"] = params.pop("top_p")
            if "top_k" in params:
                pipeline_kwargs["top_k"] = params.pop("top_k")

            if pipeline_kwargs:
                pipeline_params["pipeline_kwargs"] = pipeline_kwargs

            # Add model_kwargs if provided (for model initialization, not generation)
            if "model_kwargs" in params:
                pipeline_params["model_kwargs"] = params.pop("model_kwargs")
            else:
                pipeline_params["model_kwargs"] = {}

            # Enable trust_remote_code for models with custom code
            # This is needed for many modern models (Qwen, Kimi, Phi, etc.)
            pipeline_params["model_kwargs"]["trust_remote_code"] = True

            # Add device configuration
            if device:
                pipeline_params["device"] = device

            # Add quantization if requested
            if quantization:
                try:
                    from transformers import BitsAndBytesConfig
                except ImportError as e:
                    raise MissingDependencyError(
                        f"Quantization requires transformers with bitsandbytes: {e}\n\n"
                        f"Install with: pip install 'consoul[huggingface-local]'"
                    ) from e

                if quantization == "4bit":
                    quant_config = BitsAndBytesConfig(load_in_4bit=True)
                elif quantization == "8bit":
                    quant_config = BitsAndBytesConfig(load_in_8bit=True)
                else:
                    quant_config = None

                if quant_config:
                    pipeline_params["model_kwargs"]["quantization_config"] = (
                        quant_config
                    )

            try:
                llm = HuggingFacePipeline.from_model_id(**pipeline_params)
                return ChatHuggingFace(llm=llm, **params)  # type: ignore[no-any-return]
            except ImportError as e:
                # Missing dependency for this specific model
                error_msg = str(e)
                if "pip install" in error_msg:
                    # Error message already includes install instruction
                    raise InvalidModelError(
                        f"Failed to load local HuggingFace model '{pipeline_params['model_id']}'.\n\n"
                        f"{error_msg}"
                    ) from e
                else:
                    raise InvalidModelError(
                        f"Failed to load local HuggingFace model '{pipeline_params['model_id']}'.\n\n"
                        f"Missing dependency: {e}\n\n"
                        f"Install with: pip install <missing-package>"
                    ) from e
            except Exception as e:
                raise InvalidModelError(
                    f"Failed to load local HuggingFace model '{pipeline_params['model_id']}'.\n\n"
                    f"Error: {e}\n\n"
                    f"Make sure the model exists and you have enough memory/GPU resources."
                ) from e
        else:
            # API-based execution with HuggingFaceEndpoint
            from langchain_huggingface import HuggingFaceEndpoint

            # Extract HuggingFace-specific params
            hf_params = {
                "repo_id": params.pop("model"),
                "task": params.pop("task", "text-generation"),
                "max_new_tokens": params.pop("max_new_tokens", 512),
                "do_sample": params.pop("do_sample", True),
            }

            # Add core generation parameters that HuggingFaceEndpoint supports
            if "temperature" in params:
                hf_params["temperature"] = params.pop("temperature")
            if "max_tokens" in params:
                # HuggingFaceEndpoint uses max_length for total context + generation
                hf_params["max_length"] = params.pop("max_tokens")
            if "stop" in params:
                # Map stop to stop_sequences for HuggingFaceEndpoint
                hf_params["stop_sequences"] = params.pop("stop")

            # Add optional sampling parameters if present
            if "repetition_penalty" in params:
                hf_params["repetition_penalty"] = params.pop("repetition_penalty")
            if "top_p" in params:
                hf_params["top_p"] = params.pop("top_p")
            if "top_k" in params:
                hf_params["top_k"] = params.pop("top_k")
            if "model_kwargs" in params:
                hf_params.update(params.pop("model_kwargs"))

            # Add API token if present
            if "huggingfacehub_api_token" in params:
                hf_params["huggingfacehub_api_token"] = params.pop(
                    "huggingfacehub_api_token"
                )

            try:
                # Initialize endpoint and wrap with ChatHuggingFace
                llm = HuggingFaceEndpoint(**hf_params)
                return ChatHuggingFace(llm=llm, **params)  # type: ignore[no-any-return]
            except ImportError as e:
                raise MissingDependencyError(
                    f"Failed to import langchain-huggingface: {e}\n\n"
                    f"Install with: pip install langchain-huggingface"
                ) from e
            except Exception as e:
                error_msg = str(e).lower()
                if "api token" in error_msg or "authentication" in error_msg:
                    raise MissingAPIKeyError(
                        "HuggingFace API token required for API-based execution.\n\n"
                        "Option 1: Set HUGGINGFACEHUB_API_TOKEN environment variable\n"
                        "Get token at: https://huggingface.co/settings/tokens\n\n"
                        "Option 2: Use local execution instead (no token required)\n"
                        "Set local=True in HuggingFaceModelConfig and install:\n"
                        "pip install 'consoul[huggingface-local]'"
                    ) from e
                elif "410" in error_msg or "no longer supported" in error_msg:
                    raise ProviderInitializationError(
                        "HuggingFace Inference API endpoint has changed.\n\n"
                        "The old endpoint (api-inference.huggingface.co) is deprecated.\n"
                        "The new endpoint (router.huggingface.co) should be used automatically.\n\n"
                        "This error suggests you may have an outdated package version.\n\n"
                        "Fix:\n"
                        "  1. Update langchain-huggingface:\n"
                        "     pip install --upgrade langchain-huggingface huggingface-hub\n\n"
                        "  2. Or use latest Consoul:\n"
                        "     poetry install --sync\n\n"
                        "Note: HuggingFace Serverless Inference is STILL FREE!\n"
                        "  - Free tier with rate limits (~few hundred requests/hour)\n"
                        "  - PRO ($9/month) gives 20x more credits\n"
                        "  - See: https://huggingface.co/docs/api-inference\n\n"
                        "Alternative free options:\n"
                        "  - Groq (fast API): https://console.groq.com\n"
                        "  - Ollama (local): https://ollama.com\n"
                        "  - MLX (Apple Silicon): Select MLX provider"
                    ) from e
                elif "not found" in error_msg or "404" in error_msg:
                    raise InvalidModelError(
                        f"Model '{model_config.model}' not found on HuggingFace Hub.\n\n"
                        f"Error: {e}\n\n"
                        f"Search for models at: https://huggingface.co/models"
                    ) from e
                else:
                    raise InvalidModelError(
                        f"Failed to initialize HuggingFace model '{model_config.model}'.\n\n"
                        f"Error: {e}\n\n"
                        f"See available models: https://huggingface.co/models"
                    ) from e

    # Special handling for OpenAI to properly set stream_options
    # ChatOpenAI expects stream_options in model_kwargs, not as direct parameter
    if provider == Provider.OPENAI:
        from langchain_openai import ChatOpenAI

        # Extract or create model_kwargs with stream_options
        model_kwargs = params.pop("model_kwargs", {})
        if "stream_options" not in model_kwargs:
            model_kwargs["stream_options"] = {"include_usage": True}

        # Build ChatOpenAI params with model_kwargs
        openai_params = {**params, "model_kwargs": model_kwargs}

        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"[STREAM_OPTIONS] OpenAI init params: model_kwargs={model_kwargs}"
        )

        try:
            return ChatOpenAI(**openai_params)  # type: ignore[no-any-return]
        except ImportError as e:
            # Dependency import failed (shouldn't happen after validation)
            raise MissingDependencyError(
                f"Failed to import langchain-openai: {e}\n\n"
                f"Install with: pip install langchain-openai"
            ) from e
        except ValueError as e:
            # Invalid model name or configuration
            error_msg = str(e)
            raise InvalidModelError(
                f"Invalid model '{model_config.model}' for OpenAI.\n\n"
                f"Error: {error_msg}\n\n"
                f"See available models: https://platform.openai.com/docs/models"
            ) from e

    # Initialize the model using init_chat_model for other providers
    # Use LANGCHAIN_PROVIDER_NAMES mapping to get correct provider name
    # (e.g., "google" -> "google_genai")
    langchain_provider = LANGCHAIN_PROVIDER_NAMES.get(provider, provider.value)

    try:
        return init_chat_model(  # type: ignore[no-any-return]
            model_provider=langchain_provider,
            **params,
        )
    except ImportError as e:
        # Dependency import failed (shouldn't happen after validation)
        package = PROVIDER_PACKAGES.get(provider, provider.value)
        raise MissingDependencyError(
            f"Failed to import {package}: {e}\n\n"
            f"Install with: pip install {package.replace('_', '-')}"
        ) from e
    except ValueError as e:
        # Invalid model name or configuration
        docs_url = PROVIDER_DOCS.get(provider, "")
        error_msg = str(e).lower()

        # Special handling for Ollama model not found errors
        if provider == Provider.OLLAMA and (
            "not found" in error_msg or "404" in error_msg
        ):
            raise OllamaServiceError(
                f"Model '{model_config.model}' not found in Ollama.\n\n"
                f"To download the model:\n"
                f"   ollama pull {model_config.model}\n\n"
                f"To list available models:\n"
                f"   ollama list\n\n"
                f"See available models: {docs_url}"
            ) from e

        raise InvalidModelError(
            f"Invalid model '{model_config.model}' for {provider.value}.\n\n"
            f"Error: {e}\n\n"
            + (f"See available models: {docs_url}" if docs_url else "")
        ) from e
    except Exception as e:
        # Other initialization errors
        error_msg = str(e).lower()

        # Catch additional Ollama connection errors
        if provider == Provider.OLLAMA and (
            "connection" in error_msg or "refused" in error_msg
        ):
            raise OllamaServiceError(
                f"Failed to connect to Ollama service.\n\n"
                f"To use Ollama models:\n"
                f"1. Start Ollama service:\n"
                f"   ollama serve\n\n"
                f"2. Verify service is running:\n"
                f"   curl http://localhost:11434/api/tags\n\n"
                f"Original error: {e}"
            ) from e

        raise ProviderInitializationError(
            f"Failed to initialize {provider.value} model '{model_config.model}': {e}"
        ) from e


def supports_tool_calling(model: BaseChatModel) -> bool:
    """Check if a chat model supports tool calling via bind_tools.

    Tests whether the model has a working bind_tools implementation by
    checking if it raises NotImplementedError (the base class behavior).

    Args:
        model: The chat model to check

    Returns:
        True if model supports tool calling, False otherwise

    Example:
        >>> from consoul.ai import get_chat_model
        >>> model = get_chat_model("claude-3-5-sonnet-20241022")
        >>> supports_tool_calling(model)
        True
        >>> ollama_model = get_chat_model("deepseek-r1:70b")
        >>> supports_tool_calling(ollama_model)
        False

    Note:
        This checks if bind_tools is implemented, but some models may
        still reject tool calls at runtime (e.g., Ollama models that
        don't support tools will return 400 errors). Use try/except
        when actually invoking tools for robust error handling.
    """
    # LlamaCpp models don't support tool calling properly
    # The Jinja2 templates used by llama.cpp expect tool schemas in a format
    # that isn't compatible with LangChain's bind_tools mechanism
    try:
        from langchain_community.chat_models import ChatLlamaCpp

        if isinstance(model, ChatLlamaCpp):
            return False
    except ImportError:
        pass  # llama-cpp-python not installed, skip this check

    # Check if model has bind_tools method
    if not hasattr(model, "bind_tools"):
        return False

    # Check if the bind_tools method is overridden from base class
    # If it's the base implementation, it will raise NotImplementedError
    try:
        # Try to call bind_tools with empty list
        # Most implementations will accept this without error
        model.bind_tools([])
        return True
    except NotImplementedError:
        # Base implementation - doesn't support tools
        return False
    except Exception:
        # Other errors suggest implementation exists but failed for other reasons
        # (e.g., validation error on empty list) - assume it supports tools
        return True

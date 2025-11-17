"""ModelPickerModal - Modal for selecting AI models and providers.

This modal provides a unified interface for switching between AI providers
(OpenAI, Anthropic, Google, Ollama, HuggingFace, LlamaCpp) and selecting specific models within each provider.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

    from consoul.config.models import Provider

__all__ = ["ModelPickerModal"]

log = logging.getLogger(__name__)


# Model information database (name -> metadata)
# Updated with complete 2025 model catalog
MODEL_INFO = {
    # OpenAI GPT-5 Series (Latest Flagship)
    "gpt-5": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Flagship reasoning model",
    },
    "gpt-5-mini": {
        "provider": "openai",
        "context": "1M",
        "cost": "moderate",
        "description": "Fast & affordable reasoning",
    },
    "gpt-5-nano": {
        "provider": "openai",
        "context": "1M",
        "cost": "cheap",
        "description": "Fastest, most affordable reasoning",
    },
    "gpt-5-codex": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Optimized for agentic coding",
    },
    "gpt-5-chat-latest": {
        "provider": "openai",
        "context": "1M",
        "cost": "moderate",
        "description": "Non-reasoning chat model",
    },
    # OpenAI o-Series (Deep Reasoning)
    "o3": {
        "provider": "openai",
        "context": "128K",
        "cost": "expensive",
        "description": "Advanced reasoning & problem-solving",
    },
    "o4-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Fast reasoning with vision",
    },
    "o4-mini-high": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Budget STEM/tech reasoning",
    },
    "o3-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "cheap",
        "description": "Enhanced reasoning abilities",
    },
    "o3-deep-research": {
        "provider": "openai",
        "context": "128K",
        "cost": "expensive",
        "description": "Multi-step research with citations",
    },
    # OpenAI GPT-4.1 Series (1M context)
    "gpt-4.1": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Improved coding & long context",
    },
    "gpt-4.1-mini": {
        "provider": "openai",
        "context": "1M",
        "cost": "moderate",
        "description": "GPT-4o performance, lower latency",
    },
    "gpt-4.1-nano": {
        "provider": "openai",
        "context": "1M",
        "cost": "cheap",
        "description": "Smallest GPT-4.1 variant",
    },
    # OpenAI GPT-4o Series (Multimodal)
    "gpt-4o": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Multimodal flagship",
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "cheap",
        "description": "Cost-efficient multimodal",
    },
    # Anthropic Claude 4.5 Models (Latest - Sep/Oct 2025)
    "claude-sonnet-4-5": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "moderate",
        "description": "Best coding model in world (Sep 2025)",
    },
    "claude-haiku-4-5": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "cheap",
        "description": "Fastest, low latency (Oct 2025)",
    },
    # Anthropic Claude 4 Models (May-Aug 2025)
    "claude-opus-4-1": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "expensive",
        "description": "Agentic tasks & reasoning (Aug 2025)",
    },
    "claude-sonnet-4": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "moderate",
        "description": "Claude Sonnet 4 (May 2025)",
    },
    "claude-opus-4": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "expensive",
        "description": "Claude Opus 4 (May 2025)",
    },
    # Legacy Claude 3.x Models (for backward compatibility)
    "claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "moderate",
        "description": "Legacy Claude 3.5 Sonnet",
    },
    "claude-3-opus-20240229": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "expensive",
        "description": "Legacy Claude 3 Opus",
    },
    # Google Gemini 2.5 Models (Latest)
    "gemini-2.5-pro": {
        "provider": "google",
        "context": "1M",
        "cost": "expensive",
        "description": "Most powerful with adaptive thinking",
    },
    "gemini-2.5-flash": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Stable 2.5 flash model",
    },
    "gemini-2.5-flash-lite": {
        "provider": "google",
        "context": "1M",
        "cost": "cheap",
        "description": "Speed & cost optimized",
    },
    "gemini-2.5-computer-use": {
        "provider": "google",
        "context": "1M",
        "cost": "expensive",
        "description": "Powers UI interaction agents",
    },
    "gemini-2.5-image": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Native image generation",
    },
    # Google Gemini 2.0 Models
    "gemini-2.0-pro": {
        "provider": "google",
        "context": "1M",
        "cost": "expensive",
        "description": "Released Feb 2025",
    },
    "gemini-2.0-flash": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Default model (Jan 2025)",
    },
    "gemini-2.0-flash-thinking": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Details thinking process",
    },
    # Google Gemini 1.5 (Legacy, still available)
    "gemini-1.5-pro": {
        "provider": "google",
        "context": "2M",
        "cost": "expensive",
        "description": "Legacy with 2M context",
    },
    "gemini-1.5-flash": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Legacy flash model",
    },
    # HuggingFace Models (popular models, local models fetched dynamically)
    "meta-llama/Llama-3.1-8B-Instruct": {
        "provider": "huggingface",
        "context": "128K",
        "cost": "free",
        "description": "Meta's Llama 3.1 8B instruction model",
    },
    "meta-llama/Llama-3.2-3B-Instruct": {
        "provider": "huggingface",
        "context": "128K",
        "cost": "free",
        "description": "Smaller Llama 3.2 model",
    },
    "mistralai/Mistral-7B-Instruct-v0.3": {
        "provider": "huggingface",
        "context": "32K",
        "cost": "free",
        "description": "Mistral AI's 7B instruction model",
    },
    "google/flan-t5-xxl": {
        "provider": "huggingface",
        "context": "2K",
        "cost": "free",
        "description": "Google's FLAN-T5 XXL (11B params)",
    },
    "google/flan-t5-base": {
        "provider": "huggingface",
        "context": "512",
        "cost": "free",
        "description": "Smaller FLAN-T5 base (250M params)",
    },
    "microsoft/Phi-3-mini-4k-instruct": {
        "provider": "huggingface",
        "context": "4K",
        "cost": "free",
        "description": "Microsoft's Phi-3 Mini (3.8B params)",
    },
    "tiiuae/falcon-7b-instruct": {
        "provider": "huggingface",
        "context": "2K",
        "cost": "free",
        "description": "TII's Falcon 7B instruction model",
    },
    # Note: Ollama, HuggingFace, and LlamaCpp local models are fetched dynamically
}


class ModelPickerModal(ModalScreen[tuple[str, str] | None]):
    """Modal for selecting AI provider and model.

    Features:
    - Provider tabs (OpenAI, Anthropic, Google, Ollama, HuggingFace, LlamaCpp)
    - DataTable showing models for selected provider
    - Live search/filter by model name
    - Shows model metadata (context window, cost, rating)
    - Enter key to select, Escape to cancel
    - Returns tuple[provider, model_name] or None (cancel)
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    DEFAULT_CSS = """
    ModelPickerModal {
        align: center middle;
    }

    ModelPickerModal #modal-wrapper {
        width: 120;
        height: 75%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ModelPickerModal .modal-header {
        width: 100%;
        height: auto;
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ModelPickerModal #provider-tabs {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin: 0 0 1 0;
    }

    ModelPickerModal .provider-tab {
        margin: 0 1;
        padding: 0 2;
        background: transparent;
        color: $text-muted;
    }

    ModelPickerModal .provider-tab:hover {
        background: $primary-lighten-1;
        color: $text;
        text-style: bold;
    }

    ModelPickerModal .provider-tab.-active {
        background: $primary;
        color: $accent;
        text-style: bold;
    }

    ModelPickerModal #search-input {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    ModelPickerModal #models-table {
        width: 100%;
        height: 1fr;
        background: $surface;
    }

    ModelPickerModal .info-label {
        width: 100%;
        height: auto;
        color: $text-muted;
        margin: 1 0;
        text-align: center;
    }

    ModelPickerModal #button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ModelPickerModal Button {
        margin: 0 1;
    }
    """

    # Reactive properties
    active_provider: reactive[str] = reactive("openai")

    # Cache for GGUF models (lazy loaded)
    _gguf_models_cache: list[dict[str, Any]] | None = None
    _gguf_loading: bool = False

    def __init__(
        self,
        current_model: str,
        current_provider: Provider,
        **kwargs: Any,
    ) -> None:
        """Initialize the modal.

        Args:
            current_model: Name of currently active model
            current_provider: Currently active provider
        """
        # Initialize attributes before super().__init__ to avoid watcher issues
        self._table: DataTable[Any] | None = None
        self._model_map: dict[str, dict[str, Any]] = {}  # row_key -> model metadata

        # Check if Ollama is available
        from consoul.ai.providers import is_ollama_running

        self._ollama_available = is_ollama_running()
        # Don't check HuggingFace availability on startup (slow cache scan)
        # Always show HuggingFace tab, will load models on-demand when selected
        self._huggingface_available = True

        super().__init__(**kwargs)
        self.current_model = current_model
        self.current_provider = current_provider

        # Map local providers to the "local" tab
        local_providers = {"ollama", "llamacpp", "mlx"}
        if current_provider.value in local_providers:
            self.active_provider = "local"
        else:
            self.active_provider = current_provider.value

        log.info(
            f"ModelPickerModal: Initialized with current_model={current_model}, "
            f"current_provider={current_provider}, active_provider={self.active_provider}, "
            f"ollama_available={self._ollama_available}, "
            f"huggingface_available={self._huggingface_available}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="modal-wrapper"):
            # Header
            yield Label("Select AI Model & Provider", classes="modal-header")

            # Provider tabs with consolidated "Local" tab
            with Horizontal(id="provider-tabs"):
                providers = ["openai", "anthropic", "google"]
                if self._huggingface_available:
                    providers.append("huggingface")
                # Add consolidated "Local" tab for Ollama, LlamaCpp, MLX
                providers.append("local")

                for provider in providers:
                    tab_classes = "provider-tab"
                    if provider == self.active_provider:
                        tab_classes += " -active"
                    tab_label = Label(
                        provider.title(),
                        classes=tab_classes,
                        id=f"tab-{provider}",
                    )
                    tab_label.can_focus = True
                    yield tab_label

            # Search/filter input
            yield Input(
                placeholder="Search models by name...",
                id="search-input",
            )

            # DataTable for models
            yield DataTable(id="models-table", zebra_stripes=True, cursor_type="row")

            # Info label
            yield Label("Enter: select · Escape: cancel", classes="info-label")

            # Action buttons
            with Horizontal(id="button-row"):
                yield Button("Select", variant="primary", id="select-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_mount(self) -> None:
        """Load models and populate table when mounted."""
        log.info("ModelPickerModal: on_mount called, populating models")

        # Initialize table
        self._table = self.query_one("#models-table", DataTable)
        self._table.add_column("Model", width=35)
        self._table.add_column("Context", width=12)
        self._table.add_column("Cost", width=12)
        self._table.cursor_type = "row"
        self._table.focus()

        # Populate table
        self._populate_table()

    def watch_active_provider(self, provider: str) -> None:
        """React to provider tab changes."""
        # Update tab styling
        for tab_id in [
            "tab-openai",
            "tab-anthropic",
            "tab-google",
            "tab-huggingface",
            "tab-local",
        ]:
            try:
                tab = self.query_one(f"#{tab_id}", Label)
                if tab_id == f"tab-{provider}":
                    tab.add_class("-active")
                else:
                    tab.remove_class("-active")
            except Exception:
                pass

        # Refresh model table
        self._populate_table()

    def _populate_table(self, search_query: str = "") -> None:
        """Populate or refresh the table with models.

        Args:
            search_query: Optional search query to filter models
        """
        if not self._table:
            return

        # Clear existing rows
        self._table.clear()
        self._model_map.clear()

        # Filter models by active provider
        provider_value = self.active_provider
        provider_models = {
            name: info
            for name, info in MODEL_INFO.items()
            if info["provider"] == provider_value
        }

        # For Local tab, aggregate models from Ollama, LlamaCpp, and MLX
        if provider_value == "local":
            provider_models = {}
            self._populate_local_models(provider_models, search_query)
            self._add_local_models_to_table(provider_models, search_query)
            return

        # For Ollama, fetch dynamic models from the service
        if provider_value == "ollama":
            from consoul.ai.providers import get_ollama_models, is_ollama_running

            if is_ollama_running():
                # Fetch models with context length info
                ollama_models = get_ollama_models(include_context=True)
                for model_info in ollama_models:
                    model_name = model_info.get("name", "")
                    if model_name and model_name not in provider_models:
                        # Format context length
                        context_length = model_info.get("context_length")
                        if context_length:
                            # Convert to human-readable format (e.g., 262144 -> 256K)
                            if context_length >= 1_000_000:
                                context_str = f"{context_length // 1_000_000}M"
                            elif context_length >= 1_000:
                                context_str = f"{context_length // 1_000}K"
                            else:
                                context_str = str(context_length)
                        else:
                            context_str = "?"

                        # Add dynamic Ollama model
                        provider_models[model_name] = {
                            "provider": "ollama",
                            "context": context_str,
                            "cost": "free",
                            "description": "Local Ollama model",
                        }

        # For HuggingFace, fetch local cached models
        elif provider_value == "huggingface":
            from consoul.ai.providers import get_huggingface_local_models

            hf_models = get_huggingface_local_models()
            for model_info in hf_models:
                model_name = model_info.get("name", "")
                if model_name and model_name not in provider_models:
                    # Format size
                    size_gb = model_info.get("size_gb", 0)
                    if size_gb >= 1:
                        size_str = f"{size_gb:.1f}GB"
                    else:
                        size_str = f"{size_gb * 1024:.0f}MB"

                    # Add local HuggingFace model
                    provider_models[model_name] = {
                        "provider": "huggingface",
                        "context": "?",  # Context length not easily determined
                        "cost": "free",
                        "description": f"Local model ({size_str})",
                    }

        # For LlamaCpp, fetch GGUF models from cache (lazy loaded with caching)
        elif provider_value == "llamacpp":
            # Use cached results if available, otherwise load asynchronously
            if self._gguf_models_cache is not None:
                gguf_models = self._gguf_models_cache
            elif self._gguf_loading:
                # Still loading, show placeholder
                provider_models["_loading"] = {
                    "provider": "llamacpp",
                    "context": "-",
                    "cost": "-",
                    "description": "Loading GGUF models...",
                    "display_name": "⏳ Scanning cache directories...",
                }
                gguf_models = []
            else:
                # Start async load if not already started
                self._gguf_loading = True
                self.run_worker(self._load_gguf_models_async(), exclusive=True)
                # Show placeholder while loading
                provider_models["_loading"] = {
                    "provider": "llamacpp",
                    "context": "-",
                    "cost": "-",
                    "description": "Loading GGUF models...",
                    "display_name": "⏳ Scanning cache directories...",
                }
                gguf_models = []

            # Use filename as display name, path as unique key
            for model_info in gguf_models:
                file_name = model_info.get("name", "")
                file_path = model_info.get("path", "")

                # Use the full file path as the unique key to avoid duplicates
                # This ensures each GGUF file appears exactly once
                model_name = file_path

                if model_name and model_name not in provider_models:
                    # Format size
                    size_gb = model_info.get("size_gb", 0)
                    if size_gb >= 1:
                        size_str = f"{size_gb:.1f}GB"
                    else:
                        size_str = f"{size_gb * 1024:.0f}MB"

                    # Get quantization type
                    quant = model_info.get("quant", "?")

                    # Add GGUF model with just filename as display
                    # Store display_name separately so table shows clean filename
                    provider_models[model_name] = {
                        "provider": "llamacpp",
                        "context": "4K-128K",
                        "cost": "free",
                        "description": f"{quant}, {size_str}",
                        "display_name": file_name,  # Just the filename for display
                    }

        # For MLX, fetch popular models from mlx-community
        elif provider_value == "mlx":
            # Popular MLX models from HuggingFace mlx-community
            mlx_models = {
                "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit": {
                    "context": "128K",
                    "description": "Llama 3.1 8B, 4-bit quantized",
                },
                "mlx-community/Qwen2.5-7B-Instruct-4bit": {
                    "context": "32K",
                    "description": "Qwen 2.5 7B, 4-bit quantized",
                },
                "mlx-community/Mistral-7B-Instruct-v0.3-4bit": {
                    "context": "32K",
                    "description": "Mistral 7B v0.3, 4-bit quantized",
                },
                "mlx-community/gemma-2-9b-it-4bit": {
                    "context": "8K",
                    "description": "Gemma 2 9B, 4-bit quantized",
                },
                "mlx-community/Phi-3.5-mini-instruct-4bit": {
                    "context": "128K",
                    "description": "Phi 3.5 Mini, 4-bit quantized",
                },
            }

            for model_id, info in mlx_models.items():
                provider_models[model_id] = {
                    "provider": "mlx",
                    "context": info["context"],
                    "cost": "free",
                    "description": info["description"],
                }

        # Apply search filter if provided
        if search_query:
            query_lower = search_query.lower()
            provider_models = {
                name: info
                for name, info in provider_models.items()
                if query_lower in name.lower()
                or query_lower in info["description"].lower()
            }

        # If current model is not in the database and matches current provider, add it
        current_provider_value = self.current_provider.value
        if (
            self.current_model not in provider_models
            and provider_value == current_provider_value
        ):
            provider_models[self.current_model] = {
                "provider": provider_value,
                "context": "?",
                "cost": "?",
                "rating": "?",
                "description": "Custom model",
            }

        # Add rows, sorting by name
        for name in sorted(provider_models.keys()):
            info = provider_models[name]
            row_key = name

            self._model_map[row_key] = info

            # Format columns
            is_current = (
                name == self.current_model and provider_value == current_provider_value
            )
            # Use display_name if available (for LlamaCpp models), otherwise use name
            display_name = info.get("display_name", name)
            model_col = f"✓ {display_name}" if is_current else f"  {display_name}"
            context_col = info["context"]
            cost_col = info["cost"].title()

            self._table.add_row(model_col, context_col, cost_col, key=row_key)

            # Highlight current model row
            if is_current:
                # Move cursor to current model
                try:
                    row_keys_list = list(self._table.rows.keys())
                    row_index = next(
                        (
                            i
                            for i, key in enumerate(row_keys_list)
                            if str(key) == row_key
                        ),
                        None,
                    )
                    if row_index is not None:
                        self._table.move_cursor(row=row_index)
                except (ValueError, Exception):
                    pass

        log.debug(
            f"ModelPickerModal: Populated table with {len(provider_models)} models "
            f"for provider '{provider_value}'"
        )

    def _populate_local_models(
        self, provider_models: dict[str, dict[str, Any]], search_query: str = ""
    ) -> None:
        """Populate models from local providers (Ollama, LlamaCpp/GGUF, MLX).

        Args:
            provider_models: Dictionary to populate with model information
            search_query: Optional search query to filter models
        """
        # Section 1: Ollama models
        if self._ollama_available:
            from consoul.ai.providers import get_ollama_models, is_ollama_running

            if is_ollama_running():
                ollama_models = get_ollama_models(include_context=True)
                for model_info in ollama_models:
                    model_name = model_info.get("name", "")
                    if model_name:
                        context_length = model_info.get("context_length")
                        if context_length:
                            if context_length >= 1_000_000:
                                context_str = f"{context_length // 1_000_000}M"
                            elif context_length >= 1_000:
                                context_str = f"{context_length // 1_000}K"
                            else:
                                context_str = str(context_length)
                        else:
                            context_str = "?"

                        key = f"ollama:{model_name}"
                        provider_models[key] = {
                            "provider": "ollama",
                            "section": "ollama",
                            "context": context_str,
                            "cost": "free",
                            "description": "Ollama model",
                            "display_name": model_name,
                            "actual_model": model_name,
                        }

        # Section 2: GGUF/LlamaCpp models
        if self._gguf_models_cache is not None:
            gguf_models = self._gguf_models_cache
        elif not self._gguf_loading:
            # Start async load if not already started
            self._gguf_loading = True
            self.run_worker(self._load_gguf_models_async(), exclusive=True)
            gguf_models = []
        else:
            gguf_models = []

        for model_info in gguf_models:
            file_name = model_info.get("name", "")
            file_path = model_info.get("path", "")

            if file_path:
                size_gb = model_info.get("size_gb", 0)
                if size_gb >= 1:
                    size_str = f"{size_gb:.1f}GB"
                else:
                    size_str = f"{size_gb * 1024:.0f}MB"

                quant = model_info.get("quant", "?")
                key = f"llamacpp:{file_path}"
                provider_models[key] = {
                    "provider": "llamacpp",
                    "section": "gguf",
                    "context": "4K-128K",
                    "cost": "free",
                    "description": f"{quant}, {size_str}",
                    "display_name": file_name,
                    "actual_model": file_path,
                }

        # Section 3: MLX models (on macOS only)
        import platform

        if platform.system() == "Darwin":
            mlx_models = {
                "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit": {
                    "context": "128K",
                    "description": "Llama 3.1 8B, 4-bit quantized",
                },
                "mlx-community/Qwen2.5-7B-Instruct-4bit": {
                    "context": "32K",
                    "description": "Qwen 2.5 7B, 4-bit quantized",
                },
                "mlx-community/Mistral-7B-Instruct-v0.3-4bit": {
                    "context": "32K",
                    "description": "Mistral 7B v0.3, 4-bit quantized",
                },
                "mlx-community/gemma-2-9b-it-4bit": {
                    "context": "8K",
                    "description": "Gemma 2 9B, 4-bit quantized",
                },
                "mlx-community/Phi-3.5-mini-instruct-4bit": {
                    "context": "128K",
                    "description": "Phi 3.5 Mini, 4-bit quantized",
                },
            }

            for model_id, info in mlx_models.items():
                key = f"mlx:{model_id}"
                provider_models[key] = {
                    "provider": "mlx",
                    "section": "mlx",
                    "context": info["context"],
                    "cost": "free",
                    "description": info["description"],
                    "display_name": model_id,
                    "actual_model": model_id,
                }

    def _add_local_models_to_table(
        self, provider_models: dict[str, dict[str, Any]], search_query: str = ""
    ) -> None:
        """Add local models to table with section headers.

        Args:
            provider_models: Dictionary of model information
            search_query: Optional search query to filter models
        """
        if not self._table:
            return

        # Apply search filter if provided
        if search_query:
            query_lower = search_query.lower()
            provider_models = {
                name: info
                for name, info in provider_models.items()
                if query_lower in info.get("display_name", "").lower()
                or query_lower in info["description"].lower()
            }

        # Group models by section
        sections: dict[str, list[tuple[str, dict[str, Any]]]] = {
            "ollama": [],
            "gguf": [],
            "mlx": [],
        }

        for key, info in provider_models.items():
            section = info.get("section", "ollama")
            sections[section].append((key, info))

        # Sort models within each section
        for section in sections:
            sections[section].sort(key=lambda x: x[1].get("display_name", ""))

        # Add Ollama section
        if sections["ollama"]:
            # Add section header as a non-selectable row
            header_key = "header:ollama"
            self._table.add_row("═══ OLLAMA ═══", "", "", key=header_key)
            self._model_map[header_key] = {"section_header": True}

            for key, info in sections["ollama"]:
                self._add_model_row(key, info)

        # Add GGUF section
        if sections["gguf"]:
            if sections["ollama"]:
                # Add spacing if previous section exists
                spacer_key = "spacer:gguf"
                self._table.add_row("", "", "", key=spacer_key)
                self._model_map[spacer_key] = {"spacer": True}

            header_key = "header:gguf"
            self._table.add_row("═══ GGUF (LlamaCpp) ═══", "", "", key=header_key)
            self._model_map[header_key] = {"section_header": True}

            for key, info in sections["gguf"]:
                self._add_model_row(key, info)

        # Add MLX section
        if sections["mlx"]:
            if sections["ollama"] or sections["gguf"]:
                spacer_key = "spacer:mlx"
                self._table.add_row("", "", "", key=spacer_key)
                self._model_map[spacer_key] = {"spacer": True}

            header_key = "header:mlx"
            self._table.add_row("═══ MLX (Apple Silicon) ═══", "", "", key=header_key)
            self._model_map[header_key] = {"section_header": True}

            for key, info in sections["mlx"]:
                self._add_model_row(key, info)

        # If loading GGUF models, show loading indicator
        if self._gguf_loading and not sections["gguf"]:
            if sections["ollama"]:
                spacer_key = "spacer:loading"
                self._table.add_row("", "", "", key=spacer_key)
                self._model_map[spacer_key] = {"spacer": True}

            loading_key = "loading:gguf"
            self._table.add_row(
                "⏳ Scanning GGUF cache directories...", "", "", key=loading_key
            )
            self._model_map[loading_key] = {"loading": True}

        log.debug(
            f"ModelPickerModal: Populated Local tab with "
            f"{len(sections['ollama'])} Ollama, "
            f"{len(sections['gguf'])} GGUF, "
            f"{len(sections['mlx'])} MLX models"
        )

    def _add_model_row(self, key: str, info: dict[str, Any]) -> None:
        """Add a single model row to the table.

        Args:
            key: Unique key for the row
            info: Model information dictionary
        """
        if not self._table:
            return

        self._model_map[key] = info

        # Check if this is the current model
        current_provider_value = self.current_provider.value
        actual_model = info.get("actual_model", "")
        is_current = (
            actual_model == self.current_model
            and info["provider"] == current_provider_value
        )

        # Format display
        display_name = info.get("display_name", key)
        model_col = f"✓ {display_name}" if is_current else f"  {display_name}"
        context_col = info["context"]
        cost_col = info["cost"].title()

        self._table.add_row(model_col, context_col, cost_col, key=key)

        # Highlight current model row
        if is_current:
            try:
                row_keys_list = list(self._table.rows.keys())
                row_index = next(
                    (i for i, k in enumerate(row_keys_list) if str(k) == key),
                    None,
                )
                if row_index is not None:
                    self._table.move_cursor(row=row_index)
            except (ValueError, Exception):
                pass

    async def _load_gguf_models_async(self) -> None:
        """Asynchronously load GGUF models from cache directories.

        This runs in a worker thread to avoid blocking the UI during
        the potentially slow directory scan (rglob on large caches).
        """
        try:
            from consoul.ai.providers import get_gguf_models_from_cache

            # Run the scan (this may take seconds with large caches)
            # The function itself has caching, so subsequent calls are fast
            result = await self.run_in_executor(get_gguf_models_from_cache)

            # Cache the results in the modal
            self._gguf_models_cache = result
            self._gguf_loading = False

            # Refresh the table to show the loaded models
            # Refresh if on local tab (which includes llamacpp)
            if self.active_provider == "local":
                self._populate_table()

            log.info(f"Loaded {len(result)} GGUF models from cache")

        except Exception as e:
            log.error(f"Error loading GGUF models: {e}", exc_info=True)
            self._gguf_models_cache = []
            self._gguf_loading = False

            # Refresh to remove loading indicator
            if self.active_provider == "llamacpp":
                self._populate_table()

    async def run_in_executor(self, func: Callable[..., Any], *args: object) -> Any:
        """Run a blocking function in an executor to avoid blocking the event loop."""
        import asyncio
        import concurrent.futures

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, func, *args)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._populate_table(event.value)

    async def on_click(self, event: Click) -> None:
        """Handle click events on provider tabs."""
        target_id = (
            event.control.id
            if hasattr(event, "control")
            and event.control is not None
            and hasattr(event.control, "id")
            else None
        )

        # Provider tab clicks
        if target_id and target_id.startswith("tab-"):
            provider = target_id.replace("tab-", "")
            if provider in [
                "openai",
                "anthropic",
                "google",
                "ollama",
                "huggingface",
                "llamacpp",
                "mlx",
            ]:
                self.active_provider = provider
                log.info(f"ModelPickerModal: Switched to provider '{provider}'")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key or double-click)."""
        if event.row_key:
            row_key = str(event.row_key.value)

            # Skip section headers, spacers, and loading indicators
            model_info = self._model_map.get(row_key, {})
            if (
                model_info.get("section_header")
                or model_info.get("spacer")
                or model_info.get("loading")
            ):
                return

            # For local tab, extract actual provider and model from the key
            if self.active_provider == "local":
                if ":" in row_key:
                    provider, selected_model = row_key.split(":", 1)
                    log.info(
                        f"ModelPickerModal: Selected from Local tab provider='{provider}', "
                        f"model='{selected_model}'"
                    )
                    self.dismiss((provider, selected_model))
                else:
                    return
            else:
                selected_model = row_key
                log.info(
                    f"ModelPickerModal: Selected provider='{self.active_provider}', "
                    f"model='{selected_model}'"
                )
                self.dismiss((self.active_provider, selected_model))

    def action_select(self) -> None:
        """Handle select action (Enter key)."""
        if not self._table:
            return

        cursor_row = self._table.cursor_row
        if cursor_row is None:
            return

        # Get row key from cursor position
        row_keys = list(self._table.rows.keys())
        if 0 <= cursor_row < len(row_keys):
            row_key = str(row_keys[cursor_row])

            # Skip section headers, spacers, and loading indicators
            model_info = self._model_map.get(row_key, {})
            if (
                model_info.get("section_header")
                or model_info.get("spacer")
                or model_info.get("loading")
            ):
                return

            # For local tab, extract actual provider and model from the key
            if self.active_provider == "local":
                if ":" in row_key:
                    provider, selected_model = row_key.split(":", 1)
                    log.info(
                        f"ModelPickerModal: Selected from Local tab provider='{provider}', "
                        f"model='{selected_model}'"
                    )
                    self.dismiss((provider, selected_model))
                else:
                    return
            else:
                selected_model = row_key
                log.info(
                    f"ModelPickerModal: Selected provider='{self.active_provider}', "
                    f"model='{selected_model}'"
                )
                self.dismiss((self.active_provider, selected_model))

    def action_cancel(self) -> None:
        """Handle cancel action (Escape key)."""
        log.info("ModelPickerModal: Cancel action")
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            self.action_select()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

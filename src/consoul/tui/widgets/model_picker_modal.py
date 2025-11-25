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
        "description": "Fastest, most affordable",
    },
    "gpt-5-pro": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Pro-tier flagship model",
    },
    "gpt-5.1": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Latest GPT-5 series iteration",
    },
    # OpenAI Codex Models (Specialized Coding)
    "gpt-5-codex": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Agentic coding optimized",
    },
    "gpt-5.1-codex": {
        "provider": "openai",
        "context": "1M",
        "cost": "expensive",
        "description": "Latest codex iteration",
    },
    "gpt-5.1-codex-mini": {
        "provider": "openai",
        "context": "1M",
        "cost": "moderate",
        "description": "Efficient coding assistant",
    },
    "codex-mini-latest": {
        "provider": "openai",
        "context": "128K",
        "cost": "cheap",
        "description": "Latest mini codex",
    },
    # OpenAI Search API
    "gpt-5-search-api": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Web search integration",
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
        "description": "Fast with 1M context",
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
        "cost": "$2.50/$10",
        "description": "Multimodal flagship",
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "$0.15/$0.60",
        "description": "Cost-efficient multimodal",
    },
    "chatgpt-4o-latest": {
        "provider": "openai",
        "context": "128K",
        "cost": "$5/$15",
        "description": "ChatGPT 4o latest snapshot",
    },
    "gpt-4o-search-preview": {
        "provider": "openai",
        "context": "128K",
        "cost": "$2.50/$10",
        "description": "Search preview (latest)",
    },
    "gpt-4o-search-preview-2025-03-11": {
        "provider": "openai",
        "context": "128K",
        "cost": "$2.50/$10",
        "description": "Search preview (dated)",
    },
    # OpenAI GPT-4 Series (Legacy)
    "gpt-4": {
        "provider": "openai",
        "context": "8K",
        "cost": "$30/$60",
        "description": "Original GPT-4",
    },
    "gpt-4-turbo": {
        "provider": "openai",
        "context": "128K",
        "cost": "$10/$30",
        "description": "GPT-4 with 128K context",
    },
    # OpenAI GPT-3.5 Series (Legacy)
    "gpt-3.5-turbo": {
        "provider": "openai",
        "context": "16K",
        "cost": "$0.50/$1.50",
        "description": "Legacy fast model",
    },
    "gpt-3.5-turbo-instruct": {
        "provider": "openai",
        "context": "4K",
        "cost": "$1.50/$2",
        "description": "Completion model (not chat)",
    },
    # OpenAI o-Series (Deep Reasoning)
    "o1": {
        "provider": "openai",
        "context": "200K",
        "cost": "$15/$60",
        "description": "Reasoning model series 1",
    },
    "o1-pro": {
        "provider": "openai",
        "context": "128K",
        "cost": "pro tier",
        "description": "Pro-tier reasoning",
    },
    "o3": {
        "provider": "openai",
        "context": "200K",
        "cost": "TBA",
        "description": "Advanced reasoning (preview)",
    },
    "o3-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "$1.10/$4.40",
        "description": "Efficient reasoning",
    },
    "o4-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Fast reasoning with vision",
    },
    "o4-mini-deep-research": {
        "provider": "openai",
        "context": "128K",
        "cost": "expensive",
        "description": "Multi-step research",
    },
    # OpenAI Realtime Models (Audio/Voice)
    "gpt-realtime-mini": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Real-time voice (mini)",
    },
    "gpt-realtime": {
        "provider": "openai",
        "context": "128K",
        "cost": "expensive",
        "description": "Real-time voice (full)",
    },
    # Anthropic Claude 4.5 Models (Latest - Sep/Oct/Nov 2025)
    "claude-opus-4-5-20251101": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$5/$25",
        "description": "Premium intelligence + performance",
    },
    "claude-sonnet-4-5-20250929": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$3/$15",
        "description": "Smartest for complex agents + coding",
    },
    "claude-haiku-4-5-20251001": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$1/$5",
        "description": "Fastest near-frontier intelligence",
    },
    # Anthropic Claude 4.x Models (Legacy)
    "claude-opus-4-1-20250805": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$15/$75",
        "description": "Exceptional specialized reasoning",
    },
    "claude-opus-4-20250514": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$15/$75",
        "description": "Legacy model (use Opus 4.5)",
    },
    "claude-sonnet-4-20250514": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$3/$15",
        "description": "Legacy model (use Sonnet 4.5)",
    },
    # Anthropic Claude 3.x Models (Legacy)
    "claude-3-7-sonnet-20250219": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$3/$15",
        "description": "Legacy model (use Sonnet 4.5)",
    },
    "claude-3-5-haiku-20241022": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$0.80/$4",
        "description": "Legacy model (use Haiku 4.5)",
    },
    "claude-3-haiku-20240307": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$0.25/$1.25",
        "description": "Legacy model (use Haiku 4.5)",
    },
    "claude-3-opus-20240229": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "$15/$75",
        "description": "Legacy model (use Opus 4.5)",
    },
    # Google Gemini 2.5 Models (Latest - Stable)
    "gemini-2.5-pro": {
        "provider": "google",
        "context": "1M",
        "cost": "expensive",
        "description": "Most powerful with thinking",
    },
    "gemini-2.5-flash": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Fast multimodal",
    },
    "gemini-2.5-flash-lite": {
        "provider": "google",
        "context": "1M",
        "cost": "cheap",
        "description": "Speed & cost optimized",
    },
    "gemini-2.5-flash-image": {
        "provider": "google",
        "context": "64K",
        "cost": "moderate",
        "description": "Native image generation",
    },
    # Google Gemini 2.0 Models
    "gemini-2.0-flash": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Latest stable flash",
    },
    # Google Gemini 1.5 Models (Legacy)
    "gemini-1.5-pro": {
        "provider": "google",
        "context": "2M",
        "cost": "expensive",
        "description": "Legacy 2M context",
    },
    "gemini-1.5-flash": {
        "provider": "google",
        "context": "1M",
        "cost": "moderate",
        "description": "Legacy flash model",
    },
    # HuggingFace Models (Serverless Inference via Inference Providers)
    # NOTE: Only models deployed by Inference Providers work with free serverless API
    # Check model page on HuggingFace for "Inference Providers" section
    "meta-llama/Llama-3.1-8B-Instruct": {
        "provider": "huggingface",
        "context": "128K",
        "cost": "free",
        "description": "Llama 3.1 8B (via Novita provider)",
    },
    "meta-llama/Llama-3.2-3B-Instruct": {
        "provider": "huggingface",
        "context": "128K",
        "cost": "free",
        "description": "Llama 3.2 3B (check provider availability)",
    },
    "mistralai/Mistral-7B-Instruct-v0.3": {
        "provider": "huggingface",
        "context": "32K",
        "cost": "free",
        "description": "Mistral 7B (check provider availability)",
    },
    # NOTE: Models below may NOT work with serverless API - they lack Inference Providers
    # Removed: google/flan-t5-* (no Inference Provider deployment)
    # Removed: microsoft/Phi-3-* (no Inference Provider deployment)
    # Removed: tiiuae/falcon-* (no Inference Provider deployment)
    # For these models, use Ollama or download locally instead
    # Note: Ollama, HuggingFace local, and LlamaCpp models are fetched dynamically
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

    ModelPickerModal #tables-container {
        width: 100%;
        height: 1fr;
        background: $surface;
    }

    ModelPickerModal #models-table {
        width: 100%;
        height: 1fr;
        background: $surface;
    }

    /* Local provider sub-tabs */
    ModelPickerModal #local-provider-tabs {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: left middle;
        margin: 0 0 1 0;
    }

    ModelPickerModal .local-provider-tab {
        margin: 0 1;
        padding: 0 2;
        background: transparent;
        color: $text-muted;
    }

    ModelPickerModal .local-provider-tab:hover {
        background: $primary-lighten-1;
        color: $text;
    }

    ModelPickerModal .local-provider-tab.-active {
        background: $accent;
        color: $text;
        text-style: bold;
    }

    ModelPickerModal .local-table {
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
    active_local_provider: reactive[str] = reactive("ollama")  # ollama, gguf, or mlx

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
            # Set the active local provider sub-tab
            if current_provider.value == "llamacpp":
                self.active_local_provider = "gguf"
            else:
                self.active_local_provider = current_provider.value
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

            # Container for model tables (will be populated dynamically in on_mount)
            yield Vertical(id="tables-container")

            # Info label
            yield Label("Enter: select · Escape: cancel", classes="info-label")

            # Action buttons
            with Horizontal(id="button-row"):
                yield Button("Select", variant="primary", id="select-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_mount(self) -> None:
        """Load models and populate table when mounted."""
        log.info(
            "ModelPickerModal: on_mount called, building tables and populating models"
        )

        # Build the initial tables based on active provider
        self._rebuild_tables_container()

        # Populate table(s)
        self._populate_table()

    def watch_active_provider(self, provider: str) -> None:
        """React to provider tab changes."""
        # Skip if not mounted yet - on_mount will handle initial setup
        if not self.is_mounted:
            return

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

        # Only rebuild tables when switching between local and non-local tabs
        # Check if we need to rebuild by seeing if the container has the right tables
        needs_rebuild = False
        try:
            self.query_one("#tables-container", Vertical)  # Verify container exists
            if provider == "local":
                # For local tab, check if we have sub-tabs
                try:
                    self.query_one("#local-provider-tabs", Horizontal)
                    pass  # Correctly has local provider tabs
                except Exception:
                    needs_rebuild = True  # Missing local provider tabs
            else:
                # For non-local tabs, we should have models-table
                try:
                    self.query_one("#models-table", DataTable)
                    pass  # Correctly has models-table
                except Exception:
                    needs_rebuild = (
                        True  # Has local tables but should have models-table
                    )
        except Exception:
            needs_rebuild = True

        if needs_rebuild:
            self._rebuild_tables_container()

        # Refresh model table(s)
        self._populate_table()

    def watch_active_local_provider(self, local_provider: str) -> None:
        """React to local provider sub-tab changes."""
        # Skip if not mounted or not on local tab
        if not self.is_mounted or self.active_provider != "local":
            return

        # Update sub-tab styling
        for subtab_id in ["local-tab-ollama", "local-tab-gguf", "local-tab-mlx"]:
            try:
                tab = self.query_one(f"#{subtab_id}", Label)
                if subtab_id == f"local-tab-{local_provider}":
                    tab.add_class("-active")
                else:
                    tab.remove_class("-active")
            except Exception:
                pass

        # Refresh the table with models for the selected local provider
        self._populate_table()

    def _rebuild_tables_container(self) -> None:
        """Rebuild the tables container based on active provider."""
        try:
            container = self.query_one("#tables-container", Vertical)
        except Exception:
            return

        # Remove ALL children from container to avoid ID conflicts
        # This is more reliable than trying to remove specific widgets
        # which can fail due to async removal timing
        while len(container._nodes) > 0:
            child = container._nodes[0]
            container._nodes._remove(child)

        # For local tab, create sub-tabs and a single table
        if self.active_provider == "local":
            import platform

            # Create sub-tabs container
            subtabs_container = Horizontal(id="local-provider-tabs")
            container.mount(subtabs_container)

            # Ollama sub-tab (only if available)
            if self._ollama_available:
                ollama_tab = Label(
                    "Ollama", classes="local-provider-tab", id="local-tab-ollama"
                )
                ollama_tab.can_focus = True
                if self.active_local_provider == "ollama":
                    ollama_tab.add_class("-active")
                subtabs_container.mount(ollama_tab)

            # GGUF sub-tab (always show)
            gguf_tab = Label("GGUF", classes="local-provider-tab", id="local-tab-gguf")
            gguf_tab.can_focus = True
            if self.active_local_provider == "gguf":
                gguf_tab.add_class("-active")
            subtabs_container.mount(gguf_tab)

            # MLX sub-tab (only on macOS)
            if platform.system() == "Darwin":
                mlx_tab = Label("MLX", classes="local-provider-tab", id="local-tab-mlx")
                mlx_tab.can_focus = True
                if self.active_local_provider == "mlx":
                    mlx_tab.add_class("-active")
                subtabs_container.mount(mlx_tab)

            # Create single table for active local provider with unique ID
            table: DataTable[Any] = DataTable(
                id="local-models-table",
                zebra_stripes=True,
                cursor_type="row",
                classes="local-table",
            )
            table.add_column("Model", width=40)
            table.add_column("Context", width=12)
            table.add_column("Description", width=35)
            container.mount(table)
            table.focus()
            self._table = table
        else:
            # Single DataTable for non-local providers with unique ID
            self._table = DataTable(
                id="provider-models-table", zebra_stripes=True, cursor_type="row"
            )
            self._table.add_column("Model", width=40)
            self._table.add_column("Context", width=12)
            self._table.add_column("Description", width=35)
            container.mount(self._table)
            self._table.focus()

    def _populate_table(self, search_query: str = "") -> None:
        """Populate or refresh the table with models.

        Args:
            search_query: Optional search query to filter models
        """
        # Clear the main table
        if not self._table:
            return
        self._table.clear()

        # Clear model map
        self._model_map.clear()

        # Check if user has HuggingFace API key for online model suggestions
        # Check both config/env files and environment variables
        from consoul.config.env import get_api_key
        from consoul.config.models import Provider

        hf_api_key = get_api_key(Provider.HUGGINGFACE)
        has_hf_key = hf_api_key is not None

        # Filter models by active provider
        # Skip HuggingFace online models if no API key
        provider_value = self.active_provider
        provider_models = {
            name: info
            for name, info in MODEL_INFO.items()
            if info["provider"] == provider_value
            and not (provider_value == "huggingface" and not has_hf_key)
        }

        # For Local tab, show models for the active local provider only
        if provider_value == "local":
            provider_models = {}
            self._populate_local_models_for_active_subtab(provider_models, search_query)
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
            import platform

            from consoul.ai.providers import get_huggingface_local_models

            is_macos = platform.system() == "Darwin"

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

                    # On macOS, local PyTorch models need MLX conversion
                    # Show them with a conversion indicator
                    if is_macos:
                        model_entry: dict[str, Any] = {
                            "provider": "huggingface",
                            "context": "?",
                            "cost": "free",
                            "description": f"🔄 Convert to MLX ({size_str})",
                            "convertible": True,
                            "display_name": model_name,
                            "hf_model_size_gb": size_gb,
                        }
                        provider_models[model_name] = model_entry
                    else:
                        # On Linux/Windows, can use PyTorch directly
                        provider_models[model_name] = {
                            "provider": "huggingface",
                            "context": "?",
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

        # For MLX in Local tab, only show locally downloaded models (no HF repo IDs)
        # HF repo IDs fail in TUI due to multiprocessing conflicts (fds_to_keep errors)
        elif provider_value == "mlx":
            # Local MLX models are already added via get_local_mlx_models() above
            # Do NOT add HuggingFace repo IDs - they will fail to load in TUI
            pass

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

        # Add rows, sorting by name (only for non-local providers)
        if self._table:
            for name in sorted(provider_models.keys()):
                info = provider_models[name]
                row_key = name

                self._model_map[row_key] = info

                # Format columns
                is_current = (
                    name == self.current_model
                    and provider_value == current_provider_value
                )
                # Use display_name if available (for LlamaCpp models), otherwise use name
                display_name = info.get("display_name", name)
                model_col = f"✓ {display_name}" if is_current else f"  {display_name}"
                context_col = info["context"]
                description_col = info["description"]

                self._table.add_row(
                    model_col, context_col, description_col, key=row_key
                )

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

    def _populate_local_models_for_active_subtab(
        self, provider_models: dict[str, dict[str, Any]], search_query: str = ""
    ) -> None:
        """Populate models for the currently active local provider sub-tab.

        Args:
            provider_models: Dictionary to populate with model information
            search_query: Optional search query to filter models
        """
        # Only populate models for the active local provider
        if self.active_local_provider == "ollama":
            self._populate_ollama_models(provider_models, search_query)
        elif self.active_local_provider == "gguf":
            self._populate_gguf_models(provider_models, search_query)
        elif self.active_local_provider == "mlx":
            self._populate_mlx_models(provider_models, search_query)

        # Apply search filter
        if search_query:
            query_lower = search_query.lower()
            provider_models_filtered = {
                key: info
                for key, info in provider_models.items()
                if query_lower in info.get("display_name", "").lower()
                or query_lower in info.get("description", "").lower()
            }
            provider_models.clear()
            provider_models.update(provider_models_filtered)

        # Add models to the table
        if self._table:
            for key in sorted(
                provider_models.keys(),
                key=lambda k: provider_models[k].get("display_name", ""),
            ):
                info = provider_models[key]
                self._add_model_row_to_table(self._table, key, info)

    def _populate_ollama_models(
        self, provider_models: dict[str, dict[str, Any]], search_query: str = ""
    ) -> None:
        """Populate Ollama models.

        Args:
            provider_models: Dictionary to populate with model information
            search_query: Optional search query (unused, filtering happens after)
        """
        if not self._ollama_available:
            return

        from consoul.ai.providers import get_ollama_models, is_ollama_running

        if not is_ollama_running():
            return

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
                    "context": context_str,
                    "cost": "free",
                    "description": "Ollama model",
                    "display_name": model_name,
                    "actual_model": model_name,
                }

    def _populate_gguf_models(
        self, provider_models: dict[str, dict[str, Any]], search_query: str = ""
    ) -> None:
        """Populate GGUF models.

        Args:
            provider_models: Dictionary to populate with model information
            search_query: Optional search query (unused, filtering happens after)
        """
        # Check cache or start loading
        if self._gguf_models_cache is not None:
            gguf_models = self._gguf_models_cache
        elif not self._gguf_loading:
            # Start async load
            self._gguf_loading = True
            self.run_worker(self._load_gguf_models_async(), exclusive=True)
            # Show loading indicator
            loading_key = "loading:gguf"
            provider_models[loading_key] = {
                "provider": "llamacpp",
                "context": "-",
                "cost": "-",
                "description": "Scanning cache directories...",
                "display_name": "⏳ Loading GGUF models...",
                "loading": True,
            }
            return
        else:
            return

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
                    "context": "4K-128K",
                    "cost": "free",
                    "description": f"{quant}, {size_str}",
                    "display_name": file_name,
                    "actual_model": file_path,
                }

    def _populate_mlx_models(
        self, provider_models: dict[str, dict[str, Any]], search_query: str = ""
    ) -> None:
        """Populate MLX models and convertible HuggingFace models.

        Args:
            provider_models: Dictionary to populate with model information
            search_query: Optional search query (unused, filtering happens after)
        """
        import platform

        if platform.system() != "Darwin":
            return

        from consoul.ai.providers import get_convertible_hf_models, get_local_mlx_models

        # Get locally downloaded MLX models
        local_mlx = get_local_mlx_models()

        for model_info in local_mlx:
            model_name = model_info.get("name", "")
            model_path = model_info.get("path", "")
            size_gb = model_info.get("size_gb", 0)

            if model_name and model_path:
                if size_gb >= 1:
                    size_str = f"{size_gb:.1f}GB"
                else:
                    size_str = f"{size_gb * 1024:.0f}MB"

                key = f"mlx:{model_path}"
                provider_models[key] = {
                    "provider": "mlx",
                    "context": "?",
                    "cost": "free",
                    "description": f"✓ MLX, {size_str}",
                    "display_name": model_name,
                    "actual_model": model_path,
                    "is_mlx": True,
                }

        # Get convertible HuggingFace models
        convertible = get_convertible_hf_models()

        for model_info in convertible:
            model_name = model_info.get("name", "")
            size_gb = model_info.get("size_gb", 0)
            is_converted = model_info.get("converted", False)

            if model_name and not is_converted:
                # Only show models that haven't been converted yet
                if size_gb >= 1:
                    size_str = f"{size_gb:.1f}GB"
                else:
                    size_str = f"{size_gb * 1024:.0f}MB"

                key = f"hf-to-mlx:{model_name}"
                provider_models[key] = {
                    "provider": "mlx",
                    "context": "?",
                    "cost": "free",
                    "description": f"🔄 Convert ({size_str})",
                    "display_name": model_name,
                    "actual_model": model_name,
                    "is_mlx": False,
                    "convertible": True,
                    "hf_model_size_gb": size_gb,
                }

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
            from consoul.ai.providers import get_local_mlx_models

            # Get locally downloaded MLX models
            local_mlx = get_local_mlx_models()

            # Add local MLX models
            for model_info in local_mlx:
                model_name = model_info.get("name", "")
                model_path = model_info.get("path", "")
                size_gb = model_info.get("size_gb", 0)

                if model_name and model_path:
                    # Format size
                    if size_gb >= 1:
                        size_str = f"{size_gb:.1f}GB"
                    else:
                        size_str = f"{size_gb * 1024:.0f}MB"

                    key = f"mlx:{model_path}"
                    provider_models[key] = {
                        "provider": "mlx",
                        "section": "mlx",
                        "context": "?",  # Could extract from config.json in future
                        "cost": "free",
                        "description": f"Local, {size_str}",
                        "display_name": model_name,
                        "actual_model": model_path,
                    }

            # Also include popular MLX models from HuggingFace as suggestions
            # (only if not already in local models)
            mlx_suggestions = {
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

            for model_id, info in mlx_suggestions.items():
                key = f"mlx:{model_id}"
                # Only add suggestion if not already added as local model
                if key not in provider_models:
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
        """Add local models to separate tables.

        Args:
            provider_models: Dictionary of model information
            search_query: Optional search query to filter models
        """
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

        # Populate Ollama table
        if self._ollama_available:
            try:
                ollama_table = self.query_one("#ollama-table", DataTable)
                ollama_table.clear()

                for key, info in sections["ollama"]:
                    self._add_model_row_to_table(ollama_table, key, info)
            except Exception as e:
                log.error(f"Error populating Ollama table: {e}")

        # Populate GGUF table
        try:
            gguf_table = self.query_one("#gguf-table", DataTable)
            gguf_table.clear()

            if self._gguf_loading and not sections["gguf"]:
                # Show loading indicator
                loading_key = "loading:gguf"
                gguf_table.add_row(
                    "⏳ Scanning GGUF cache directories...", "", "", key=loading_key
                )
                self._model_map[loading_key] = {"loading": True}
            else:
                for key, info in sections["gguf"]:
                    self._add_model_row_to_table(gguf_table, key, info)
        except Exception as e:
            log.error(f"Error populating GGUF table: {e}")

        # Populate MLX table (macOS only)
        import platform

        if platform.system() == "Darwin":
            try:
                mlx_table = self.query_one("#mlx-table", DataTable)
                mlx_table.clear()

                for key, info in sections["mlx"]:
                    self._add_model_row_to_table(mlx_table, key, info)
            except Exception as e:
                log.error(f"Error populating MLX table: {e}")

        log.debug(
            f"ModelPickerModal: Populated Local tab with "
            f"{len(sections['ollama'])} Ollama, "
            f"{len(sections['gguf'])} GGUF, "
            f"{len(sections['mlx'])} MLX models"
        )

    def _add_model_row(self, key: str, info: dict[str, Any]) -> None:
        """Add a single model row to the main table (for non-local providers).

        Args:
            key: Unique key for the row
            info: Model information dictionary
        """
        if not self._table:
            return

        self._add_model_row_to_table(self._table, key, info)

    def _add_model_row_to_table(
        self, table: DataTable[Any], key: str, info: dict[str, Any]
    ) -> None:
        """Add a single model row to a specific table.

        Args:
            table: The DataTable to add the row to
            key: Unique key for the row
            info: Model information dictionary
        """
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
        description_col = info["description"]

        table.add_row(model_col, context_col, description_col, key=key)

        # Highlight current model row
        if is_current:
            try:
                row_keys_list = list(table.rows.keys())
                row_index = next(
                    (i for i, k in enumerate(row_keys_list) if str(k) == key),
                    None,
                )
                if row_index is not None:
                    table.move_cursor(row=row_index)
                    table.focus()
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
                "huggingface",
                "local",
            ]:
                self.active_provider = provider
                log.info(f"ModelPickerModal: Switched to provider '{provider}'")

        # Local provider sub-tab clicks
        if target_id and target_id.startswith("local-tab-"):
            local_provider = target_id.replace("local-tab-", "")
            if local_provider in ["ollama", "gguf", "mlx"]:
                self.active_local_provider = local_provider
                log.info(
                    f"ModelPickerModal: Switched to local provider '{local_provider}'"
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key or double-click)."""
        if event.row_key:
            row_key = str(event.row_key.value)

            # Skip loading indicators
            model_info = self._model_map.get(row_key, {})
            if model_info.get("loading"):
                return

            # Check if this is a convertible HuggingFace model (needs MLX conversion)
            if model_info.get("convertible"):
                # Show conversion modal instead of selecting
                self._show_mlx_conversion_modal(model_info)
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

    def _show_mlx_conversion_modal(self, model_info: dict[str, Any]) -> None:
        """Show MLX conversion modal for a convertible HuggingFace model.

        Args:
            model_info: Model information dict with 'display_name' and 'hf_model_size_gb'
        """
        model_name = model_info.get("display_name", "")
        size_gb = model_info.get("hf_model_size_gb", 0)

        if not model_name:
            return

        from consoul.tui.widgets.mlx_conversion_modal import MLXConversionModal

        def handle_conversion_result(
            result: dict[str, str | int | bool] | None,
        ) -> None:
            """Handle conversion modal result.

            Args:
                result: Conversion parameters or None if cancelled
            """
            if result is None:
                # User cancelled
                return

            # Start conversion in background
            self._start_mlx_conversion(result)

        modal = MLXConversionModal(model_name, size_gb)
        self.app.push_screen(modal, handle_conversion_result)

    def _start_mlx_conversion(self, params: dict[str, str | int | bool]) -> None:
        """Start MLX conversion in background.

        Args:
            params: Conversion parameters from MLXConversionModal
        """
        model_name = str(params.get("model_name", ""))
        quantize = bool(params.get("quantize", True))
        q_bits = int(params.get("q_bits", 4))

        # Run conversion in worker thread to avoid blocking UI
        async def run_conversion() -> None:
            """Run conversion task asynchronously."""
            from consoul.ai.providers import convert_hf_to_mlx

            # Show notification
            if hasattr(self.app, "notify"):
                self.app.notify(
                    f"Starting MLX conversion for {model_name}...\n"
                    f"This may take 5-30 minutes.",
                    severity="information",
                    timeout=10,
                )

            # Run conversion
            try:
                result = convert_hf_to_mlx(
                    hf_model_name=model_name,
                    quantize=quantize,
                    q_bits=q_bits,
                )

                # Show result
                if hasattr(self.app, "notify"):
                    if result.get("success"):
                        if result.get("skipped"):
                            self.app.notify(
                                f"Model {model_name} already converted",
                                severity="information",
                            )
                        else:
                            self.app.notify(
                                f"✓ Successfully converted {model_name} to MLX!\n"
                                f"Output: {result.get('output_path', 'unknown')}",
                                severity="information",
                                timeout=10,
                            )
                        # Refresh model list
                        self._populate_table()
                    else:
                        error = result.get("error", "Unknown error")
                        details = result.get("details", "")
                        self.app.notify(
                            f"✗ Conversion failed: {error}\n{details}",
                            severity="error",
                            timeout=15,
                        )
            except Exception as e:
                if hasattr(self.app, "notify"):
                    self.app.notify(
                        f"✗ Conversion error: {type(e).__name__}: {e}",
                        severity="error",
                        timeout=10,
                    )

        # Start the conversion worker
        self.run_worker(run_conversion(), exclusive=False)

    def action_select(self) -> None:
        """Handle select action (Enter key)."""
        # Get the currently focused table
        focused_table = None

        if self.active_provider == "local":
            # Try to find which local table has focus
            for table_id in ["ollama-table", "gguf-table", "mlx-table"]:
                try:
                    table = self.query_one(f"#{table_id}", DataTable)
                    if table.has_focus:
                        focused_table = table
                        break
                except Exception:
                    pass
        else:
            # Use the main table for non-local providers
            focused_table = self._table

        if not focused_table:
            return

        cursor_row = focused_table.cursor_row
        if cursor_row is None:
            return

        # Get row key from cursor position
        row_keys = list(focused_table.rows.keys())
        if 0 <= cursor_row < len(row_keys):
            row_key = str(row_keys[cursor_row])

            # Skip loading indicators
            model_info = self._model_map.get(row_key, {})
            if model_info.get("loading"):
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

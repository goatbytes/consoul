"""ModelCard - Individual model card widget for model picker."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

    from consoul.registry.types import ModelEntry

__all__ = ["ModelCard"]


class ModelCard(Vertical):
    """A card widget for displaying a single AI model.

    Displays model information including name, description, capabilities,
    pricing, and metadata with visual feedback for selection state.
    """

    class CardClicked(Message):
        """Message sent when a card is clicked."""

        def __init__(self, model_id: str, provider: str) -> None:
            """Initialize CardClicked message.

            Args:
                model_id: ID of the model that was clicked
                provider: Provider name
            """
            super().__init__()
            self.model_id = model_id
            self.provider = provider

    DEFAULT_CSS = """
    ModelCard {
        width: 100%;
        height: auto;
        min-height: 5;
        padding: 1;
        margin: 0 1 1 0;
        background: $surface;
        border: round $primary;
    }

    ModelCard:hover {
        background: $surface-lighten-1;
        border: round $accent;
    }

    ModelCard.selected {
        # background: $primary;
        border: round #4BB543;
    }

    ModelCard.selected:hover {
        background: $primary-lighten-1;
    }

    ModelCard .model-header {
        width: 100%;
        height: auto;
    }

    ModelCard .model-name {
        width: 1fr;
        color: $text;
        text-style: bold;
    }

    ModelCard.selected .model-name {
        color: auto;
    }

    ModelCard .model-id {
        width: auto;
        color: $text-muted;
        text-align: right;
    }

    ModelCard.selected .model-id {
        color: auto 70%;
    }

    ModelCard .model-description {
        width: 100%;
        color: $text-muted;
    }

    ModelCard.selected .model-description {
        color: auto 70%;
    }

    ModelCard .model-metadata {
        width: 100%;
        height: auto;
    }

    ModelCard .metadata-left {
        width: 1fr;
        height: auto;
    }

    ModelCard .metadata-right {
        width: auto;
        height: auto;
        content-align: right top;
    }

    ModelCard .model-badges {
        color: $text-muted;
    }

    ModelCard.selected .model-badges {
        color: auto 70%;
    }

    ModelCard .model-stats {
        color: $text-muted;
    }

    ModelCard.selected .model-stats {
        color: auto 70%;
    }

    ModelCard .model-pricing {
        color: $text-muted;
    }

    ModelCard.selected .model-pricing {
        color: auto;
    }

    ModelCard .model-date {
        width: 100%;
        color: $text-muted;
        text-align: right;
    }

    ModelCard.selected .model-date {
        color: auto 70%;
    }
    """

    # Reactive properties
    is_selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        model: ModelEntry,
        is_current: bool = False,
    ) -> None:
        """Initialize model card.

        Args:
            model: Model entry from registry
            is_current: Whether this is the currently selected model
        """
        super().__init__()
        self.model = model
        self.is_current_model = is_current
        self.model_id = model.id
        self.provider = model.metadata.provider

    def compose(self) -> ComposeResult:
        """Compose the card widgets."""
        # Model name with tier badge and current indicator
        tier_badge = self._get_tier_badge()
        current_indicator = "[green]✓[/] " if self.is_current_model else ""

        # Header row with name and model ID
        with Horizontal(classes="model-header"):
            name_text = f"{current_indicator}{self.model.name} {tier_badge}"
            yield Label(name_text, classes="model-name")
            yield Label(self.model.id, classes="model-id")

        # Description
        # yield Label(self.model.metadata.description, classes="model-description")

        # Metadata row with two columns
        with Horizontal(classes="model-metadata"):
            # Left column: badges and stats
            with Vertical(classes="metadata-left"):
                # Capabilities badges
                badges = self._get_capability_badges()
                if badges:
                    yield Label(" ".join(badges), classes="model-badges", markup=True)

                # Context and output stats
                ctx_formatted = self._format_tokens(self.model.metadata.context_window)
                out_formatted = self._format_tokens(
                    self.model.metadata.max_output_tokens
                )
                stats_text = f"{ctx_formatted} context • {out_formatted} output"
                yield Label(stats_text, classes="model-stats")

            # Right column: pricing and date
            with Vertical(classes="metadata-right"):
                # Pricing with color coding
                pricing = self.model.get_pricing("standard")
                price_color = self._get_price_color(pricing.output_price)
                input_fmt = self._format_price(pricing.input_price)
                output_fmt = self._format_price(pricing.output_price)
                pricing_text = f"[{price_color}]${input_fmt}/${output_fmt} per MTok[/]"
                yield Label(pricing_text, classes="model-pricing", markup=True)

                # Release date
                release_date = self.model.metadata.created.strftime("%b %Y")
                is_new = (datetime.now().date() - self.model.metadata.created).days < 90
                date_text = f"✦ {release_date}" if is_new else release_date
                yield Label(date_text, classes="model-date")

    def _format_price(self, price: float) -> str:
        """Format price for display.

        Args:
            price: Price in dollars

        Returns:
            Formatted string (e.g., "5", "5.50", "0.15")
        """
        if price == 0:
            return "0"
        elif price >= 1 and price == int(price):
            # Whole dollar amounts: 5, 10, 25
            return f"{int(price)}"
        else:
            # Always show 2 decimals for non-whole amounts: 0.15, 5.50, 15.75
            return f"{price:.2f}"

    def _format_tokens(self, tokens: int) -> str:
        """Format token count for display.

        Args:
            tokens: Number of tokens

        Returns:
            Formatted string (e.g., "200K", "1M", "2.1M")
        """
        if tokens >= 1_000_000:
            millions = tokens / 1_000_000
            # Show decimal if not a whole number
            if millions == int(millions):
                return f"{int(millions)}M"
            else:
                return f"{millions:.1f}M"
        elif tokens >= 1_000:
            thousands = tokens // 1_000
            return f"{thousands}K"
        else:
            return str(tokens)

    def _get_tier_badge(self) -> str:
        """Get tier badge for model based on name/capabilities."""
        name_lower = self.model.name.lower()
        if (
            "opus" in name_lower
            or "pro" in name_lower
            or self.model.id.startswith("o1")
        ):
            return "▪ Premium"
        elif (
            "haiku" in name_lower
            or "mini" in name_lower
            or "nano" in name_lower
            or "lite" in name_lower
        ):
            return "▪ Fast"
        return "▪ Balanced"

    def _get_capability_badges(self) -> list[str]:
        """Get capability badges for model."""
        badges = []
        if self.model.supports_vision():
            badges.append("▣ Vision")
        if self.model.supports_tools():
            badges.append("⛏ Tools")
        if self.model.supports_reasoning():
            badges.append("∴ Reasoning")

        # Additional capabilities
        caps = [c.value for c in self.model.metadata.capabilities]
        if "streaming" in caps:
            badges.append("≋ Streaming")
        if "caching" in caps:
            badges.append("≣ Caching")

        return badges

    def _get_price_color(self, output_price: float) -> str:
        """Get color based on output price.

        Price tiers based on market analysis:
        - Budget: $0-4 (Q1) - Fast/mini models
        - Standard: $4-12 (Q1-Q3) - Balanced models
        - Premium: $12-25 - Pro/Opus models
        - Ultra: $25+ - Specialized/reasoning models
        """
        if output_price <= 4.0:
            return "#00d787"  # Bright green - budget friendly
        elif output_price <= 12.0:
            return "#ffd700"  # Gold - standard pricing
        elif output_price <= 25.0:
            return "#ff8700"  # Orange - premium pricing
        else:
            return "#ff5f5f"  # Coral red - ultra premium

    def watch_is_selected(self, selected: bool) -> None:
        """Update visual state when selection changes."""
        self.set_class(selected, "selected")

    async def on_click(self, event: Click) -> None:
        """Handle click events on the card."""
        event.stop()
        self.post_message(self.CardClicked(self.model_id, self.provider))

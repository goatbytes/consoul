"""Tests for TUI-specific configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from consoul.config.models import ConsoulCoreConfig, OpenAIModelConfig
from consoul.tui.config import ConsoulTuiConfig, TuiConfig
from consoul.tui.profiles import ProfileConfig


class TestTuiConfigDefaults:
    """Test TuiConfig default values."""

    def test_default_config(self) -> None:
        """Test TuiConfig with default values."""
        config = TuiConfig()
        assert config.theme == "consoul-dark"
        assert config.gc_mode == "streaming-aware"
        assert config.stream_buffer_size == 200
        assert config.stream_debounce_ms == 150
        assert config.stream_renderer == "markdown"
        assert config.show_sidebar is True
        assert config.show_timestamps is True
        assert config.show_token_count is True
        assert config.initial_conversation_load == 50
        assert config.enable_virtualization is True
        assert config.enable_multiline_input is True
        assert config.enable_mouse is True
        assert config.vim_mode is False

    def test_gc_interval_default(self) -> None:
        """Test GC interval default value."""
        config = TuiConfig()
        assert config.gc_interval_seconds == 30.0
        assert config.gc_generation == 0


class TestTuiConfigValidation:
    """Test TuiConfig field validation."""

    def test_gc_interval_valid_bounds(self) -> None:
        """Test gc_interval_seconds accepts valid values."""
        # Minimum
        config = TuiConfig(gc_interval_seconds=5.0)
        assert config.gc_interval_seconds == 5.0

        # Maximum
        config = TuiConfig(gc_interval_seconds=300.0)
        assert config.gc_interval_seconds == 300.0

        # Middle
        config = TuiConfig(gc_interval_seconds=60.0)
        assert config.gc_interval_seconds == 60.0

    def test_gc_interval_below_minimum(self) -> None:
        """Test gc_interval_seconds rejects values below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(gc_interval_seconds=3.0)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("gc_interval_seconds",)
        assert "greater than or equal to 5" in errors[0]["msg"].lower()

    def test_gc_interval_above_maximum(self) -> None:
        """Test gc_interval_seconds rejects values above maximum."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(gc_interval_seconds=400.0)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("gc_interval_seconds",)
        assert "less than or equal to 300" in errors[0]["msg"].lower()

    def test_gc_generation_valid_values(self) -> None:
        """Test gc_generation accepts valid values (0-2)."""
        for gen in [0, 1, 2]:
            config = TuiConfig(gc_generation=gen)
            assert config.gc_generation == gen

    def test_gc_generation_invalid_negative(self) -> None:
        """Test gc_generation rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(gc_generation=-1)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("gc_generation",)

    def test_gc_generation_invalid_above_max(self) -> None:
        """Test gc_generation rejects values > 2."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(gc_generation=3)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("gc_generation",)

    def test_stream_buffer_size_bounds(self) -> None:
        """Test stream_buffer_size validation."""
        # Valid
        config = TuiConfig(stream_buffer_size=100)
        assert config.stream_buffer_size == 100

        # Below minimum
        with pytest.raises(ValidationError):
            TuiConfig(stream_buffer_size=30)

        # Above maximum
        with pytest.raises(ValidationError):
            TuiConfig(stream_buffer_size=2000)

    def test_stream_debounce_ms_bounds(self) -> None:
        """Test stream_debounce_ms validation."""
        # Valid
        config = TuiConfig(stream_debounce_ms=100)
        assert config.stream_debounce_ms == 100

        # Below minimum
        with pytest.raises(ValidationError):
            TuiConfig(stream_debounce_ms=30)

        # Above maximum
        with pytest.raises(ValidationError):
            TuiConfig(stream_debounce_ms=600)

    def test_initial_conversation_load_bounds(self) -> None:
        """Test initial_conversation_load validation."""
        # Valid
        config = TuiConfig(initial_conversation_load=50)
        assert config.initial_conversation_load == 50

        # Below minimum
        with pytest.raises(ValidationError):
            TuiConfig(initial_conversation_load=5)

        # Above maximum
        with pytest.raises(ValidationError):
            TuiConfig(initial_conversation_load=300)


class TestTuiConfigLiterals:
    """Test TuiConfig Literal type validation."""

    def test_valid_gc_modes(self) -> None:
        """Test valid gc_mode values."""
        for mode in ["auto", "manual", "streaming-aware"]:
            config = TuiConfig(gc_mode=mode)  # type: ignore[arg-type]
            assert config.gc_mode == mode

    def test_invalid_gc_mode(self) -> None:
        """Test invalid gc_mode is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(gc_mode="invalid")  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("gc_mode",)
        assert (
            "Input should be 'auto', 'manual' or 'streaming-aware'" in errors[0]["msg"]
        )

    def test_valid_stream_renderers(self) -> None:
        """Test valid stream_renderer values."""
        for renderer in ["markdown", "richlog", "hybrid"]:
            config = TuiConfig(stream_renderer=renderer)  # type: ignore[arg-type]
            assert config.stream_renderer == renderer

    def test_invalid_stream_renderer(self) -> None:
        """Test invalid stream_renderer is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(stream_renderer="plaintext")  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("stream_renderer",)


class TestTuiConfigExtraForbid:
    """Test that extra fields are forbidden."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that typos in config are caught."""
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(themee="dark")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Extra inputs are not permitted" in errors[0]["msg"]

    def test_unknown_field_rejected(self) -> None:
        """Test unknown fields are rejected."""
        with pytest.raises(ValidationError):
            TuiConfig(unknown_setting=True)  # type: ignore[call-arg]


class TestConsoulConfigIntegration:
    """Test TuiConfig integration with ConsoulTuiConfig."""

    def test_consoul_config_has_tui_field(self) -> None:
        """Test that ConsoulTuiConfig includes tui field."""
        config = ConsoulTuiConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default profile",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            core=ConsoulCoreConfig(),
        )
        assert hasattr(config, "tui")
        assert isinstance(config.tui, TuiConfig)

    def test_tui_config_has_defaults(self) -> None:
        """Test that config.tui contains default TUI settings."""
        config = ConsoulTuiConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default profile",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            core=ConsoulCoreConfig(),
        )
        assert config.tui.theme == "consoul-dark"
        assert config.tui.gc_mode == "streaming-aware"
        assert config.tui.stream_buffer_size == 200

    def test_tui_config_can_be_customized(self) -> None:
        """Test that TUI settings can be customized in ConsoulTuiConfig."""
        custom_tui = TuiConfig(
            theme="dracula",
            gc_mode="manual",
            stream_buffer_size=300,
        )
        config = ConsoulTuiConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default profile",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            core=ConsoulCoreConfig(),
            tui=custom_tui,
        )
        assert config.tui.theme == "dracula"
        assert config.tui.gc_mode == "manual"
        assert config.tui.stream_buffer_size == 300

    def test_yaml_roundtrip_preserves_tui_settings(self) -> None:
        """Test that TUI settings survive YAML serialization."""
        config = ConsoulTuiConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default profile",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            core=ConsoulCoreConfig(),
            tui=TuiConfig(theme="nord", show_timestamps=False),
        )

        # Serialize to dict
        data = config.model_dump(mode="json", exclude_unset=True)

        # Should include tui settings
        assert "tui" in data
        assert data["tui"]["theme"] == "nord"
        assert data["tui"]["show_timestamps"] is False

    def test_tui_validation_errors_propagate(self) -> None:
        """Test that TUI validation errors are caught when creating ConsoulTuiConfig."""
        # TuiConfig validation errors should propagate up
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(gc_interval_seconds=1.0)  # Below minimum

        errors = exc_info.value.errors()
        assert any("gc_interval_seconds" in str(err["loc"]) for err in errors)

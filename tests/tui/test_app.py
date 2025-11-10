"""Tests for ConsoulApp TUI application."""

from __future__ import annotations

import gc

from consoul.tui.app import ConsoulApp
from consoul.tui.config import TuiConfig


class TestConsoulAppGarbageCollection:
    """Test GC management preserves library-first design."""

    def test_gc_state_restored_after_app_lifecycle(self) -> None:
        """Test that original GC state is restored after app unmount.

        This ensures library-first design: embedding apps don't lose GC
        when Consoul TUI exits.
        """
        # Record original GC state
        original_gc_enabled = gc.isenabled()

        try:
            # Test with GC originally enabled
            gc.enable()
            config = TuiConfig(gc_mode="streaming-aware")
            app = ConsoulApp(config=config, test_mode=True)
            assert app._original_gc_enabled is True

            # Simulate unmount (skip mount to avoid event loop requirement)
            app.on_unmount()
            # GC should be restored to enabled
            assert gc.isenabled() is True

            # Test with GC originally disabled
            gc.disable()
            app = ConsoulApp(config=config, test_mode=True)
            assert app._original_gc_enabled is False

            app.on_unmount()
            # GC should be restored to disabled
            assert gc.isenabled() is False

        finally:
            # Cleanup: restore original state
            if original_gc_enabled:
                gc.enable()
            else:
                gc.disable()

    def test_gc_mode_determines_behavior(self) -> None:
        """Test that GC mode configuration is respected."""
        # Just verify the config is stored correctly
        # Actual GC manipulation happens in on_mount() which requires event loop
        config = TuiConfig(gc_mode="streaming-aware")
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.gc_mode == "streaming-aware"

        config = TuiConfig(gc_mode="auto")
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.gc_mode == "auto"

    def test_gc_not_modified_when_auto_mode(self) -> None:
        """Test that GC is not modified in auto mode."""
        original_gc_enabled = gc.isenabled()

        try:
            config = TuiConfig(gc_mode="auto")
            app = ConsoulApp(config=config, test_mode=True)

            # In auto mode, GC state should not be modified
            # We can't call on_mount() without event loop, but we can verify
            # that the config is set correctly
            assert app.config.gc_mode == "auto"

            app.on_unmount()
            # GC should still be in original state
            assert gc.isenabled() == original_gc_enabled

        finally:
            if original_gc_enabled:
                gc.enable()

    def test_original_gc_state_stored_in_init(self) -> None:
        """Test that original GC state is captured in __init__."""
        # Enable GC
        gc.enable()
        app = ConsoulApp(test_mode=True)
        assert app._original_gc_enabled is True

        # Disable GC
        gc.disable()
        app = ConsoulApp(test_mode=True)
        assert app._original_gc_enabled is False

        # Restore
        gc.enable()


class TestConsoulAppInitialization:
    """Test ConsoulApp initialization."""

    def test_app_initialization_with_defaults(self) -> None:
        """Test app initializes with default config."""
        app = ConsoulApp(test_mode=True)
        assert app.title == "Consoul - AI Terminal Assistant"
        assert app.streaming is False
        assert app.conversation_id is None

    def test_app_initialization_with_custom_config(self) -> None:
        """Test app initializes with custom config."""
        config = TuiConfig(theme="dracula", gc_mode="manual")
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.theme == "dracula"
        assert app.config.gc_mode == "manual"

    def test_app_does_not_crash_with_invalid_theme(self) -> None:
        """Test that invalid theme doesn't crash during __init__.

        Previously, notify() was called from __init__ which would crash
        because message pump isn't running yet. Now theme validation
        happens in on_mount().
        """
        config = TuiConfig(theme="nonexistent-theme")
        # Should not raise RuntimeError
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.theme == "nonexistent-theme"

        # Notification should happen in on_mount (when message pump is running)
        # We can't easily test this without actually running the app,
        # but we verify that __init__ doesn't crash


class TestConsoulAppReactiveState:
    """Test reactive state management."""

    def test_reactive_state_initialization(self) -> None:
        """Test reactive state variables initialize correctly."""
        app = ConsoulApp(test_mode=True)
        assert app.streaming is False
        assert app.conversation_id is None
        assert app.current_profile == "default"
        assert app.current_model == ""

    def test_streaming_state_can_be_changed(self) -> None:
        """Test that streaming reactive state can be modified."""
        app = ConsoulApp(test_mode=True)
        app.streaming = True
        assert app.streaming is True
        app.streaming = False
        assert app.streaming is False

"""Tests for wrapper functions metadata handling (SOUL-313 round-trip requirement)."""

from __future__ import annotations

from consoul.sdk.models import SessionMetadata
from consoul.sdk.wrapper import restore_session, save_session_state


class TestMetadataRoundTrip:
    """Test that metadata survives save/restore cycle."""

    def test_save_preserves_console_metadata(self) -> None:
        """save_session_state includes metadata from console._session_metadata."""

        # Use a mock-like object instead of real Consoul to avoid API dependencies
        class MockConsoul:
            model_name = "gpt-4o"
            temperature = 0.7

            class History:
                @staticmethod
                def get_messages_as_dicts() -> list[dict[str, str]]:
                    return [{"role": "user", "content": "Hello"}]

            history = History()

        console = MockConsoul()
        console.session_id = "test123"  # type: ignore[attr-defined]
        console._session_metadata = SessionMetadata(  # type: ignore[attr-defined]
            user_id="alice",
            tenant_id="acme",
            tags=["vip"],
            custom={"plan": "enterprise"},
        )

        state = save_session_state(console)  # type: ignore[arg-type]

        assert "metadata" in state
        assert state["metadata"]["user_id"] == "alice"
        assert state["metadata"]["tenant_id"] == "acme"
        assert state["metadata"]["tags"] == ["vip"]
        assert state["metadata"]["custom"]["plan"] == "enterprise"

    def test_save_with_explicit_metadata_overrides(self) -> None:
        """save_session_state uses explicit metadata over console metadata."""

        class MockConsoul:
            model_name = "gpt-4o"
            temperature = 0.7

            class History:
                @staticmethod
                def get_messages_as_dicts() -> list[dict[str, str]]:
                    return []

            history = History()

        console = MockConsoul()
        console.session_id = "test123"  # type: ignore[attr-defined]
        console._session_metadata = SessionMetadata(user_id="old_user")  # type: ignore[attr-defined]

        # Explicit metadata should override
        new_metadata = SessionMetadata(user_id="new_user", tenant_id="new_tenant")
        state = save_session_state(console, metadata=new_metadata)  # type: ignore[arg-type]

        assert state["metadata"]["user_id"] == "new_user"
        assert state["metadata"]["tenant_id"] == "new_tenant"

    def test_save_with_dict_metadata(self) -> None:
        """save_session_state accepts dict as metadata."""

        class MockConsoul:
            model_name = "gpt-4o"
            temperature = 0.7

            class History:
                @staticmethod
                def get_messages_as_dicts() -> list[dict[str, str]]:
                    return []

            history = History()

        console = MockConsoul()
        console.session_id = "test123"  # type: ignore[attr-defined]

        state = save_session_state(
            console,  # type: ignore[arg-type]
            metadata={"user_id": "bob", "custom": {"key": "value"}},
        )

        assert state["metadata"]["user_id"] == "bob"
        assert state["metadata"]["custom"]["key"] == "value"


class TestRestoreMetadata:
    """Test that restore_session correctly restores metadata."""

    def test_restore_attaches_metadata(self) -> None:
        """restore_session attaches metadata to console._session_metadata."""
        state = {
            "session_id": "test123",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "metadata": {
                "user_id": "alice",
                "tenant_id": "acme",
                "namespace": "acme:alice:",
                "tags": ["vip", "beta"],
                "custom": {"plan": "enterprise"},
                "schema_version": "1.0",
            },
        }

        console = restore_session(state)

        # Check metadata was restored
        assert hasattr(console, "_session_metadata")
        metadata = console._session_metadata  # type: ignore[attr-defined]

        assert isinstance(metadata, SessionMetadata)
        assert metadata.user_id == "alice"
        assert metadata.tenant_id == "acme"
        assert metadata.namespace == "acme:alice:"
        assert metadata.tags == ["vip", "beta"]
        assert metadata.custom["plan"] == "enterprise"

    def test_restore_without_metadata(self) -> None:
        """restore_session works when state has no metadata."""
        state = {
            "session_id": "test123",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
        }

        console = restore_session(state)

        # Should not have metadata attribute (or it should be None)
        # After create_session with no user_id/tenant_id, metadata should be None
        # since we didn't pass user_id or tenant_id
        # Actually, in this case restore calls create_session which may not set it
        # Just verify it doesn't crash and metadata is None or not set
        assert console is not None
        assert getattr(console, "_session_metadata", None) is None

    def test_full_round_trip(self) -> None:
        """Test complete save -> restore -> save cycle preserves metadata."""

        class MockConsoul:
            model_name = "gpt-4o"
            temperature = 0.7

            class History:
                @staticmethod
                def get_messages_as_dicts() -> list[dict[str, str]]:
                    return [{"role": "user", "content": "Hello"}]

            history = History()

        # Create initial state with metadata
        console = MockConsoul()
        console.session_id = "test123"  # type: ignore[attr-defined]
        console._session_metadata = SessionMetadata(  # type: ignore[attr-defined]
            user_id="alice",
            tenant_id="acme",
            tags=["original"],
            custom={"key": "value"},
        )

        # Save
        state1 = save_session_state(console)  # type: ignore[arg-type]

        # Restore
        restored = restore_session(state1)

        # Verify metadata survived
        assert hasattr(restored, "_session_metadata")
        metadata = restored._session_metadata  # type: ignore[attr-defined]
        assert metadata.user_id == "alice"
        assert metadata.tenant_id == "acme"
        assert metadata.tags == ["original"]
        assert metadata.custom["key"] == "value"

    def test_metadata_with_partial_fields(self) -> None:
        """restore_session handles partial metadata correctly."""
        state = {
            "session_id": "test123",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "metadata": {
                "user_id": "alice",
                # Missing tenant_id, namespace, tags, custom
            },
        }

        console = restore_session(state)

        metadata = console._session_metadata  # type: ignore[attr-defined]
        assert metadata.user_id == "alice"
        assert metadata.tenant_id is None
        assert metadata.namespace is None
        assert metadata.tags == []
        assert metadata.custom == {}

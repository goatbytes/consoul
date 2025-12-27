"""Tests for SessionHooks and HookedSessionStore."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from consoul.sdk.session_store import HookedSessionStore, MemorySessionStore


class TestHookedSessionStoreSave:
    """Test HookedSessionStore.save() behavior."""

    def test_save_without_hooks(self) -> None:
        """Save works without any hooks."""
        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[])

        store.save("test123", {"messages": [{"role": "user", "content": "hi"}]})

        loaded = base_store.load("test123")
        assert loaded is not None
        assert loaded["messages"][0]["content"] == "hi"

    def test_on_before_save_transforms_state(self) -> None:
        """on_before_save can transform state."""

        class TransformHook:
            def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                return {**state, "transformed": True}

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[TransformHook()])

        store.save("test123", {"messages": []})

        loaded = base_store.load("test123")
        assert loaded is not None
        assert loaded["transformed"] is True

    def test_on_after_save_called(self) -> None:
        """on_after_save is called after save."""
        calls: list[tuple[str, dict[str, Any]]] = []

        class AuditHook:
            def on_after_save(self, session_id: str, state: dict[str, Any]) -> None:
                calls.append((session_id, state))

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[AuditHook()])

        store.save("test123", {"messages": []})

        assert len(calls) == 1
        assert calls[0][0] == "test123"

    def test_hooks_applied_in_order(self) -> None:
        """on_before_save hooks applied in order."""
        order: list[str] = []

        class FirstHook:
            def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                order.append("first")
                return {**state, "first": True}

        class SecondHook:
            def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                order.append("second")
                return {**state, "second": True}

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[FirstHook(), SecondHook()])

        store.save("test123", {"messages": []})

        assert order == ["first", "second"]

    def test_on_before_save_error_aborts_save(self) -> None:
        """Error in on_before_save aborts the save."""

        class FailingHook:
            def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                raise ValueError("Hook failed")

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[FailingHook()])

        with pytest.raises(ValueError, match="Hook failed"):
            store.save("test123", {"messages": []})

        # Verify nothing was saved
        assert base_store.load("test123") is None

    def test_on_after_save_error_does_not_fail_save(self) -> None:
        """Error in on_after_save is logged but save succeeds."""

        class FailingAfterHook:
            def on_after_save(self, session_id: str, state: dict[str, Any]) -> None:
                raise ValueError("After hook failed")

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[FailingAfterHook()])

        # Should not raise
        store.save("test123", {"messages": []})

        # Save should have succeeded
        assert base_store.load("test123") is not None


class TestHookedSessionStoreLoad:
    """Test HookedSessionStore.load() behavior."""

    def test_load_without_hooks(self) -> None:
        """Load works without any hooks."""
        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[])
        loaded = store.load("test123")

        assert loaded is not None

    def test_on_after_load_transforms_state(self) -> None:
        """on_after_load can transform state."""

        class DecryptHook:
            def on_after_load(
                self, session_id: str, state: dict[str, Any] | None
            ) -> dict[str, Any] | None:
                if state is None:
                    return None
                return {**state, "decrypted": True}

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[DecryptHook()])
        loaded = store.load("test123")

        assert loaded is not None
        assert loaded["decrypted"] is True

    def test_hooks_applied_in_reverse_order(self) -> None:
        """on_after_load hooks applied in reverse order."""
        order: list[str] = []

        class FirstHook:
            def on_after_load(
                self, session_id: str, state: dict[str, Any] | None
            ) -> dict[str, Any] | None:
                order.append("first")
                return state

        class SecondHook:
            def on_after_load(
                self, session_id: str, state: dict[str, Any] | None
            ) -> dict[str, Any] | None:
                order.append("second")
                return state

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[FirstHook(), SecondHook()])
        store.load("test123")

        # Reverse order for unwrapping
        assert order == ["second", "first"]

    def test_on_after_load_returning_none_propagates(self) -> None:
        """on_after_load returning None propagates as not found."""

        class FilterHook:
            def on_after_load(
                self, session_id: str, state: dict[str, Any] | None
            ) -> dict[str, Any] | None:
                # Pretend session is filtered out
                return None

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[FilterHook()])
        loaded = store.load("test123")

        assert loaded is None


class TestHookedSessionStoreDelete:
    """Test HookedSessionStore.delete() behavior."""

    def test_delete_without_hooks(self) -> None:
        """Delete works without any hooks."""
        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[])
        store.delete("test123")

        assert base_store.load("test123") is None

    def test_on_before_delete_called(self) -> None:
        """on_before_delete is called before delete."""
        calls: list[str] = []

        class DeleteHook:
            def on_before_delete(self, session_id: str) -> None:
                calls.append(f"before:{session_id}")

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[DeleteHook()])
        store.delete("test123")

        assert calls == ["before:test123"]

    def test_on_after_delete_called(self) -> None:
        """on_after_delete is called after delete."""
        calls: list[str] = []

        class DeleteHook:
            def on_after_delete(self, session_id: str) -> None:
                calls.append(f"after:{session_id}")

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[DeleteHook()])
        store.delete("test123")

        assert calls == ["after:test123"]

    def test_on_before_delete_error_aborts_delete(self) -> None:
        """Error in on_before_delete aborts the delete."""

        class FailingHook:
            def on_before_delete(self, session_id: str) -> None:
                raise ValueError("Cannot delete")

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[FailingHook()])

        with pytest.raises(ValueError, match="Cannot delete"):
            store.delete("test123")

        # Session should still exist
        assert base_store.load("test123") is not None

    def test_on_after_delete_error_does_not_fail_delete(self) -> None:
        """Error in on_after_delete is logged but delete succeeds."""

        class FailingAfterHook:
            def on_after_delete(self, session_id: str) -> None:
                raise ValueError("After delete failed")

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[FailingAfterHook()])

        # Should not raise
        store.delete("test123")

        # Delete should have succeeded
        assert base_store.load("test123") is None


class TestPartialHookImplementation:
    """Test that hooks can implement only some methods."""

    def test_hook_with_only_on_before_save(self) -> None:
        """Hook with only on_before_save works."""

        class BeforeSaveOnlyHook:
            def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                return {**state, "modified": True}

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[BeforeSaveOnlyHook()])

        # Should work without on_after_save or on_after_load
        store.save("test123", {"messages": []})
        loaded = store.load("test123")

        assert loaded is not None
        assert loaded["modified"] is True

    def test_hook_with_only_on_after_save(self) -> None:
        """Hook with only on_after_save works."""
        calls: list[str] = []

        class AfterSaveOnlyHook:
            def on_after_save(self, session_id: str, state: dict[str, Any]) -> None:
                calls.append(session_id)

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[AfterSaveOnlyHook()])

        store.save("test123", {"messages": []})

        assert calls == ["test123"]

    def test_hook_with_only_on_after_load(self) -> None:
        """Hook with only on_after_load works."""

        class AfterLoadOnlyHook:
            def on_after_load(
                self, session_id: str, state: dict[str, Any] | None
            ) -> dict[str, Any] | None:
                if state:
                    return {**state, "loaded": True}
                return state

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[AfterLoadOnlyHook()])
        loaded = store.load("test123")

        assert loaded is not None
        assert loaded["loaded"] is True

    def test_hook_with_only_delete_hooks(self) -> None:
        """Hook with only delete hooks works."""
        calls: list[str] = []

        class DeleteOnlyHook:
            def on_before_delete(self, session_id: str) -> None:
                calls.append(f"before:{session_id}")

            def on_after_delete(self, session_id: str) -> None:
                calls.append(f"after:{session_id}")

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[DeleteOnlyHook()])

        # Save and load should work
        store.save("another", {"messages": []})
        store.load("test123")

        # Delete should trigger hooks
        store.delete("test123")

        assert calls == ["before:test123", "after:test123"]

    def test_empty_hook_class(self) -> None:
        """Hook with no methods works (no-op)."""

        class EmptyHook:
            pass

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[EmptyHook()])

        # All operations should work
        store.save("test123", {"messages": []})
        loaded = store.load("test123")
        store.delete("test123")

        # Just verify it didn't crash
        assert loaded is not None


class TestAsyncHooks:
    """Test that async hooks are handled correctly."""

    def test_async_on_before_save(self) -> None:
        """Async on_before_save is awaited."""

        class AsyncHook:
            async def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                await asyncio.sleep(0.001)  # Simulate async work
                return {**state, "async_modified": True}

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[AsyncHook()])

        store.save("test123", {"messages": []})
        loaded = base_store.load("test123")

        assert loaded is not None
        assert loaded["async_modified"] is True

    def test_async_on_after_load(self) -> None:
        """Async on_after_load is awaited."""

        class AsyncHook:
            async def on_after_load(
                self, session_id: str, state: dict[str, Any] | None
            ) -> dict[str, Any] | None:
                await asyncio.sleep(0.001)
                if state:
                    return {**state, "async_loaded": True}
                return state

        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[AsyncHook()])
        loaded = store.load("test123")

        assert loaded is not None
        assert loaded["async_loaded"] is True

    def test_mixed_sync_async_hooks(self) -> None:
        """Mix of sync and async hooks works."""
        order: list[str] = []

        class SyncHook:
            def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                order.append("sync")
                return state

        class AsyncHook:
            async def on_before_save(
                self, session_id: str, state: dict[str, Any]
            ) -> dict[str, Any]:
                order.append("async")
                return state

        base_store = MemorySessionStore()
        store = HookedSessionStore(base_store, hooks=[SyncHook(), AsyncHook()])

        store.save("test123", {"messages": []})

        assert order == ["sync", "async"]


class TestHookedSessionStoreDelegation:
    """Test that other methods delegate to underlying store."""

    def test_exists_delegates(self) -> None:
        """exists() delegates to underlying store."""
        base_store = MemorySessionStore()
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[])

        assert store.exists("test123") is True
        assert store.exists("nonexistent") is False

    def test_cleanup_delegates(self) -> None:
        """cleanup() delegates to underlying store."""
        base_store = MemorySessionStore(ttl=0)  # Immediate expiry
        base_store.save("test123", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[])

        # Wait a tiny bit for expiry
        import time

        time.sleep(0.01)

        cleaned = store.cleanup()
        assert cleaned == 1

    def test_list_sessions_delegates(self) -> None:
        """list_sessions() delegates to underlying store."""
        base_store = MemorySessionStore()
        base_store.save("alice:conv1", {"messages": []})
        base_store.save("alice:conv2", {"messages": []})
        base_store.save("bob:conv1", {"messages": []})

        store = HookedSessionStore(base_store, hooks=[])

        all_sessions = store.list_sessions()
        assert len(all_sessions) == 3

        alice_sessions = store.list_sessions(namespace="alice:")
        assert len(alice_sessions) == 2

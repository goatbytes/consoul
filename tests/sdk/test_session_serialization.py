"""Tests for safe session state serialization and restoration.

Tests verify that session state can be safely serialized to JSON without
RCE vulnerabilities (no pickle), restored correctly, and works with various
storage backends.
"""

import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from consoul.sdk import (
    create_session,
    restore_session,
    save_session_state,
)
from consoul.sdk.session_store import (
    FileSessionStore,
    MemorySessionStore,
    RedisSessionStore,
)


class TestSessionStateSerialization:
    """Test session state save/restore functionality."""

    def test_save_session_state_basic(self):
        """Test basic session state extraction."""
        console = create_session(session_id="test123", model="gpt-4o", temperature=0.7)

        # Add some conversation history
        console.chat("Hello!")  # This will add user + assistant messages

        # Extract state
        state = save_session_state(console)

        # Verify structure
        assert isinstance(state, dict)
        assert state["session_id"] == "test123"
        assert state["model"] == "gpt-4o"
        assert state["temperature"] == 0.7
        assert "messages" in state
        assert "created_at" in state
        assert "updated_at" in state
        assert "config" in state

        # Verify messages are serializable
        assert isinstance(state["messages"], list)
        assert len(state["messages"]) >= 2  # At least user + assistant

    def test_save_session_state_json_serializable(self):
        """Test that saved state is JSON-serializable (no pickle)."""
        console = create_session(session_id="test456", model="gpt-4o")
        console.chat("Test message")

        state = save_session_state(console)

        # Should not raise
        json_str = json.dumps(state)
        assert isinstance(json_str, str)

        # Should round-trip correctly
        restored_dict = json.loads(json_str)
        assert restored_dict["session_id"] == "test456"
        assert restored_dict["model"] == "gpt-4o"

    def test_save_session_state_no_executable_code(self):
        """Test that saved state contains no executable code."""
        console = create_session(session_id="test789", model="gpt-4o")
        console.chat("Sensitive command")

        state = save_session_state(console)
        json_str = json.dumps(state)

        # Verify no pickle/exec/eval in JSON
        assert b"pickle" not in json_str.encode()
        assert "__reduce__" not in json_str
        assert "exec" not in json_str
        assert "eval" not in json_str
        assert "__import__" not in json_str

    def test_restore_session_basic(self):
        """Test basic session restoration."""
        # Create and save session
        console = create_session(
            session_id="test_restore", model="gpt-4o", temperature=0.8
        )
        console.chat("Original message")

        state = save_session_state(console)

        # Restore session
        restored = restore_session(state)

        # Verify configuration restored
        assert restored.model_name == "gpt-4o"
        assert restored.temperature == 0.8

        # Verify conversation history restored
        messages = restored.history.get_messages_as_dicts()
        assert len(messages) >= 2  # User + assistant
        assert any("Original message" in msg.get("content", "") for msg in messages)

    def test_restore_session_preserves_context(self):
        """Test that restored session preserves conversation context."""
        # Create session with multi-turn conversation
        console = create_session(session_id="context_test", model="gpt-4o")
        console.chat("My name is Alice")
        console.chat("What is my name?")

        # Save and restore
        state = save_session_state(console)
        restored = restore_session(state)

        # Verify full history preserved
        original_messages = console.history.get_messages_as_dicts()
        restored_messages = restored.history.get_messages_as_dicts()

        assert len(restored_messages) == len(original_messages)
        assert any("Alice" in msg.get("content", "") for msg in restored_messages)

    def test_restore_session_missing_fields(self):
        """Test that restore fails with missing required fields."""
        incomplete_state = {
            "session_id": "test",
            "model": "gpt-4o",
            # Missing temperature and messages
        }

        with pytest.raises(ValueError, match="Missing required field"):
            restore_session(incomplete_state)

    def test_save_restore_round_trip(self):
        """Test complete save/restore round trip."""
        # Create session
        console = create_session(
            session_id="round_trip", model="gpt-4o", temperature=0.5
        )
        console.chat("Test conversation")

        # Save
        state = save_session_state(console)

        # Restore
        restored = restore_session(state)

        # Chat with restored session
        response = restored.chat("Continue conversation")
        assert isinstance(response, str)

        # Verify history continuity
        messages = restored.history.get_messages_as_dicts()
        assert len(messages) >= 4  # Original user+assistant + new user+assistant

    def test_restore_session_no_duplicate_system_prompt(self):
        """Test that restoring a session doesn't duplicate the system prompt.

        This is a critical regression test for the bug where restore_session()
        was passing system_prompt to create_session() AND restoring it from
        saved messages, causing duplicate system messages.
        """
        # Create session with explicit system prompt
        console = create_session(
            session_id="system_test",
            model="gpt-4o",
            system_prompt="You are a helpful assistant.",
        )
        console.chat("Hello!")

        # Get original message count
        original_messages = console.history.get_messages_as_dicts()
        original_count = len(original_messages)

        # Count system messages in original
        original_system_count = sum(
            1 for msg in original_messages if msg.get("role") == "system"
        )

        # Save state
        state = save_session_state(console)

        # Restore session
        restored = restore_session(state)

        # Get restored messages
        restored_messages = restored.history.get_messages_as_dicts()
        restored_count = len(restored_messages)

        # Count system messages in restored session
        restored_system_count = sum(
            1 for msg in restored_messages if msg.get("role") == "system"
        )

        # Verify no duplication
        assert restored_count == original_count, (
            f"Message count changed after restore: {original_count} -> {restored_count}"
        )
        assert restored_system_count == original_system_count, (
            f"System message count changed: {original_system_count} -> {restored_system_count}. "
            "This indicates system prompt duplication!"
        )

        # Verify exact message content matches
        for i, (orig, rest) in enumerate(
            zip(original_messages, restored_messages, strict=True)
        ):
            assert orig["role"] == rest["role"], (
                f"Message {i} role mismatch: {orig['role']} != {rest['role']}"
            )
            assert orig["content"] == rest["content"], f"Message {i} content mismatch"

    def test_restore_session_preserves_system_prompt_metadata(self):
        """Test that restored sessions preserve system prompt metadata.

        This is a regression test for the bug where restore_session() was
        restoring the conversation history but not setting _explicit_system_prompt,
        causing operations like clear() to lose the original system prompt.
        """
        # Create session with explicit system prompt
        original_prompt = "You are a specialized AI assistant."
        console = create_session(
            session_id="metadata_test",
            model="gpt-4o",
            system_prompt=original_prompt,
        )
        console.chat("Hello!")

        # Verify original has the system prompt metadata
        assert hasattr(console, "_explicit_system_prompt")
        assert console._explicit_system_prompt == original_prompt

        # Save state
        state = save_session_state(console)

        # Verify system prompt is in saved config
        assert "config" in state
        assert state["config"].get("system_prompt") == original_prompt

        # Restore session
        restored = restore_session(state)

        # Verify system prompt metadata is restored
        assert hasattr(restored, "_explicit_system_prompt")
        assert restored._explicit_system_prompt == original_prompt, (
            "System prompt metadata was not restored! "
            "This will break operations like clear() that rely on _explicit_system_prompt."
        )

        # Verify clear() would work correctly (it should re-add the system prompt)
        # Don't actually call clear() in the test since it requires a model call,
        # but verify the metadata is there for it to use
        assert restored._explicit_system_prompt is not None

    def test_restore_session_preserves_tools_enabled(self):
        """Test that restored sessions preserve tools_enabled state.

        This is a regression test for the bug where restore_session() was
        hard-coding tools=False, causing tool-enabled sessions to lose that
        capability after restoration.
        """
        # Create session WITH tools enabled
        console_with_tools = create_session(
            session_id="tools_test",
            model="gpt-4o",
            tools=True,  # Enable tools
        )

        # Verify tools are enabled
        assert hasattr(console_with_tools, "tools_enabled")
        assert console_with_tools.tools_enabled is True

        # Save state
        state = save_session_state(console_with_tools)

        # Verify tools_enabled is in saved config
        assert "config" in state
        assert state["config"].get("tools_enabled") is True

        # Restore session (without explicit tools parameter)
        restored = restore_session(state)

        # Verify tools are still enabled after restore
        assert hasattr(restored, "tools_enabled")
        assert restored.tools_enabled is True, (
            "Tools were disabled after restore! "
            "This breaks tool-enabled sessions after persistence."
        )

    def test_restore_session_preserves_tools_disabled(self):
        """Test that sessions without tools stay that way after restore."""
        # Create session WITHOUT tools
        console_no_tools = create_session(
            session_id="no_tools_test",
            model="gpt-4o",
            tools=False,
        )

        # Verify tools are disabled
        assert console_no_tools.tools_enabled is False

        # Save state
        state = save_session_state(console_no_tools)

        # Verify tools_enabled is False in saved config
        assert state["config"].get("tools_enabled") is False

        # Restore session
        restored = restore_session(state)

        # Verify tools are still disabled
        assert restored.tools_enabled is False

    def test_restore_session_tools_override(self):
        """Test that tools parameter can override saved state."""
        # Create session with tools enabled
        console = create_session(
            session_id="override_test",
            model="gpt-4o",
            tools=True,
        )

        state = save_session_state(console)
        assert state["config"]["tools_enabled"] is True

        # Restore with explicit tools=False (override)
        restored_disabled = restore_session(state, tools=False)
        assert restored_disabled.tools_enabled is False

        # Restore with explicit tools=True (confirm saved state)
        restored_enabled = restore_session(state, tools=True)
        assert restored_enabled.tools_enabled is True

        # Restore with specific tools list (override)
        restored_specific = restore_session(state, tools=["search"])
        assert restored_specific.tools_enabled is True

    def test_restore_session_preserves_summarization_config(self):
        """Test that summarization configuration is preserved across restore.

        This is a regression test for the bug where restore_session() was
        omitting summarization settings, causing restored sessions to lose
        important context management configuration.
        """
        # Create session with custom summarization settings
        console = create_session(
            session_id="summarize_test",
            model="gpt-4o",
            summarize=True,
            summarize_threshold=30,
            keep_recent=15,
            summary_model="gpt-4o-mini",
        )

        # Verify original settings
        assert hasattr(console, "_summarize")
        assert console._summarize is True
        assert console._summarize_threshold == 30
        assert console._keep_recent == 15
        assert console._summary_model == "gpt-4o-mini"

        # Save state
        state = save_session_state(console)

        # Verify summarization config is saved
        config = state["config"]
        assert config.get("summarize") is True
        assert config.get("summarize_threshold") == 30
        assert config.get("keep_recent") == 15
        assert config.get("summary_model") == "gpt-4o-mini"

        # Restore session
        restored = restore_session(state)

        # Verify all summarization settings are restored
        assert restored._summarize is True, (
            "Summarization was not restored! "
            "Sessions will lose context management after restore."
        )
        assert restored._summarize_threshold == 30, (
            "Summarization threshold not restored"
        )
        assert restored._keep_recent == 15, "keep_recent not restored"
        assert restored._summary_model == "gpt-4o-mini", "summary_model not restored"

    def test_restore_session_default_summarization(self):
        """Test that sessions without summarization restore correctly."""
        # Create session without summarization (defaults)
        console = create_session(
            session_id="no_summarize_test",
            model="gpt-4o",
            # summarize defaults to False
        )

        # Save and restore
        state = save_session_state(console)
        restored = restore_session(state)

        # Verify defaults are maintained
        assert restored._summarize is False
        assert restored._summarize_threshold == 20  # Default
        assert restored._keep_recent == 10  # Default
        assert restored._summary_model is None  # Default

    def test_restore_session_complete_config_equivalence(self):
        """Test that restored session is functionally equivalent to original.

        This comprehensive test verifies that ALL configuration is preserved,
        ensuring no silent behavioral changes after save/restore.
        """
        # Create session with comprehensive configuration
        console = create_session(
            session_id="complete_test",
            model="gpt-4o",
            temperature=0.8,
            system_prompt="You are a helpful assistant.",
            tools=True,
            summarize=True,
            summarize_threshold=25,
            keep_recent=12,
            summary_model="gpt-4o-mini",
        )

        console.chat("Test message")

        # Save state
        state = save_session_state(console)

        # Restore session
        restored = restore_session(state)

        # Verify ALL configuration matches
        assert restored.model_name == console.model_name
        assert restored.temperature == console.temperature
        assert restored._explicit_system_prompt == console._explicit_system_prompt
        assert restored.tools_enabled == console.tools_enabled
        assert restored._summarize == console._summarize
        assert restored._summarize_threshold == console._summarize_threshold
        assert restored._keep_recent == console._keep_recent
        assert restored._summary_model == console._summary_model

        # Verify conversation history matches
        original_messages = console.history.get_messages_as_dicts()
        restored_messages = restored.history.get_messages_as_dicts()
        assert len(original_messages) == len(restored_messages)

        print("✅ Restored session is functionally equivalent to original")

    def test_restore_session_accepts_dict(self):
        """Test that restore_session accepts dict (typical usage)."""
        console = create_session(session_id="dict_test", model="gpt-4o")
        console.chat("Hello")

        # Save as dict
        state_dict = save_session_state(console)
        assert isinstance(state_dict, dict)

        # Restore from dict (should work)
        restored = restore_session(state_dict)
        assert restored.model_name == "gpt-4o"

    def test_restore_session_accepts_session_state(self):
        """Test that restore_session accepts SessionState instance.

        This verifies the documented workflow from SessionState docstring works.
        """
        from consoul.sdk.models import SessionState

        console = create_session(session_id="model_test", model="gpt-4o")
        console.chat("Hello")

        # Save as dict
        state_dict = save_session_state(console)

        # Convert to SessionState instance (as shown in docs)
        state = SessionState.from_dict(state_dict)
        assert isinstance(state, SessionState)

        # Restore from SessionState instance (should work per docs)
        restored = restore_session(state)
        assert restored.model_name == "gpt-4o"

    def test_restore_session_rejects_invalid_type(self):
        """Test that restore_session raises TypeError for invalid types."""
        import pytest

        # Try to restore with invalid type (string)
        with pytest.raises(TypeError, match="state must be a dict or SessionState"):
            restore_session("invalid")

        # Try with None
        with pytest.raises(TypeError, match="state must be a dict or SessionState"):
            restore_session(None)

        # Try with list
        with pytest.raises(TypeError, match="state must be a dict or SessionState"):
            restore_session([])


class TestMemorySessionStore:
    """Test in-memory session storage."""

    def test_memory_store_save_load(self):
        """Test basic save/load operations."""
        store = MemorySessionStore()

        state = {
            "session_id": "user123",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        # Save
        store.save("user123", state)

        # Load
        loaded = store.load("user123")
        assert loaded is not None
        assert loaded["session_id"] == "user123"
        assert loaded["model"] == "gpt-4o"

    def test_memory_store_ttl_expiration(self):
        """Test TTL-based session expiration."""
        store = MemorySessionStore(ttl=0.1)  # 100ms TTL

        state = {
            "session_id": "expire_test",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        store.save("expire_test", state)

        # Should exist immediately
        assert store.exists("expire_test")

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        assert not store.exists("expire_test")
        assert store.load("expire_test") is None

    def test_memory_store_cleanup(self):
        """Test cleanup of expired sessions."""
        store = MemorySessionStore(ttl=0.1)

        # Create multiple sessions
        for i in range(5):
            state = {
                "session_id": f"session_{i}",
                "model": "gpt-4o",
                "temperature": 0.7,
                "messages": [],
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            store.save(f"session_{i}", state)

        # Wait for expiration
        time.sleep(0.15)

        # Cleanup
        count = store.cleanup()
        assert count == 5

    def test_memory_store_delete(self):
        """Test session deletion."""
        store = MemorySessionStore()

        state = {
            "session_id": "delete_test",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        store.save("delete_test", state)
        assert store.exists("delete_test")

        store.delete("delete_test")
        assert not store.exists("delete_test")

    def test_memory_store_thread_safety(self):
        """Test concurrent access to memory store."""
        store = MemorySessionStore()
        errors = []

        def worker(session_id: str):
            try:
                state = {
                    "session_id": session_id,
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "messages": [],
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }
                store.save(session_id, state)
                loaded = store.load(session_id)
                assert loaded is not None
                store.delete(session_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(f"session_{i}",)) for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_memory_store_non_serializable_raises(self):
        """Test that non-JSON-serializable data raises error."""
        store = MemorySessionStore()

        # Create state with non-serializable object
        bad_state = {
            "session_id": "bad",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "callback": lambda x: x,  # Not JSON-serializable
        }

        with pytest.raises(ValueError, match="JSON-serializable"):
            store.save("bad", bad_state)


class TestFileSessionStore:
    """Test file-based session storage."""

    def test_file_store_save_load(self):
        """Test basic file save/load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)

            state = {
                "session_id": "file_test",
                "model": "gpt-4o",
                "temperature": 0.7,
                "messages": [],
                "created_at": time.time(),
                "updated_at": time.time(),
            }

            store.save("file_test", state)

            # Verify file exists (filename is Base64-encoded)
            import base64

            expected_filename = (
                base64.urlsafe_b64encode(b"file_test").decode().rstrip("=") + ".json"
            )
            session_file = Path(tmpdir) / expected_filename
            assert session_file.exists()

            # Load
            loaded = store.load("file_test")
            assert loaded is not None
            assert loaded["session_id"] == "file_test"

    def test_file_store_persistence(self):
        """Test that files persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save with first store instance
            store1 = FileSessionStore(tmpdir)
            state = {
                "session_id": "persist_test",
                "model": "gpt-4o",
                "temperature": 0.7,
                "messages": [{"role": "user", "content": "Hello"}],
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            store1.save("persist_test", state)

            # Load with second store instance
            store2 = FileSessionStore(tmpdir)
            loaded = store2.load("persist_test")

            assert loaded is not None
            assert loaded["session_id"] == "persist_test"
            assert len(loaded["messages"]) == 1

    def test_file_store_ttl_expiration(self):
        """Test file-based TTL expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir, ttl=0.1)

            state = {
                "session_id": "file_expire",
                "model": "gpt-4o",
                "temperature": 0.7,
                "messages": [],
                "created_at": time.time(),
                "updated_at": time.time(),
            }

            store.save("file_expire", state)
            assert store.exists("file_expire")

            # Wait for expiration
            time.sleep(0.15)

            # Should be expired
            assert not store.exists("file_expire")

    def test_file_store_cleanup(self):
        """Test cleanup of expired files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir, ttl=0.1)

            # Create multiple sessions
            for i in range(3):
                state = {
                    "session_id": f"cleanup_{i}",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "messages": [],
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }
                store.save(f"cleanup_{i}", state)

            # Wait for expiration
            time.sleep(0.15)

            # Cleanup
            count = store.cleanup()
            assert count == 3

            # Verify files deleted
            files = list(Path(tmpdir).glob("*.json"))
            assert len(files) == 0

    def test_file_store_invalid_json(self):
        """Test handling of corrupted JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)

            # Create corrupt JSON file
            corrupt_file = Path(tmpdir) / "corrupt.json"
            corrupt_file.write_text("{ invalid json }")

            # Should return None for corrupt file
            loaded = store.load("corrupt")
            assert loaded is None

    def test_file_store_uses_base64_filenames(self):
        """Test that session files use URL-safe Base64 encoded filenames (SOUL-351)."""
        import base64

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)

            # Session ID with special characters
            session_id = "alice:conv1"
            store.save(session_id, {"messages": []})

            # Filename should be Base64-encoded
            expected_encoded = (
                base64.urlsafe_b64encode(session_id.encode("utf-8"))
                .decode("ascii")
                .rstrip("=")
            )
            expected_path = Path(tmpdir) / f"{expected_encoded}.json"

            assert expected_path.exists(), (
                f"Expected Base64 filename {expected_path.name} not found"
            )

            # Old sanitized filename should NOT exist
            old_sanitized = "aliceconv1.json"
            old_path = Path(tmpdir) / old_sanitized
            assert not old_path.exists(), (
                f"Old sanitized filename {old_sanitized} should not exist"
            )


class TestSessionStateModel:
    """Test SessionState model."""

    def test_session_state_to_dict(self):
        """Test SessionState.to_dict()."""
        from consoul.sdk.models import SessionState

        state = SessionState(
            session_id="test",
            model="gpt-4o",
            temperature=0.7,
            messages=[],
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={"key": "value"},
        )

        state_dict = state.to_dict()

        assert state_dict["session_id"] == "test"
        assert state_dict["model"] == "gpt-4o"
        assert state_dict["temperature"] == 0.7
        assert state_dict["config"]["key"] == "value"

    def test_session_state_from_dict(self):
        """Test SessionState.from_dict()."""
        from consoul.sdk.models import SessionState

        state_dict = {
            "session_id": "test",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "created_at": 1234567890.0,
            "updated_at": 1234567890.0,
            "config": {"key": "value"},
        }

        state = SessionState.from_dict(state_dict)

        assert state.session_id == "test"
        assert state.model == "gpt-4o"
        assert state.temperature == 0.7
        assert state.config["key"] == "value"

    def test_session_state_from_dict_missing_fields(self):
        """Test that from_dict raises on missing fields."""
        from consoul.sdk.models import SessionState

        incomplete = {
            "session_id": "test",
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Missing required field"):
            SessionState.from_dict(incomplete)


class TestConversationHistoryRestore:
    """Test ConversationHistory.restore_from_dicts()."""

    def test_restore_from_dicts_basic(self):
        """Test basic message restoration."""
        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        message_dicts = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        history.restore_from_dicts(message_dicts)

        assert len(history) == 2
        messages = history.get_messages_as_dicts()
        assert messages[0]["content"] == "Hello!"
        assert messages[1]["content"] == "Hi there!"

    def test_restore_from_dicts_preserves_all_metadata(self):
        """Test that all AIMessage metadata is preserved during round-trip.

        This is a regression test for the bug where restore_from_dicts() was
        only restoring content and tool_calls, discarding additional_kwargs
        (function_call), name, response_metadata, etc.
        """
        from langchain_core.messages import AIMessage

        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        # Add message with comprehensive metadata
        ai_msg = AIMessage(
            content="Let me call a function",
            name="assistant_agent",
            id="msg_123",
            tool_calls=[
                {"id": "call_1", "name": "get_weather", "args": {"city": "SF"}}
            ],
            additional_kwargs={
                "function_call": {"name": "get_weather", "arguments": '{"city":"SF"}'}
            },
            response_metadata={"model": "gpt-4o", "finish_reason": "function_call"},
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 15,
                "total_tokens": 25,
            },
        )
        history.messages.append(ai_msg)

        # Convert to dicts
        message_dicts = history.get_messages_as_dicts()

        # Create new history and restore
        new_history = ConversationHistory("gpt-4o")
        new_history.restore_from_dicts(message_dicts)

        # Verify all metadata was preserved
        restored_msg = new_history.messages[0]
        assert isinstance(restored_msg, AIMessage)
        assert restored_msg.content == "Let me call a function"
        assert restored_msg.name == "assistant_agent"
        assert restored_msg.id == "msg_123"
        assert len(restored_msg.tool_calls) == 1
        assert restored_msg.tool_calls[0]["name"] == "get_weather"
        assert "function_call" in restored_msg.additional_kwargs, (
            "additional_kwargs not preserved! This breaks OpenAI function calling."
        )
        assert restored_msg.additional_kwargs["function_call"]["name"] == "get_weather"
        assert restored_msg.response_metadata.get("model") == "gpt-4o"
        assert restored_msg.response_metadata.get("finish_reason") == "function_call"
        assert restored_msg.usage_metadata is not None

    def test_restore_from_dicts_openai_function_calling(self):
        """Test that OpenAI function calling format is preserved."""
        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        # Simulate OpenAI function calling response
        message_dicts = [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "content": "",
                "additional_kwargs": {
                    "function_call": {
                        "name": "get_weather",
                        "arguments": '{"location": "San Francisco"}',
                    }
                },
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "name": "get_weather",
                        "args": {"location": "San Francisco"},
                    }
                ],
            },
        ]

        history.restore_from_dicts(message_dicts)

        # Verify function_call is preserved
        ai_msg = history.messages[1]
        assert "additional_kwargs" in history.get_messages_as_dicts()[1]
        assert hasattr(ai_msg, "additional_kwargs")
        assert "function_call" in ai_msg.additional_kwargs
        assert ai_msg.additional_kwargs["function_call"]["name"] == "get_weather"

    def test_restore_from_dicts_named_messages(self):
        """Test that message names are preserved for multi-agent scenarios."""
        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        message_dicts = [
            {"role": "user", "content": "Hello", "name": "user_alice"},
            {"role": "assistant", "content": "Hi", "name": "agent_bob"},
        ]

        history.restore_from_dicts(message_dicts)

        # Verify names are preserved
        assert history.messages[0].name == "user_alice"
        assert history.messages[1].name == "agent_bob"

        # Verify round-trip
        restored_dicts = history.get_messages_as_dicts()
        assert restored_dicts[0].get("name") == "user_alice"
        assert restored_dicts[1].get("name") == "agent_bob"

    def test_restore_from_dicts_with_tool_calls(self):
        """Test restoration with tool call metadata."""
        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        message_dicts = [
            {"role": "user", "content": "List files"},
            {
                "role": "assistant",
                "content": "Let me check...",
                "tool_calls": [
                    {"id": "call_123", "name": "bash", "args": {"command": "ls"}}
                ],
            },
            {
                "role": "tool",
                "content": "file1.txt\nfile2.txt",
                "tool_call_id": "call_123",
            },
        ]

        history.restore_from_dicts(message_dicts)

        assert len(history) == 3
        messages = history.get_messages()

        # Verify tool call preserved
        assert hasattr(messages[1], "tool_calls")
        assert len(messages[1].tool_calls) == 1

    def test_restore_from_dicts_invalid_role(self):
        """Test that invalid role raises error."""
        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        message_dicts = [
            {"role": "invalid_role", "content": "Test"},
        ]

        with pytest.raises(ValueError, match="Unknown message role"):
            history.restore_from_dicts(message_dicts)

    def test_restore_from_dicts_missing_fields(self):
        """Test that missing fields raise error."""
        from consoul.ai.history import ConversationHistory

        history = ConversationHistory("gpt-4o")

        message_dicts = [
            {"role": "user"},  # Missing content
        ]

        with pytest.raises(ValueError, match="must have 'role' and 'content'"):
            history.restore_from_dicts(message_dicts)


class TestIntegrationWithStore:
    """Integration tests with session stores."""

    def test_complete_workflow_memory_store(self):
        """Test complete save/restore workflow with MemorySessionStore."""
        store = MemorySessionStore(ttl=3600)

        # Create session and chat
        console = create_session(session_id="workflow_test", model="gpt-4o")
        console.chat("Hello!")

        # Save to store
        state = save_session_state(console)
        store.save("workflow_test", state)

        # Load from store
        loaded_state = store.load("workflow_test")
        assert loaded_state is not None

        # Restore session
        restored = restore_session(loaded_state)

        # Continue conversation
        restored.chat("Continue")

        # Verify history
        messages = restored.history.get_messages_as_dicts()
        assert len(messages) >= 4  # Original user+assistant + new user+assistant

    def test_complete_workflow_file_store(self):
        """Test complete save/restore workflow with FileSessionStore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir, ttl=3600)

            # Create session and chat
            console = create_session(session_id="file_workflow", model="gpt-4o")
            console.chat("Test message")

            # Save to store
            state = save_session_state(console)
            store.save("file_workflow", state)

            # Simulate server restart - new store instance
            store2 = FileSessionStore(tmpdir, ttl=3600)

            # Load from store
            loaded_state = store2.load("file_workflow")
            assert loaded_state is not None

            # Restore session
            restored = restore_session(loaded_state)

            # Verify conversation continues
            restored.chat("Another message")
            messages = restored.history.get_messages_as_dicts()
            assert any("Test message" in msg.get("content", "") for msg in messages)


@pytest.mark.skipif(True, reason="Redis integration test - requires Redis server")
class TestRedisSessionStore:
    """Test Redis-based session storage.

    Note: These tests require a running Redis server and are skipped by default.
    Run with: pytest -m redis
    """

    def test_redis_store_save_load(self):
        """Test Redis save/load operations."""
        import redis

        client = redis.Redis(host="localhost", port=6379, db=15)  # Use test DB
        store = RedisSessionStore(client, ttl=3600, prefix="test:session:")

        state = {
            "session_id": "redis_test",
            "model": "gpt-4o",
            "temperature": 0.7,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        # Save
        store.save("redis_test", state)

        # Load
        loaded = store.load("redis_test")
        assert loaded is not None
        assert loaded["session_id"] == "redis_test"

        # Cleanup
        store.delete("redis_test")

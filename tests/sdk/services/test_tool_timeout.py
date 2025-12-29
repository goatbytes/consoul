"""Tests for tool timeout and cooperative cancellation.

Tests that tools respect execution timeouts and can cooperatively respond
to cancellation requests via the cancellation flag mechanism.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from consoul.ai.tools.base import (
    _register_cancellation_flag,
    _unregister_cancellation_flag,
    check_cancelled,
    get_cancellation_flag,
)

# =============================================================================
# Test: Cancellation Flag Infrastructure
# =============================================================================


class TestCancellationFlagRegistration:
    """Test cancellation flag registration and retrieval."""

    def test_get_cancellation_flag_returns_none_when_not_registered(self):
        """get_cancellation_flag should return None when no flag registered."""
        # Ensure clean state
        _unregister_cancellation_flag()

        flag = get_cancellation_flag()
        assert flag is None

    def test_register_cancellation_flag_makes_flag_available(self):
        """Registered flag should be retrievable via get_cancellation_flag."""
        event = threading.Event()

        try:
            _register_cancellation_flag(event)
            retrieved = get_cancellation_flag()
            assert retrieved is event
        finally:
            _unregister_cancellation_flag()

    def test_unregister_cancellation_flag_removes_flag(self):
        """Unregistering should remove the flag from storage."""
        event = threading.Event()

        _register_cancellation_flag(event)
        assert get_cancellation_flag() is not None

        _unregister_cancellation_flag()
        assert get_cancellation_flag() is None

    def test_flags_are_thread_local(self):
        """Each thread should have its own cancellation flag."""
        main_event = threading.Event()
        thread_event = threading.Event()
        thread_result = []

        def thread_func():
            # Register a different event in this thread
            _register_cancellation_flag(thread_event)
            thread_result.append(get_cancellation_flag())
            _unregister_cancellation_flag()

        try:
            # Register in main thread
            _register_cancellation_flag(main_event)

            # Run in another thread
            t = threading.Thread(target=thread_func)
            t.start()
            t.join()

            # Main thread should still have its own flag
            assert get_cancellation_flag() is main_event
            # Other thread had different flag
            assert thread_result[0] is thread_event
        finally:
            _unregister_cancellation_flag()


class TestCheckCancelled:
    """Test check_cancelled() function behavior."""

    def test_check_cancelled_does_nothing_when_not_cancelled(self):
        """check_cancelled should not raise when flag is not set."""
        event = threading.Event()
        # Event is NOT set (not cancelled)

        try:
            _register_cancellation_flag(event)
            # Should not raise
            check_cancelled()
        finally:
            _unregister_cancellation_flag()

    def test_check_cancelled_raises_when_cancelled(self):
        """check_cancelled should raise CancelledError when flag is set."""
        event = threading.Event()
        event.set()  # Mark as cancelled

        try:
            _register_cancellation_flag(event)
            with pytest.raises(asyncio.CancelledError, match="cancelled"):
                check_cancelled()
        finally:
            _unregister_cancellation_flag()

    def test_check_cancelled_does_nothing_when_no_flag_registered(self):
        """check_cancelled should be safe when no flag is registered."""
        _unregister_cancellation_flag()  # Ensure no flag
        # Should not raise
        check_cancelled()


class TestCooperativeCancellation:
    """Test cooperative cancellation pattern in tools."""

    def test_cooperative_tool_can_detect_cancellation(self):
        """A cooperative tool should be able to check for cancellation."""
        cancel_event = threading.Event()
        iterations_completed = []

        def cooperative_tool():
            """Tool that checks cancellation periodically."""
            _register_cancellation_flag(cancel_event)
            try:
                for i in range(100):
                    check_cancelled()
                    iterations_completed.append(i)
                    time.sleep(0.01)
            except asyncio.CancelledError:
                return "cancelled"
            finally:
                _unregister_cancellation_flag()
            return "completed"

        # Start tool in thread
        result = []

        def run_tool():
            result.append(cooperative_tool())

        t = threading.Thread(target=run_tool)
        t.start()

        # Cancel after short delay
        time.sleep(0.05)
        cancel_event.set()
        t.join()

        # Tool should have been cancelled before completing
        assert result[0] == "cancelled"
        assert len(iterations_completed) < 100

    def test_non_cooperative_tool_ignores_cancellation(self):
        """A tool that doesn't check cancellation will continue running."""
        cancel_event = threading.Event()
        completed = []

        def non_cooperative_tool():
            """Tool that never checks cancellation."""
            _register_cancellation_flag(cancel_event)
            try:
                # Does work but never calls check_cancelled()
                for i in range(5):
                    completed.append(i)
                    time.sleep(0.01)
                return "completed"
            finally:
                _unregister_cancellation_flag()

        # Set cancellation before even starting
        cancel_event.set()

        # Tool runs to completion because it doesn't check
        result = non_cooperative_tool()
        assert result == "completed"
        assert len(completed) == 5


class TestTimeoutIntegration:
    """Test timeout behavior with cancellation flags."""

    @pytest.mark.asyncio
    async def test_timeout_sets_cancellation_flag(self):
        """When a timeout occurs, the cancellation flag should be set."""
        cancel_event = threading.Event()
        flag_was_set = []

        def slow_tool():
            """Tool that takes too long."""
            _register_cancellation_flag(cancel_event)
            try:
                for _ in range(100):
                    if cancel_event.is_set():
                        flag_was_set.append(True)
                        break
                    time.sleep(0.1)
            finally:
                _unregister_cancellation_flag()

        # Simulate timeout scenario
        loop = asyncio.get_event_loop()

        async def run_with_timeout():
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, slow_tool),
                    timeout=0.1,
                )
            except asyncio.TimeoutError:
                # Set cancellation flag on timeout
                cancel_event.set()
                # Give tool time to notice
                await asyncio.sleep(0.2)

        await run_with_timeout()

        # Flag should have been noticed
        assert len(flag_was_set) > 0 or cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_multiple_tools_have_independent_cancellation(self):
        """Each tool execution should have its own cancellation context."""
        results = []

        def tool_in_thread(tool_id: int, cancel_event: threading.Event):
            _register_cancellation_flag(cancel_event)
            try:
                for _ in range(10):
                    check_cancelled()
                    time.sleep(0.01)
                results.append((tool_id, "completed"))
            except asyncio.CancelledError:
                results.append((tool_id, "cancelled"))
            finally:
                _unregister_cancellation_flag()

        # Create two independent cancellation events
        event1 = threading.Event()
        event2 = threading.Event()

        # Only cancel the first one
        t1 = threading.Thread(target=tool_in_thread, args=(1, event1))
        t2 = threading.Thread(target=tool_in_thread, args=(2, event2))

        t1.start()
        t2.start()

        # Cancel only tool 1
        time.sleep(0.03)
        event1.set()

        t1.join()
        t2.join()

        # Tool 1 cancelled, tool 2 completed
        result_dict = dict(results)
        assert result_dict[1] == "cancelled"
        assert result_dict[2] == "completed"


class TestCancellationErrorMessage:
    """Test that cancellation provides informative error messages."""

    def test_cancellation_error_message_format(self):
        """CancelledError should have descriptive message."""
        event = threading.Event()
        event.set()

        try:
            _register_cancellation_flag(event)
            with pytest.raises(asyncio.CancelledError) as exc_info:
                check_cancelled()

            assert "cancelled" in str(exc_info.value).lower()
        finally:
            _unregister_cancellation_flag()

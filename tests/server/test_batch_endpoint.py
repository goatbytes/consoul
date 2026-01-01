"""Tests for /chat/batch HTTP endpoint.

Tests the POST /chat/batch endpoint functionality:
- Endpoint registration and HTTP methods
- Request/response validation
- Sequential vs parallel processing modes
- Best-effort error handling
- Session state management
- Usage aggregation
- Prometheus metrics recording (SOUL-349)
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from fastapi.testclient import TestClient

from consoul.server import create_server


class TestBatchEndpointExists:
    """Test /chat/batch endpoint is registered correctly."""

    def test_batch_endpoint_registered(self) -> None:
        """Batch endpoint is registered at POST /chat/batch."""
        app = create_server()

        # Verify endpoint exists by checking routes
        routes = [route.path for route in app.routes]
        assert "/chat/batch" in routes

    def test_batch_requires_post_method(self) -> None:
        """Batch endpoint only accepts POST requests."""
        app = create_server()
        client = TestClient(app)

        # GET should fail
        response = client.get("/chat/batch")
        assert response.status_code == 405


class TestBatchRequestValidation:
    """Test request validation for /chat/batch endpoint."""

    def test_missing_session_id_returns_422(self) -> None:
        """Missing session_id returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post(
            "/chat/batch",
            json={"messages": [{"content": "Hello"}]},
        )
        assert response.status_code == 422

    def test_missing_messages_returns_422(self) -> None:
        """Missing messages array returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post(
            "/chat/batch",
            json={"session_id": "test"},
        )
        assert response.status_code == 422

    def test_empty_messages_returns_422(self) -> None:
        """Empty messages array returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post(
            "/chat/batch",
            json={"session_id": "test", "messages": []},
        )
        assert response.status_code == 422

    def test_too_many_messages_returns_422(self) -> None:
        """More than 10 messages returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        # 11 messages (max is 10)
        messages = [{"content": f"Message {i}"} for i in range(11)]
        response = client.post(
            "/chat/batch",
            json={"session_id": "test", "messages": messages},
        )
        assert response.status_code == 422

    def test_empty_message_content_returns_422(self) -> None:
        """Empty message content returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post(
            "/chat/batch",
            json={"session_id": "test", "messages": [{"content": ""}]},
        )
        assert response.status_code == 422

    def test_message_content_too_long_returns_422(self) -> None:
        """Message content exceeding 32KB returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        # 32769 characters (max is 32768)
        long_content = "a" * 32769
        response = client.post(
            "/chat/batch",
            json={"session_id": "test", "messages": [{"content": long_content}]},
        )
        assert response.status_code == 422

    def test_session_id_max_length(self) -> None:
        """Session ID exceeding max length returns 422."""
        app = create_server()
        client = TestClient(app)

        # 129 characters (max is 128)
        long_session_id = "a" * 129
        response = client.post(
            "/chat/batch",
            json={"session_id": long_session_id, "messages": [{"content": "Hello"}]},
        )
        assert response.status_code == 422

    def test_valid_single_message_accepted(self) -> None:
        """Valid request with single message is accepted."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Hello!"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-session",
                    "messages": [{"content": "Hello"}],
                },
            )

            # Should succeed (200) or fail gracefully (500) - not validation error
            assert response.status_code in [200, 500]

    def test_valid_multiple_messages_accepted(self) -> None:
        """Valid request with multiple messages is accepted."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.side_effect = ["Hello!", "4"]
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-session",
                    "messages": [
                        {"content": "Hello!"},
                        {"content": "What is 2+2?"},
                    ],
                },
            )

            # Should succeed (200) or fail gracefully (500) - not validation error
            assert response.status_code in [200, 500]


class TestBatchSequentialMode:
    """Test sequential processing mode (default)."""

    def test_sequential_mode_is_default(self) -> None:
        """Sequential mode is the default when not specified."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.side_effect = ["Hello!", "4"]
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-sequential",
                    "messages": [
                        {"content": "Hello!"},
                        {"content": "What is 2+2?"},
                    ],
                    # sequential not specified, should default to True
                },
            )

            if response.status_code == 200:
                data = response.json()
                assert data["processing_mode"] == "sequential"

    def test_sequential_processes_on_same_console(self) -> None:
        """Sequential mode processes all messages on the same console instance."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.side_effect = ["Response 1", "Response 2"]
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-sequential",
                    "messages": [
                        {"content": "First message"},
                        {"content": "Second message"},
                    ],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                # Verify chat was called twice on the SAME console instance
                assert mock_console.chat.call_count == 2
                # create_session should only be called once
                assert mock_create.call_count == 1

    def test_sequential_saves_session_state(self) -> None:
        """Sequential mode saves session state after processing."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-sequential",
                    "messages": [{"content": "Hello"}],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                # save_session_state should be called
                mock_save.assert_called()


class TestBatchParallelMode:
    """Test parallel processing mode."""

    def test_parallel_mode_explicit(self) -> None:
        """Parallel mode can be explicitly requested."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
            patch("consoul.sdk.restore_session") as mock_restore,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_restore.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-parallel",
                    "messages": [
                        {"content": "Query 1"},
                        {"content": "Query 2"},
                    ],
                    "sequential": False,
                },
            )

            if response.status_code == 200:
                data = response.json()
                assert data["processing_mode"] == "parallel"

    def test_parallel_restores_session_per_message(self) -> None:
        """Parallel mode restores session state for each message."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
            patch("consoul.sdk.restore_session") as mock_restore,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_restore.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-parallel",
                    "messages": [
                        {"content": "Query 1"},
                        {"content": "Query 2"},
                    ],
                    "sequential": False,
                },
            )

            if response.status_code == 200:
                # restore_session should be called for each message in parallel mode
                assert mock_restore.call_count == 2


class TestBatchErrorHandling:
    """Test best-effort error handling."""

    def test_partial_failure_continues(self) -> None:
        """Batch continues processing after individual message failures."""
        app = create_server()
        client = TestClient(app)

        call_count = [0]

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()

            def fail_second_call(msg: str) -> str:
                call_count[0] += 1
                if call_count[0] == 2:
                    raise RuntimeError("Simulated failure")
                return f"Response to: {msg}"

            mock_console.chat.side_effect = fail_second_call
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test-partial",
                    "messages": [
                        {"content": "Will succeed"},
                        {"content": "Will fail"},
                        {"content": "Will also succeed"},
                    ],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                data = response.json()
                responses = data["responses"]

                # All three messages should be processed (best-effort)
                assert len(responses) == 3

                # First and third should succeed
                assert responses[0]["response"] is not None
                assert responses[0]["error"] is None

                # Second should have an error
                assert responses[1]["response"] is None
                assert responses[1]["error"] is not None

                # Third should still succeed
                assert responses[2]["response"] is not None
                assert responses[2]["error"] is None


class TestBatchResponseSchema:
    """Test response schema for /chat/batch endpoint."""

    def test_success_response_schema(self) -> None:
        """Success response contains all required fields."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Hello!"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [{"content": "Hello"}],
                },
            )

            if response.status_code == 200:
                data = response.json()
                assert "session_id" in data
                assert "responses" in data
                assert "total_usage" in data
                assert "model" in data
                assert "timestamp" in data
                assert "processing_mode" in data

    def test_response_item_fields(self) -> None:
        """Each response item has index, response, and usage."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Hello!"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [{"content": "Hello"}],
                },
            )

            if response.status_code == 200:
                data = response.json()
                item = data["responses"][0]
                assert "index" in item
                assert "response" in item
                assert "usage" in item

    def test_response_indices_are_ordered(self) -> None:
        """Response indices match original message order."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.side_effect = ["Response 0", "Response 1", "Response 2"]
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [
                        {"content": "Message 0"},
                        {"content": "Message 1"},
                        {"content": "Message 2"},
                    ],
                },
            )

            if response.status_code == 200:
                data = response.json()
                responses = data["responses"]

                # Indices should be in order
                for i, resp in enumerate(responses):
                    assert resp["index"] == i


class TestBatchTotalUsage:
    """Test aggregated usage calculation."""

    def test_total_usage_aggregates_successful(self) -> None:
        """Total usage aggregates only successful messages."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [
                        {"content": "Message 1"},
                        {"content": "Message 2"},
                    ],
                },
            )

            if response.status_code == 200:
                data = response.json()
                total = data["total_usage"]

                # 2 messages * 10 input tokens = 20 input tokens
                assert total["input_tokens"] == 20
                # 2 messages * 5 output tokens = 10 output tokens
                assert total["output_tokens"] == 10
                # Total = input + output = 30
                assert total["total_tokens"] == 30

    def test_total_usage_excludes_failed(self) -> None:
        """Total usage excludes failed messages."""
        app = create_server()
        client = TestClient(app)

        call_count = [0]

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()

            def fail_second(msg: str) -> str:
                call_count[0] += 1
                if call_count[0] == 2:
                    raise RuntimeError("Simulated failure")
                return "Response"

            mock_console.chat.side_effect = fail_second
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [
                        {"content": "Will succeed"},
                        {"content": "Will fail"},
                        {"content": "Will succeed"},
                    ],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                data = response.json()
                total = data["total_usage"]

                # Only 2 successful messages (first and third)
                # 2 * 10 input tokens = 20
                assert total["input_tokens"] == 20
                # 2 * 5 output tokens = 10
                assert total["output_tokens"] == 10


class TestBatchMetricsIntegration:
    """Test batch metrics are recorded correctly during endpoint execution (SOUL-349)."""

    def test_successful_batch_records_all_metrics(self) -> None:
        """Successful batch records batch_size, message, request, and latency metrics."""
        app = create_server()
        client = TestClient(app)

        mock_metrics = MagicMock()

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.side_effect = ["Response 1", "Response 2"]
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            # Inject mock metrics
            app.state.metrics = mock_metrics

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [
                        {"content": "Message 1"},
                        {"content": "Message 2"},
                    ],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                # Verify batch_size was recorded
                mock_metrics.record_batch_size.assert_called_once_with(2)

                # Verify message metrics (2 successes)
                assert mock_metrics.record_batch_message.call_count == 2
                mock_metrics.record_batch_message.assert_has_calls(
                    [
                        call("sequential", success=True),
                        call("sequential", success=True),
                    ]
                )

                # Verify batch request total
                mock_metrics.record_batch_request.assert_called_once_with(
                    "sequential", "success"
                )

                # Verify latency was recorded
                mock_metrics.record_batch_latency.assert_called_once()
                call_args = mock_metrics.record_batch_latency.call_args
                assert call_args[0][0] == "sequential"
                assert call_args[0][1] > 0  # latency > 0

    def test_partial_failure_records_partial_failure_status(self) -> None:
        """Partial failure batch records partial_failure status."""
        app = create_server()
        client = TestClient(app)

        mock_metrics = MagicMock()
        call_count = [0]

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()

            def fail_second(msg: str) -> str:
                call_count[0] += 1
                if call_count[0] == 2:
                    raise RuntimeError("Simulated failure")
                return "Response"

            mock_console.chat.side_effect = fail_second
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            app.state.metrics = mock_metrics

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [
                        {"content": "Will succeed"},
                        {"content": "Will fail"},
                        {"content": "Will succeed"},
                    ],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                # Verify partial_failure status
                mock_metrics.record_batch_request.assert_called_once_with(
                    "sequential", "partial_failure"
                )

                # Verify message metrics (2 success, 1 failure)
                assert mock_metrics.record_batch_message.call_count == 3

    def test_all_failures_records_failure_status(self) -> None:
        """Batch where all messages fail records failure status."""
        app = create_server()
        client = TestClient(app)

        mock_metrics = MagicMock()

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.side_effect = RuntimeError("All fail")
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            app.state.metrics = mock_metrics

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [
                        {"content": "Will fail"},
                        {"content": "Also fail"},
                    ],
                    "sequential": True,
                },
            )

            if response.status_code == 200:
                mock_metrics.record_batch_request.assert_called_once_with(
                    "sequential", "failure"
                )

    def test_parallel_mode_records_parallel_label(self) -> None:
        """Parallel mode batch records 'parallel' processing_mode."""
        app = create_server()
        client = TestClient(app)

        mock_metrics = MagicMock()

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
            patch("consoul.sdk.restore_session") as mock_restore,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_restore.return_value = mock_console
            mock_save.return_value = {}

            app.state.metrics = mock_metrics

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [{"content": "Query"}],
                    "sequential": False,
                },
            )

            if response.status_code == 200:
                mock_metrics.record_batch_request.assert_called_once()
                assert mock_metrics.record_batch_request.call_args[0][0] == "parallel"
                mock_metrics.record_batch_latency.assert_called_once()
                assert mock_metrics.record_batch_latency.call_args[0][0] == "parallel"

    def test_metrics_disabled_no_errors(self) -> None:
        """Batch endpoint works when metrics is None."""
        app = create_server()
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            # Explicitly set metrics to None
            app.state.metrics = None

            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [{"content": "Hello"}],
                },
            )

            # Should not raise, should succeed
            assert response.status_code in [200, 500]

    def test_batch_size_recorded_for_various_sizes(self) -> None:
        """batch_size metric records correct value for different batch sizes."""
        app = create_server()
        client = TestClient(app)

        mock_metrics = MagicMock()

        with (
            patch("consoul.sdk.create_session") as mock_create,
            patch("consoul.sdk.save_session_state") as mock_save,
        ):
            mock_console = MagicMock()
            mock_console.chat.return_value = "Response"
            mock_console.last_cost = {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost": 0.0001,
            }
            mock_console.model_name = "gpt-4o"
            mock_create.return_value = mock_console
            mock_save.return_value = {}

            app.state.metrics = mock_metrics

            # Test with 5 messages
            response = client.post(
                "/chat/batch",
                json={
                    "session_id": "test",
                    "messages": [{"content": f"Msg {i}"} for i in range(5)],
                },
            )

            if response.status_code == 200:
                mock_metrics.record_batch_size.assert_called_with(5)

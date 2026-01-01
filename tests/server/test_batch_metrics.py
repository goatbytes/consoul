"""Tests for batch endpoint Prometheus metrics (SOUL-349).

Tests the batch-specific metrics added to MetricsCollector:
- consoul_batch_request_total
- consoul_batch_size
- consoul_batch_message_total
- consoul_batch_latency_seconds
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestBatchMetricDefinitions:
    """Test batch metric definitions in MetricsCollector."""

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_batch_request_total_defined(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """batch_request_total counter is defined with correct labels."""
        from consoul.server.observability.metrics import MetricsCollector

        MetricsCollector()

        # Find the call that creates batch_request_total
        calls = [
            c
            for c in mock_counter.call_args_list
            if c[0][0] == "consoul_batch_request_total"
        ]
        assert len(calls) == 1
        assert calls[0][0][2] == ["processing_mode", "status"]

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_batch_message_total_defined(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """batch_message_total counter is defined with correct labels."""
        from consoul.server.observability.metrics import MetricsCollector

        MetricsCollector()

        # Find the call that creates batch_message_total
        calls = [
            c
            for c in mock_counter.call_args_list
            if c[0][0] == "consoul_batch_message_total"
        ]
        assert len(calls) == 1
        assert calls[0][0][2] == ["status", "processing_mode"]

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_batch_size_histogram_buckets(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """batch_size histogram has correct buckets (1-10)."""
        from consoul.server.observability.metrics import MetricsCollector

        MetricsCollector()

        calls = [
            c for c in mock_histogram.call_args_list if c[0][0] == "consoul_batch_size"
        ]
        assert len(calls) == 1
        assert calls[0][1]["buckets"] == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_batch_latency_buckets_match_request_latency(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """batch_latency histogram matches request_latency buckets."""
        from consoul.server.observability.metrics import MetricsCollector

        expected_buckets = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
        MetricsCollector()

        calls = [
            c
            for c in mock_histogram.call_args_list
            if c[0][0] == "consoul_batch_latency_seconds"
        ]
        assert len(calls) == 1
        assert calls[0][1]["buckets"] == expected_buckets

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_batch_latency_has_processing_mode_label(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """batch_latency histogram has processing_mode label."""
        from consoul.server.observability.metrics import MetricsCollector

        MetricsCollector()

        calls = [
            c
            for c in mock_histogram.call_args_list
            if c[0][0] == "consoul_batch_latency_seconds"
        ]
        assert len(calls) == 1
        assert calls[0][0][2] == ["processing_mode"]


class TestBatchMetricRecordingDisabled:
    """Test batch metrics are no-op when disabled."""

    def test_record_batch_request_disabled(self) -> None:
        """record_batch_request is no-op when disabled."""
        with patch(
            "consoul.server.observability.metrics._import_prometheus",
            return_value=False,
        ):
            from consoul.server.observability.metrics import MetricsCollector

            metrics = MetricsCollector()
            # Should not raise
            metrics.record_batch_request("sequential", "success")

    def test_record_batch_size_disabled(self) -> None:
        """record_batch_size is no-op when disabled."""
        with patch(
            "consoul.server.observability.metrics._import_prometheus",
            return_value=False,
        ):
            from consoul.server.observability.metrics import MetricsCollector

            metrics = MetricsCollector()
            # Should not raise
            metrics.record_batch_size(5)

    def test_record_batch_message_disabled(self) -> None:
        """record_batch_message is no-op when disabled."""
        with patch(
            "consoul.server.observability.metrics._import_prometheus",
            return_value=False,
        ):
            from consoul.server.observability.metrics import MetricsCollector

            metrics = MetricsCollector()
            # Should not raise
            metrics.record_batch_message("parallel", success=True)

    def test_record_batch_latency_disabled(self) -> None:
        """record_batch_latency is no-op when disabled."""
        with patch(
            "consoul.server.observability.metrics._import_prometheus",
            return_value=False,
        ):
            from consoul.server.observability.metrics import MetricsCollector

            metrics = MetricsCollector()
            # Should not raise
            metrics.record_batch_latency("sequential", 2.5)


class TestBatchMetricRecordingEnabled:
    """Test batch metric recording methods when enabled."""

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_request_sequential_success(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_request applies correct labels for sequential success."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_request("sequential", "success")

        metrics.batch_request_total.labels.assert_called_with(
            processing_mode="sequential",
            status="success",
        )
        metrics.batch_request_total.labels().inc.assert_called_once()

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_request_parallel_partial_failure(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_request applies correct labels for parallel partial failure."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_request("parallel", "partial_failure")

        metrics.batch_request_total.labels.assert_called_with(
            processing_mode="parallel",
            status="partial_failure",
        )
        metrics.batch_request_total.labels().inc.assert_called_once()

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_request_failure_status(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_request applies correct labels for failure status."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_request("sequential", "failure")

        metrics.batch_request_total.labels.assert_called_with(
            processing_mode="sequential",
            status="failure",
        )

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_size_observes_value(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_size observes the batch size."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_size(5)

        metrics.batch_size.observe.assert_called_once_with(5)

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_size_max_value(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_size handles max batch size (10)."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_size(10)

        metrics.batch_size.observe.assert_called_once_with(10)

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_message_success(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_message records success correctly."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_message("sequential", success=True)

        metrics.batch_message_total.labels.assert_called_with(
            status="success",
            processing_mode="sequential",
        )
        metrics.batch_message_total.labels().inc.assert_called_once()

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_message_failure(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_message records failure correctly."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_message("parallel", success=False)

        metrics.batch_message_total.labels.assert_called_with(
            status="failed",
            processing_mode="parallel",
        )
        metrics.batch_message_total.labels().inc.assert_called_once()

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_latency_sequential(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_latency observes latency with sequential mode."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_latency("sequential", 2.5)

        metrics.batch_latency.labels.assert_called_with(processing_mode="sequential")
        metrics.batch_latency.labels().observe.assert_called_once_with(2.5)

    @patch("consoul.server.observability.metrics._import_prometheus", return_value=True)
    @patch("consoul.server.observability.metrics._Counter")
    @patch("consoul.server.observability.metrics._Histogram")
    @patch("consoul.server.observability.metrics._Gauge")
    def test_record_batch_latency_parallel(
        self,
        mock_gauge: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
        mock_import: MagicMock,
    ) -> None:
        """record_batch_latency observes latency with parallel mode."""
        from consoul.server.observability.metrics import MetricsCollector

        metrics = MetricsCollector()
        metrics.record_batch_latency("parallel", 0.05)

        metrics.batch_latency.labels.assert_called_with(processing_mode="parallel")
        metrics.batch_latency.labels().observe.assert_called_once_with(0.05)

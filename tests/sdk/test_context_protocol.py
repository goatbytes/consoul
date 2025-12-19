"""Tests for ContextProvider protocol validation."""

from __future__ import annotations

import pytest

from consoul.sdk.protocols import ContextProvider


class TestContextProviderProtocol:
    """Test ContextProvider protocol validation and compliance."""

    def test_simple_provider_implements_protocol(self):
        """Test that a simple class with get_context method implements the protocol."""

        class SimpleProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"test": "context"}

        provider = SimpleProvider()
        assert isinstance(provider, ContextProvider)

    def test_provider_with_state_implements_protocol(self):
        """Test that a stateful provider implements the protocol."""

        class StatefulProvider:
            def __init__(self, data: dict[str, str]):
                self.data = data

            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return self.data.copy()

        provider = StatefulProvider({"domain": "legal", "jurisdiction": "CA"})
        assert isinstance(provider, ContextProvider)

    def test_provider_with_query_awareness_implements_protocol(self):
        """Test that a query-aware provider implements the protocol."""

        class QueryAwareProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                if query and "urgent" in query.lower():
                    return {"priority": "high", "context": "Emergency context"}
                return {"priority": "normal", "context": "Standard context"}

        provider = QueryAwareProvider()
        assert isinstance(provider, ContextProvider)

        # Verify query-aware behavior
        urgent_context = provider.get_context("This is urgent!")
        assert urgent_context["priority"] == "high"

        normal_context = provider.get_context("Regular question")
        assert normal_context["priority"] == "normal"

    def test_provider_with_conversation_tracking(self):
        """Test provider that tracks conversation state."""

        class ConversationTracker:
            def __init__(self):
                self.conversations: dict[str, list[str]] = {}

            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                if conversation_id:
                    history = self.conversations.get(conversation_id, [])
                    return {
                        "conversation_history": "\n".join(history[-5:]),
                        "message_count": str(len(history)),
                    }
                return {"conversation_history": "New conversation"}

        provider = ConversationTracker()
        assert isinstance(provider, ContextProvider)

        # Test with conversation ID
        context = provider.get_context(conversation_id="conv-123")
        assert "conversation_history" in context

    def test_invalid_provider_missing_method(self):
        """Test that a class without get_context does not implement protocol."""

        class InvalidProvider:
            def get_data(self) -> dict[str, str]:
                return {"test": "data"}

        provider = InvalidProvider()
        assert not isinstance(provider, ContextProvider)

    def test_invalid_provider_wrong_signature(self):
        """Test that wrong method signature does not implement protocol."""

        class WrongSignature:
            def get_context(self) -> str:  # Wrong return type
                return "context string"

        provider = WrongSignature()
        # Note: Python's runtime_checkable only checks method existence,
        # not exact signatures at runtime. Type checkers (mypy) catch this.
        assert isinstance(provider, ContextProvider)  # Runtime allows this

    def test_provider_can_return_empty_context(self):
        """Test that providers can return empty context dict."""

        class EmptyProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {}

        provider = EmptyProvider()
        assert isinstance(provider, ContextProvider)
        assert provider.get_context() == {}

    def test_provider_with_error_handling(self):
        """Test provider that handles errors gracefully."""

        class RobustProvider:
            def __init__(self, fail: bool = False):
                self.fail = fail

            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                if self.fail:
                    raise ValueError("Simulated provider failure")
                return {"status": "ok"}

        # Normal operation
        provider = RobustProvider(fail=False)
        assert provider.get_context() == {"status": "ok"}

        # Error case
        failing_provider = RobustProvider(fail=True)
        with pytest.raises(ValueError, match="Simulated provider failure"):
            failing_provider.get_context()

    def test_multiple_providers_composition(self):
        """Test that multiple providers can be used together."""

        class DomainProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"domain": "legal", "expertise": "workers compensation"}

        class JurisdictionProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"jurisdiction": "California", "regulations": "2024"}

        providers = [DomainProvider(), JurisdictionProvider()]

        # All should implement protocol
        for provider in providers:
            assert isinstance(provider, ContextProvider)

        # Compose context from all providers
        combined_context = {}
        for provider in providers:
            combined_context.update(provider.get_context())

        assert "domain" in combined_context
        assert "jurisdiction" in combined_context
        assert len(combined_context) == 4  # 4 keys total

    def test_provider_with_database_simulation(self):
        """Test provider that simulates database queries."""

        class MockDatabase:
            def query(self, search: str) -> list[str]:
                return [f"Result for {search}"]

        class DatabaseProvider:
            def __init__(self, db: MockDatabase):
                self.db = db

            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                if query:
                    results = self.db.query(query)
                    return {
                        "search_results": "\n".join(results),
                        "result_count": str(len(results)),
                    }
                return {"search_results": "No query provided"}

        mock_db = MockDatabase()
        provider = DatabaseProvider(mock_db)

        assert isinstance(provider, ContextProvider)

        context = provider.get_context(query="test query")
        assert "Result for test query" in context["search_results"]
        assert context["result_count"] == "1"

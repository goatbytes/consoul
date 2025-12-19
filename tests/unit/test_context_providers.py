"""Integration tests for ContextProvider protocol with SDK."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from consoul.sdk import Consoul


class SimpleContextProvider:
    """Simple test provider that returns static context."""

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        return {"test_domain": "Test domain context", "test_expertise": "Testing"}


class DynamicContextProvider:
    """Provider that uses query for context-aware responses."""

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        if query and "urgent" in query.lower():
            return {"priority": "HIGH", "context": "Urgent request handling"}
        return {"priority": "NORMAL", "context": "Standard request handling"}


class FailingContextProvider:
    """Provider that raises an exception."""

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        raise ValueError("Simulated provider failure")


class StatefulContextProvider:
    """Provider that maintains conversation state."""

    def __init__(self):
        self.call_count = 0
        self.conversations: dict[str, list[str]] = {}

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        self.call_count += 1
        if conversation_id:
            history = self.conversations.get(conversation_id, [])
            return {
                "conversation_id": conversation_id,
                "message_count": str(len(history)),
                "call_count": str(self.call_count),
            }
        return {"call_count": str(self.call_count)}


@pytest.fixture
def mock_model():
    """Mock the get_chat_model to avoid API calls."""
    with patch("consoul.ai.providers.get_chat_model") as mock:
        # Create a mock model that returns a simple response
        mock_llm = Mock()
        mock_llm.model_name = "gpt-4o-mini"
        mock_llm.invoke = Mock(
            return_value=Mock(content="Test response", tool_calls=None)
        )
        mock.return_value = mock_llm
        yield mock


class TestContextProviderIntegration:
    """Test ContextProvider integration with Consoul SDK."""

    def test_single_provider_integration(self, mock_model):
        """Test that a single provider's context is injected."""
        provider = SimpleContextProvider()

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are an AI assistant.",
            context_providers=[provider],
            tools=False,
        )

        # Verify system message was added with context
        messages = console.history.messages
        assert len(messages) == 1
        assert messages[0].__class__.__name__ == "SystemMessage"

        # Should contain provider context
        content = messages[0].content
        assert "Test Domain" in content  # Title-cased from test_domain
        assert "Test domain context" in content
        assert "Test Expertise" in content
        assert "Testing" in content
        assert "You are an AI assistant." in content

    def test_multiple_providers_composition(self, mock_model):
        """Test that multiple providers' contexts are merged."""

        class Provider1:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"domain": "Legal", "jurisdiction": "California"}

        class Provider2:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"expertise": "Workers Compensation", "year": "2024"}

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are a legal assistant.",
            context_providers=[Provider1(), Provider2()],
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # All provider contexts should be present
        assert "Domain" in content
        assert "Legal" in content
        assert "Jurisdiction" in content
        assert "California" in content
        assert "Expertise" in content
        assert "Workers Compensation" in content
        assert "Year" in content
        assert "2024" in content
        assert "You are a legal assistant." in content

    def test_empty_provider_list(self, mock_model):
        """Test that empty provider list works correctly."""
        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are an AI assistant.",
            context_providers=[],
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # Should only contain the base system prompt
        assert content == "You are an AI assistant."

    def test_none_provider_list(self, mock_model):
        """Test that None provider list works correctly."""
        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are an AI assistant.",
            context_providers=None,
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # Should only contain the base system prompt
        assert content == "You are an AI assistant."

    def test_failing_provider_graceful_degradation(self, mock_model):
        """Test that failing providers don't crash initialization."""

        class WorkingProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"working": "This provider works"}

        with patch("logging.warning") as mock_warning:
            console = Consoul(
                model="gpt-4o-mini",
                system_prompt="You are an AI assistant.",
                context_providers=[
                    WorkingProvider(),
                    FailingContextProvider(),
                ],
                tools=False,
            )

            # Should log warning about failing provider
            assert mock_warning.called
            warning_message = mock_warning.call_args[0][0]
            assert "FailingContextProvider" in warning_message
            assert "failed" in warning_message.lower()

            # Working provider's context should still be present
            messages = console.history.messages
            content = messages[0].content
            assert "Working" in content
            assert "This provider works" in content

    def test_provider_with_empty_context(self, mock_model):
        """Test provider that returns empty dict."""

        class EmptyProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {}

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are an AI assistant.",
            context_providers=[EmptyProvider()],
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # Should contain base prompt only (no env/git context by default for privacy)
        # Provider returned empty dict, so no provider context either
        assert "You are an AI assistant." in content
        # Env context should NOT be included by default (privacy)
        assert "## Environment" not in content

    def test_provider_with_special_characters_in_keys(self, mock_model):
        """Test that provider keys with special characters are handled."""

        class SpecialKeysProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {
                    "patient_id": "12345",
                    "medical_record_number": "MRN-67890",
                    "last_visit_date": "2024-01-15",
                }

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are a medical assistant.",
            context_providers=[SpecialKeysProvider()],
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # Keys should be title-cased with underscores replaced
        assert "Patient Id" in content
        assert "12345" in content
        assert "Medical Record Number" in content
        assert "MRN-67890" in content
        assert "Last Visit Date" in content
        assert "2024-01-15" in content

    def test_provider_context_ordering(self, mock_model):
        """Test that context appears before base prompt."""

        class OrderTestProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"context_section": "This should appear first"}

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="Base prompt comes after context.",
            context_providers=[OrderTestProvider()],
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # Context should appear before base prompt
        context_pos = content.find("This should appear first")
        base_pos = content.find("Base prompt comes after context")
        assert context_pos < base_pos

    def test_no_system_prompt_with_providers(self, mock_model):
        """Test that providers have no effect without system_prompt."""
        provider = SimpleContextProvider()

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt=None,
            context_providers=[provider],
            tools=False,
        )

        # No system message should be added
        messages = console.history.messages
        assert len(messages) == 0

    def test_provider_with_multiline_content(self, mock_model):
        """Test provider that returns multiline content."""

        class MultilineProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {
                    "medical_history": "- Hypertension (2019)\n"
                    "- Type 2 Diabetes (2020)\n"
                    "- Allergies: Penicillin"
                }

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are a medical assistant.",
            context_providers=[MultilineProvider()],
            tools=False,
        )

        messages = console.history.messages
        content = messages[0].content

        # Multiline content should be preserved
        assert "Hypertension (2019)" in content
        assert "Type 2 Diabetes (2020)" in content
        assert "Allergies: Penicillin" in content

    def test_stateful_provider_call_tracking(self, mock_model):
        """Test that stateful providers work correctly."""
        provider = StatefulContextProvider()

        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are an AI assistant.",
            context_providers=[provider],
            tools=False,
        )

        # Provider should be called once during initialization
        assert provider.call_count == 1

        # Verify context was added
        messages = console.history.messages
        content = messages[0].content
        assert "Call Count" in content
        assert "1" in content

    def test_query_aware_provider_receives_query(self, mock_model):
        """Test that providers receive query parameter per message."""

        class QueryCapturingProvider:
            def __init__(self):
                self.queries = []

            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                self.queries.append(query)
                if query:
                    return {"query_received": f"Received: {query}"}
                return {"query_received": "No query"}

        provider = QueryCapturingProvider()
        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="You are an AI assistant.",
            context_providers=[provider],
            tools=False,
        )

        # Initial call should be None
        assert len(provider.queries) == 1
        assert provider.queries[0] is None

        # Send first message
        console.chat("What is 2+2?")

        # Provider should have been called with the query
        assert len(provider.queries) == 2
        assert provider.queries[1] == "What is 2+2?"

        # Send second message
        console.chat("What about 3+3?")

        # Provider should have been called again
        assert len(provider.queries) == 3
        assert provider.queries[2] == "What about 3+3?"

    def test_provider_context_changes_per_message(self, mock_model):
        """Test that context updates dynamically for each message."""

        class DynamicProvider:
            def __init__(self):
                self.message_count = 0

            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                if query:
                    self.message_count += 1
                    return {
                        "message_count": str(self.message_count),
                        "last_query": query,
                    }
                return {"message_count": "0", "last_query": "none"}

        provider = DynamicProvider()
        console = Consoul(
            model="gpt-4o-mini",
            system_prompt="Base prompt",
            context_providers=[provider],
            tools=False,
        )

        # Send first message
        console.chat("First message")

        # System prompt should be updated with message_count=1
        system_message = console.history.messages[0]
        assert "Message Count" in system_message.content
        assert "1" in system_message.content
        assert "First message" in system_message.content

        # Send second message
        console.chat("Second message")

        # System prompt should be updated with message_count=2
        system_message = console.history.messages[0]
        assert "2" in system_message.content
        assert "Second message" in system_message.content

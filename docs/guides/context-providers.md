# Context Providers Guide

**Dynamic Context Injection for Domain-Specific AI Agents**

This guide explains how to use the ContextProvider protocol to build domain-specific AI applications with Consoul. Context providers enable dynamic, query-aware context injection from databases, APIs, and other runtime sources.

## Table of Contents

- [Quick Start](#quick-start)
- [What are Context Providers?](#what-are-context-providers)
- [When to Use Context Providers](#when-to-use-context-providers)
- [The ContextProvider Protocol](#the-contextprovider-protocol)
- [Creating Your First Provider](#creating-your-first-provider)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Complete Examples](#complete-examples)
- [API Reference](#api-reference)

## Quick Start

```python
from consoul import Consoul

class SimpleContextProvider:
    """Minimal context provider example."""

    def get_context(self, query=None, conversation_id=None):
        return {
            "domain_knowledge": "Relevant domain-specific information",
            "timestamp": "2024-12-18",
        }

# Use it with Consoul
provider = SimpleContextProvider()
console = Consoul(
    model="gpt-4o",
    system_prompt="You are an AI assistant...",
    context_providers=[provider],  # Dynamic context injection!
)

response = console.chat("Your question here")
```

That's it! No inheritance, no complex interfaces - just implement `get_context()`.

## What are Context Providers?

Context providers enable **dynamic context injection** into AI system prompts. Instead of static prompts, you can:

- **Query databases** for relevant information
- **Call APIs** to fetch real-time data
- **Track conversation state** across messages
- **Personalize responses** based on user/session data
- **Compose multiple sources** of domain knowledge

### Static vs Dynamic Context

**Static Context** (`build_enhanced_system_prompt`):
```python
# Context is fixed at initialization
prompt = build_enhanced_system_prompt(
    "You are a legal assistant.",
    context_sections={
        "jurisdiction": "California law",
        "practice_area": "Workers' compensation"
    }
)
```

**Dynamic Context** (ContextProvider):
```python
# Context changes based on each query
class LegalProvider:
    def get_context(self, query=None, conversation_id=None):
        # Query database for cases relevant to this question
        cases = self.db.search(query)
        return {"relevant_cases": format_cases(cases)}
```

## When to Use Context Providers

### Use Context Providers When:

✅ **Dynamic Data**: Context changes based on queries or sessions
✅ **External Sources**: Data comes from databases, APIs, file systems
✅ **Query-Aware**: Different questions need different context
✅ **Stateful**: Tracking conversation history or user sessions
✅ **Composable**: Combining multiple data sources
✅ **Real-Time**: Fresh data needed for each interaction

### Use Static Prompts When:

❌ **Fixed Content**: Context never changes
❌ **Small Size**: Less than 500 tokens
❌ **File-Based**: Static files loaded at startup
❌ **General Purpose**: Not domain-specific

### Examples by Domain

| Domain | Use Case | Data Source |
|--------|----------|-------------|
| Legal AI | Case law precedents | Legal database |
| Medical | Patient history | EHR system |
| Support | Customer profile | CRM database |
| E-commerce | Product catalog | Inventory API |
| Finance | Market data | Trading platform |
| Education | Student progress | LMS database |

## The ContextProvider Protocol

```python
from typing import Protocol

class ContextProvider(Protocol):
    """Protocol for dynamic context injection."""

    def get_context(
        self,
        query: str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, str]:
        """Return context sections to inject into system prompt.

        Args:
            query: Current user query (enables query-aware context)
            conversation_id: Conversation ID (enables stateful context)

        Returns:
            Dictionary mapping section names to content strings.
            Each key becomes a section header in the prompt.

        Example:
            {
                "domain_knowledge": "Relevant info...",
                "user_profile": "User preferences...",
                "session_data": "Conversation history..."
            }
        """
        ...
```

### Key Features

**Structural Typing**: Any class with `get_context()` matching this signature implements the protocol automatically. No inheritance required!

**Query-Aware**: The `query` parameter lets you return different context based on what the user is asking.

**Stateful**: The `conversation_id` parameter enables tracking state across a conversation.

**Composable**: Return dict allows clean section organization and multiple provider composition.

## Creating Your First Provider

### Example: Knowledge Base Provider

```python
class KnowledgeBaseProvider:
    """Inject relevant documentation based on user queries."""

    def __init__(self, knowledge_base):
        self.kb = knowledge_base

    def get_context(self, query=None, conversation_id=None):
        if not query:
            # Return general context
            return {"docs": "General documentation overview"}

        # Search knowledge base for relevant articles
        articles = self.kb.search(query, limit=3)

        # Format for prompt injection
        articles_text = "\n\n".join(
            f"**{art['title']}**\n{art['summary']}"
            for art in articles
        )

        return {
            "relevant_documentation": articles_text,
            "search_query": query,
        }
```

### Usage

```python
from consoul import Consoul

kb = MyKnowledgeBase()
provider = KnowledgeBaseProvider(kb)

console = Consoul(
    model="gpt-4o",
    system_prompt="You are a technical support assistant.",
    context_providers=[provider]
)

# Each query gets fresh, relevant context
response = console.chat("How do I configure SSO?")
```

## Advanced Usage

### Multiple Providers

Combine multiple context sources:

```python
console = Consoul(
    model="gpt-4o",
    system_prompt="You are a comprehensive assistant.",
    context_providers=[
        UserProfileProvider(user_id="12345"),
        KnowledgeBaseProvider(kb),
        ComplianceProvider(regulations=["GDPR", "HIPAA"]),
    ]
)
```

Contexts are merged in order. Later providers can override earlier ones.

### Query-Aware Context

```python
class SmartProvider:
    """Different context based on query type."""

    def get_context(self, query=None, conversation_id=None):
        if not query:
            return {"default": "General context"}

        query_lower = query.lower()

        if "price" in query_lower or "cost" in query_lower:
            return self._get_pricing_context()
        elif "technical" in query_lower or "how" in query_lower:
            return self._get_technical_context()
        else:
            return self._get_general_context()
```

### Stateful Conversation Tracking

```python
class ConversationTracker:
    """Track conversation history for context-aware responses."""

    def __init__(self):
        self.conversations = {}

    def get_context(self, query=None, conversation_id=None):
        if not conversation_id:
            return {"status": "New conversation"}

        # Retrieve or create conversation history
        history = self.conversations.setdefault(conversation_id, [])

        if query:
            history.append(query)

        # Return recent history as context
        recent = history[-5:]  # Last 5 queries
        return {
            "conversation_history": "\n".join(recent),
            "message_count": str(len(history)),
        }
```

### Error Handling

```python
class RobustProvider:
    """Handle errors gracefully."""

    def get_context(self, query=None, conversation_id=None):
        try:
            data = self.api.fetch_data(query)
            return {"data": self._format(data)}
        except APIError as e:
            # Log error, return partial context
            logger.warning(f"API failed: {e}")
            return {
                "error": "Live data unavailable",
                "cached_data": self._get_cached_data(),
            }
        except Exception as e:
            # Don't crash the entire prompt generation
            logger.error(f"Provider failed: {e}")
            return {"error": "Context unavailable"}
```

The SDK catches exceptions from providers and continues with partial context.

## Best Practices

### 1. Keep Context Concise

**Target**: < 2000 tokens per provider

LLMs have finite context windows (8K-128K tokens depending on model). Too much context:
- Increases costs
- Slows processing
- May reduce response quality

```python
# ❌ Bad: Dumping entire database
def get_context(self, query=None, conversation_id=None):
    all_data = self.db.get_all()  # 50K tokens!
    return {"data": str(all_data)}

# ✅ Good: Targeted, relevant data
def get_context(self, query=None, conversation_id=None):
    top_5 = self.db.search(query, limit=5)  # ~500 tokens
    return {"relevant_data": format_concise(top_5)}
```

### 2. Security & Privacy

```python
class SecureProvider:
    """Security best practices."""

    def get_context(self, query=None, conversation_id=None):
        # ✅ Sanitize input
        clean_query = self._sanitize(query)

        # ✅ Fetch data with auth
        data = self.db.query(clean_query, user=self.user)

        # ✅ Filter sensitive fields
        safe_data = self._remove_pii(data)

        # ✅ Validate output
        validated = self._validate_output(safe_data)

        return validated
```

**Key Principles**:
- Sanitize all inputs (prevent SQL injection, etc.)
- Never expose credentials or internal IDs
- Filter PII before returning
- Log context generation for audits
- Respect user permissions

### 3. Performance Optimization

```python
from functools import lru_cache
from datetime import datetime, timedelta

class OptimizedProvider:
    """Performance-optimized context provider."""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    @lru_cache(maxsize=100)
    def _fetch_slow_data(self, key):
        """Cache expensive operations."""
        return self.db.slow_query(key)

    def get_context(self, query=None, conversation_id=None):
        # Check cache first
        cache_key = (query, conversation_id)
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached

        # Fetch and cache
        context = self._generate_context(query)
        self.cache[cache_key] = (context, datetime.now())

        return context
```

**Optimization Strategies**:
- Cache frequently-used context
- Use database indexes for fast queries
- Implement pagination for large datasets
- Consider async for I/O-bound operations
- Monitor performance metrics

### 4. Testing

```python
import pytest

class TestMyProvider:
    """Test context provider thoroughly."""

    def test_basic_context_generation(self):
        provider = MyProvider(mock_db)
        context = provider.get_context()
        assert "required_field" in context

    def test_query_aware_context(self):
        provider = MyProvider(mock_db)

        # Different queries should return different context
        ctx1 = provider.get_context("pricing question")
        ctx2 = provider.get_context("technical question")

        assert ctx1 != ctx2

    def test_error_handling(self):
        provider = MyProvider(failing_db)

        # Should not raise, return partial context
        context = provider.get_context()
        assert "error" in context

    def test_protocol_compliance(self):
        from consoul.sdk.protocols import ContextProvider

        provider = MyProvider(mock_db)
        assert isinstance(provider, ContextProvider)
```

## Complete Examples

See `examples/sdk/context_providers/` for production-ready implementations:

### Legal AI (`legal_context_provider.py`)
Workers' compensation assistant with case law database integration.

**Features**:
- Query-aware case retrieval
- Jurisdiction-specific context
- Citation formatting

**Run**: `python examples/sdk/context_providers/legal_context_provider.py`

### Medical Chatbot (`medical_context_provider.py`)
HIPAA-compliant medical assistant with EHR integration.

**Features**:
- Patient demographics and history
- Current medications and allergies
- Safety disclaimers

**Run**: `python examples/sdk/context_providers/medical_context_provider.py`

### Customer Support (`crm_context_provider.py`)
Enterprise support bot with CRM system integration.

**Features**:
- Customer tier and product info
- Support history tracking
- SLA-aware responses

**Run**: `python examples/sdk/context_providers/crm_context_provider.py`

## API Reference

### ContextProvider Protocol

**Location**: `consoul.sdk.protocols.ContextProvider`

**Methods**:
- `get_context(query: str | None = None, conversation_id: str | None = None) -> dict[str, str]`

**Parameters**:
- `query`: Current user question (optional, enables query-aware context)
- `conversation_id`: Conversation identifier (optional, enables stateful context)

**Returns**:
- Dictionary mapping section names to content strings

**Raises**:
- Any exception is caught by SDK and logged; conversation continues with partial context

### Consoul Constructor

**Parameter**: `context_providers: list[Any] | None = None`

**Example**:
```python
console = Consoul(
    model="gpt-4o",
    system_prompt="Base prompt...",
    context_providers=[provider1, provider2],  # List of providers
)
```

### Context Injection Flow

1. User sends query to `console.chat(query)`
2. SDK calls `provider.get_context(query, conversation_id)` for each provider
3. Contexts are merged into `dict[str, str]`
4. Each section formatted as:
   ```
   # Section Name
   section content
   ```
5. Prepended to system prompt
6. Sent to LLM

## See Also

- **Examples**: `examples/sdk/context_providers/`
- **Integration Guide**: `docs/api/integration-guide.md`
- **Protocol Source**: `src/consoul/sdk/protocols.py`
- **Tests**: `tests/sdk/test_context_protocol.py`

## Support

- **Issues**: https://github.com/goatbytes/consoul/issues
- **Discussions**: https://github.com/goatbytes/consoul/discussions
- **Documentation**: https://docs.consoul.ai

---

**Version**: Consoul v0.5.0+
**Last Updated**: 2024-12-18

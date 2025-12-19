# Context Provider Examples

This directory contains example implementations of the **ContextProvider protocol** for domain-specific AI agents.

## What are Context Providers?

Context Providers enable dynamic injection of domain-specific knowledge into AI system prompts at runtime. Instead of static prompts, you can query databases, APIs, or other data sources to provide contextually-relevant information to the AI.

## Quick Start

```python
from consoul import Consoul
from examples.sdk.context_providers.legal_context_provider import (
    LegalContextProvider,
    MockCaseLawDatabase,
)

# Initialize your data source
case_db = MockCaseLawDatabase()

# Create a context provider
provider = LegalContextProvider("California", case_db)

# Use it with Consoul
console = Consoul(
    model="gpt-4o",
    system_prompt="You are a legal assistant...",
    context_providers=[provider],  # Dynamic context injection!
    tools=False
)

# Context is automatically injected for each query
response = console.chat("What are the rules for construction injuries?")
```

## Examples in This Directory

### 1. Legal AI (`legal_context_provider.py`)
**Domain:** Workers' Compensation Law
**Data Source:** Case Law Database
**Use Case:** Legal assistant with jurisdiction-specific precedents

**Key Features:**
- Query-aware case law retrieval
- Jurisdiction-specific context
- Citation formatting for legal responses

**Run Example:**
```bash
export OPENAI_API_KEY=your-key-here
python examples/sdk/context_providers/legal_context_provider.py
```

### 2. Medical Chatbot (`medical_context_provider.py`)
**Domain:** Patient Care
**Data Source:** Electronic Health Records (EHR)
**Use Case:** Medical assistant with patient-specific context

**Key Features:**
- Patient demographics and medical history
- Current medications and allergies
- Recent vital signs
- HIPAA compliance considerations

**Run Example:**
```bash
export ANTHROPIC_API_KEY=your-key-here
python examples/sdk/context_providers/medical_context_provider.py
```

### 3. Customer Support (`crm_context_provider.py`)
**Domain:** Enterprise Software Support
**Data Source:** CRM System
**Use Case:** Support bot with customer account context

**Key Features:**
- Customer tier and product information
- Support history and ticket tracking
- Product usage metrics
- SLA-aware response priorities

**Run Example:**
```bash
export OPENAI_API_KEY=your-key-here
python examples/sdk/context_providers/crm_context_provider.py
```

## When to Use Context Providers

### Use Context Providers When:
✅ You need **dynamic** context that changes based on queries
✅ Your context comes from **external sources** (databases, APIs)
✅ You want **query-aware** context injection
✅ You're building **domain-specific** AI agents
✅ You need **stateful** context tracking across conversations

### Use Static Prompts When:
❌ Your context is **static** and doesn't change
❌ You have **small** amounts of context (< 500 tokens)
❌ Context is **file-based** and known at initialization
❌ You're building **general-purpose** assistants

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
            Dictionary mapping section names to content strings
        """
        ...
```

Any class with a `get_context()` method matching this signature automatically implements the protocol (structural typing).

## Creating Your Own Provider

```python
class MyContextProvider:
    """Your custom context provider."""

    def __init__(self, config):
        # Initialize your data source
        self.db = MyDatabase(config)

    def get_context(self, query=None, conversation_id=None):
        # Query your data source
        data = self.db.search(query)

        # Return formatted context
        return {
            "domain_knowledge": "Relevant domain info...",
            "query_specific_data": data,
            "timestamp": datetime.now().isoformat(),
        }

# Usage
provider = MyContextProvider(config)
console = Consoul(
    model="gpt-4o",
    system_prompt="You are an AI assistant...",
    context_providers=[provider]
)
```

## Multiple Providers

You can use multiple context providers together:

```python
console = Consoul(
    model="gpt-4o",
    system_prompt="You are a comprehensive assistant...",
    context_providers=[
        KnowledgeBaseProvider(),
        UserProfileProvider(user_id),
        ComplianceProvider(regulations),
    ]
)
```

Contexts from all providers are merged before building the system prompt.

## Best Practices

### 1. Keep Context Concise
- Target: < 2000 tokens per provider
- LLMs have token limits (~8K-128K depending on model)
- More context ≠ better responses

### 2. Handle Errors Gracefully
```python
def get_context(self, query=None, conversation_id=None):
    try:
        data = self.api.fetch_data(query)
        return {"data": data}
    except APIError as e:
        # Log error, return partial context
        logger.warning(f"API failed: {e}")
        return {"error": "Data unavailable"}
```

The SDK will catch exceptions and continue with partial context from other providers.

### 3. Security Considerations
- **Sanitize** all data before returning from `get_context()`
- **Don't expose** sensitive credentials or internal IDs
- **Validate** input query strings to prevent injection attacks
- **Log** context generation for audit trails

### 4. Performance Optimization
- **Cache** frequently-used context
- **Limit** database queries (use indexes, pagination)
- **Async** for I/O-bound operations (if using async SDK methods)
- **Monitor** context generation latency

## Documentation

- **Protocol Definition:** `src/consoul/sdk/protocols.py`
- **Full Guide:** `docs/guides/context-providers.md`
- **Integration Guide:** `docs/api/integration-guide.md`

## Support

For questions or issues:
- GitHub Issues: https://github.com/goatbytes/consoul/issues
- Documentation: https://docs.consoul.ai

---

**Note:** These examples use mock data sources for demonstration. Production implementations should connect to real databases/APIs with proper authentication, error handling, and security measures.

# Integration Guide

Real-world guide for integrating Consoul SDK into your Python projects.

## Quick Integration Checklist

Before integrating Consoul, consider:

- ✅ **Dependencies**: Consoul adds ~19 core dependencies (LangChain ecosystem)
- ✅ **Install Size**: ~200MB+ with all dependencies
- ✅ **Python Version**: Requires Python 3.10+
- ✅ **API Keys**: Need keys for your chosen provider(s)
- ✅ **File System**: Creates `~/.config/consoul/` and `~/.local/share/consoul/`

## Installation for Projects

### As a Project Dependency

Add to your `requirements.txt`:

```txt
consoul>=0.2.2
```

Or `pyproject.toml`:

```toml
[project]
dependencies = [
    "consoul>=0.2.2",
]
```

Or with Poetry:

```bash
poetry add consoul
```

### Virtual Environment (Recommended)

Always use a virtual environment to avoid dependency conflicts:

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Consoul
pip install consoul
```

## Common Integration Patterns

### 1. Standalone Scripts

Perfect for automation, CLI tools, or one-off scripts:

```python
#!/usr/bin/env python3
"""Analyze code and generate report."""

from consoul import Consoul

def main():
    analyzer = Consoul(
        tools=["grep", "code_search", "read"],
        persist=False  # Don't save conversation history
    )

    result = analyzer.chat("Find all TODO comments and summarize them")
    print(result)

if __name__ == "__main__":
    main()
```

**Why `persist=False`?** Prevents creating conversation history files for one-off scripts.

### 2. Web Services / APIs

For FastAPI, Flask, Django, etc.:

```python
from fastapi import FastAPI
from consoul import Consoul

app = FastAPI()

# Create shared instance (optional)
# Or create per-request for better isolation
code_assistant = Consoul(
    tools=["grep", "code_search"],
    persist=False,  # Don't persist in services
    system_prompt="You are a code assistant API. Be concise."
)

@app.post("/analyze")
async def analyze_code(query: str):
    response = code_assistant.ask(query, show_tokens=True)
    return {
        "response": response.content,
        "tokens": response.tokens,
        "model": response.model
    }
```

**Best Practices for Services:**
- Set `persist=False` to avoid database writes
- Consider creating new `Consoul()` instances per-request for isolation
- Monitor token usage with `console.last_cost`
- Set appropriate timeouts for LLM calls

### 3. Long-Running Applications

For daemons, background workers, or services:

```python
import logging
from consoul import Consoul

logger = logging.getLogger(__name__)

class AIAgent:
    def __init__(self):
        self.console = Consoul(
            tools=["bash", "grep"],
            persist=False,
            temperature=0.3
        )

    def process_task(self, task: str) -> str:
        try:
            result = self.console.chat(task)

            # Log token usage
            cost = self.console.last_cost
            logger.info(
                f"Task completed. "
                f"Tokens: {cost['total_tokens']}, "
                f"Est. cost: ${cost['estimated_cost']:.4f}"
            )

            return result
        except Exception as e:
            logger.error(f"Task failed: {e}")
            raise

    def reset_context(self):
        """Clear conversation history between tasks."""
        self.console.clear()

# Usage
agent = AIAgent()
result = agent.process_task("List Python files")
agent.reset_context()  # Fresh context for next task
```

### 4. Custom Tool Integration

Add your own tools alongside Consoul's built-in tools:

```python
from consoul import Consoul
from langchain_core.tools import tool
import requests

@tool
def get_api_status(service: str) -> str:
    """Check if an API service is online."""
    try:
        response = requests.get(f"https://{service}/health", timeout=5)
        return f"{service} is {'online' if response.ok else 'offline'}"
    except Exception as e:
        return f"{service} is offline: {e}"

# Mix custom tools with built-in tools
console = Consoul(tools=[get_api_status, "bash", "grep"])

# AI can now use your custom tool
console.chat("Check if api.example.com is online")
```

### 5. Multiple Consoul Instances

Use different instances for different purposes:

```python
from consoul import Consoul

# Code reviewer (safe, read-only tools)
reviewer = Consoul(
    tools="safe",
    system_prompt="You are a code reviewer. Find issues.",
    temperature=0.3
)

# Code writer (file editing enabled)
writer = Consoul(
    tools=["create_file", "edit_lines", "bash"],
    system_prompt="You are a code generator. Write clean code.",
    temperature=0.7
)

# Research assistant (web tools only)
researcher = Consoul(
    tools=["web_search", "read_url"],
    system_prompt="You are a research assistant. Cite sources."
)

# Use each for specific tasks
issues = reviewer.chat("Review this file for bugs")
researcher.chat("What are best practices for FastAPI?")
writer.chat("Create a FastAPI endpoint for user auth")
```

## Domain-Specific Context Customization

### Overview

Consoul's prompt builder supports fine-grained control over system context injection, enabling domain-specific applications beyond coding assistants. Perfect for legal AI, medical chatbots, customer support, and other specialized use cases.

**Key Features:**
- **Granular Environment Context**: Select specific environment info (OS, shell, directory, datetime, git)
- **Custom Context Sections**: Inject domain-specific data (case law, patient records, product info)
- **Profile-Free SDK Mode**: Clean prompts by default with opt-in context

### Granular Environment Context

Control exactly which environment information appears in system prompts:

```python
from consoul.ai.prompt_builder import build_enhanced_system_prompt

# Minimal context - just timestamp (e.g., medical records)
prompt = build_enhanced_system_prompt(
    "You are a medical assistant.",
    include_datetime_info=True,  # Only include timestamp
    include_os_info=False,       # No OS details
    include_git_info=False,      # No git context
    auto_append_tools=False,     # Chat-only mode
)
```

**Available Granular Flags:**
- `include_os_info`: OS/platform information
- `include_shell_info`: Shell type (zsh, bash, etc.)
- `include_directory_info`: Current working directory
- `include_datetime_info`: Current date/time with timezone
- `include_git_info`: Git repository details

**Default Behavior:** All flags default to `False` for clean, profile-free SDK usage.

### Custom Context Sections

Inject domain-specific context as structured sections:

```python
from consoul.ai.prompt_builder import build_enhanced_system_prompt

# Legal AI with case law context
prompt = build_enhanced_system_prompt(
    "You are a workers' compensation legal assistant for California.",
    context_sections={
        "jurisdiction": "California workers' compensation law",
        "case_law": "Recent precedents from 2024: Case A vs Company B...",
        "client_background": "Construction industry, injured worker claims",
    },
    include_os_info=False,  # No environment noise
    auto_append_tools=False,  # Chat-only mode
)

# Medical chatbot with patient context
prompt = build_enhanced_system_prompt(
    "You are a medical assistant providing patient care guidance.",
    context_sections={
        "patient_demographics": "Age: 45, Gender: M, Weight: 180lbs",
        "medical_history": "Hypertension (2020), Type 2 Diabetes (2022)",
        "current_medications": "Metformin 500mg BID, Lisinopril 10mg QD",
    },
    include_datetime_info=True,  # Timestamp for medical records
    auto_append_tools=False,
)

# Customer support with product context
prompt = build_enhanced_system_prompt(
    "You are a customer support agent for TechCorp.",
    context_sections={
        "customer_tier": "Premium",
        "product_line": "Enterprise Software Suite",
        "common_issues": "License activation, SSO integration, API rate limits",
    },
    auto_append_tools=False,
)
```

**Section Formatting:**
- Dict keys become section headers (e.g., `patient_demographics` → `# Patient Demographics`)
- Underscores are replaced with spaces and title-cased
- Sections maintain insertion order (Python 3.7+)
- Context ordering: Environment → Custom Sections → Base Prompt

### Using with Consoul SDK

Integrate custom prompts with the Consoul SDK:

```python
from consoul import Consoul
from consoul.ai.prompt_builder import build_enhanced_system_prompt

# Legal AI application
legal_prompt = build_enhanced_system_prompt(
    "You are a workers' compensation legal assistant.",
    context_sections={
        "jurisdiction": "California law",
        "case_law_database": load_case_law(),  # Your data
    },
    auto_append_tools=False,
)

console = Consoul(
    model="gpt-4o",
    system_prompt=legal_prompt,
    persist=True,
    db_path="~/legal-ai/history.db",
    tools=False,  # Chat-only mode
)

response = console.chat("Analyze this injury claim...")
```

### Backward Compatibility

Legacy parameters are still supported for CLI/TUI usage:

```python
# Legacy: enables ALL system info (OS, shell, directory, datetime)
prompt = build_enhanced_system_prompt(
    "You are a coding assistant.",
    include_env_context=True,  # All system context
    include_git_context=True,  # Git repository info
)

# New approach: granular control
prompt = build_enhanced_system_prompt(
    "You are a coding assistant.",
    include_os_info=True,
    include_directory_info=True,
    include_git_info=True,
)
```

**Migration Guide:**
- `include_env_context=True` → Use granular flags (`include_os_info`, `include_shell_info`, etc.)
- `include_git_context=True` → Use `include_git_info=True`
- Legacy parameters take precedence if provided

### Real-World Use Cases

#### Legal AI System

```python
from consoul import Consoul
from consoul.ai.prompt_builder import build_enhanced_system_prompt

def create_legal_assistant(jurisdiction: str, case_data: dict):
    prompt = build_enhanced_system_prompt(
        f"You are a legal assistant specializing in {jurisdiction} law.",
        context_sections={
            "jurisdiction": jurisdiction,
            "case_law": case_data["precedents"],
            "client_background": case_data["client_info"],
            "relevant_statutes": case_data["statutes"],
        },
        include_datetime_info=True,  # Legal timestamp
        auto_append_tools=False,
    )

    return Consoul(
        model="gpt-4o",
        system_prompt=prompt,
        temperature=0.3,  # Precise legal analysis
        persist=True,
    )
```

#### Medical Chatbot

```python
def create_medical_assistant(patient_record: dict):
    prompt = build_enhanced_system_prompt(
        "You are a medical assistant providing care guidance.",
        context_sections={
            "patient_demographics": format_demographics(patient_record),
            "medical_history": format_history(patient_record),
            "current_medications": format_medications(patient_record),
            "allergies": patient_record.get("allergies", "None"),
        },
        include_datetime_info=True,  # Critical for medical records
        auto_append_tools=False,
    )

    return Consoul(
        model="claude-3-5-sonnet-20241022",
        system_prompt=prompt,
        temperature=0.2,  # Careful medical responses
        persist=True,
    )
```

#### Customer Support Bot

```python
def create_support_agent(customer: dict, product: str):
    prompt = build_enhanced_system_prompt(
        f"You are a customer support agent for {product}.",
        context_sections={
            "customer_tier": customer["tier"],
            "account_status": customer["status"],
            "product_version": customer["product_version"],
            "common_issues": load_known_issues(product),
            "support_history": customer["recent_tickets"],
        },
        auto_append_tools=False,
    )

    return Consoul(
        model="gpt-4o-mini",
        system_prompt=prompt,
        temperature=0.7,  # Friendly responses
        persist=True,
    )
```

### Best Practices

1. **Minimize Context**: Only include relevant information to reduce token usage
2. **Structure Data**: Use clear, consistent formatting in custom sections
3. **Update Context**: Rebuild prompts when domain data changes
4. **Test Thoroughly**: Verify context appears correctly in system prompts
5. **Monitor Tokens**: Track token usage with custom context sections

## Configuration Management

### Environment Variables

Recommended approach for API keys:

```python
import os
from consoul import Consoul

# Consoul automatically reads from environment
# OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.

console = Consoul(model="gpt-4o")
```

Set in your environment:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### Programmatic Configuration

Override settings per-instance:

```python
from consoul import Consoul

console = Consoul(
    model="gpt-4o",
    temperature=0.5,
    system_prompt="Custom prompt",
    api_key="sk-...",  # Override environment variable
)
```

## Migration from Profiles (SDK v0.5.0+)

### Profile Removal Notice

⚠️ **BREAKING CHANGE**: The `profile` parameter has been removed from Consoul SDK in v0.5.0.

**Why?** Profiles couple SDK to TUI/CLI workflow concepts (coding assistant behavior, environment context injection). This prevents Consoul from being a general-purpose LLM SDK for domain-specific applications (legal AI, medical chatbots, customer support, etc.).

**What changed:**
- ✅ **SDK**: Profile-free (explicit parameters only) - `profile` parameter removed
- ✅ **TUI/CLI**: Profiles continue working as a convenience feature
- ✅ **Config files**: Can still define profiles for TUI/CLI usage
- ❌ **Removed**: `profile` parameter no longer accepted in SDK `Consoul()` constructor

### Migration Path

#### Before (Profile-Based SDK) ❌

```python
from consoul import Consoul

# Old approach: relies on profile configuration
console = Consoul(profile="default")
console = Consoul(profile="creative", temperature=0.8)
```

**Problems:**
- Implicit configuration from profile files
- Assumes coding assistant domain (env/git context injection)
- Requires understanding profile system
- Couples library to application layer

#### After (Profile-Free SDK) ✅

```python
from consoul import Consoul

# New approach: explicit parameters
console = Consoul(
    model="claude-sonnet-4",
    temperature=0.7,
    system_prompt="You are a helpful assistant.",
    tools=True,
    persist=True,
)

# Domain-specific example (legal AI)
console = Consoul(
    model="gpt-4o",
    temperature=0.3,
    system_prompt="You are a workers' compensation legal assistant...",
    tools=False,  # Chat-only
    persist=True,
    db_path="~/legal-ai/history.db",
)
```

**Benefits:**
- Explicit, self-documenting code
- No hidden configuration
- Works for any domain (legal, medical, support, etc.)
- Clean separation: SDK = library, TUI/CLI = application

### Migrating Profile Configurations

If you have existing profiles in `~/.config/consoul/config.yaml`, translate them to explicit SDK parameters:

#### Profile Definition

```yaml
# config.yaml
profiles:
  production:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
      temperature: 0.3
    system_prompt: "You are a production assistant."
    conversation:
      persist: true
      summarize: false
```

#### SDK Translation

```python
# Old (removed in v0.5.0)
# console = Consoul(profile="production")  # ❌ TypeError

# New (explicit)
console = Consoul(
    model="claude-3-5-sonnet-20241022",  # From profile.model
    temperature=0.3,                      # From profile.model.temperature
    system_prompt="You are a production assistant.",  # From profile.system_prompt
    persist=True,                         # From profile.conversation.persist
    summarize=False,                      # From profile.conversation.summarize
)
```

### Profile Mapping Reference

| Profile Field | SDK Parameter | Example |
|--------------|---------------|---------|
| `profile.model.model` | `model` | `"gpt-4o"` |
| `profile.model.temperature` | `temperature` | `0.7` |
| `profile.system_prompt` | `system_prompt` | `"You are..."` |
| `profile.conversation.persist` | `persist` | `True` |
| `profile.conversation.summarize` | `summarize` | `False` |
| `profile.conversation.summarize_threshold` | `summarize_threshold` | `20` |
| `profile.conversation.keep_recent` | `keep_recent` | `10` |
| `profile.conversation.summary_model` | `summary_model` | `"gpt-4o-mini"` |
| `profile.conversation.db_path` | `db_path` | `"~/history.db"` |

### Using Profiles in TUI/CLI (Still Supported)

Profiles **continue to work** in TUI/CLI as a convenience feature:

```bash
# TUI application - profiles still work
consoul  # Uses default profile

# CLI mode - profiles still work
consoul chat --profile creative

# Config management
consoul config profiles list
consoul config profiles set creative
```

**Key point:** Profiles are a **TUI/CLI feature**, not an SDK feature. If you're building a library or domain-specific application, use explicit SDK parameters instead.

### Custom System Prompts

For advanced prompt building with domain-specific context:

```python
from consoul import Consoul
from consoul.ai.prompt_builder import build_enhanced_system_prompt

# Build custom prompt with domain context
legal_prompt = build_enhanced_system_prompt(
    "You are a workers' compensation legal assistant.",
    context_sections={
        "jurisdiction": "California law",
        "case_law": load_case_law_database(),
    },
    include_os_info=False,  # No environment noise
    auto_append_tools=False,
)

console = Consoul(
    model="gpt-4o",
    system_prompt=legal_prompt,
    tools=False,
)
```

See [Domain-Specific Context Customization](#domain-specific-context-customization) for details.

### Timeline

- **v0.4.0**: Profile parameter deprecated with warnings (SOUL-289 Phase 1)
- **v0.5.0** (Current): Profile parameter removed from SDK (SOUL-289 Phase 3, breaking change)

### Migration Checklist

- [ ] Identify all uses of `profile` parameter in SDK code (will raise `TypeError` in v0.5.0)
- [ ] Translate profile configurations to explicit parameters
- [ ] Update imports: `ProfileConfig` is now in `consoul.tui.profiles` (TUI/CLI only)
- [ ] Update documentation and examples
- [ ] Consider domain-specific prompt customization (if applicable)
- [ ] Test with v0.5.0 to ensure no `TypeError` exceptions

### Getting Help

Questions about migration?
- **[GitHub Discussions](https://github.com/goatbytes/consoul/discussions)** - Migration help
- **[Migration Guide](https://docs.consoul.ai/migration/profiles)** - Detailed guide
- **[Examples](https://github.com/goatbytes/consoul/tree/main/examples/sdk)** - Profile-free examples

---

### Profile-Based Configuration (TUI/CLI Only)

**Note:** The following section applies to TUI/CLI usage only. SDK users should use explicit parameters instead.

Create `~/.config/consoul/config.yaml` for TUI/CLI:

```yaml
profiles:
  production:
    model: claude-3-5-sonnet-20241022
    temperature: 0.3

  development:
    model: gpt-4o
    temperature: 0.7

  local:
    model: llama3.2
    provider: ollama
```

Use profiles in code:

```python
from consoul import Consoul

# Use specific profile
console = Consoul(profile="production")

# Override profile settings
console = Consoul(profile="production", temperature=0.5)
```

## Dependency Considerations

### What Consoul Installs

Consoul has ~19 core dependencies:

- **LangChain ecosystem** (langchain, langchain-community, langchain-openai, etc.)
- **AI Providers** (anthropic, openai, google-ai-generativelanguage)
- **Tools** (tiktoken, tree-sitter, grep-ast, duckduckgo-search)
- **Utilities** (pydantic, rich, pyyaml, requests)

### Potential Conflicts

If your project already uses:

- **LangChain**: Ensure version compatibility (Consoul requires langchain>=1.0.7)
- **Pydantic**: Consoul requires pydantic>=2.12.4
- **Tiktoken**: Consoul requires tiktoken>=0.12.0

### Minimal Installation

If you only need the SDK (no TUI):

```bash
pip install consoul  # Core SDK only
```

## Error Handling

### Graceful Degradation

```python
from consoul import Consoul

def safe_chat(query: str) -> str:
    try:
        console = Consoul(persist=False)
        return console.chat(query)
    except ValueError as e:
        # Configuration error
        return f"Configuration error: {e}"
    except Exception as e:
        # API error, network error, etc.
        return f"Error: {e}"

result = safe_chat("Hello")
```

### Timeout Handling

For web services, set timeouts:

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Use with timeout
try:
    with timeout(30):
        result = console.chat("Complex query...")
except TimeoutError:
    print("LLM request timed out")
```

## Performance Tips

### 1. Reuse Instances

Creating `Consoul()` instances has overhead. Reuse when possible:

```python
# ❌ Don't do this
def query(text):
    console = Consoul()  # Creates new instance each time
    return console.chat(text)

# ✅ Do this
console = Consoul()

def query(text):
    return console.chat(text)
```

### 2. Disable Persistence for Stateless Operations

```python
# Faster for one-off queries
console = Consoul(persist=False)
```

### 3. Use Appropriate Tools

Only enable tools you need:

```python
# ❌ All tools (slower, more tokens)
console = Consoul(tools=True)

# ✅ Only needed tools (faster)
console = Consoul(tools=["grep", "code_search"])
```

### 4. Monitor Token Usage

```python
console = Consoul()
response = console.chat("Query...")

cost = console.last_cost
print(f"Tokens used: {cost['total_tokens']}")
print(f"Estimated cost: ${cost['estimated_cost']:.4f}")
```

## Security Considerations

### Tool Permissions

Start with minimal permissions:

```python
# ✅ Safe (read-only)
console = Consoul(tools="safe")

# ⚠️ Caution (file operations)
console = Consoul(tools="caution")

# ⚠️ Dangerous (destructive operations)
console = Consoul(tools="dangerous")
```

### API Key Management

Never hardcode API keys:

```python
# ❌ DON'T
console = Consoul(api_key="sk-hardcoded-key")

# ✅ DO - Use environment variables
console = Consoul()  # Reads from env

# ✅ DO - Load from secrets manager
import boto3
secrets = boto3.client('secretsmanager')
api_key = secrets.get_secret_value(SecretId='openai-key')['SecretString']
console = Consoul(api_key=api_key)
```

### Input Validation

Sanitize user input before passing to AI:

```python
def sanitize_input(text: str) -> str:
    # Remove potential prompt injection attempts
    text = text.replace("Ignore previous instructions", "")
    text = text.strip()[:1000]  # Limit length
    return text

user_query = sanitize_input(user_input)
result = console.chat(user_query)
```

## Testing

### Unit Tests

Mock Consoul for testing:

```python
from unittest.mock import Mock, patch
import pytest

def process_query(query: str) -> str:
    from consoul import Consoul
    console = Consoul(persist=False)
    return console.chat(query)

def test_process_query():
    with patch('consoul.Consoul') as MockConsoul:
        mock_console = Mock()
        mock_console.chat.return_value = "Mocked response"
        MockConsoul.return_value = mock_console

        result = process_query("test")
        assert result == "Mocked response"
```

### Integration Tests

Test with real API (use test keys):

```python
import pytest
from consoul import Consoul

@pytest.mark.integration
def test_real_chat():
    console = Consoul(
        model="gpt-4o-mini",  # Cheaper model for testing
        persist=False
    )
    result = console.chat("What is 2+2?")
    assert "4" in result
```

## Troubleshooting

### Common Issues

**1. "No API key found"**
```python
# Solution: Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."
```

**2. "ModuleNotFoundError: No module named 'rich'"**
```bash
# Solution: Upgrade to v0.2.1+
pip install --upgrade consoul
```

**3. "Profile 'xyz' not found"**
```python
# Solution: Use valid profile or create config
consoul init
```

**4. Large dependency footprint**
```bash
# Solution: Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install consoul
```

## Examples Repository

See [GitHub examples](https://github.com/goatbytes/consoul/tree/main/examples) for:

- FastAPI integration
- Django integration
- Background worker example
- Custom tool examples
- Testing examples

## Next Steps

- [Tutorial](tutorial.md) - Step-by-step SDK learning
- [Tools Documentation](tools.md) - Master built-in tools
- [API Reference](reference.md) - Complete API docs
- [Building Agents](agents.md) - Create specialized agents

## Support

- **[GitHub Issues](https://github.com/goatbytes/consoul/issues)** - Report bugs
- **[Discussions](https://github.com/goatbytes/consoul/discussions)** - Ask questions
- **[Discord](https://discord.gg/consoul)** - Community chat

---

**Ready to integrate?** Start with a [minimal example](#1-standalone-scripts) and expand from there.

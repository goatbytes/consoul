# Consoul SDK Simplification Proposal

## Goal
Make it **ridiculously easy** to add AI chat to any Python application.

## Current State (❌ Too Complex)

**Smallest working example: 173 lines**

```python
# Requires understanding:
# - Configuration loading with fallbacks
# - Tool registry setup
# - Approval providers
# - LangChain model initialization
# - Conversation history management
# - Async patterns

from consoul.ai.tools import RiskLevel, ToolRegistry, bash_execute
from consoul.ai.tools.permissions import PermissionPolicy
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config.loader import load_config
from consoul.config.models import ToolConfig
# ... 168 more lines
```

## Proposed State (✅ Simple)

### Tier 1: Absolute Minimal (5 lines)

```python
from consoul import Consoul

console = Consoul()
response = console.chat("What is 2+2?")
print(response)
```

**Features:**
- Auto-detects API keys from environment
- Uses default profile
- Returns plain string
- No configuration needed

### Tier 2: Quick Customization (15 lines)

```python
from consoul import Consoul

console = Consoul(
    model="gpt-4o",              # Auto-detect provider
    profile="code-review",        # Use built-in profile
    tools=True,                   # Enable tool calling
    temperature=0.7,
    system_prompt="You are helpful.",
)

# Stateful conversation
console.chat("What files are here?")
console.chat("Read the first one")  # Remembers context

# Rich response
response = console.ask("Explain", show_tokens=True)
print(f"Used {response.tokens} tokens")
```

### Tier 3: Full SDK Control (Advanced)

Current SDK remains unchanged for power users who need:
- Custom approval providers
- Custom audit loggers
- Fine-grained tool configuration
- Multi-provider scenarios

## Implementation

### 1. Create `Consoul` Convenience Class

**Location:** `src/consoul/sdk.py`

```python
"""High-level SDK for easy Consoul integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from consoul.ai import ConversationHistory, get_chat_model
from consoul.ai.tools import ToolRegistry, bash_execute, RiskLevel
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config import load_config
from consoul.config.models import ToolConfig, PermissionPolicy


class ConsoulResponse:
    """Response from Consoul chat/ask methods."""

    def __init__(self, content: str, tokens: int = 0, model: str = ""):
        self.content = content
        self.tokens = tokens
        self.model = model

    def __str__(self) -> str:
        return self.content


class Consoul:
    """High-level Consoul SDK interface.

    Examples:
        Basic chat:
        >>> console = Consoul()
        >>> console.chat("Hello!")
        'Hi! How can I help you?'

        With tools:
        >>> console = Consoul(tools=True)
        >>> console.chat("List files")

        Custom model:
        >>> console = Consoul(model="gpt-4o")
        >>> response = console.ask("Explain", show_tokens=True)
        >>> print(f"Tokens: {response.tokens}")
    """

    def __init__(
        self,
        model: str | None = None,
        profile: str = "default",
        tools: bool = False,
        temperature: float | None = None,
        system_prompt: str | None = None,
        persist: bool = True,
    ):
        """Initialize Consoul SDK.

        Args:
            model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet").
                   Auto-detects provider. Defaults to profile's model.
            profile: Profile name to use (default: "default")
            tools: Enable tool calling with CLI approval (default: False)
            temperature: Override temperature (0.0-2.0)
            system_prompt: Override system prompt
            persist: Save conversation history (default: True)
        """
        # Load configuration
        self.config = load_config()

        # Get profile
        if profile not in self.config.profiles:
            from consoul.config.profiles import get_builtin_profiles
            builtin = get_builtin_profiles()
            if profile in builtin:
                # Use builtin profile
                self.profile = self.config.profiles.get(
                    profile,
                    self.config._create_profile_from_dict(builtin[profile])
                )
            else:
                raise ValueError(f"Profile '{profile}' not found")
        else:
            self.profile = self.config.profiles[profile]

        # Override temperature if specified
        if temperature is not None:
            self.profile.model.temperature = temperature

        # Override system prompt if specified
        if system_prompt is not None:
            self.profile.system_prompt = system_prompt

        # Initialize model
        if model:
            self.model = get_chat_model(model, config=self.config)
            self.model_name = model
        else:
            self.model = get_chat_model(self.profile.model, config=self.config)
            self.model_name = self.profile.model.model

        # Initialize conversation history
        self.history = ConversationHistory(
            model_name=self.model_name,
            model=self.model,
            persist=persist,
            **self._get_conversation_kwargs()
        )

        # Add system prompt
        if self.profile.system_prompt:
            self.history.add_system_message(self.profile.system_prompt)

        # Initialize tools if requested
        self.tools_enabled = tools
        if tools:
            self._setup_tools()
        else:
            self.registry = None

    def _get_conversation_kwargs(self) -> dict[str, Any]:
        """Get ConversationHistory kwargs from profile."""
        conv = self.profile.conversation
        kwargs = {
            "db_path": conv.db_path,
            "summarize": conv.summarize,
            "summarize_threshold": conv.summarize_threshold,
            "keep_recent": conv.keep_recent,
        }

        # Handle summary_model
        if conv.summary_model:
            kwargs["summary_model"] = get_chat_model(
                conv.summary_model, config=self.config
            )

        return kwargs

    def _setup_tools(self) -> None:
        """Setup tool calling with CLI approval."""
        tool_config = ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.BALANCED,
            audit_logging=True,
        )

        approval_provider = CliApprovalProvider(show_arguments=True)

        self.registry = ToolRegistry(
            config=tool_config,
            approval_provider=approval_provider,
        )

        # Register bash tool
        self.registry.register(
            tool=bash_execute,
            risk_level=RiskLevel.CAUTION,
        )

        # Bind tools to model
        self.model = self.registry.bind_to_model(self.model)

    def chat(self, message: str) -> str:
        """Send a message and get a response.

        Args:
            message: Your message to the AI

        Returns:
            AI's response as a string
        """
        self.history.add_user_message(message)

        # Get response (streaming handled internally)
        messages = self.history.get_trimmed_messages(reserve_tokens=1000)
        response = self.model.invoke(messages)

        # Extract content
        content = response.content if hasattr(response, 'content') else str(response)

        self.history.add_assistant_message(content)
        return content

    def ask(self, message: str, show_tokens: bool = False) -> ConsoulResponse:
        """Send a message and get a rich response with metadata.

        Args:
            message: Your message
            show_tokens: Include token count in response

        Returns:
            ConsoulResponse with content, tokens, and model info
        """
        content = self.chat(message)

        tokens = 0
        if show_tokens:
            tokens = self.history.count_tokens()

        return ConsoulResponse(
            content=content,
            tokens=tokens,
            model=self.model_name,
        )

    def clear(self) -> None:
        """Clear conversation history and start fresh."""
        self.history.clear()
        if self.profile.system_prompt:
            self.history.add_system_message(self.profile.system_prompt)
```

### 2. Update `src/consoul/__init__.py`

```python
"""Consoul - AI-powered terminal assistant with rich TUI.

Brings the power of modern AI assistants directly to your terminal with a rich,
interactive TUI. Built on Textual's reactive framework and LangChain's provider
abstraction.

Quick Start:
    >>> from consoul import Consoul
    >>> console = Consoul()
    >>> console.chat("Hello!")
    'Hi! How can I help you?'
"""

__version__ = "0.1.0"
__author__ = "GoatBytes.IO"
__license__ = "Apache-2.0"

# High-level SDK
from consoul.sdk import Consoul, ConsoulResponse

__all__ = [
    "__author__",
    "__license__",
    "__version__",
    # SDK
    "Consoul",
    "ConsoulResponse",
]
```

### 3. Create Minimal Examples

**examples/sdk/minimal_chat.py** (5 lines):
```python
from consoul import Consoul

console = Consoul()
print(console.chat("What is 2+2?"))
print(console.chat("What files are in this directory?"))
```

**examples/sdk/quick_start.py** (15 lines):
```python
from consoul import Consoul

# Customize as needed
console = Consoul(
    model="gpt-4o",
    profile="code-review",
    tools=True,
    temperature=0.7,
)

# Stateful conversation
console.chat("List all Python files")
console.chat("Show me the first one")

# Rich response
response = console.ask("Summarize it", show_tokens=True)
print(f"Response: {response.content}")
print(f"Tokens: {response.tokens}")
```

**examples/sdk/custom_profile.py** (20 lines):
```python
from consoul import Consoul

# Use different profiles for different tasks
code_reviewer = Consoul(profile="code-review")
creative = Consoul(profile="creative", temperature=0.9)

# Code review
print(code_reviewer.chat("Review this function: def foo(): pass"))

# Creative writing
print(creative.chat("Write a haiku about Python"))
```

### 4. Update Documentation

**README.md Quick Start:**
```markdown
## Quick Start

### Installation
```bash
pip install consoul
export ANTHROPIC_API_KEY=your-key-here
```

### Minimal Example (5 lines)
```python
from consoul import Consoul

console = Consoul()
console.chat("What is 2+2?")
console.chat("List files in current directory")
```

### With Tools (10 lines)
```python
from consoul import Consoul

console = Consoul(
    model="gpt-4o",
    tools=True,  # Enable bash execution with approval
)

console.chat("What files are here?")
console.chat("Show me the README")
```

### Advanced: Full SDK
For advanced use cases, use the full SDK:
- [Tool Calling Integration](docs/sdk/tool-calling-integration.md)
- [Custom Approval Providers](docs/sdk/custom-approval.md)
- [Custom Audit Logging](docs/sdk/custom-audit.md)
```

## Benefits

### For New Users
- ✅ **5 lines to get started** (vs 173 lines)
- ✅ **1 import** (vs 7+ imports)
- ✅ **Zero configuration** (vs complex setup)
- ✅ **Discoverable** (`from consoul import Consoul`)

### For Existing Users
- ✅ **Full SDK unchanged** (backward compatible)
- ✅ **Progressive disclosure** (simple → advanced)
- ✅ **Better documentation** (clear tiers)

### For Library Adoption
- ✅ **Lower barrier to entry**
- ✅ **Copy-paste friendly**
- ✅ **Competes with simpler libraries** (openai, anthropic SDKs)

## Migration Path

### Phase 1: Create SDK wrapper (2-3 hours)
- Create `src/consoul/sdk.py` with `Consoul` class
- Update `__init__.py` exports
- Add basic tests

### Phase 2: Examples (1 hour)
- Create `minimal_chat.py` (5 lines)
- Create `quick_start.py` (15 lines)
- Create `custom_profile.py` (20 lines)

### Phase 3: Documentation (1-2 hours)
- Update README.md with quick start
- Add SDK tier comparison
- Update docs/sdk/ with simple examples first

## Comparison to Other Libraries

### OpenAI SDK (Current)
```python
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

### Anthropic SDK (Current)
```python
from anthropic import Anthropic
client = Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
print(message.content[0].text)
```

### Consoul SDK (Proposed)
```python
from consoul import Consoul
console = Consoul()
print(console.chat("Hello"))
```

**Even simpler than official SDKs!** ✨

## Trade-offs

### Pros
- Significantly easier onboarding
- Better competitive positioning
- Higher adoption potential
- Clearer value proposition

### Cons
- Additional code to maintain (~200 lines)
- Another abstraction layer
- Potential confusion with TUI vs SDK

### Mitigation
- Keep SDK class small and focused
- Excellent documentation with tier comparison
- Clear separation: `Consoul()` = SDK, `consoul` command = TUI

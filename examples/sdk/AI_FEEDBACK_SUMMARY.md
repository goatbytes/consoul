# AI Feedback on Consoul SDK Simplification

## Overview

Asked OpenAI Codex (GPT-5) to review the proposed SDK simplification approach.

## Prompt

Reviewed the proposal to simplify Consoul SDK from 173 lines (current) to 5 lines (proposed) with a three-tier design.

## Codex AI Feedback (GPT-5)

### 1. Auto-Detection Approach ✅
> "Auto-detecting config and condensing setup to `Consoul()` lowers the barrier and mirrors how OpenAI/Anthropic clients feel—good direction."

**Action Items:**
- Document what defaults are applied (model, profile, retries, approval flow)
- Add lightweight introspection: `console.settings` property
- Make hidden wiring inspectable for enterprise teams

### 2. Progressive Exposure ✅
> "Progressive exposure works best if each layer composes with the next: Minimal returns a fully functional client, Quick is just `Consoul(profile=…, tools=…)`, Full accepts pluggable interfaces without changing usage elsewhere."

**Action Items:**
- Keep ONE class that accepts richer kwargs
- Avoid separate "advanced SDK"
- Use builder-style helpers for complexity
- Ensure each tier composes cleanly

### 3. Method Naming ⚠️
> "`console.chat()` communicates 'send one chat turn,' but many SDKs use `client.chat.completions.create` or `client.responses.create`. Consider `console.ask()` or `console.run()` for single-shot calls, and a `session = console.session()` for multi-turn state."

**Recommendations:**
- Consider `console.ask()` for single-shot
- Consider `console.run()` for execution-focused
- If `chat()` sticks, clearly document semantics (streaming? multi-turn?)
- Maybe: `session = console.session()` for explicit multi-turn

**Decision:** Implement both:
- `chat(message) -> str` - Simple, stateful (keeps history)
- `ask(message, show_tokens=False) -> ConsoulResponse` - Rich response with metadata

### 4. SDK Patterns to Follow 💡

#### From OpenAI
- Fluent client creation
- Transport injection: `Consoul(api_key=None, http_client=None)`

#### From Anthropic
- `with_default_params` patterns
- Override model/temperature once for all calls

#### From LangChain
- Tool registry abstractions
- Decorators to register Python callables as tools
- Context managers for temporary tool scopes

### 5. Additional Improvements 💡

#### A. Tool Discovery
```python
# Auto-discover with clear warnings
console = Consoul()  # Discovers available tools

# Opt-out for enterprise
console = Consoul(discover_tools=False)
```

#### B. CLI Equivalent
```bash
consoul chat "What files are here?"
```
Mirrors the minimal code path for quick smoke tests.

#### C. Framework Snippets
Ship ready-to-copy snippets for:
- FastAPI middleware
- Notebook helpers
- Common integration patterns

#### D. Structured Responses
```python
# Parse response as structured data
result = console.chat("List files", format=Dict[str, Any])
```

#### E. Inline Telemetry
```python
console.chat("Hello")

# Debug without verbose logging
print(console.last_request)  # API call details
print(console.last_cost)     # Token usage and cost estimate
```

## Implementation Checklist

Based on Codex feedback:

### Core SDK
- [x] Create `Consoul` class in `src/consoul/sdk.py`
- [ ] Implement `chat(message) -> str` method
- [ ] Implement `ask(message, show_tokens=False) -> ConsoulResponse` method
- [ ] Add `console.settings` property for introspection
- [ ] Add `console.last_request` property
- [ ] Add `console.last_cost` property
- [ ] Support `format=Dict[str, Any]` parameter for structured responses
- [ ] Add `discover_tools` parameter (default: False for safety)

### OpenAI-inspired Features
- [ ] Support `api_key` parameter override
- [ ] Support custom `http_client` injection
- [ ] Fluent client creation pattern

### Anthropic-inspired Features
- [ ] Implement `with_default_params()` context manager or method
- [ ] Allow one-time model/temperature override

### LangChain-inspired Features
- [ ] Decorator for registering custom tools: `@console.tool`
- [ ] Context manager for temporary tool scopes

### CLI Command
- [ ] Implement `consoul chat "prompt"` command
- [ ] Mirror minimal SDK path
- [ ] Quick smoke testing capability

### Framework Integration
- [ ] FastAPI middleware example
- [ ] Jupyter notebook helper
- [ ] Streamlit integration example

### Documentation
- [ ] Quick start in README (5 lines)
- [ ] Document all defaults applied
- [ ] API reference for introspection properties
- [ ] Migration guide for existing users

## Comparison: Before vs After

### Before (173 lines)
```python
from consoul.ai.tools import RiskLevel, ToolRegistry, bash_execute
from consoul.ai.tools.permissions import PermissionPolicy
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config.loader import load_config
from consoul.config.models import ToolConfig
import argparse
import asyncio
# ... 166 more lines ...
```

### After (5 lines)
```python
from consoul import Consoul

console = Consoul()
console.chat("What is 2+2?")
console.chat("List files here")
```

### With Codex Suggestions (10 lines)
```python
from consoul import Consoul

console = Consoul(
    model="gpt-4o",
    tools=True,
    discover_tools=False,  # Opt-out of auto-discovery
)

response = console.ask("Hello", show_tokens=True)
print(f"Response: {response.content}")
print(f"Cost: {console.last_cost}")
print(f"Settings: {console.settings}")
```

## Ticket Created

**SOUL-78**: Create high-level Consoul SDK wrapper for ease of use
- **Priority**: High
- **Story Points**: 8
- **Labels**: sdk, enhancement, ux-improvement, quick-win
- **Status**: Todo

## Next Steps

1. Implement core `Consoul` class with Codex recommendations
2. Add introspection properties (settings, last_request, last_cost)
3. Create minimal examples (5, 10, 15, 20 lines)
4. Add CLI command: `consoul chat "prompt"`
5. Write comprehensive tests
6. Update documentation with quick start
7. Get early user feedback

## References

- Proposal: examples/sdk/SIMPLIFICATION_PROPOSAL.md
- Ticket: .gira/board/todo/SOUL-78.json
- Codex session: 019a7c02-e1b5-7a61-a977-d61f2234bf5a

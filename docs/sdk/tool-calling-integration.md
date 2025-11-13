# Tool Calling SDK Integration

Guide for integrating Consoul's tool calling system into host applications without TUI dependencies.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Custom Approval Provider](#custom-approval-provider)
- [Custom Audit Logger](#custom-audit-logger)
- [Configuration](#configuration)
- [Testing](#testing)
- [Examples](#examples)

## Overview

Consoul is designed as an SDK that host applications can embed. The tool calling system works in any environment:

- **CLI tools** - Terminal-based approval prompts
- **Web applications** - HTTP API approval workflows
- **IDE plugins** - Dialog-based approval
- **Headless services** - Policy-based auto-approval

The core tool system is independent of the Textual TUI, allowing full customization of approval UX and audit logging.

### When to Use Custom Integration

Use custom providers when:
- Building CLI tools (use `CliApprovalProvider`)
- Integrating into web apps (implement HTTP-based approval)
- Building IDE extensions (implement dialog-based approval)
- Implementing custom audit/compliance requirements
- Running in headless/automated environments

Use the built-in TUI when:
- Building interactive terminal applications
- Wanting rich terminal UI out-of-the-box

## Architecture

```
┌─────────────────────────────────────────────┐
│           Host Application                  │
│  (CLI tool, Web app, IDE plugin)           │
└─────────────────┬───────────────────────────┘
                  │
                  ├─► Custom ApprovalProvider
                  │   (Your UX implementation)
                  │
                  ├─► Custom AuditLogger
                  │   (Your logging backend)
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         Consoul Core (SDK)                  │
│  ┌──────────────────────────────────────┐  │
│  │ ToolRegistry                         │  │
│  │  - Tool registration                 │  │
│  │  - Approval coordination             │  │
│  │  - Security validation               │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │ Tool Implementations                 │  │
│  │  - bash_execute                      │  │
│  │  - read_file                         │  │
│  │  - Custom tools                      │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Key Components

- **ToolRegistry**: Central registry managing tools, approval, and audit
- **ApprovalProvider**: Protocol for implementing custom approval UX
- **AuditLogger**: Protocol for implementing custom audit logging
- **ToolConfig**: Configuration for tool behavior and policies

## Quick Start

### Minimal CLI Example

```python
from consoul.config.loader import load_config
from consoul.ai.tools import ToolRegistry, RiskLevel
from consoul.ai.tools.implementations import bash_execute, read_file
from consoul.ai.tools.providers import CliApprovalProvider

# Load configuration
config = load_config()

# Create CLI approval provider
approval_provider = CliApprovalProvider(verbose=True)

# Create tool registry with custom provider
registry = ToolRegistry(
    config=config.tools,
    approval_provider=approval_provider
)

# Register tools
registry.register(bash_execute, risk_level=RiskLevel.CAUTION)
registry.register(read_file, risk_level=RiskLevel.SAFE, tags=["filesystem", "readonly"])

# Use with LangChain
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
model_with_tools = registry.bind_to_model(model)

# Now the AI can use tools with CLI approval prompts
response = model_with_tools.invoke("Read README.md and list all Python files")
```

### Configuration

```yaml
# config.yaml
profiles:
  default:
    tools:
      enabled: true
      permission_policy: balanced
      audit_logging: true
```

## Custom Approval Provider

### Protocol Definition

```python
from typing import Protocol
from consoul.ai.tools.approval import ToolApprovalRequest, ToolApprovalResponse

class ApprovalProvider(Protocol):
    """Protocol for custom approval implementations."""

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        """Request approval for tool execution.

        Args:
            request: Contains tool_name, arguments, risk_level, etc.

        Returns:
            ToolApprovalResponse with approved=True/False
        """
        ...
```

### CLI Approval (Built-in)

Consoul provides `CliApprovalProvider` for terminal-based approval:

```python
from consoul.ai.tools.providers import CliApprovalProvider

# Basic usage
provider = CliApprovalProvider()

# With options
provider = CliApprovalProvider(
    show_arguments=True,  # Display tool arguments
    verbose=True          # Show risk level and context
)

registry = ToolRegistry(config.tools, approval_provider=provider)
```

Output:
```
============================================================
Tool Execution Request: bash_execute
============================================================

Arguments:
  command: ls -la

Risk Level: CAUTION

============================================================
Approve execution? (y/n):
```

### Web Approval Example

For web applications, implement HTTP-based approval:

```python
import aiohttp
from consoul.ai.tools.approval import (
    ApprovalProvider,
    ToolApprovalRequest,
    ToolApprovalResponse,
)

class WebApprovalProvider:
    """HTTP-based approval for web applications."""

    def __init__(self, approval_url: str, auth_token: str):
        self.approval_url = approval_url
        self.auth_token = auth_token

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        """Send approval request to web API."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.approval_url,
                json={
                    "tool_name": request.tool_name,
                    "arguments": request.arguments,
                    "risk_level": request.risk_level.value,
                    "tool_call_id": request.tool_call_id,
                },
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    return ToolApprovalResponse(
                        approved=False,
                        reason=f"HTTP {resp.status}"
                    )

                data = await resp.json()
                return ToolApprovalResponse(
                    approved=data["approved"],
                    reason=data.get("reason"),
                )

# Usage
provider = WebApprovalProvider(
    approval_url="https://api.example.com/tool-approval",
    auth_token="your-token"
)
registry = ToolRegistry(config.tools, approval_provider=provider)
```

### Policy-Based Auto-Approval

For headless environments, implement policy-based approval:

```python
class PolicyApprovalProvider:
    """Auto-approve based on policy rules."""

    def __init__(self, allow_safe: bool = True, allow_caution: bool = False):
        self.allow_safe = allow_safe
        self.allow_caution = allow_caution

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        """Auto-approve based on risk level."""
        from consoul.ai.tools import RiskLevel

        if request.risk_level == RiskLevel.SAFE and self.allow_safe:
            return ToolApprovalResponse(
                approved=True,
                reason="Auto-approved: SAFE risk level"
            )

        if request.risk_level == RiskLevel.CAUTION and self.allow_caution:
            return ToolApprovalResponse(
                approved=True,
                reason="Auto-approved: CAUTION risk level"
            )

        return ToolApprovalResponse(
            approved=False,
            reason=f"Policy denied: {request.risk_level.value}"
        )
```

## Custom Audit Logger

### Protocol Definition

```python
from typing import Protocol
from consoul.ai.tools.audit import AuditEvent

class AuditLogger(Protocol):
    """Protocol for custom audit logging."""

    async def log_event(self, event: AuditEvent) -> None:
        """Log an audit event.

        Args:
            event: Contains timestamp, event_type, tool_name, arguments, result, etc.
        """
        ...
```

### Database Audit Logger

```python
import asyncpg
from consoul.ai.tools.audit import AuditLogger, AuditEvent

class PostgresAuditLogger:
    """Audit logger using PostgreSQL."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    async def log_event(self, event: AuditEvent) -> None:
        """Log event to PostgreSQL."""
        try:
            conn = await asyncpg.connect(self.connection_string)

            await conn.execute(
                """
                INSERT INTO tool_audit_log (
                    timestamp, event_type, tool_name, arguments,
                    decision, result, duration_ms, error
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                event.timestamp,
                event.event_type,
                event.tool_name,
                json.dumps(event.arguments),
                event.decision,
                event.result,
                event.duration_ms,
                event.error,
            )

            await conn.close()
        except Exception as e:
            # Don't break tool execution on audit failures
            import sys
            print(f"Audit logging error: {e}", file=sys.stderr)

# Usage
audit_logger = PostgresAuditLogger("postgresql://localhost/consoul")
registry = ToolRegistry(
    config.tools,
    approval_provider=provider,
    audit_logger=audit_logger
)
```

### Multi-Backend Logger

```python
class MultiAuditLogger:
    """Log to multiple backends simultaneously."""

    def __init__(self, loggers: list[AuditLogger]):
        self.loggers = loggers

    async def log_event(self, event: AuditEvent) -> None:
        """Log to all backends concurrently."""
        import asyncio

        tasks = [logger.log_event(event) for logger in self.loggers]
        await asyncio.gather(*tasks, return_exceptions=True)

# Usage: Log to both file and database
from consoul.ai.tools.audit import FileAuditLogger

multi_logger = MultiAuditLogger([
    FileAuditLogger(Path.home() / ".consoul" / "audit.jsonl"),
    PostgresAuditLogger("postgresql://localhost/consoul"),
])
```

## Configuration

### Programmatic Setup

```python
from consoul.config.models import ToolConfig, BashToolConfig
from consoul.ai.tools.permissions import PermissionPolicy

# Create tool configuration programmatically
tool_config = ToolConfig(
    enabled=True,
    permission_policy=PermissionPolicy.BALANCED,
    audit_logging=True,
    audit_log_file=Path("/var/log/consoul/audit.jsonl"),
    bash=BashToolConfig(
        timeout=60,
        whitelist_patterns=["git status", "git log", "ls", "pwd"],
        blocked_patterns=["sudo", "rm -rf /"],
    ),
)

registry = ToolRegistry(config=tool_config)
```

### Per-User Policies

```python
def create_user_registry(user_id: str, user_role: str) -> ToolRegistry:
    """Create tool registry with user-specific policy."""

    # Select policy based on user role
    if user_role == "admin":
        policy = PermissionPolicy.TRUSTING
    elif user_role == "developer":
        policy = PermissionPolicy.BALANCED
    else:
        policy = PermissionPolicy.PARANOID

    config = ToolConfig(
        enabled=True,
        permission_policy=policy,
        audit_logging=True,
    )

    # Custom audit logger with user context
    audit_logger = UserAuditLogger(user_id=user_id)

    return ToolRegistry(
        config=config,
        approval_provider=get_user_approval_provider(user_id),
        audit_logger=audit_logger,
    )
```

### Environment-Based Configuration

```python
import os

def get_environment_config() -> ToolConfig:
    """Load configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.PARANOID,
            audit_logging=True,
            audit_log_file=Path("/var/log/consoul/audit.jsonl"),
        )
    elif env == "development":
        return ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.BALANCED,
            audit_logging=True,
        )
    else:  # testing
        return ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.UNRESTRICTED,
            audit_logging=False,
        )
```

## Testing

### Mock Approval Provider

```python
from consoul.ai.tools.approval import ToolApprovalRequest, ToolApprovalResponse

class MockApprovalProvider:
    """Mock provider for testing."""

    def __init__(self, always_approve: bool = True):
        self.always_approve = always_approve
        self.requests = []  # Track requests for assertions

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        self.requests.append(request)

        return ToolApprovalResponse(
            approved=self.always_approve,
            reason="Mock approval" if self.always_approve else "Mock denial"
        )
```

### Unit Test Example

```python
import pytest
from consoul.config.models import ToolConfig
from consoul.ai.tools import ToolRegistry, RiskLevel
from consoul.ai.tools.permissions import PermissionPolicy

@pytest.fixture
def mock_registry():
    """Create registry with mock approval."""
    config = ToolConfig(
        enabled=True,
        permission_policy=PermissionPolicy.UNRESTRICTED,
        audit_logging=False,
    )

    provider = MockApprovalProvider(always_approve=True)

    return ToolRegistry(config, approval_provider=provider)

@pytest.mark.asyncio
async def test_tool_approval(mock_registry):
    """Test tool approval workflow."""
    from langchain_core.tools import tool

    @tool
    def test_tool(x: int) -> int:
        """Test tool."""
        return x * 2

    mock_registry.register(test_tool, risk_level=RiskLevel.SAFE)

    # Request approval
    response = await mock_registry.request_tool_approval(
        tool_name="test_tool",
        arguments={"x": 5},
    )

    assert response.approved
```

### Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_end_to_end_tool_execution():
    """Test complete tool execution with real components."""
    from consoul.config.loader import load_config
    from consoul.ai.tools import bash_execute

    config = load_config()

    # Use real CLI provider but with mock input
    provider = CliApprovalProvider()
    registry = ToolRegistry(config.tools, approval_provider=provider)
    registry.register(bash_execute, risk_level=RiskLevel.SAFE)

    # Execute safe command
    result = bash_execute(command="echo 'test'")
    assert "test" in result
```

## Working with Built-in Tools

### read_file Tool

The `read_file` tool allows AI agents to read file contents with security controls and truncation limits.

#### Basic Usage

```python
from consoul.ai.tools import ToolRegistry, RiskLevel
from consoul.ai.tools.implementations import read_file

registry = ToolRegistry(config=config.tools, approval_provider=provider)

# Register as SAFE (read-only, no side effects)
registry.register(
    read_file,
    risk_level=RiskLevel.SAFE,
    tags=["filesystem", "readonly"]
)

# AI can now read files
response = model_with_tools.invoke("Read the README.md file")
```

#### Custom Configuration

```python
from consoul.ai.tools.implementations import read_file, set_read_config
from consoul.config.models import ReadToolConfig

# Configure read tool limits
read_config = ReadToolConfig(
    max_lines_default=1000,        # Max lines per read (without offset/limit)
    max_line_length=2000,          # Truncate lines longer than this
    max_output_chars=40000,        # Max total output characters
    allowed_extensions=[".py", ".md", ".txt", ".json"],  # Whitelist extensions
    blocked_paths=["/etc/shadow", "/proc"],  # Blacklist sensitive paths
    enable_pdf=True,               # Enable PDF support (requires pypdf)
    pdf_max_pages=50,              # Max PDF pages to read
)

# Inject config before registration
set_read_config(read_config)
registry.register(read_file, risk_level=RiskLevel.SAFE)
```

#### Security Features

- **Extension filtering**: Only allow specific file types
- **Path blocking**: Prevent access to sensitive paths
- **Line truncation**: Limit per-line characters (prevents minified files)
- **Output limits**: Cap total character count (prevents context overflow)
- **Binary detection**: Rejects non-text files (except PDFs if enabled)

#### PDF Support (Optional)

```python
# Install PDF support
# pip install consoul[pdf]

# Enable in config
config = ReadToolConfig(
    enable_pdf=True,
    pdf_max_pages=50,
    allowed_extensions=[".pdf", ".txt", ".md"]
)
set_read_config(config)

# AI can now read PDFs
response = model_with_tools.invoke("Read documentation.pdf pages 1-5")
```

## Examples

Complete working examples are available in `examples/sdk/`:

- **cli_approval_example.py** - Complete CLI tool with approval
- **web_approval_provider.py** - HTTP-based approval implementation
- **custom_audit_logger.py** - Database and cloud audit loggers
- **read_file_example.py** - Working with the read_file tool

## Best Practices

### Approval Providers

✅ **DO:**
- Implement timeout handling
- Log approval decisions
- Provide clear context to users
- Handle network failures gracefully
- Use async/await properly

❌ **DON'T:**
- Block the event loop with sync I/O
- Throw exceptions on denial
- Store secrets in plain text
- Skip validation of responses

### Audit Loggers

✅ **DO:**
- Handle logging failures gracefully (don't break tool execution)
- Use structured logging formats
- Implement log rotation
- Secure sensitive data
- Batch writes for performance

❌ **DON'T:**
- Block tool execution on logging errors
- Log sensitive data (passwords, keys)
- Use synchronous I/O
- Ignore storage limits

### Configuration

✅ **DO:**
- Use environment-specific configs
- Implement per-user policies
- Document security implications
- Test policy enforcement
- Validate configuration on startup

❌ **DON'T:**
- Use UNRESTRICTED in production
- Hardcode credentials
- Skip validation
- Ignore policy violations

## Troubleshooting

### Provider Not Called

**Problem**: Custom approval provider not being invoked

**Solutions:**
1. Ensure `permission_policy` is not set to `UNRESTRICTED`
2. Check tool risk level requires approval
3. Verify provider is passed to `ToolRegistry`
4. Check tool is not in whitelist

### Async Issues

**Problem**: "coroutine was never awaited" errors

**Solutions:**
1. Always use `async def` for provider methods
2. Use `await` when calling async functions
3. Don't call async functions from sync code
4. Use `asyncio.run()` for top-level execution

### Audit Logging Not Working

**Problem**: Events not appearing in audit log

**Solutions:**
1. Verify `audit_logging=True` in config
2. Check log file path is writable
3. Look for errors in stderr
4. Ensure audit logger is passed to registry

## API Reference

See full API documentation:
- [Tool Calling Guide](../tools.md)
- [Configuration Reference](../user-guide/configuration.md)
- [API Documentation](../api/index.md)

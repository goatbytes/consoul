# Tool Calling

Comprehensive guide to Consoul's tool calling system for AI-powered command execution.

## Table of Contents

- [Introduction](#introduction)
- [Available Tools](#available-tools)
- [Quick Start](#quick-start)
- [Security Model](#security-model)
- [Configuration](#configuration)
- [Using Tools](#using-tools)
- [Custom Tool Development](#custom-tool-development)
- [Audit Logging](#audit-logging)
- [Troubleshooting](#troubleshooting)

## Introduction

### What is Tool Calling?

Tool calling enables AI models to execute commands and interact with your system. When the AI needs to perform an action (like running a bash command), it can request to use a "tool" - a validated, security-controlled function that performs the operation.

Consoul's tool calling system is built on:
- **LangChain**: Industry-standard tool abstraction
- **Security-first design**: Multi-layer approval and validation
- **Audit logging**: Complete execution history
- **Extensibility**: Easy custom tool development

### Architecture

```
AI Model → Tool Request → Security Validation → User Approval → Execution → Result
                              ↓                      ↓              ↓
                         Risk Analysis          Audit Log    Audit Log
                         Policy Check           (request)    (result)
                         Whitelist/Blacklist
```

### Security Philosophy

⚠️ **Tool calling is powerful but potentially dangerous.** Consoul implements multiple security layers:

1. **Risk Classification**: Every tool is classified by risk level
2. **Permission Policies**: Configurable security postures (PARANOID to UNRESTRICTED)
3. **User Approval**: Interactive confirmation for dangerous operations
4. **Command Validation**: Pattern-based blocking of dangerous commands
5. **Audit Logging**: Complete execution history for accountability

## Available Tools

### bash_execute

Execute bash commands with security controls.

**Capabilities:**
- Run shell commands with timeout enforcement
- Capture stdout, stderr, and exit codes
- Working directory control
- Command validation and blocking
- Whitelist support for trusted commands

**Risk Level**: Varies based on command (SAFE to DANGEROUS)

**Example:**
```python
# Safe command (auto-approved with BALANCED policy)
result = bash_execute(command="ls -la", cwd="/tmp")

# Dangerous command (requires approval)
result = bash_execute(command="rm -rf old_files/", cwd="/home/user")
```

**Security Features:**
- Blocks dangerous patterns (sudo, rm -rf /, fork bombs)
- Configurable timeout (default 30s, max 10min)
- Working directory validation
- Whitelist/blacklist pattern matching

**Configuration:**
```yaml
tools:
  enabled: true
  bash:
    timeout: 30
    blocked_patterns:
      - "^sudo\\s"
      - "rm\\s+(-[rf]+\\s+)?/"
    whitelist_patterns:
      - "git status"
      - "git log"
      - "ls"
```

### read_file

Read file contents with security controls and format detection.

**Capabilities:**
- Read text files with line numbers (cat -n style)
- Extract text from PDF documents with page markers
- Support for line ranges (offset/limit)
- Support for PDF page ranges
- Encoding fallback (UTF-8 → Latin-1)
- Binary file detection and rejection

**Risk Level**: SAFE (read-only, no side effects)

**Example:**
```python
# Read entire file
result = read_file(file_path="src/main.py")

# Read specific line range
result = read_file(file_path="README.md", offset=10, limit=20)

# Read PDF pages
result = read_file(file_path="docs/design.pdf", start_page=5, end_page=7)
```

**Security Features:**
- Blocks reading from sensitive system paths (/etc/shadow, /proc, /dev, /sys)
- Prevents directory traversal attacks (..)
- Detects and rejects binary files (except PDFs)
- Validates file extensions against allowed list
- Configurable path blacklist and extension whitelist

**Configuration:**
```yaml
tools:
  enabled: true
  read:
    max_lines_default: 2000       # Max lines to read without limit
    max_line_length: 2000          # Truncate long lines
    max_output_chars: 40000        # Total output character limit
    enable_pdf: true               # Enable PDF reading
    pdf_max_pages: 50              # Max PDF pages to read
    allowed_extensions:            # Allowed file types (empty = all)
      - ".py"
      - ".js"
      - ".md"
      - ".txt"
      - ".json"
      - ".yaml"
      - ".yml"
      - ".toml"
      - ".csv"
      - ".pdf"
    blocked_paths:                 # Paths that cannot be read
      - "/etc/shadow"
      - "/etc/passwd"
      - "/proc"
      - "/dev"
      - "/sys"
```

**Common Use Cases:**
- Reading source code for analysis and review
- Accessing documentation files (README, design docs)
- Reading configuration files (YAML, JSON, TOML)
- Extracting text from PDF documentation
- Reviewing log files with line range filtering
- Analyzing data files (CSV, JSON)

**Troubleshooting:**

| Error | Cause | Solution |
|-------|-------|----------|
| `File not found` | File doesn't exist | Check file path and working directory |
| `Permission denied` | No read access | Check file permissions with `ls -la` |
| `Unsupported binary file` | Binary file detected | Only text and PDF files supported |
| `Extension not allowed` | File type blocked | Add extension to `allowed_extensions` |
| `Path not allowed` | Blocked path | Remove from `blocked_paths` if safe |
| `PDF reading is disabled` | PDF support off | Set `enable_pdf: true` in config |
| `Output truncated` | File exceeds limits | Adjust `max_lines_default` or use offset/limit |
| `Line truncated` | Line too long | Increase `max_line_length` in config |
| `PDF has no extractable text` | Scanned/image PDF | PDF is scanned or contains only images |

**PDF Support:**

PDF reading requires the optional `pypdf` package:
```bash
# Install with pip
pip install consoul[pdf]

# Or with poetry
poetry install --extras pdf
```

PDF features:
- Page markers: `=== Page N ===` between pages
- Page range support: `start_page` and `end_page` (1-indexed, inclusive)
- Automatic page limit enforcement (`pdf_max_pages`)
- Handles blank pages and extraction errors gracefully
- Detects scanned PDFs with no extractable text

Example PDF usage:
```python
# Read all pages (up to pdf_max_pages)
result = read_file(file_path="manual.pdf")

# Read specific page range
result = read_file(file_path="design.pdf", start_page=1, end_page=3)

# Read from page 10 to end (up to limit)
result = read_file(file_path="report.pdf", start_page=10)
```

## Quick Start

### 1. Enable Tool Calling

**In config.yaml:**
```yaml
profiles:
  default:
    tools:
      enabled: true
      permission_policy: balanced  # Recommended
```

### 2. Choose a Permission Policy

```yaml
tools:
  permission_policy: balanced  # PARANOID, BALANCED, TRUSTING, or UNRESTRICTED
```

See [Permission Policies](#permission-policies) for details.

### 3. Start Consoul

```bash
# TUI mode (interactive approval)
consoul

# Ask the AI to run a command
> "What files are in the current directory?"
```

The AI will request to use `bash_execute`, and you'll see an approval modal if the policy requires it.

### 4. Review Audit Logs

```bash
# View audit log
tail -f ~/.consoul/tool_audit.jsonl

# Query with jq
jq 'select(.event_type=="execution")' ~/.consoul/tool_audit.jsonl

# Count approvals vs denials
jq -r '.event_type' ~/.consoul/tool_audit.jsonl | sort | uniq -c
```

## Security Model

### Risk Levels

Every tool and command is classified by risk:

| Risk Level | Description | Examples | Default Behavior |
|------------|-------------|----------|------------------|
| **SAFE** | Read-only, no side effects | `ls`, `pwd`, `cat` | Auto-approve (BALANCED+) |
| **CAUTION** | Modifies files/state | `mkdir`, `git commit`, `mv` | Prompt (BALANCED) |
| **DANGEROUS** | High-risk operations | `rm -rf`, `chmod 777`, `dd` | Prompt (all policies) |
| **BLOCKED** | Prohibited operations | `sudo`, `rm -rf /`, fork bombs | Always blocked |

### Permission Policies

Consoul provides four predefined security policies:

#### Policy Comparison

```
┌──────────────┬──────┬─────────┬───────────┬─────────┬──────────────────┐
│ Policy       │ SAFE │ CAUTION │ DANGEROUS │ BLOCKED │ Use Case         │
├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
│ PARANOID     │ ⚠️   │ ⚠️      │ ⚠️        │ ❌      │ Production, max  │
│              │      │         │           │         │ security         │
├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
│ BALANCED ⭐  │ ✅   │ ⚠️      │ ⚠️        │ ❌      │ Recommended      │
│              │      │         │           │         │ default          │
├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
│ TRUSTING     │ ✅   │ ✅      │ ⚠️        │ ❌      │ Development,     │
│              │      │         │           │         │ convenience      │
├──────────────┼──────┼─────────┼───────────┼─────────┼──────────────────┤
│ UNRESTRICTED │ ✅   │ ✅      │ ✅        │ ❌      │ Testing only,    │
│              │      │         │           │         │ DANGEROUS        │
└──────────────┴──────┴─────────┴───────────┴─────────┴──────────────────┘

Legend: ✅ Auto-approve  ⚠️ Require approval  ❌ Always blocked
```

#### PARANOID Policy

**Maximum security** - Approve every command individually.

```yaml
tools:
  permission_policy: paranoid
```

**Behavior:**
- Prompts for ALL commands (even `ls`)
- Best for production environments
- Highest security, lowest convenience
- Recommended when AI is untrusted

**Use cases:**
- Production systems
- Shared/multi-user environments
- When working with sensitive data

#### BALANCED Policy ⭐ (Recommended)

**Recommended default** - Auto-approve SAFE, prompt for CAUTION+.

```yaml
tools:
  permission_policy: balanced
```

**Behavior:**
- Auto-approves: `ls`, `pwd`, `cat`, `git status`
- Prompts: `mkdir`, `rm`, `git commit`, `chmod`
- Always prompts: Dangerous operations
- Good balance of security and usability

**Use cases:**
- General development work
- Personal projects
- Default for new users

#### TRUSTING Policy

**Convenience-focused** - Auto-approve SAFE+CAUTION, prompt DANGEROUS+.

```yaml
tools:
  permission_policy: trusting
```

**Behavior:**
- Auto-approves: Most file operations, git commands
- Prompts: `rm -rf`, dangerous permissions, system commands
- Suitable for trusted environments
- Lower security, higher convenience

**Use cases:**
- Trusted development environments
- Personal machines with backups
- When AI behavior is well-understood

#### UNRESTRICTED Policy ⚠️

**Minimal restrictions** - Auto-approve all except BLOCKED (DANGEROUS).

```yaml
tools:
  permission_policy: unrestricted
```

⚠️ **WARNING: This policy is DANGEROUS and should ONLY be used in testing environments.**

**Behavior:**
- Auto-approves: Nearly everything
- Only blocks: `sudo`, `rm -rf /`, fork bombs
- **NO user approval** for dangerous operations
- Suitable ONLY for isolated testing

**Use cases:**
- Automated testing
- CI/CD pipelines
- Isolated development containers
- **NEVER use in production**

### Approval Modes

Fine-tune when approval is requested:

```yaml
tools:
  approval_mode: always  # or: once_per_session, whitelist, risk_based, never
```

| Mode | Description | Use Case |
|------|-------------|----------|
| **always** | Approve every execution | Maximum security |
| **once_per_session** | Approve first use, cache approval | Convenience with safety |
| **whitelist** | Only prompt non-whitelisted tools | Trusted command patterns |
| **risk_based** | Prompt based on risk level | Balanced approach (default) |
| **never** | Auto-approve all (DANGEROUS) | Testing only |

⚠️ **Note**: `approval_mode` is ignored when `permission_policy` is set. Use policies instead.

### Command Validation

#### Blocked Command Patterns

Default blocked patterns (always prohibited):

```python
# Dangerous sudo operations
"^sudo\\s"

# Root filesystem deletion
"rm\\s+(-[rf]+\\s+)?/"

# Disk operations
"dd\\s+if="

# Dangerous permissions
"chmod\\s+777"

# Fork bomb
":\\(\\)\\{.*:\\|:.*\\};:"

# Download-and-execute
"wget.*\\|.*bash"
"curl.*\\|.*sh"

# Direct disk writes
">\s*/dev/sd[a-z]"

# Filesystem operations
"mkfs"
"fdisk"
```

#### Custom Blocked Commands

Add your own patterns:

```yaml
tools:
  bash:
    blocked_patterns:
      - "^docker\\s+rm"        # Block container deletion
      - "systemctl\\s+stop"    # Block service stopping
      - "reboot"               # Block system reboot
      - "shutdown"             # Block system shutdown
```

#### Whitelist Patterns

Auto-approve trusted commands:

```yaml
tools:
  bash:
    whitelist_patterns:
      # Literal matches (default)
      - "git status"
      - "git log"
      - "ls"
      - "pwd"

      # Regex patterns (auto-detected when your pattern contains regex characters)
      - "git (status|log|diff)"
      - "ls\\s+(-[la]+\\s+)?"
      - "npm\\s+(test|run\\s+lint)"
```

**Pattern Types:**

1. **Literal** (default): Exact string match
   ```yaml
   - "git status"              # Matches: "git status" only
   - "./gradlew build"         # Matches: "./gradlew build" only
   ```

2. **Regex**: Pattern matching (any pattern containing regex characters is treated as regex)
   ```yaml
   - "git (status|log)"        # Matches: "git status" or "git log"
   - "npm\\s+test.*"           # Matches: "npm test", "npm test --coverage"
   ```

**Security Note**: Literal matching is safer than regex. Use regex only when necessary.

## Configuration

### ToolConfig Reference

Complete configuration options:

```yaml
tools:
  # Enable/disable tool calling
  enabled: true

  # Permission policy (recommended approach)
  permission_policy: balanced  # paranoid, balanced, trusting, unrestricted

  # Approval mode (deprecated - use permission_policy instead)
  approval_mode: risk_based    # always, once_per_session, whitelist, risk_based, never

  # Tool whitelist (empty = all tools allowed)
  allowed_tools:
    - bash_execute
    - custom_tool

  # Legacy auto-approve flag (DANGEROUS - use permission_policy instead)
  auto_approve: false

  # Default timeout (DEPRECATED - use bash.timeout instead)
  timeout: 30

  # Audit logging
  audit_logging: true
  audit_log_file: ~/.consoul/tool_audit.jsonl

  # Bash-specific settings
  bash:
    timeout: 30                   # Execution timeout (seconds, max 600)
    working_directory: null       # Optional fixed working directory
    blocked_patterns:             # Custom blocked patterns
      - "^sudo\\s"
      - "rm\\s+(-[rf]+\\s+)?/"
    whitelist_patterns:           # Auto-approved commands
      - "git status"
      - "ls"
```

### Example Configurations

#### Development Environment

```yaml
profiles:
  development:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022

    tools:
      enabled: true
      permission_policy: trusting
      audit_logging: true
      bash:
        timeout: 60
        whitelist_patterns:
          - "git status"
          - "git log"
          - "git diff"
          - "npm test"
          - "npm run lint"
          - "ls"
          - "pwd"
```

#### Production Environment

```yaml
profiles:
  production:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022

    tools:
      enabled: true
      permission_policy: paranoid
      audit_logging: true
      audit_log_file: /var/log/consoul/audit.jsonl
      bash:
        timeout: 30
        blocked_patterns:
          - "^sudo\\s"
          - "rm"
          - "mv"
          - "chmod"
          - "chown"
        whitelist_patterns:
          - "git status"
          - "ls"
```

#### Testing/CI Environment

```yaml
profiles:
  ci:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022

      tools:
        enabled: true
        permission_policy: unrestricted  # ⚠️ Testing only
        audit_logging: true
        bash:
          timeout: 300  # Longer timeout for tests
        whitelist_patterns:
          - ".*"  # ⚠️ Allow everything (testing only)
```

### Environment Overrides

Tool calling settings currently load from `config.yaml`. Consoul does not yet expose
`CONSOUL_TOOLS_*` environment variables, so update the configuration file (or profile
overrides) directly when changing tool policies, audit paths, or bash timeouts.

## Using Tools

### In TUI (Interactive Mode)

When running `consoul` in TUI mode:

1. **AI requests tool**: The AI determines it needs to execute a command
2. **Security validation**: Command is analyzed for risk level
3. **Approval modal** (if required): You see tool details and can approve/deny
4. **Execution**: If approved, command executes with timeout
5. **Result display**: Output shown in chat interface
6. **Audit logging**: Event recorded to audit log

**Approval Modal:**
```
┌─────────────────────────────────────────┐
│ Tool Approval Required                  │
├─────────────────────────────────────────┤
│ Tool: bash_execute                      │
│ Risk: CAUTION                           │
│                                         │
│ Command:                                │
│   git commit -m "Add feature"           │
│                                         │
│ Working Directory:                      │
│   /home/user/project                    │
│                                         │
│        [Approve]  [Deny]                │
└─────────────────────────────────────────┘
```

**Keyboard Shortcuts:**
- `Enter` or `y` - Approve
- `Escape` or `n` - Deny
- `Tab` - Switch between buttons

### In CLI Mode

When using Consoul as a library:

```python
from consoul.config.loader import load_config
from consoul.ai.tools import ToolRegistry, bash_execute, RiskLevel
from consoul.ai.tools.providers import CliApprovalProvider

# Load configuration
config = load_config()

# Create approval provider for CLI
approval_provider = CliApprovalProvider()

# Create tool registry
registry = ToolRegistry(
    config=config.tools,
    approval_provider=approval_provider
)

# Register tools
registry.register(bash_execute, risk_level=RiskLevel.CAUTION)

# Request approval and execute
response = await registry.request_tool_approval(
    tool_name="bash_execute",
    arguments={"command": "git status"},
    context={"user": "developer@example.com"}
)

if response.approved:
    result = bash_execute(command="git status")
    print(result)
```

### Programmatically (SDK)

Create custom approval logic:

```python
from consoul.ai.tools.approval import ApprovalProvider, ToolApprovalRequest, ToolApprovalResponse

class CustomApprovalProvider(ApprovalProvider):
    """Custom approval logic for automated systems."""

    async def request_approval(self, request: ToolApprovalRequest) -> ToolApprovalResponse:
        # Auto-approve git commands
        if "git" in request.arguments.get("command", ""):
            return ToolApprovalResponse(
                approved=True,
                reason="Auto-approved: git command"
            )

        # Deny rm commands
        if "rm" in request.arguments.get("command", ""):
            return ToolApprovalResponse(
                approved=False,
                reason="Denied: rm commands not allowed"
            )

        # Default: require manual review
        return ToolApprovalResponse(
            approved=False,
            reason="Manual approval required"
        )

# Use custom provider
registry = ToolRegistry(
    config=config.tools,
    approval_provider=CustomApprovalProvider()
)
```

## Custom Tool Development

### Creating a Custom Tool

Tools are created using LangChain's `@tool` decorator:

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    """Input schema for weather tool."""
    location: str = Field(description="City name or zip code")
    units: str = Field(default="celsius", description="Temperature units (celsius/fahrenheit)")

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius") -> str:
    """Get current weather for a location.

    This tool fetches weather data from an API and returns
    current conditions including temperature, humidity, and conditions.

    Args:
        location: City name or zip code
        units: Temperature units (celsius or fahrenheit)

    Returns:
        Weather information as formatted string

    Raises:
        ValueError: If location is invalid
        ConnectionError: If weather API is unavailable
    """
    # Input validation
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")

    if units not in ["celsius", "fahrenheit"]:
        raise ValueError(f"Invalid units: {units}")

    # Implementation (example - replace with real API)
    try:
        # Call weather API
        response = requests.get(
            f"https://api.weather.com/current?location={location}&units={units}",
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        return f"Weather in {location}: {data['temp']}°{units[0].upper()}, {data['conditions']}"

    except requests.RequestException as e:
        raise ConnectionError(f"Failed to fetch weather: {e}")
```

### Registering Custom Tools

```python
from consoul.ai.tools import ToolRegistry, RiskLevel
from consoul.config.loader import load_config

# Load configuration
config = load_config()

# Create registry
registry = ToolRegistry(config=config.tools)

# Register custom tool
registry.register(
    tool=get_weather,
    risk_level=RiskLevel.SAFE,  # API call, no system changes
    tags=["api", "weather", "readonly"],
    enabled=True
)

# List all tools
tools = registry.list_tools()
print([tool.name for tool in tools])
# Output: ['bash_execute', 'get_weather']

# Bind to model for tool calling
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
model_with_tools = registry.bind_to_model(model)

# Now the AI can use your custom tool
response = model_with_tools.invoke("What's the weather in London?")
```

### Best Practices

#### 1. Clear Docstrings

```python
@tool
def my_tool(arg: str) -> str:
    """One-line summary of what the tool does.

    Detailed explanation of the tool's purpose, behavior,
    and any important notes for the AI to understand.

    Args:
        arg: Clear description of the argument

    Returns:
        Description of return value

    Raises:
        ValueError: When validation fails
    """
    pass
```

The AI uses the docstring to understand when and how to use the tool.

#### 2. Input Validation

```python
from pydantic import BaseModel, Field, validator

class MyToolInput(BaseModel):
    """Input schema with validation."""

    path: str = Field(description="File path")
    count: int = Field(ge=1, le=100, description="Number of items (1-100)")

    @validator("path")
    def validate_path(cls, v):
        """Validate path is safe."""
        if ".." in v:
            raise ValueError("Path cannot contain '..'")
        if v.startswith("/"):
            raise ValueError("Absolute paths not allowed")
        return v

@tool(args_schema=MyToolInput)
def my_tool(path: str, count: int) -> str:
    """Tool with validated inputs."""
    # Validation already done by Pydantic
    pass
```

#### 3. Error Handling

```python
from consoul.ai.tools.exceptions import ToolExecutionError

@tool
def my_tool(arg: str) -> str:
    """Tool with proper error handling."""
    try:
        # Tool implementation
        result = do_something(arg)
        return result

    except ValueError as e:
        # Re-raise validation errors
        raise

    except Exception as e:
        # Wrap unexpected errors
        raise ToolExecutionError(f"Tool execution failed: {e}")
```

#### 4. Timeout Handling

```python
import asyncio
from consoul.config.models import ToolConfig

@tool
async def long_running_tool(query: str) -> str:
    """Tool with timeout handling."""
    try:
        # Use asyncio.timeout for async operations
        async with asyncio.timeout(30):  # 30 second timeout
            result = await fetch_data(query)
            return result

    except asyncio.TimeoutError:
        raise ToolExecutionError("Operation timed out after 30 seconds")
```

#### 5. Risk Level Assignment

Choose appropriate risk level:

```python
# SAFE: Read-only operations, no side effects
registry.register(get_weather, risk_level=RiskLevel.SAFE)
registry.register(search_docs, risk_level=RiskLevel.SAFE)

# CAUTION: Modifies state, but reversible
registry.register(create_file, risk_level=RiskLevel.CAUTION)
registry.register(send_email, risk_level=RiskLevel.CAUTION)

# DANGEROUS: Destructive or irreversible operations
registry.register(delete_database, risk_level=RiskLevel.DANGEROUS)
registry.register(deploy_production, risk_level=RiskLevel.DANGEROUS)
```

### Complete Example: Database Query Tool

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any
import sqlite3
from consoul.ai.tools import ToolRegistry, RiskLevel
from consoul.ai.tools.exceptions import ToolExecutionError

class DatabaseQueryInput(BaseModel):
    """Input schema for database query tool."""

    query: str = Field(description="SQL query to execute (SELECT only)")
    database: str = Field(description="Database file path")
    limit: int = Field(default=100, ge=1, le=1000, description="Max rows to return")

    @validator("query")
    def validate_readonly(cls, v: str) -> str:
        """Ensure query is read-only."""
        query_upper = v.strip().upper()

        # Only allow SELECT queries
        if not query_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        # Block dangerous keywords
        dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        for keyword in dangerous:
            if keyword in query_upper:
                raise ValueError(f"Query contains forbidden keyword: {keyword}")

        return v

    @validator("database")
    def validate_database_path(cls, v: str) -> str:
        """Validate database path is safe."""
        if ".." in v:
            raise ValueError("Path cannot contain '..'")
        if not v.endswith(".db"):
            raise ValueError("Database file must have .db extension")
        return v

@tool(args_schema=DatabaseQueryInput)
def query_database(query: str, database: str, limit: int = 100) -> str:
    """Execute a read-only SQL query against a SQLite database.

    This tool allows querying SQLite databases with read-only access.
    Only SELECT queries are permitted. Results are limited to prevent
    overwhelming the AI context.

    Args:
        query: SQL SELECT query to execute
        database: Path to SQLite database file (.db)
        limit: Maximum number of rows to return (1-1000)

    Returns:
        Query results formatted as a table string

    Raises:
        ValueError: If query is invalid or contains forbidden operations
        ToolExecutionError: If database access fails

    Example:
        >>> result = query_database(
        ...     query="SELECT name, email FROM users WHERE active=1",
        ...     database="app.db",
        ...     limit=50
        ... )
    """
    try:
        # Connect to database (read-only mode)
        conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Execute query with limit
        cursor.execute(f"{query} LIMIT {limit}")
        rows = cursor.fetchall()

        # Format results
        if not rows:
            return "Query returned no results."

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Build result table
        result_lines = []
        result_lines.append(" | ".join(columns))
        result_lines.append("-" * (len(" | ".join(columns))))

        for row in rows:
            result_lines.append(" | ".join(str(row[col]) for col in columns))

        result = "\n".join(result_lines)

        # Add metadata
        result += f"\n\n({len(rows)} rows returned, limit={limit})"

        conn.close()
        return result

    except sqlite3.Error as e:
        raise ToolExecutionError(f"Database error: {e}")

    except Exception as e:
        raise ToolExecutionError(f"Failed to execute query: {e}")

# Register the tool
def register_database_tools(registry: ToolRegistry):
    """Register database-related tools."""
    registry.register(
        tool=query_database,
        risk_level=RiskLevel.SAFE,  # Read-only, no modifications
        tags=["database", "query", "readonly"],
        enabled=True
    )

# Usage example
if __name__ == "__main__":
    from consoul.config.loader import load_config

    config = load_config()
    registry = ToolRegistry(config=config.tools)

    # Register tool
    register_database_tools(registry)

    # Test tool
    result = query_database(
        query="SELECT * FROM users WHERE active=1",
        database="test.db",
        limit=10
    )
    print(result)
```

### Integration with TUI

To make your custom tool available in the TUI:

```python
# src/consoul/ai/tools/implementations/custom_tools.py
from langchain_core.tools import tool
from consoul.ai.tools import RiskLevel

@tool
def my_custom_tool(arg: str) -> str:
    """Your custom tool implementation."""
    return f"Result: {arg}"

# Export from __init__.py
# src/consoul/ai/tools/implementations/__init__.py
from consoul.ai.tools.implementations.custom_tools import my_custom_tool

__all__ = ["bash_execute", "my_custom_tool"]

# Register in TUI app
# src/consoul/tui/app.py (in _setup_tool_registry method)
def _setup_tool_registry(self) -> None:
    """Setup tool registry with all tools."""
    from consoul.ai.tools.implementations import bash_execute, my_custom_tool

    # Register bash tool
    self.tool_registry.register(
        bash_execute,
        risk_level=RiskLevel.CAUTION,
        tags=["system", "bash"]
    )

    # Register custom tool
    self.tool_registry.register(
        my_custom_tool,
        risk_level=RiskLevel.SAFE,
        tags=["custom"]
    )
```

## Audit Logging

### Overview

Consoul logs every tool execution event to provide complete accountability and traceability.

**Event Types:**
- `request` - Tool execution requested
- `approval` - User approved execution
- `denial` - User denied execution
- `execution` - Tool started executing
- `result` - Tool completed successfully
- `error` - Tool execution failed

### Log Format

Logs are stored in JSONL format (one JSON object per line):

```jsonl
{"timestamp": "2025-11-12T10:30:45.123456Z", "event_type": "request", "tool_name": "bash_execute", "arguments": {"command": "git status"}, "user": null, "decision": null, "result": null, "duration_ms": null, "error": null, "metadata": {}}
{"timestamp": "2025-11-12T10:30:46.234567Z", "event_type": "approval", "tool_name": "bash_execute", "arguments": {"command": "git status"}, "user": null, "decision": true, "result": null, "duration_ms": 1100, "error": null, "metadata": {}}
{"timestamp": "2025-11-12T10:30:47.345678Z", "event_type": "execution", "tool_name": "bash_execute", "arguments": {"command": "git status"}, "user": null, "decision": null, "result": null, "duration_ms": null, "error": null, "metadata": {}}
{"timestamp": "2025-11-12T10:30:47.456789Z", "event_type": "result", "tool_name": "bash_execute", "arguments": {"command": "git status"}, "user": null, "decision": null, "result": "On branch main...", "duration_ms": 111, "error": null, "metadata": {}}
```

### Configuration

```yaml
tools:
  # Enable audit logging (recommended)
  audit_logging: true

  # Log file path
  audit_log_file: ~/.consoul/tool_audit.jsonl
```

### Querying Logs

#### View Recent Activity

```bash
# Tail audit log
tail -f ~/.consoul/tool_audit.jsonl

# View last 10 events
tail -n 10 ~/.consoul/tool_audit.jsonl
```

#### Using jq (JSON Query)

```bash
# View all executions
jq 'select(.event_type=="execution")' ~/.consoul/tool_audit.jsonl

# Count approvals vs denials
jq -r '.event_type' ~/.consoul/tool_audit.jsonl | grep -E "approval|denial" | sort | uniq -c

# Find denied commands
jq 'select(.event_type=="denial") | .arguments.command' ~/.consoul/tool_audit.jsonl

# View errors
jq 'select(.event_type=="error") | {tool: .tool_name, error: .error}' ~/.consoul/tool_audit.jsonl

# Commands executed today
jq --arg date "$(date +%Y-%m-%d)" \
  'select(.timestamp | startswith($date)) | select(.event_type=="execution") | .arguments.command' \
  ~/.consoul/tool_audit.jsonl

# Execution times (slowest first)
jq 'select(.event_type=="result") | {command: .arguments.command, duration_ms: .duration_ms}' \
  ~/.consoul/tool_audit.jsonl | jq -s 'sort_by(.duration_ms) | reverse'

# Generate summary report
jq -s 'group_by(.event_type) | map({event_type: .[0].event_type, count: length})' \
  ~/.consoul/tool_audit.jsonl
```

#### Using grep

```bash
# Search for specific command
grep "git commit" ~/.consoul/tool_audit.jsonl

# Find all errors
grep '"event_type":"error"' ~/.consoul/tool_audit.jsonl

# Find long-running operations (>5000ms)
grep -E '"duration_ms":[5-9][0-9]{3,}|"duration_ms":[0-9]{5,}' ~/.consoul/tool_audit.jsonl
```

### Custom Audit Backends

Implement custom audit logging for databases, remote services, etc:

```python
from consoul.ai.tools.audit import AuditLogger, AuditEvent
import asyncpg

class PostgresAuditLogger:
    """Audit logger that writes to PostgreSQL."""

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
                    user_id, decision, result, duration_ms, error, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                event.timestamp,
                event.event_type,
                event.tool_name,
                json.dumps(event.arguments),
                event.user,
                event.decision,
                event.result,
                event.duration_ms,
                event.error,
                json.dumps(event.metadata)
            )

            await conn.close()

        except Exception as e:
            # Don't disrupt tool execution on logging errors
            import sys
            print(f"Audit logging error: {e}", file=sys.stderr)

# Use custom audit logger
from consoul.ai.tools import ToolRegistry

registry = ToolRegistry(
    config=config.tools,
    audit_logger=PostgresAuditLogger("postgresql://localhost/consoul")
)
```

### Security Considerations

- Audit logs contain command arguments and results
- Sensitive data (passwords, API keys) may be logged
- Restrict log file permissions: `chmod 600 ~/.consoul/tool_audit.jsonl`
- Consider log rotation for long-running systems
- Regularly back up audit logs for compliance

### Log Rotation

```bash
# logrotate configuration
cat > /etc/logrotate.d/consoul << 'EOF'
/home/*/.consoul/tool_audit.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}
EOF
```

## Troubleshooting

### Common Errors

#### ToolNotFoundError

**Error:**
```
ToolNotFoundError: Tool 'bash_execute' not found in registry
```

**Cause**: Tool not registered with ToolRegistry

**Solution:**
```python
from consoul.ai.tools import ToolRegistry, bash_execute, RiskLevel

registry = ToolRegistry(config=config.tools)
registry.register(bash_execute, risk_level=RiskLevel.CAUTION)
```

#### BlockedCommandError

**Error:**
```
BlockedCommandError: Command matches blocked pattern: ^sudo\s
```

**Cause**: Command matched a blocked pattern

**Solutions:**

1. **Remove from blocklist** (if safe):
   ```yaml
   tools:
     bash:
       blocked_patterns: []  # Clear all blocked patterns (DANGEROUS)
   ```

2. **Use whitelist to bypass blocklist**:
   ```yaml
   tools:
     bash:
       whitelist_patterns:
         - "sudo apt-get update"  # Specific safe sudo command
   ```

3. **Modify command** to avoid pattern

#### ToolValidationError

**Error:**
```
ToolValidationError: Invalid arguments for tool 'bash_execute': field required (command)
```

**Cause**: Missing or invalid tool arguments

**Solution**: Check tool schema and provide required arguments:
```python
# Get tool schema
tool_meta = registry.get_tool("bash_execute")
print(tool_meta.schema)

# Provide all required arguments
result = bash_execute(command="ls", cwd="/tmp")  # cwd is optional
```

#### Approval Modal Not Showing

**Problem**: Tool executes without approval when it should prompt

**Causes & Solutions:**

1. **Permission policy too permissive**:
   ```yaml
   # Change from:
   tools:
     permission_policy: trusting

   # To:
   tools:
     permission_policy: balanced
   ```

2. **Command whitelisted**:
   ```yaml
   # Remove from whitelist or use PARANOID policy
   tools:
     bash:
       whitelist_patterns: []  # Clear whitelist
   ```

3. **Approval cached** (`once_per_session` mode):
   ```python
   # Clear approval cache
   registry._approved_this_session.clear()

   # Or restart application
   ```

#### Timeout Errors

**Error:**
```
ToolExecutionError: Command timed out after 30 seconds
```

**Solutions:**

1. **Increase timeout**:
   ```yaml
   tools:
     bash:
       timeout: 120  # 2 minutes
   ```

2. **Optimize command** to run faster

3. **Split into smaller operations**

#### Permission Denied

**Error:**
```
ToolExecutionError: Permission denied: /path/to/file
```

**Solutions:**

1. **Check file permissions**:
   ```bash
   ls -la /path/to/file
   chmod +r /path/to/file
   ```

2. **Run with appropriate user**

3. **Change working directory**:
   ```python
   result = bash_execute(
       command="cat file.txt",
       cwd="/accessible/directory"
   )
   ```

#### Audit Log Not Writing

**Problem**: No events in audit log file

**Checks:**

1. **Audit logging enabled**:
   ```yaml
   tools:
     audit_logging: true
   ```

2. **Log directory exists and writable**:
   ```bash
   mkdir -p ~/.consoul
   chmod 755 ~/.consoul
   ```

3. **Check log file permissions**:
   ```bash
   ls -la ~/.consoul/tool_audit.jsonl
   chmod 644 ~/.consoul/tool_audit.jsonl
   ```

4. **Verify path in config**:
   ```yaml
   tools:
     audit_log_file: ~/.consoul/tool_audit.jsonl
   ```

### Performance Issues

#### Slow Tool Execution

**Symptoms**: Commands take longer than expected

**Solutions:**

1. **Check timeout settings** (may be waiting for timeout):
   ```yaml
   tools:
     bash:
       timeout: 30  # Lower if appropriate
   ```

2. **Profile command execution**:
   ```bash
   time bash -c "your_command"
   ```

3. **Check system resources**:
   ```bash
   top
   df -h  # Disk space
   ```

#### High Memory Usage

**Cause**: Large command output stored in memory

**Solutions:**

1. **Limit output size**:
   ```bash
   # Instead of:
   find / -name "*.py"

   # Use:
   find /project -name "*.py" | head -100
   ```

2. **Stream output** (for custom tools):
   ```python
   @tool
   def streaming_tool(arg: str) -> str:
       # Process in chunks instead of loading all at once
       pass
   ```

### Debug Mode

Enable debug logging to troubleshoot issues:

```yaml
logging:
  level: DEBUG
  file: ~/.consoul/debug.log
  console: true
```

View debug logs:
```bash
tail -f ~/.consoul/debug.log | grep -i tool
```

### Getting Help

1. **Check documentation**: Review this guide and [configuration docs](user-guide/configuration.md)
2. **Search issues**: https://github.com/goatbytes/consoul/issues
3. **Ask questions**: https://github.com/goatbytes/consoul/discussions
4. **Report bugs**: Include audit logs and debug output

### Example Debug Session

```bash
# 1. Enable debug logging
cat >> ~/.consoul/config.yaml << 'EOF'
logging:
  level: DEBUG
  console: true
EOF

# 2. Clear audit log
> ~/.consoul/tool_audit.jsonl

# 3. Run problematic command
consoul

# 4. Check audit log for details
cat ~/.consoul/tool_audit.jsonl | jq

# 5. Search debug log
grep -i "tool" ~/.consoul/debug.log

# 6. Report issue with logs
gh issue create --title "Tool execution issue" \
  --body "$(cat ~/.consoul/debug.log | tail -100)"
```

## Best Practices Summary

### Security

✅ **DO:**
- Use BALANCED policy as default
- Enable audit logging
- Review audit logs regularly
- Use whitelist for trusted commands
- Test in safe environments first
- Restrict log file permissions

❌ **DON'T:**
- Use UNRESTRICTED in production
- Disable audit logging
- Auto-approve dangerous operations
- Commit API keys or sensitive data
- Ignore security warnings

### Performance

✅ **DO:**
- Set appropriate timeouts
- Limit command output size
- Use whitelists for frequently-used commands
- Profile slow operations
- Cache approval decisions (`once_per_session`)

❌ **DON'T:**
- Set excessively long timeouts
- Process huge outputs in memory
- Prompt for every trivial command

### Reliability

✅ **DO:**
- Validate tool inputs
- Handle errors gracefully
- Log errors for debugging
- Test tools thoroughly
- Document tool behavior

❌ **DON'T:**
- Ignore validation errors
- Swallow exceptions silently
- Assume tools always succeed
- Skip error handling

## See Also

- [Configuration Guide](user-guide/configuration.md) - Complete configuration reference
- [Security Policy](../SECURITY.md) - Security best practices
- [API Documentation](api/index.md) - Full API reference
- [Examples](../examples/) - Working code examples
- [Tool Calling Config Examples](examples/tool-calling-config.yaml) - Configuration templates
- [Custom Tool Example](examples/custom-tool-example.py) - Complete custom tool implementation

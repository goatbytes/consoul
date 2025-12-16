# SDK Tool Specification Guide

Complete guide to configuring tools in the Consoul SDK.

## Table of Contents

- [Quick Start](#quick-start)
- [Tool Specification Options](#tool-specification-options)
- [Built-in Tools Reference](#built-in-tools-reference)
- [Tool Categories](#tool-categories)
- [Custom Tools](#custom-tools)
- [Tool Discovery](#tool-discovery)
- [Security Considerations](#security-considerations)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Quick Start

Here are 5 common patterns to get started quickly:

### 1. Read-Only Safe Tools

For research and analysis without file modifications:

```python
from consoul import Consoul

# Only search and web tools (all read-only)
console = Consoul(tools="safe")

# Or specify exact safe tools
console = Consoul(tools=["grep", "code_search", "read_url", "web_search"])
```

### 2. All File Operations

Enable all file editing capabilities:

```python
# All file editing tools (create, edit, delete, append)
console = Consoul(tools="file-edit")

# Or combine with search
console = Consoul(tools=["search", "file-edit"])
```

### 3. Custom Tool

Add your own tool alongside built-in tools:

```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """Custom tool for specific task."""
    return f"Processed: {query}"

console = Consoul(tools=[my_tool, "bash", "grep"])
```

### 4. Category-Based

Use tool categories for easy configuration:

```python
# All search tools (grep, code_search, find_references)
console = Consoul(tools="search")

# Multiple categories
console = Consoul(tools=["search", "web", "execute"])
```

### 5. Auto-Discovery

Automatically load tools from `.consoul/tools/`:

```python
# Discover custom tools + enable built-in
console = Consoul(tools=True, discover_tools=True)

# Or only discovered tools
console = Consoul(tools=False, discover_tools=True)
```

## Tool Specification Options

The `tools` parameter accepts multiple formats for maximum flexibility.

### Boolean Values

```python
# Enable all built-in tools (default)
console = Consoul(tools=True)

# Disable all tools
console = Consoul(tools=False)

# Also disables tools
console = Consoul(tools=None)
```

### Risk Level Strings

Filter tools by their risk classification:

```python
# Only SAFE tools (read-only operations)
console = Consoul(tools="safe")

# SAFE + CAUTION tools (includes file operations)
console = Consoul(tools="caution")

# All tools including DANGEROUS (delete operations)
console = Consoul(tools="dangerous")
```

**Risk Level Hierarchy:**

- `"safe"` → Only SAFE tools
- `"caution"` → SAFE + CAUTION tools
- `"dangerous"` → SAFE + CAUTION + DANGEROUS tools

### Category Strings

Use functional categories:

```python
# Search tools: grep, code_search, find_references
console = Consoul(tools="search")

# File editing: create_file, edit_lines, edit_replace, append_file, delete_file
console = Consoul(tools="file-edit")

# Web tools: read_url, web_search
console = Consoul(tools="web")

# Execute tools: bash
console = Consoul(tools="execute")
```

### Tool Name Lists

Specify exact tools you want:

```python
# Specific tools by name
console = Consoul(tools=["bash", "grep", "code_search"])

# Just one tool
console = Consoul(tools=["bash"])
```

### Category Lists

Mix multiple categories:

```python
# Search and web tools
console = Consoul(tools=["search", "web"])

# All except file editing
console = Consoul(tools=["search", "web", "execute"])
```

### Mixed Lists

Combine categories, tool names, and custom tools:

```python
from langchain_core.tools import tool

@tool
def my_tool(x: str) -> str:
    """Custom tool."""
    return x

# Category + tool name
console = Consoul(tools=["search", "bash"])

# Category + custom tool
console = Consoul(tools=["search", my_tool])

# Everything mixed
console = Consoul(tools=["search", "bash", my_tool, "web"])
```

### Empty List

```python
# Same as tools=False
console = Consoul(tools=[])
```

## Built-in Tools Reference

All 11 built-in tools available in Consoul:

| Tool Name | Category | Risk Level | Description |
|-----------|----------|------------|-------------|
| `bash` | execute | CAUTION | Execute bash commands with security controls |
| `grep` | search | SAFE | Search for text patterns in files using ripgrep/grep |
| `code_search` | search | SAFE | Search for code symbols (functions, classes) using AST parsing |
| `find_references` | search | SAFE | Find all references/usages of a code symbol |
| `create_file` | file-edit | CAUTION | Create new files with overwrite protection |
| `edit_lines` | file-edit | CAUTION | Line-based editing with exact line ranges |
| `edit_replace` | file-edit | CAUTION | Search/replace with progressive matching |
| `append_file` | file-edit | CAUTION | Append content to files |
| `delete_file` | file-edit | DANGEROUS | Delete files with validation |
| `read_url` | web | SAFE | Read and convert web pages to markdown |
| `web_search` | web | SAFE | Search the web using SearxNG/DuckDuckGo/Jina |

**Full documentation for each tool**: See [docs/tools.md](tools.md)

## Tool Categories

Categories group related tools for easy specification:

| Category | Tools Included | Count | Use Case |
|----------|---------------|-------|----------|
| `search` | grep, code_search, find_references | 3 | Code analysis, finding symbols/patterns |
| `file-edit` | create_file, edit_lines, edit_replace, append_file, delete_file | 5 | File manipulation, code editing |
| `web` | read_url, web_search | 2 | Web research, documentation lookup |
| `execute` | bash | 1 | Command execution, system operations |

**Example Usage:**

```python
# All search tools
Consoul(tools="search")
# Enables: grep, code_search, find_references

# Search + web
Consoul(tools=["search", "web"])
# Enables: grep, code_search, find_references, read_url, web_search

# Everything except file editing
Consoul(tools=["search", "web", "execute"])
# Enables: All tools EXCEPT create_file, edit_lines, edit_replace, append_file, delete_file
```

## Custom Tools

Create and register your own tools using LangChain's `@tool` decorator.

### Using @tool Decorator

The simplest way to create custom tools:

```python
from langchain_core.tools import tool
from consoul import Consoul

@tool
def calculate_total(items: list[float]) -> float:
    """Calculate the total sum of a list of numbers.

    Args:
        items: List of numbers to sum

    Returns:
        The total sum
    """
    return sum(items)

# Use with Consoul
console = Consoul(tools=[calculate_total, "bash"])
```

### Using BaseTool Subclass

For more complex tools with state:

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    """Input schema for weather tool."""
    location: str = Field(description="City name or zip code")

class WeatherTool(BaseTool):
    """Tool to fetch weather data."""
    name = "get_weather"
    description = "Get current weather for a location"
    args_schema = WeatherInput

    def _run(self, location: str) -> str:
        """Fetch weather data."""
        # Implementation here
        return f"Weather in {location}: 72°F, Sunny"

# IMPORTANT: Must instantiate the tool
weather_tool = WeatherTool()

console = Consoul(tools=[weather_tool, "bash"])
```

**⚠️ Important**: When using BaseTool subclasses, you must instantiate them. Tool discovery only finds instances, not class definitions.

### Best Practices

1. **Clear docstrings**: The AI uses docstrings to understand when/how to use the tool
2. **Input validation**: Use Pydantic schemas for type safety
3. **Error handling**: Raise descriptive errors
4. **Risk level**: Custom tools default to CAUTION level

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class QueryInput(BaseModel):
    """Validated input schema."""
    query: str = Field(min_length=1, description="Search query")
    limit: int = Field(ge=1, le=100, description="Result limit (1-100)")

@tool(args_schema=QueryInput)
def search_database(query: str, limit: int = 10) -> str:
    """Search the database for records.

    This tool searches the database with the given query and returns
    up to `limit` results.

    Args:
        query: Search query string (required)
        limit: Maximum results to return (1-100, default: 10)

    Returns:
        Search results as formatted string

    Raises:
        ValueError: If query is empty or limit is invalid
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")

    # Implementation
    results = perform_search(query, limit)
    return format_results(results)
```

## Tool Discovery

Automatically discover and load tools from a `.consoul/tools/` directory in your project.

### Setup

1. **Create the directory structure:**

```bash
mkdir -p .consoul/tools
```

2. **Add Python files with tools:**

```python
# .consoul/tools/my_custom_tools.py
from langchain_core.tools import tool

@tool
def process_data(data: str) -> str:
    """Process data in a custom way."""
    return data.upper()

@tool
def analyze_metrics(metrics: dict) -> str:
    """Analyze performance metrics."""
    # Custom analysis logic
    return "Analysis complete"
```

3. **Enable discovery in SDK:**

```python
from consoul import Consoul

# Discover + use built-in tools
console = Consoul(tools=True, discover_tools=True)

# Only discovered tools (no built-in)
console = Consoul(tools=False, discover_tools=True)

# Specific built-in + discovered
console = Consoul(tools=["bash", "grep"], discover_tools=True)
```

### File Structure

```
your-project/
├── .consoul/
│   └── tools/
│       ├── data_tools.py       # Data processing tools
│       ├── api_tools.py        # API integration tools
│       └── analysis_tools.py   # Analysis tools
└── your_code.py
```

### What Gets Discovered

✅ **Discovered:**

- Functions decorated with `@tool`
- Instantiated `BaseTool` objects

❌ **Not Discovered:**

- `__init__.py` files
- Files starting with `_` (private)
- `BaseTool` class definitions (must be instantiated)
- Regular functions without `@tool` decorator

### Discovery Example

```python
# .consoul/tools/math_tools.py
from langchain_core.tools import tool, BaseTool

@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

# This class will NOT be discovered (it's a class, not an instance)
class DivideTool(BaseTool):
    name = "divide"
    description = "Divide two numbers"

    def _run(self, a: float, b: float) -> float:
        return a / b

# This WILL be discovered (it's an instance)
divide_tool = DivideTool()
```

### Recursive Discovery

By default, discovery is recursive:

```python
# Discovers tools from all subdirectories
.consoul/
└── tools/
    ├── utils/
    │   └── helpers.py      # ✅ Discovered
    ├── integrations/
    │   ├── slack.py        # ✅ Discovered
    │   └── github.py       # ✅ Discovered
    └── custom.py           # ✅ Discovered
```

### Error Handling

Discovery gracefully handles errors:

- **Syntax errors**: Logged as warnings, file skipped
- **Import errors**: Logged as warnings, file skipped
- **Runtime errors**: Logged as warnings, file skipped
- Non-tool objects: Silently ignored

## Security Considerations

### Risk Levels Explained

Every tool is classified by its potential impact:

| Risk Level | Impact | Examples | User Approval |
|------------|--------|----------|---------------|
| **SAFE** | Read-only, no side effects | grep, code_search, read_url, web_search | Auto-approved* |
| **CAUTION** | Modifies files/state, reversible | bash, create_file, edit_file | Requires approval* |
| **DANGEROUS** | High-risk, potentially irreversible | delete_file | Always requires approval |

\* Depends on permission policy (see Configuration)

### When to Use Which Risk Level

**Assign SAFE to:**

- Read-only operations
- Web API calls that don't modify state
- Search and lookup operations
- Data analysis without side effects

**Assign CAUTION to:**

- File creation/modification
- Command execution
- API calls that modify state
- Operations that can be undone

**Assign DANGEROUS to:**

- File/data deletion
- Irreversible operations
- System modifications
- Production deployments

### Custom Tool Security

Custom tools default to **CAUTION** risk level for safety:

```python
@tool
def my_tool(arg: str) -> str:
    """My custom tool."""
    return arg

# Registered as RiskLevel.CAUTION by default
console = Consoul(tools=[my_tool])
```

For read-only custom tools, document clearly:

```python
@tool
def lookup_data(key: str) -> str:
    """Look up data by key (read-only operation).

    This tool only reads data and makes no modifications.
    Safe for unrestricted use.
    """
    return database.get(key)
```

### Best Practices

✅ **DO:**

- Start with `tools="safe"` for read-only tasks
- Use specific tool lists instead of `tools=True` when possible
- Enable only the tools you need
- Review audit logs regularly
- Test tools in safe environments first

❌ **DON'T:**

- Use `tools="dangerous"` unless necessary
- Auto-approve dangerous operations in production
- Disable audit logging
- Give custom tools lower risk levels than appropriate

## Common Use Cases

### Use Case 1: Code Research (Read-Only)

Analyze code without making changes:

```python
from consoul import Consoul

# Only safe search tools
console = Consoul(tools="safe")

# Or be specific
console = Consoul(tools=["grep", "code_search", "find_references"])

# Usage
response = console.ask("Find all functions named 'process_data' and show their usage")
```

### Use Case 2: Web Research

Search and read web content:

```python
# Enable web tools
console = Consoul(tools="web")

# Or combine with search
console = Consoul(tools=["search", "web"])

response = console.ask("Search for Python asyncio tutorials and summarize the top result")
```

### Use Case 3: Development with File Editing

Full development capabilities:

```python
# All search and file editing tools
console = Consoul(tools=["search", "file-edit"])

# Or add bash for testing
console = Consoul(tools=["search", "file-edit", "bash"])

response = console.ask("Refactor the login function to use async/await")
```

### Use Case 4: Mixed Safe + Specific Dangerous

Most tools safe, but allow specific operations:

```python
# Safe tools + specific powerful tools
console = Consoul(tools=["search", "web", "bash", "create_file"])

# Excludes: edit_lines, edit_replace, append_file, delete_file
```

### Use Case 5: Custom Tools for Domain

Add domain-specific tools:

```python
from langchain_core.tools import tool

@tool
def query_customer_db(customer_id: str) -> str:
    """Query customer database."""
    return fetch_customer(customer_id)

@tool
def send_notification(message: str, recipient: str) -> str:
    """Send notification to user."""
    send_email(recipient, message)
    return "Sent"

# Combine with built-in tools
console = Consoul(tools=[
    query_customer_db,
    send_notification,
    "bash",
    "grep"
])
```

### Use Case 6: Auto-Discovery + Categories

Project-specific tools + built-in categories:

```python
# Discover custom tools from .consoul/tools/
# Plus enable search and web categories
console = Consoul(
    tools=["search", "web"],
    discover_tools=True
)

# Now has: grep, code_search, find_references, read_url, web_search
# Plus: Any tools found in .consoul/tools/
```

## Troubleshooting

### Error: Unknown tool or category 'xyz'

**Problem:**
```python
console = Consoul(tools=["invalid"])
# ValueError: Unknown tool or category 'invalid'
```

**Solution:**
Check available tools and categories:

```python
# Valid tool names:
# bash, grep, code_search, find_references, create_file,
# edit_lines, edit_replace, append_file, delete_file,
# read_url, web_search

# Valid categories:
# search, file-edit, web, execute

# Valid risk levels:
# safe, caution, dangerous
```

### Error: Tool specification must be...

**Problem:**
```python
console = Consoul(tools=123)
# ValueError: Invalid tools parameter type
```

**Solution:**
Use one of the valid types:
- Boolean: `True` or `False`
- String: tool name, category, or risk level
- List: list of strings and/or BaseTool instances

### Discovery Not Working

**Problem:**
Tools in `.consoul/tools/` are not being discovered.

**Solutions:**

1. **Check `discover_tools` is enabled:**
   ```python
   console = Consoul(tools=True, discover_tools=True)
   ```

2. **Verify directory structure:**
   ```bash
   ls -la .consoul/tools/
   # Should show your .py files
   ```

3. **Check file names:**
   - Files starting with `_` are skipped
   - `__init__.py` is skipped

4. **Verify tools are instances:**
   ```python
   # ❌ Won't be discovered
   class MyTool(BaseTool):
       ...

   # ✅ Will be discovered
   my_tool = MyTool()
   ```

5. **Check for syntax/import errors:**
   ```python
   # Discovery skips files with errors
   # Check logs for warnings
   ```

### Tools Not Available in Chat

**Problem:**
AI says it cannot use a tool you enabled.

**Solutions:**

1. **Verify tools are enabled:**
   ```python
   console = Consoul(tools=["bash", "grep"])
   print(console.settings)
   # Check 'tools_enabled' is True
   ```

2. **Check tool specification:**
   ```python
   # Make sure you're not using tools=False
   console = Consoul(tools=False)  # ❌ No tools
   console = Consoul(tools=True)   # ✅ All tools
   ```

3. **Restart if needed:**
   SDK caches tool configuration on initialization.

### Custom Tool Not Working

**Problem:**
Custom tool raises errors when called.

**Common Issues:**

1. **Missing docstring:**
   ```python
   @tool
   def my_tool(x: str) -> str:
       """This docstring is REQUIRED."""
       return x
   ```

2. **Invalid input schema:**
   ```python
   from pydantic import BaseModel, Field

   class MyInput(BaseModel):
       arg: str = Field(description="Description REQUIRED")

   @tool(args_schema=MyInput)
   def my_tool(arg: str) -> str:
       ...
   ```

3. **Not instantiated (for BaseTool):**
   ```python
   # ❌ Wrong
   console = Consoul(tools=[MyTool])

   # ✅ Correct
   console = Consoul(tools=[MyTool()])
   ```

## See Also

- **[Complete Tool Documentation](tools.md)** - Detailed docs for all 11 built-in tools
- **[SDK Examples](https://github.com/goatbytes/consoul/tree/main/examples/sdk)** - Runnable code examples
- **[Tool Specification Examples](https://github.com/goatbytes/consoul/tree/main/examples/sdk/tool_specification)** - All specification patterns
- **[Configuration Guide](user-guide/configuration.md)** - Security policies and settings
- **[API Reference](api/index.md)** - Complete API documentation

---

**Quick Links:**

- [Quick Start](#quick-start) - Get started in 60 seconds
- [Built-in Tools](#built-in-tools-reference) - See all available tools
- [Custom Tools](#custom-tools) - Create your own tools
- [Categories](#tool-categories) - Group tools by function
- [Security](#security-considerations) - Risk levels and best practices

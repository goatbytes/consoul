# Consoul SDK Examples

This directory contains comprehensive examples demonstrating various features of the Consoul SDK.

## Quick Start Examples

### Minimal Chat

The simplest possible Consoul setup:

```bash
python minimal_chat.py
```

**File**: `minimal_chat.py`
**Shows**: Basic chat interaction with default settings

### Quick Start

Common initialization patterns:

```bash
python quick_start.py
```

**File**: `quick_start.py`
**Shows**: Multiple ways to initialize Consoul with different configurations

## Tool Specification

Comprehensive guide to configuring tools in the Consoul SDK.

**Directory**: `tool_specification/`
**Documentation**: [tool_specification/README.md](tool_specification/README.md)

### Examples

1. **Basic Patterns** (`01_basic_patterns.py`)
   - Boolean tool specification (True/False)
   - Risk level filtering (safe/caution)
   - Specific tool lists

2. **Categories** (`02_categories.py`)
   - Category-based filtering (search, file-edit, web, execute)
   - Multiple categories
   - Category + specific tool combinations

3. **Custom Tools** (`03_custom_tools.py`)
   - @tool decorator for simple functions
   - BaseTool class for advanced control
   - Integration with built-in tools

4. **Tool Discovery** (`04_tool_discovery.py`)
   - Auto-loading tools from `.consoul/tools/`
   - Recursive directory scanning
   - Combining discovery with other specifications

5. **Security** (`05_security_examples.py`)
   - Risk-based filtering
   - Principle of least privilege
   - Graduated trust levels
   - Security best practices

### Quick Reference

```python
from consoul import Consoul

# All built-in tools
console = Consoul(tools=True)

# Only safe (read-only) tools
console = Consoul(tools="safe")

# Specific tools by name
console = Consoul(tools=["bash", "grep"])

# Tools by category
console = Consoul(tools="search")  # All search tools
console = Consoul(tools=["search", "web"])  # Multiple categories

# Custom tools
from langchain_core.tools import tool

@tool
def my_tool(input: str) -> str:
    """My custom tool."""
    return f"Result: {input}"

console = Consoul(tools=[my_tool, "bash"])

# Auto-discover custom tools
console = Consoul(tools="safe", discover_tools=True)
```

**Full documentation**: [docs/sdk-tools.md](../../docs/sdk-tools.md)

## Advanced Features

### Model Registry

Access comprehensive model metadata, pricing, and capabilities:

```bash
python model_registry_example.py
```

**File**: `model_registry_example.py`
**Shows**:
- List 1,114+ available models with filters
- Get tier-specific pricing information
- Query model capabilities (vision, tools, reasoning, etc.)
- Access complete model metadata
- Find cheapest models by provider

### Custom Approval Provider

Implement custom approval logic for tool execution:

```bash
python cli_approval_example.py
```

**File**: `cli_approval_example.py`
**Shows**: CLI-based approval provider for tool execution approval

### Web Approval Provider

HTTP-based approval system for remote approval:

```bash
python web_approval_provider.py
```

**File**: `web_approval_provider.py`
**Shows**: Web server for remote tool approval via HTTP

### Custom Audit Logger

Track and log AI interactions:

```bash
python custom_audit_logger.py
```

**File**: `custom_audit_logger.py`
**Shows**: Custom audit logging for tool executions and conversations

### Custom Profile

Create and use custom AI profiles:

```bash
python custom_profile.py
```

**File**: `custom_profile.py`
**Shows**: Defining custom AI behavior profiles

### Read File Example

Programmatic file reading and analysis:

```bash
python read_file_example.py
```

**File**: `read_file_example.py`
**Shows**: Using Consoul to analyze file contents

## Example Categories

### By Difficulty

**Beginner**:
- `minimal_chat.py` - Simplest setup
- `quick_start.py` - Common patterns
- `tool_specification/01_basic_patterns.py` - Basic tool config

**Intermediate**:
- `tool_specification/02_categories.py` - Category filtering
- `tool_specification/03_custom_tools.py` - Custom tools
- `custom_profile.py` - Custom profiles

**Advanced**:
- `tool_specification/04_tool_discovery.py` - Auto-discovery
- `model_registry_example.py` - Model registry and pricing
- `cli_approval_example.py` - Custom approval
- `custom_audit_logger.py` - Audit logging
- `web_approval_provider.py` - Remote approval

### By Feature

**Tools**:
- `tool_specification/` - Complete tool specification guide
- `custom_approval_provider.py` - Tool approval

**Security**:
- `tool_specification/05_security_examples.py` - Security best practices
- `cli_approval_example.py` - Approval workflows

**Logging & Audit**:
- `custom_audit_logger.py` - Custom logging

**AI Behavior**:
- `custom_profile.py` - Custom profiles
- `read_file_example.py` - Programmatic usage

**Model Management**:
- `model_registry_example.py` - Model metadata and pricing

## Running Examples

All examples are standalone Python scripts:

```bash
# Run any example directly
python <example_name>.py

# Example with tool specification
python tool_specification/02_categories.py
```

## Common Patterns

### Initialize with Safe Tools

```python
from consoul import Consoul

console = Consoul(tools="safe", persist=False)
console.start()
```

### Initialize with Custom Tools

```python
from consoul import Consoul
from langchain_core.tools import tool

@tool
def analyze_code(code: str) -> str:
    """Analyze code for potential issues."""
    # Your analysis logic
    return "Analysis results"

console = Consoul(tools=[analyze_code, "grep"], persist=False)
```

### Initialize with Discovery

```python
from consoul import Consoul

# Auto-discover tools from .consoul/tools/
console = Consoul(
    tools="search",
    discover_tools=True,
    persist=False
)
```

## Additional Resources

- **Full Tool Documentation**: [docs/sdk-tools.md](../../docs/sdk-tools.md)
- **API Documentation**: See `Consoul` class docstrings
- **Main README**: [../../README.md](../../README.md)

## Need Help?

- Check the [tool specification README](tool_specification/README.md) for tool-related questions
- Review the [full documentation](../../docs/sdk-tools.md)
- Look at similar examples for reference
- Check the `Consoul` class docstrings

## Contributing

Found an issue or have a suggestion? Please report it at the [Consoul repository](https://github.com/goatbytes/consoul).

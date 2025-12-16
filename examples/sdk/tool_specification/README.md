# Tool Specification Examples

This directory contains comprehensive examples demonstrating all aspects of tool specification in the Consoul SDK.

## Quick Start

Run any example directly:

```bash
python 01_basic_patterns.py
python 02_categories.py
python 03_custom_tools.py
python 04_tool_discovery.py
python 05_security_examples.py
```

## Examples Overview

### 1. Basic Patterns (`01_basic_patterns.py`)

Learn the fundamental ways to specify tools:

- **Boolean**: `tools=True` (all tools) or `tools=False` (no tools)
- **Risk Level**: `tools="safe"` or `tools="caution"`
- **Specific Tools**: `tools=["bash", "grep"]`

**Best for**: Understanding the core tool specification options.

### 2. Categories (`02_categories.py`)

Explore category-based filtering for groups of related tools:

- **Single Category**: `tools="search"` (all search tools)
- **Multiple Categories**: `tools=["search", "web"]`
- **Mix**: `tools=["search", "bash"]` (category + specific tool)

**Available Categories**:
- `search`: grep, code_search, find_references
- `file-edit`: create_file, edit_file_lines, edit_file_search_replace, append_to_file, delete_file
- `web`: read_url, web_search
- `execute`: bash

**Best for**: Enabling groups of related tools without listing each one.

### 3. Custom Tools (`03_custom_tools.py`)

Create and integrate your own tools:

- **@tool Decorator**: Simple functions become tools
- **BaseTool Class**: Advanced control and state management
- **Integration**: Mix custom tools with built-in tools and categories

**Best for**: Extending Consoul with project-specific capabilities.

### 4. Tool Discovery (`04_tool_discovery.py`)

Automatic tool loading from directories:

- **Auto-Discovery**: Load tools from `.consoul/tools/`
- **Recursive**: Discover tools in subdirectories
- **Combination**: Discovery + built-in tools, categories, or lists

**Best for**: Managing large custom tool collections.

### 5. Security (`05_security_examples.py`)

Security best practices and risk-based filtering:

- **Risk Levels**: SAFE (read-only) vs CAUTION (read-write)
- **Least Privilege**: Only grant necessary capabilities
- **Graduated Trust**: Start safe, upgrade as needed
- **Discovery Security**: Considerations for auto-loaded tools

**Best for**: Understanding security implications and best practices.

## Common Patterns

### Read-Only Mode (Maximum Security)

```python
from consoul import Consoul

# Only safe, read-only tools
console = Consoul(tools="safe")
```

**Use cases**: Untrusted AI, public-facing assistants, code exploration

### Development Mode (Full Capabilities)

```python
# All built-in tools
console = Consoul(tools=True)

# Or use categories
console = Consoul(tools=["search", "file-edit", "web", "execute"])
```

**Use cases**: Trusted AI, code generation, automated development

### Custom Toolset

```python
# Specific tools only
console = Consoul(tools=["grep", "bash", "create_file"])

# Or mix categories and specific tools
console = Consoul(tools=["search", "create_file", "edit_file_lines"])
```

**Use cases**: Specialized tasks, principle of least privilege

### Custom + Discovery

```python
# Auto-discover custom tools + specific built-in tools
console = Consoul(
    tools=["search", "bash"],
    discover_tools=True
)
```

**Use cases**: Project-specific tools + core capabilities

## Tool Reference

### Built-in Tools

| Tool | Category | Risk | Description |
|------|----------|------|-------------|
| bash | execute | CAUTION | Execute shell commands |
| grep | search | SAFE | Search file contents |
| code_search | search | SAFE | Semantic code search |
| find_references | search | SAFE | Find symbol references |
| create_file | file-edit | CAUTION | Create new files |
| edit_file_lines | file-edit | CAUTION | Edit specific line ranges |
| edit_file_search_replace | file-edit | CAUTION | Search and replace in files |
| append_to_file | file-edit | CAUTION | Append to files |
| delete_file | file-edit | CAUTION | Delete files |
| read_url | web | SAFE | Fetch URL content |
| web_search | web | SAFE | Search the web |

### Risk Levels

- **SAFE**: Read-only operations, no system changes, ideal for untrusted interactions
- **CAUTION**: File operations and command execution, requires oversight
- **DANGEROUS**: Reserved for high-risk operations (currently unused)

## Security Guidelines

### 1. Start Safe

```python
# Begin with read-only tools
console = Consoul(tools="safe")
```

### 2. Principle of Least Privilege

```python
# Only grant what's needed
console = Consoul(tools=["grep", "create_file"])  # Not tools=True
```

### 3. Use Version Control

Always use git to provide a safety net for file operations:

```bash
git status  # Before AI interaction
# ... AI makes changes ...
git diff    # Review changes
git commit  # Or git restore to undo
```

### 4. Review Generated Code

Never blindly execute AI-generated code, especially:
- Shell commands
- File deletions
- System configuration changes

### 5. Graduated Trust

```python
# Phase 1: Evaluation (safe only)
console = Consoul(tools="safe")

# Phase 2: Supervised (caution with review)
console = Consoul(tools="caution")

# Phase 3: Trusted (full capabilities with git safety net)
console = Consoul(tools=True)
```

## Tool Discovery Setup

### Directory Structure

```
your-project/
├── .consoul/
│   └── tools/
│       ├── my_tools.py          # Auto-discovered
│       ├── utils/
│       │   └── helpers.py       # Auto-discovered (recursive)
│       └── _private.py          # Skipped (starts with _)
├── src/
└── ...
```

### Example Custom Tool

```python
# .consoul/tools/my_tools.py

from langchain_core.tools import tool

@tool
def my_custom_tool(input: str) -> str:
    """Description of what this tool does."""
    return f"Processed: {input}"

# For BaseTool subclasses, must instantiate:
from langchain_core.tools import BaseTool

class MyAdvancedTool(BaseTool):
    name: str = "my_advanced_tool"
    description: str = "Advanced tool with custom logic"

    def _run(self, input: str) -> str:
        return f"Advanced: {input}"

# REQUIRED: Instantiate the class
my_advanced_tool = MyAdvancedTool()
```

### Enable Discovery

```python
from consoul import Consoul

# Auto-discover from .consoul/tools/
console = Consoul(
    tools="safe",           # Built-in tools
    discover_tools=True     # + discovered tools
)
```

## Next Steps

1. **Start with `01_basic_patterns.py`** to understand core concepts
2. **Explore `02_categories.py`** for category-based filtering
3. **Create custom tools** with `03_custom_tools.py` as a guide
4. **Set up discovery** following `04_tool_discovery.py`
5. **Review security** with `05_security_examples.py`

## Additional Resources

- **Full Documentation**: [docs/sdk-tools.md](../../../docs/sdk-tools.md)
- **SDK Reference**: [examples/sdk/README.md](../README.md)
- **API Documentation**: See `Consoul` class docstring

## Troubleshooting

### "No tools registered"

```python
# Problem: tools=[] or tools=False
console = Consoul(tools=[])

# Solution: Specify tools
console = Consoul(tools=True)  # or tools="safe", etc.
```

### "Invalid category"

```python
# Problem: Typo in category name
console = Consoul(tools="serach")  # Wrong

# Solution: Use exact category names
console = Consoul(tools="search")  # Correct
```

### Custom tool not discovered

```python
# Problem: BaseTool class not instantiated
class MyTool(BaseTool):
    ...
# Not instantiated - won't be discovered!

# Solution: Instantiate the class
my_tool = MyTool()  # This will be discovered
```

### Tools not combining

```python
# Problem: Overwriting instead of combining
console = Consoul(tools="search")
console = Consoul(tools="web")  # Overwrites previous

# Solution: Combine in single call
console = Consoul(tools=["search", "web"])  # Both categories
```

## Contributing

Found an issue or have a suggestion? Please report it at the [Consoul repository](https://github.com/goatbytes/consoul).

# Code Search Guide

Comprehensive guide to Consoul's code search tools for semantic code analysis and navigation.

## Table of Contents

- [Overview](#overview)
- [Available Tools](#available-tools)
- [When to Use Which Tool](#when-to-use-which-tool)
- [Language Support](#language-support)
- [Common Use Cases](#common-use-cases)
- [Performance](#performance)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)

## Overview

Consoul provides three complementary code search tools that work together to help you understand and navigate codebases:

1. **grep_search** - Fast text-based pattern matching
2. **code_search** - AST-based semantic symbol search
3. **find_references** - Symbol usage finder

These tools are designed to work like an IDE's navigation features, but accessible through AI chat or programmatic SDK usage.

### Key Benefits

- **Semantic Understanding**: AST-based parsing understands code structure, not just text
- **Multi-Language**: Support for Python, JavaScript/TypeScript, Go, Rust, Java, C/C++
- **Fast with Caching**: Intelligent mtime-based caching provides 5-10x speedup
- **Safe Operations**: All search tools are read-only (RiskLevel.SAFE)
- **AI-Friendly**: Designed for tool calling with clear, structured JSON output

## Available Tools

### grep_search

**Purpose:** Fast text pattern matching across files

**Use when:**
- Searching for simple text strings or regex patterns
- Finding TODO/FIXME comments
- Searching across any file type (not just code)
- Need fastest possible search
- Pattern doesn't require understanding code structure

**Technology:** ripgrep (with grep fallback)

**Speed:** Very fast (<1s for typical projects)

**Example:**
```python
from consoul.ai.tools import grep_search

# Find all TODO comments in Python files
result = grep_search.invoke({
    "pattern": "TODO",
    "glob_pattern": "*.py",
    "case_sensitive": False
})
```

### code_search

**Purpose:** Find symbol definitions (functions, classes, methods)

**Use when:**
- Finding where a function/class is defined
- Locating symbol definitions before reading code
- Building code inventory or documentation
- Need to understand code structure

**Technology:** tree-sitter AST parsing

**Speed:** Fast with cache (~1-2s first run, <1s cached)

**Example:**
```python
from consoul.ai.tools import code_search

# Find the ToolRegistry class definition
result = code_search.invoke({
    "query": "ToolRegistry",
    "symbol_type": "class"
})
```

### find_references

**Purpose:** Find all usages/references of a symbol

**Use when:**
- Planning to refactor/rename a function
- Understanding how a symbol is used
- Finding dead code (zero references)
- Impact analysis before changes
- Understanding dependencies

**Technology:** tree-sitter AST parsing (with cache)

**Speed:** Medium (~2-3s first run, <1s cached)

**Example:**
```python
from consoul.ai.tools import find_references

# Find all usages of bash_execute
result = find_references.invoke({
    "symbol": "bash_execute",
    "scope": "project"
})
```

## When to Use Which Tool

### Decision Matrix

| Question | Tool | Why |
|----------|------|-----|
| "Where is function X defined?" | `code_search` | Finds definitions semantically |
| "Where is function X used?" | `find_references` | Finds all usages |
| "Find all TODO comments" | `grep_search` | Text pattern in comments |
| "What functions are in file.py?" | `code_search` | Lists all symbols |
| "Is this function still used?" | `find_references` | Check for usages |
| "Find all error messages" | `grep_search` | String literal search |
| "Find calls to deprecated_fn" | `find_references` | Finds function calls |
| "Find class MyClass" | `code_search` | Find class definition |
| "Search across all file types" | `grep_search` | Works on any text |
| "Find imports of module X" | `find_references` | Finds import statements |

### Tool Comparison

|  | grep_search | code_search | find_references |
|---|-------------|-------------|-----------------|
| **What it finds** | Text patterns | Symbol definitions | Symbol usages |
| **Understanding** | Text-based | Structure-aware | Structure-aware |
| **Speed** | Very fast | Fast (cached) | Medium (cached) |
| **File types** | Any text | Source code | Source code |
| **Comments** | ✅ Finds in comments | ❌ Ignores comments | ❌ Ignores comments |
| **Strings** | ✅ Finds in strings | ❌ Ignores strings | ❌ Ignores strings |
| **Context** | Line context | Symbol context | Usage context |
| **Cache** | N/A | ✅ Cached | ✅ Cached |

### Common Workflows

**Refactoring a Function:**
```
1. code_search → Find definition
2. find_references → Find all usages
3. Analyze impact
4. Make changes
5. find_references → Verify no broken references
```

**Understanding a Feature:**
```
1. grep_search → Find relevant comments/docs
2. code_search → Find main classes/functions
3. find_references → Understand dependencies
```

**Code Review:**
```
1. grep_search → Find TODOs, FIXMEs, console.logs
2. code_search → Check new symbols added
3. find_references → Verify proper usage
```

## Language Support

### Support Matrix

| Language | Extension | grep_search | code_search | find_references | Notes |
|----------|-----------|-------------|-------------|-----------------|-------|
| **Python** | .py | ✅ | ✅ | ✅ | Full support |
| **JavaScript** | .js | ✅ | ✅ | ✅ | Full support |
| **TypeScript** | .ts, .tsx | ✅ | ✅ | ✅ | Full support |
| **JSX** | .jsx | ✅ | ✅ | ✅ | Full support |
| **Go** | .go | ✅ | ✅ | ✅ | Full support |
| **Rust** | .rs | ✅ | ✅ | ❌ | Use grep_search for references |
| **Java** | .java | ✅ | ✅ | ❌ | Use grep_search for references |
| **C** | .c, .h | ✅ | ✅ | ❌ | Use grep_search for references |
| **C++** | .cpp, .hpp | ✅ | ✅ | ❌ | Use grep_search for references |

**Legend:**
- ✅ Full support - All features work correctly
- ❌ No support - Tool doesn't work for this language

**Note:** find_references currently only implements reference detection for Python, JavaScript/TypeScript, and Go. For Rust, Java, and C/C++, use grep_search for text-based reference finding.

### Detected Node Types by Language

#### Python
- **Definitions:** function_definition, class_definition, method
- **References:** call, import_from_statement, attribute

#### JavaScript/TypeScript
- **Definitions:** function_declaration, class_declaration, method_definition
- **References:** call_expression, import_specifier, member_expression

#### Go
- **Definitions:** function_declaration, type_declaration
- **References:** call_expression, selector_expression

## Common Use Cases

### 1. Find All TODO Comments

**Goal:** Locate all TODO items across the project

**Tool:** grep_search

```python
result = grep_search.invoke({
    "pattern": r"TODO|FIXME|XXX|HACK",
    "glob_pattern": "*.{py,js,ts}",
    "context_lines": 2
})
```

**Why grep_search?** TODOs are in comments, which AST tools ignore.

### 2. Find Function Definition

**Goal:** Locate where `calculate_total` is defined

**Tool:** code_search

```python
result = code_search.invoke({
    "query": "calculate_total",
    "symbol_type": "function"
})
```

**Why code_search?** Finds exact definition location semantically.

### 3. Find All Function Usages

**Goal:** Find every call to `deprecated_function` before removing it

**Tool:** find_references

```python
result = find_references.invoke({
    "symbol": "deprecated_function",
    "scope": "project",
    "include_definition": True  # Shows definition + usages
})
```

**Why find_references?** Distinguishes function calls from definition.

### 4. Locate Dead Code

**Goal:** Find functions with zero references

**Workflow:**
```python
# 1. Get all functions
functions = code_search.invoke({"symbol_type": "function"})

# 2. Check each for references
for func in parse_results(functions):
    refs = find_references.invoke({"symbol": func["name"]})
    if len(parse_results(refs)) == 0:
        print(f"Dead code: {func['name']} at {func['file']}:{func['line']}")
```

### 5. Understand Class Dependencies

**Goal:** See how `ShoppingCart` class is used

**Workflow:**
```python
# 1. Find class definition
definition = code_search.invoke({
    "query": "ShoppingCart",
    "symbol_type": "class"
})

# 2. Find all usages
usages = find_references.invoke({
    "symbol": "ShoppingCart",
    "scope": "project"
})

# 3. Analyze instantiations vs imports
```

### 6. Search Across Documentation

**Goal:** Find documentation for a specific API

**Tool:** grep_search

```python
result = grep_search.invoke({
    "pattern": "authenticate user",
    "path": "docs/",
    "case_sensitive": False
})
```

**Why grep_search?** Markdown/docs aren't source code.

### 7. Find All Methods of a Class

**Goal:** List all methods in `ToolRegistry` class

**Tool:** code_search

```python
result = code_search.invoke({
    "query": ".*",  # Match all
    "symbol_type": "method",
    "path": "src/consoul/ai/tools/registry.py"
})
```

### 8. Pre-Refactoring Analysis

**Goal:** Safely rename `old_name` to `new_name`

**Complete Workflow:**
```python
# 1. Find definition
definition = code_search.invoke({"query": "old_name"})
print(f"Defined at: {definition}")

# 2. Find all usages
references = find_references.invoke({"symbol": "old_name"})
usage_count = len(parse_results(references))
print(f"Found {usage_count} usages")

# 3. Review each usage before refactoring
# 4. Make changes
# 5. Verify with find_references again
```

## Performance

### Speed Benchmarks

**Typical project (1000 files, ~100K LOC):**

| Tool | First Run | Cached | Cache Benefit |
|------|-----------|--------|---------------|
| grep_search | 0.5s | 0.5s | N/A (always fast) |
| code_search | 2.5s | 0.3s | **8x faster** |
| find_references | 3.0s | 0.4s | **7x faster** |

**Large project (5000 files, ~500K LOC):**

| Tool | First Run | Cached | Cache Benefit |
|------|-----------|--------|---------------|
| grep_search | 1.2s | 1.2s | N/A |
| code_search | 8.5s | 0.8s | **10x faster** |
| find_references | 10.0s | 1.0s | **10x faster** |

### Cache Behavior

**How caching works:**
1. **First search:** Parses AST and caches results with file mtime
2. **Subsequent searches:** Checks mtime, returns cached data if unchanged
3. **File modified:** Detects mtime change, reparses file
4. **Shared cache:** code_search and find_references share cache instance

**Cache keys:**
- code_search: `tags:{file_path}`
- find_references: `refs:{file_path}`

**Cache location:**
- Default: `~/.consoul/cache/code-search.v1/`
- Configurable via CodeSearchCache initialization

### Optimization Tips

**1. Use narrowest scope possible**
```python
# Slow - searches entire project
find_references.invoke({"symbol": "foo", "scope": "project"})

# Fast - searches one directory
find_references.invoke({"symbol": "foo", "scope": "directory", "path": "src/"})

# Fastest - searches one file
find_references.invoke({"symbol": "foo", "scope": "file", "path": "src/main.py"})
```

**2. Use ripgrep for text search**
```bash
# Install ripgrep for 5-10x faster grep_search
brew install ripgrep  # macOS
apt-get install ripgrep  # Ubuntu
```

**3. Warm up cache for common operations**
```python
# Run code_search once to populate cache
code_search.invoke({"query": ".*", "path": "src/"})

# Future searches will be much faster
```

**4. Filter by symbol type**
```python
# Faster - parses less
code_search.invoke({"query": "Foo", "symbol_type": "class"})

# Slower - searches all symbol types
code_search.invoke({"query": "Foo"})
```

**5. Use case-insensitive search wisely**
```python
# Slower - must check more variations
find_references.invoke({"symbol": "foo", "case_sensitive": False})

# Faster - exact match only
find_references.invoke({"symbol": "Foo", "case_sensitive": True})
```

## Integration Patterns

### Pattern 1: Multi-Step Discovery

```python
from consoul import Consoul

console = Consoul(tools=True)

# Step 1: Find potential matches with grep
grep_results = console.chat("Search for 'calculate' in Python files")

# Step 2: Find exact definitions
code_results = console.chat("Find the calculate_total function definition")

# Step 3: Find all usages
ref_results = console.chat("Find all usages of calculate_total")
```

### Pattern 2: Programmatic Search Workflow

```python
from consoul.ai.tools import grep_search, code_search, find_references
import json

def analyze_function(function_name: str):
    """Complete analysis of a function."""

    # 1. Find definition
    definition = code_search.invoke({
        "query": function_name,
        "symbol_type": "function"
    })
    def_data = json.loads(definition)

    if not def_data:
        print(f"Function {function_name} not found")
        return

    # 2. Find references
    references = find_references.invoke({
        "symbol": function_name,
        "scope": "project"
    })
    ref_data = json.loads(references)

    # 3. Report
    print(f"Function: {function_name}")
    print(f"Defined at: {def_data[0]['file']}:{def_data[0]['line']}")
    print(f"Used {len(ref_data)} times")

    return {
        "definition": def_data[0],
        "references": ref_data,
        "usage_count": len(ref_data)
    }

# Use it
analyze_function("bash_execute")
```

### Pattern 3: Custom Approval for Search

```python
from consoul.ai.tools import ToolRegistry, RiskLevel
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.ai.tools import grep_search, code_search, find_references

# All search tools are SAFE - can auto-approve
registry = ToolRegistry(
    config=config.tools,
    approval_provider=CliApprovalProvider()
)

# Register search tools (all SAFE)
registry.register(grep_search, risk_level=RiskLevel.SAFE)
registry.register(code_search, risk_level=RiskLevel.SAFE)
registry.register(find_references, risk_level=RiskLevel.SAFE)

# Bind to model for AI usage
model = registry.bind_to_model(model)
```

### Pattern 4: Batch Analysis

```python
def find_unused_functions(directory: str):
    """Find functions with zero references."""

    # Get all functions
    all_functions = code_search.invoke({
        "symbol_type": "function",
        "path": directory
    })

    functions = json.loads(all_functions)
    unused = []

    for func in functions:
        # Check for usages
        refs = find_references.invoke({
            "symbol": func["name"],
            "scope": "directory",
            "path": directory
        })

        ref_count = len(json.loads(refs))
        if ref_count == 0:
            unused.append(func)

    return unused

# Find unused functions in src/
unused = find_unused_functions("src/")
print(f"Found {len(unused)} unused functions")
```

## Best Practices

### 1. Choose the Right Tool

✅ **DO:**
- Use grep_search for comments, strings, and documentation
- Use code_search to find definitions
- Use find_references to find usages
- Combine tools for comprehensive analysis

❌ **DON'T:**
- Use grep_search for finding function calls (use find_references)
- Use code_search for text in comments (use grep_search)
- Search entire project when you know the directory

### 2. Leverage Caching

✅ **DO:**
- Run searches on same files multiple times to benefit from cache
- Use code_search before find_references (shares cache)
- Keep searches in same session for cache benefit

❌ **DON'T:**
- Clear cache unnecessarily
- Run searches in separate processes (cache not shared)

### 3. Scope Appropriately

✅ **DO:**
- Use file scope when you know the file
- Use directory scope for package/module searches
- Use project scope only when necessary

❌ **DON'T:**
- Default to project scope for everything
- Search entire codebase for file-specific questions

### 4. Handle Results Properly

✅ **DO:**
- Parse JSON results before using
- Check for empty results
- Handle errors gracefully
- Validate file paths exist

❌ **DON'T:**
- Assume results are always valid
- Ignore empty result sets
- Skip error handling

### 5. Performance Optimization

✅ **DO:**
- Install ripgrep for faster grep_search
- Use specific symbol_type filters
- Warm cache for frequently searched directories
- Use case-sensitive search when possible

❌ **DON'T:**
- Search with overly broad patterns
- Disable caching
- Search large binary files
- Use case-insensitive unless needed

## See Also

- [Tool Calling Documentation](../tools.md) - Complete tool reference
- [SDK Integration Guide](../sdk/tool-calling-integration.md) - Embedding in applications
- [Code Examples](../examples/code-search-example.py) - Working Python examples
- [Troubleshooting Guide](code-search-troubleshooting.md) - Common issues and solutions

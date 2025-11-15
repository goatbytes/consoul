# Tool Calling

Comprehensive guide to Consoul's tool calling system for AI-powered command execution.

## Table of Contents

- [Introduction](#introduction)
- [Available Tools](#available-tools)
  - [bash_execute](#bash_execute)
  - [grep_search](#grep_search)
  - [code_search](#code_search)
  - [find_references](#find_references)
  - [read_file](#read_file)
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

### grep_search

Search for text patterns in files using ripgrep or grep.

**Capabilities:**
- Fast regex-based text search across files and directories
- Automatic ripgrep detection with grep fallback
- Glob pattern filtering (e.g., "*.py", "*.{js,ts}")
- Case-sensitive/insensitive search
- Context lines (before/after matches)
- JSON formatted results with file paths, line numbers, and context

**Risk Level**: SAFE (read-only operation)

**Example:**
```python
# Basic search
result = grep_search(
    pattern="def main",
    path="src/",
    glob_pattern="*.py"
)

# Case-insensitive search with context
result = grep_search(
    pattern="TODO",
    path=".",
    case_sensitive=False,
    context_lines=2
)

# Regex pattern search
result = grep_search(
    pattern=r"class \w+Error",
    path="src/",
    glob_pattern="*.py"
)
```

**Output Format:**
```json
[
  {
    "file": "src/main.py",
    "line": 42,
    "text": "def main():",
    "context_before": [
      "#!/usr/bin/env python3",
      ""
    ],
    "context_after": [
      "    print('Hello, world!')",
      "    return 0"
    ]
  }
]
```

**Parameters:**
- `pattern` (str): Regex pattern to search for (required)
- `path` (str): Directory or file path to search (default: ".")
- `glob_pattern` (str | None): Glob pattern to filter files (e.g., "*.py")
- `case_sensitive` (bool): Whether search is case-sensitive (default: True)
- `context_lines` (int): Number of context lines before/after matches (default: 0)
- `timeout` (int | None): Search timeout in seconds (default: 30)

**Performance:**
- Automatically uses ripgrep (rg) if available for ~5-10x speedup
- Falls back to grep if ripgrep not installed
- Both produce identical normalized JSON output

**Configuration:**
```yaml
tools:
  grep_search:
    timeout: 30  # Max search time in seconds
```

**Use Cases:**
- Find function/class definitions
- Search for TODO/FIXME comments
- Locate error handling patterns
- Code review and analysis
- Documentation searches

### code_search

Search for code symbols (functions, classes, methods) using AST parsing.

**Capabilities:**
- Semantic search by symbol structure (not text patterns)
- Multi-language support (Python, JS/TS, Go, Rust, Java, C/C++)
- Symbol type filtering (function, class, method)
- Regex pattern matching on symbol names
- Automatic caching with mtime invalidation (5-10x speedup)
- JSON formatted results with context

**Risk Level**: SAFE (read-only operation)

**Example:**
```python
# Find all functions named 'calculate_total'
result = code_search(
    query="calculate_total",
    symbol_type="function"
)

# Find classes matching pattern
result = code_search(
    query="Shopping.*",
    symbol_type="class",
    path="src/"
)

# Case-insensitive search
result = code_search(
    query="PROCESS.*",
    case_sensitive=False
)
```

**Output Format:**
```json
[
  {
    "name": "calculate_total",
    "type": "function",
    "line": 5,
    "file": "src/utils.py",
    "text": "def calculate_total(items):",
    "context_before": ["", "# Calculate total price"],
    "context_after": ["    total = 0", "    for item in items:"],
    "parent": null
  }
]
```

**Parameters:**
- `query` (str): Symbol name or regex pattern (required)
- `path` (str): Directory or file path to search (default: ".")
- `symbol_type` (str | None): Filter by "function", "class", or "method"
- `case_sensitive` (bool): Case-sensitive matching (default: False)
- `timeout` (int | None): Search timeout in seconds (default: 60)

**Performance:**
- First search: Parses AST (slower, ~1-2s per 100 files)
- Cached searches: 5-10x faster via mtime-based caching
- Automatic cache invalidation on file modification
- Skips files > 1MB by default (configurable)

**Supported Languages:**
- Python (.py)
- JavaScript/TypeScript (.js, .jsx, .ts, .tsx)
- Go (.go)
- Rust (.rs)
- Java (.java)
- C/C++ (.c, .cpp, .h, .hpp)

**Configuration:**
```yaml
tools:
  code_search:
    timeout: 60                # Max parsing time in seconds
    max_file_size_kb: 1024     # Skip files larger than 1MB
    supported_extensions:      # Customize supported file types
      - .py
      - .js
      - .go
```

**Use Cases:**
- Find function/class definitions
- Navigate large codebases
- Code refactoring (find all usages)
- Architecture analysis
- Symbol inventory

**vs grep_search:**
- grep_search: Fast text matching, finds any pattern
- code_search: Slower but semantic, finds symbols by structure

### find_references

Find all references/usages of a code symbol across the codebase.

**Capabilities:**
- Distinguish symbol references (usages) from definitions
- Multi-language AST-based reference detection
- Scope control: file, directory, project
- Optional definition inclusion
- Case-sensitive/insensitive matching
- JSON formatted results with context

**Risk Level**: SAFE (read-only operation)

**Example:**
```python
# Find all usages of a function (excluding definition)
result = find_references(
    symbol="calculate_total",
    path="src/",
    scope="directory"
)

# Find all references including the definition
result = find_references(
    symbol="ShoppingCart",
    path="src/cart.py",
    scope="file",
    include_definition=True
)

# Case-insensitive regex pattern matching
result = find_references(
    symbol="process.*",
    path=".",
    scope="project",
    case_sensitive=False
)
```

**Output Format:**
```json
[
  {
    "symbol": "calculate_total",
    "type": "call",
    "line": 42,
    "file": "src/utils.py",
    "text": "    total = calculate_total(items)",
    "context_before": ["def process_order(items):", "    # Calculate final price"],
    "context_after": ["    tax = total * 0.08", "    return total + tax"],
    "is_definition": false
  }
]
```

**Parameters:**
- `symbol` (str): Symbol name or regex pattern (required)
- `path` (str): File/directory path to search (default: ".")
- `scope` (str): Search scope - "file", "directory", or "project" (default: "project")
- `case_sensitive` (bool): Case-sensitive matching (default: False)
- `include_definition` (bool): Include symbol definition in results (default: False)

**Reference Types (by language):**

Python:
- `call` - Function/method calls (e.g., `foo()`, `obj.method()`)
- `import_from` - Imports (e.g., `from module import foo`)
- `attribute` - Attribute access (e.g., `obj.foo`)

JavaScript/TypeScript:
- `call_expression` - Function calls
- `import_specifier` - Import statements
- `member_expression` - Property access

Go:
- `call_expression` - Function calls
- `selector_expression` - Field/method access

**Supported Languages:**
- Python (.py) - Full support
- JavaScript/TypeScript (.js, .jsx, .ts, .tsx) - Full support
- Go (.go) - Full support
- Kotlin (.kt) - Full support

**Note:** While code_search supports Rust, Java, and C/C++, find_references currently only implements reference detection for Python, JavaScript/TypeScript, Go, and Kotlin. Use grep_search for text-based reference finding in other languages.

**Scope Options:**

| Scope | Behavior | Use Case |
|-------|----------|----------|
| `file` | Search single file | Quick reference check in one file |
| `directory` | Search directory (non-recursive) | Search specific package/module |
| `project` | Search entire project (recursive) | Complete reference audit |

**Configuration:**
```yaml
tools:
  find_references:
    max_file_size_kb: 1024     # Skip files larger than 1MB
    max_results: 100           # Limit results (prevents overflow)
    supported_extensions:      # Customize supported file types
      - .py
      - .js
      - .ts
      - .go
```

**Use Cases:**
- Find all usages before refactoring
- Locate dead code (zero references)
- Understand code dependencies
- Impact analysis for API changes
- Navigate large codebases

**vs code_search:**
- code_search: Finds definitions (where symbols are declared)
- find_references: Finds usages (where symbols are used)

**Performance:**
- Shares cache with code_search (5-10x speedup on cached files)
- First search: Parses AST (~1-2s per 100 files)
- Cached searches: ~10x faster
- Skips files > 1MB by default

**Example Workflows:**

Find function before renaming:
```python
# Check all usages first
refs = find_references(symbol="old_function_name")
# If safe: rename and update all references
```

Locate dead code:
```python
# Search for zero references
refs = find_references(symbol="unused_helper")
# If empty: safe to remove
```

Include definition for complete picture:
```python
# Get definition + all usages
refs = find_references(
    symbol="DatabaseConnection",
    include_definition=True
)
# First result (is_definition=True) shows where it's defined
# Remaining results show all usages
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
from consoul.ai.tools.implementations import read_file

# Tools are LangChain StructuredTool instances; call via .invoke()
# Read entire file
result = read_file.invoke({"file_path": "src/main.py"})

# Read specific line range
result = read_file.invoke({"file_path": "README.md", "offset": 10, "limit": 20})

# Read PDF pages
result = read_file.invoke(
    {"file_path": "docs/design.pdf", "start_page": 5, "end_page": 7}
)
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
pip install "consoul[pdf]"

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

## Tool Comparison

### When to Use Which Tool

| Task | Recommended Tool | Why |
|------|------------------|-----|
| Find TODO comments | `grep_search` | Comments aren't in AST |
| Find function definition | `code_search` | Semantic structure-aware search |
| Find all function calls | `find_references` | Tracks symbol usages |
| Search error messages | `grep_search` | String literal search |
| Pre-refactoring analysis | `find_references` | Impact analysis |
| Search any file type | `grep_search` | Works on all text |
| Find class definition | `code_search` | AST-based symbol search |
| Locate dead code | `code_search` + `find_references` | Definition without usages |
| Read file contents | `read_file` | Formatted output with line numbers |
| Run analysis scripts | `bash_execute` | Execute commands |

### Search Tools Comparison Matrix

Comparison of the three code search tools:

|  | grep_search | code_search | find_references |
|---|-------------|-------------|-----------------|
| **What it finds** | Text patterns | Symbol definitions | Symbol usages |
| **Understanding** | Text-based | Structure-aware (AST) | Structure-aware (AST) |
| **Speed** | Very fast (<1s) | Fast (cached: <1s, uncached: 1-2s) | Medium (cached: <1s, uncached: 2-3s) |
| **File types** | Any text | Source code only | Source code only |
| **Comments** | ✅ Finds in comments | ❌ Ignores comments | ❌ Ignores comments |
| **Strings** | ✅ Finds in strings | ❌ Ignores strings | ❌ Ignores strings |
| **Cache** | N/A | ✅ mtime-based | ✅ Shared with code_search |
| **Context** | Line context (before/after) | Symbol context | Usage context |
| **Regex support** | ✅ Full regex | ✅ Symbol names only | ✅ Symbol names only |
| **Risk Level** | SAFE | SAFE | SAFE |

### Multi-Language Support

Support matrix for all available tools:

| Language | Extensions | grep_search | code_search | find_references | read_file |
|----------|-----------|-------------|-------------|-----------------|-----------|
| **Python** | .py | ✅ | ✅ | ✅ | ✅ |
| **JavaScript** | .js, .jsx | ✅ | ✅ | ✅ | ✅ |
| **TypeScript** | .ts, .tsx | ✅ | ✅ | ✅ | ✅ |
| **Go** | .go | ✅ | ✅ | ✅ | ✅ |
| **Kotlin** | .kt | ✅ | ✅ | ✅ | ✅ |
| **Rust** | .rs | ✅ | ✅ | ❌ | ✅ |
| **Java** | .java | ✅ | ✅ | ❌ | ✅ |
| **C/C++** | .c, .cpp, .h, .hpp | ✅ | ✅ | ❌ | ✅ |
| **Markdown** | .md | ✅ | ❌ | ❌ | ✅ |
| **JSON** | .json | ✅ | ❌ | ❌ | ✅ |
| **YAML** | .yaml, .yml | ✅ | ❌ | ❌ | ✅ |
| **PDF** | .pdf | ❌ | ❌ | ❌ | ✅* |

**Legend:**
- ✅ Full support - All features work correctly
- ❌ No support - Tool doesn't work for this file type
- \* Requires `pypdf` package (install with `pip install consoul[pdf]`)

**Note:** find_references supports Python, JavaScript/TypeScript, Go, and Kotlin. For Rust, Java, and C/C++, use grep_search for text-based reference finding.

### Common Workflows

#### Workflow 1: Refactoring a Function

```python
from consoul.ai.tools import code_search, find_references
import json

# Step 1: Find definition
definition = code_search.invoke({
    "query": "old_function_name",
    "symbol_type": "function"
})

def_data = json.loads(definition)
print(f"Defined at: {def_data[0]['file']}:{def_data[0]['line']}")

# Step 2: Find all usages
references = find_references.invoke({
    "symbol": "old_function_name",
    "scope": "project"
})

ref_data = json.loads(references)
print(f"Used {len(ref_data)} times in {len({r['file'] for r in ref_data})} files")

# Step 3: Review each usage before refactoring
for ref in ref_data:
    print(f"  {ref['file']}:{ref['line']} - {ref['type']}")
```

#### Workflow 2: Understanding a Feature

```python
# Step 1: Find documentation mentions
docs = grep_search.invoke({
    "pattern": "authentication",
    "path": "docs/",
    "case_sensitive": False
})

# Step 2: Find main classes
classes = code_search.invoke({
    "query": ".*Auth.*",
    "symbol_type": "class",
    "path": "src/"
})

# Step 3: Find dependencies
references = find_references.invoke({
    "symbol": "AuthManager",
    "scope": "project"
})
```

#### Workflow 3: Code Review

```python
# Find potential issues
todos = grep_search.invoke({
    "pattern": r"TODO|FIXME|XXX|HACK",
    "glob_pattern": "*.py"
})

# Find new symbols added
new_functions = code_search.invoke({
    "query": "process_.*",
    "symbol_type": "function",
    "path": "src/new_feature/"
})

# Verify proper usage
for func in json.loads(new_functions):
    refs = find_references.invoke({
        "symbol": func["name"],
        "scope": "project"
    })
    ref_count = len(json.loads(refs))
    print(f"{func['name']}: {ref_count} usages")
```

### Performance Characteristics

| Tool | First Run | Cached | Cache Benefit | Typical Project (1000 files) |
|------|-----------|--------|---------------|------------------------------|
| **grep_search** | 0.5s | 0.5s | N/A (always fast) | 0.5-1s |
| **code_search** | 2.5s | 0.3s | **8x faster** | 1-3s uncached, 0.2-0.5s cached |
| **find_references** | 3.0s | 0.4s | **7x faster** | 2-4s uncached, 0.3-0.6s cached |
| **read_file** | <0.1s | N/A | N/A | <0.1s per file |
| **bash_execute** | Varies | N/A | N/A | Command-dependent |

**Optimization Tips:**
1. Use narrowest scope possible (`file` > `directory` > `project`)
2. Install ripgrep for faster grep_search
3. Filter by symbol_type in code_search
4. Use case-sensitive search when possible
5. Warm cache for frequently searched directories

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

## Code Search Caching

### Overview

Consoul implements intelligent caching for code search operations to dramatically improve performance on repeated searches. The cache stores parsed AST (Abstract Syntax Tree) data to avoid expensive re-parsing of unchanged files.

**Key Benefits:**
- **5-10x faster** repeated searches
- **Automatic invalidation** when files change
- **LRU eviction** to manage cache size
- **SQLite-backed** for reliability
- **Thread-safe** for concurrent access

### How It Works

```
First Search:  Parse File → Cache AST → Return Results  (~100ms)
Second Search: Check Cache → Return Results            (~10ms)
File Modified: Invalidate → Re-parse → Update Cache
```

The cache uses file modification time (mtime) to detect changes:
1. When a file is parsed, its AST and mtime are cached
2. On subsequent searches, mtime is checked
3. If mtime matches, cached AST is returned (cache hit)
4. If mtime differs, file is re-parsed (cache miss)

### Configuration

The cache is automatically enabled for code search operations with sensible defaults:

```python
from consoul.ai.tools.cache import CodeSearchCache

# Default configuration (recommended)
cache = CodeSearchCache()
# Location: ~/.consoul/cache/code-search.v1/
# Size limit: 100MB
# Eviction: LRU (least-recently-used)

# Custom configuration
cache = CodeSearchCache(
    cache_dir=Path("/tmp/my-project-cache"),  # Use dedicated directory
    size_limit_mb=200  # 200MB cache
)
```

### Cache Safety

⚠️ **Important:** When using custom cache directories, use dedicated directories for cache data only.

**Safe custom directories:**
- ✅ `/tmp/my-app-cache` - Temporary dedicated directory
- ✅ `/var/cache/my-app` - System cache directory
- ✅ `~/.cache/my-project` - User cache directory
- ✅ `project-root/.cache` - Project-specific cache

**Unsafe custom directories (DON'T USE):**
- ❌ `/home/user/documents` - Contains other important files
- ❌ `/Users/user/Desktop` - User workspace
- ❌ `/var/www` - Application code
- ❌ Any directory with mixed content

**Why?** Consoul manages cache directories and may recreate them on errors. While custom directories are never automatically deleted (safety feature), you should still use dedicated cache directories to avoid mixing cache data with other important files.

### Usage Example

```python
from pathlib import Path
from consoul.ai.tools.cache import CodeSearchCache

cache = CodeSearchCache()

# Check cache before parsing
file_path = Path("src/myproject/utils.py")
cached_tags = cache.get_cached_tags(file_path)

if cached_tags is None:
    # Cache miss - parse file
    tags = parse_file_ast(file_path)  # Expensive operation
    cache.cache_tags(file_path, tags)
else:
    # Cache hit - use cached data
    tags = cached_tags  # ~10x faster

# Get cache statistics
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.1%}")
print(f"Cache size: {stats.size_bytes / 1024 / 1024:.1f} MB")
print(f"Entries: {stats.entry_count}")
```

### Cache Statistics

Monitor cache performance:

```python
stats = cache.get_stats()

# CacheStats attributes:
stats.hits         # Number of cache hits
stats.misses       # Number of cache misses
stats.hit_rate     # Hit rate (0.0 to 1.0)
stats.size_bytes   # Current cache size in bytes
stats.entry_count  # Number of cached files
```

### Cache Management

```python
# Clear all cached entries
cache.invalidate_cache()

# Close cache (releases SQLite connections)
cache.close()

# Cache automatically reopens on next access
```

### Cache Versioning

The cache directory includes a version number (`code-search.v1`) to handle schema changes:

- When the cache format changes, the version is incremented
- Different versions use separate directories
- Old cache versions are automatically ignored
- This prevents compatibility issues after upgrades

### Error Handling

The cache gracefully handles errors:

```python
# If SQLite fails, cache falls back to in-memory dict
# Operations continue working, just without persistence

cache = CodeSearchCache()
# If diskcache fails: cache._cache = dict()
# All operations still work, just not persisted to disk
```

### Performance Tips

1. **Let the cache warm up**: First searches are slower while building cache
2. **Monitor hit rate**: Aim for >80% hit rate in typical workflows
3. **Adjust size limit**: Increase if working with large codebases
4. **Clear stale cache**: Run `invalidate_cache()` after major refactors

### Thread Safety

The cache is thread-safe via SQLite's locking mechanism:

```python
# Multiple threads can safely share a cache instance
cache = CodeSearchCache()

def search_worker(file_paths):
    for path in file_paths:
        tags = cache.get_cached_tags(path)
        # ...

# Safe to run concurrently
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(search_worker, file_batches)
```

### Troubleshooting

**Cache not persisting:**
- Check write permissions on cache directory
- Verify disk space available
- Check for SQLite errors in logs

**Low hit rate:**
- Files may be changing frequently
- Check if mtime is being preserved (some tools reset mtime)
- Verify cache size limit isn't too small

**Cache directory growing:**
- LRU eviction activates at size limit
- Manually clear with `invalidate_cache()` if needed
- Consider lowering `size_limit_mb`

## See Also

- [Configuration Guide](user-guide/configuration.md) - Complete configuration reference
- [Security Policy](../SECURITY.md) - Security best practices
- [API Documentation](api/index.md) - Full API reference
- [Examples](../examples/) - Working code examples
- [Tool Calling Config Examples](examples/tool-calling-config.yaml) - Configuration templates
- [Custom Tool Example](examples/custom-tool-example.py) - Complete custom tool implementation

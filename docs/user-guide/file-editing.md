# File Editing Tools

Let the AI write, edit, and manage files for you—with powerful safety controls and surgical precision.

## Introduction

Consoul's file editing tools let AI models create, modify, and delete files in your project. Instead of copying code from a chat window and manually pasting it into your editor, the AI can make changes directly—and you can review them first.

**Quick example:**
```bash
$ consoul chat "Add error handling to calculate_total in src/utils.py"
```

The AI will find the function, add try/catch blocks, preserve your formatting, and make the change—all without you opening an editor.

**Related Tools:**

- [Code Search](code-search.md) - Find code before editing
- [Image Analysis](image-analysis.md) - Analyze screenshots and UI

## Table of Contents

- [Overview](#overview)
- [Available Tools](#available-tools)
  - [edit_file_lines](#edit_file_lines)
  - [edit_file_search_replace](#edit_file_search_replace)
  - [create_file](#create_file)
  - [delete_file](#delete_file)
  - [append_to_file](#append_to_file)
- [Configuration](#configuration)
- [Security & Permissions](#security-permissions)
- [Progressive Matching](#progressive-matching)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

## Overview

### What are File Editing Tools?

File editing tools enable AI models to create, modify, and delete files in your project with precision and safety controls. These tools provide:

- **Line-based editing**: Modify specific lines or ranges with surgical precision
- **Search/replace**: Find and replace content with progressive matching
- **Safety controls**: Path validation, extension filtering, size limits
- **Preview-before-edit**: Dry-run mode shows diff previews without modifications
- **Atomic operations**: Temp file + rename prevents corruption
- **Optimistic locking**: Detects concurrent edits via expected_hash

### Why Use File Editing Tools?

**Instead of manual editing:**
```bash
# Manual approach
$ vim src/utils.py  # Find line 42
$ # Make change manually
$ # Hope you didn't introduce syntax errors
```

**AI-powered editing:**
```python
console.chat("Add error handling to the calculate_total function in src/utils.py")
# AI finds function, adds try/catch, preserves formatting
```

**Benefits:**

- ✅ AI understands context and intent
- ✅ Preserves formatting (tabs/spaces, line endings)
- ✅ Generates diff previews for review
- ✅ Validates changes before applying
- ✅ Prevents path traversal and dangerous operations

### Security Model

Most file editing tools are classified as **Risk Level: CAUTION**, with the exception of `delete_file` which is **Risk Level: DANGEROUS** due to its destructive nature. All file operations require user approval by default.

**Security layers:**

1. **Path validation**: Blocks `..` traversal and absolute dangerous paths
2. **Extension filtering**: Whitelist of allowed file extensions
3. **Size limits**: Prevents runaway edits (max bytes, max edits)
4. **Approval workflow**: User confirms before modifications
5. **Audit logging**: All operations logged with timestamps

### Quick Start

**Enable in configuration:**

```yaml
profiles:
  default:
    tools:
      enabled: true
      permission_policy: balanced  # Prompts for CAUTION-level tools
```

**Basic usage:**

```python
from consoul import Consoul

console = Consoul(tools=True)

# Let AI edit files
console.chat("Fix the typo in line 12 of README.md")
console.chat("Refactor the login function to use async/await")
console.chat("Add type hints to all functions in src/models.py")
```

## Available Tools

### edit_file_lines

Edit specific lines or line ranges with exact precision.

**Capabilities:**

- Edit single lines or ranges (e.g., "5-10", "42")
- Replace multiple non-overlapping ranges in one operation
- Delete lines by providing empty content
- Insert lines by expanding ranges
- Optimistic locking via `expected_hash`
- Dry-run mode for previews

**Risk Level**: CAUTION (modifies files, requires approval)

**Input Schema:**
```python
class EditFileLinesInput(BaseModel):
    file_path: str              # File to edit
    line_edits: dict[str, str]  # {"3-5": "new content", "10": "line 10"}
    expected_hash: str | None   # SHA256 for optimistic locking
    dry_run: bool               # Preview without modifying (default: False)
```

**Example:**
```python
from consoul.ai.tools.implementations import edit_file_lines

# Edit single line
result = edit_file_lines.invoke({
    "file_path": "src/main.py",
    "line_edits": {"42": "    logger.error('Something went wrong')"}
})

# Edit multiple ranges
result = edit_file_lines.invoke({
    "file_path": "src/config.py",
    "line_edits": {
        "1-3": "# Updated header\n# Version 2.0\n# Author: Team",
        "25": "DEBUG = False"
    }
})

# Preview changes (dry-run)
result = edit_file_lines.invoke({
    "file_path": "src/utils.py",
    "line_edits": {"10-15": "# TODO: Refactor this section"},
    "dry_run": True
})
# Result contains diff preview, file unchanged
```

**Response Format:**
```json
{
  "status": "success",
  "bytes_written": 1024,
  "checksum": "abc123...",
  "changed_lines": ["3-5", "10"],
  "preview": "--- a/src/main.py\n+++ b/src/main.py\n@@ -42,1 +42,1 @@\n-    print('Error')\n+    logger.error('Something went wrong')\n"
}
```

**Common Use Cases:**

- Fix specific lines identified by linters
- Update version numbers or constants
- Add logging statements
- Fix syntax errors at known line numbers
- Batch update configuration values

### edit_file_search_replace

Search for content and replace with progressive matching (strict/whitespace/fuzzy).

**Capabilities:**

- **Strict matching**: Exact text match (default)
- **Whitespace tolerance**: Ignores leading/trailing whitespace and indentation
- **Fuzzy matching**: Similarity-based matching for typos
- **Tab preservation**: Maintains original indentation style
- **CRLF preservation**: Keeps Windows line endings
- **Ambiguity detection**: Warns if search text appears multiple times
- **Similarity suggestions**: "Did you mean...?" for failed searches

**Risk Level**: CAUTION (modifies files, requires approval)

**Input Schema:**
```python
class EditFileSearchReplaceInput(BaseModel):
    file_path: str
    edits: list[dict]           # [{"search": "old", "replace": "new"}]
    tolerance: str              # "strict", "whitespace", or "fuzzy"
    expected_hash: str | None
    dry_run: bool
```

**Example (Strict):**
```python
from consoul.ai.tools.implementations import edit_file_search_replace

# Exact match
result = edit_file_search_replace.invoke({
    "file_path": "src/models.py",
    "edits": [
        {"search": "class User:", "replace": "class User(BaseModel):"}
    ],
    "tolerance": "strict"
})
```

**Example (Whitespace Tolerance):**
```python
# Ignores indentation differences - useful when search block has different indent
result = edit_file_search_replace.invoke({
    "file_path": "src/app.py",
    "edits": [
        {
            "search": "def login():\n    validate()\n    return True",
            "replace": "async def login():\n    await validate()\n    return True"
        }
    ],
    "tolerance": "whitespace"
})
# Matches even if actual file has different indentation
# Preserves original tabs/spaces in replacement
```

**Example (Fuzzy Matching):**
```python
# Handles typos and minor differences
result = edit_file_search_replace.invoke({
    "file_path": "src/utils.py",
    "edits": [
        {
            "search": "def calculate_totle():",  # Typo in search
            "replace": "def calculate_total():"
        }
    ],
    "tolerance": "fuzzy"
})
# Matches "def calculate_total():" with 90%+ similarity
# Warning: "Fuzzy matched with 94% similarity"
```

**Response Format:**
```json
{
  "status": "success",
  "bytes_written": 2048,
  "checksum": "def456...",
  "preview": "--- a/src/models.py\n+++ b/src/models.py\n...",
  "warnings": ["Fuzzy matched 'calculate_totle' → 'calculate_total' (94% similarity)"]
}
```

**Common Use Cases:**

- Refactor function signatures
- Rename classes/variables
- Update import statements
- Fix typos with fuzzy matching
- Multi-line block replacements

### create_file

Create new files or overwrite existing ones with safety controls.

**Capabilities:**

- Create files with automatic parent directory creation
- Overwrite protection (disabled by default)
- Extension validation
- Content size limits
- Dry-run preview shows "new file" diff
- Returns SHA256 checksum

**Risk Level**: CAUTION (creates files, requires approval)

**Input Schema:**
```python
class CreateFileInput(BaseModel):
    file_path: str
    content: str
    overwrite: bool      # Allow overwriting existing files (default: False)
    dry_run: bool
```

**Example:**
```python
from consoul.ai.tools.implementations import create_file

# Create new file
result = create_file.invoke({
    "file_path": "src/new_feature.py",
    "content": '''"""New feature module."""

def new_function():
    """Placeholder for new functionality."""
    pass
'''
})

# Create with nested directories
result = create_file.invoke({
    "file_path": "docs/guides/advanced/custom-tools.md",
    "content": "# Custom Tools Guide\n\n..."
})
# Creates docs/guides/advanced/ directories automatically

# Preview file creation (dry-run)
result = create_file.invoke({
    "file_path": "config/production.yaml",
    "content": "env: production\ndebug: false\n",
    "dry_run": True
})
# Shows diff: all lines marked as additions, file not created
```

**Overwrite Control:**
```python
# Attempt to overwrite without permission (default)
result = create_file.invoke({
    "file_path": "README.md",  # File exists
    "content": "New content",
    "overwrite": False  # Default
})
# Error: "File already exists and overwrite=False"

# Explicit overwrite (requires allow_overwrite in config)
result = create_file.invoke({
    "file_path": "README.md",
    "content": "Updated content",
    "overwrite": True  # Requires FileEditToolConfig.allow_overwrite=True
})
```

**Response Format:**
```json
{
  "status": "success",
  "bytes_written": 512,
  "checksum": "789abc...",
  "preview": "--- /dev/null\n+++ b/src/new_feature.py\n@@ -0,0 +1,5 @@\n+\"\"\"New feature module.\"\"\"\n+\n+def new_function():\n+..."
}
```

**Common Use Cases:**

- Generate boilerplate code files
- Create configuration files
- Initialize project structure
- Generate documentation
- Create test files

### delete_file

Safely delete files with validation and approval.

**Capabilities:**

- Delete individual files (not directories)
- Path validation (blocks dangerous paths)
- Extension filtering
- Dry-run preview shows deletion diff
- Returns absolute path and timestamp

**Risk Level**: DANGEROUS (destructive operation, always requires approval)

**Input Schema:**
```python
class DeleteFileInput(BaseModel):
    file_path: str
    dry_run: bool
```

**Example:**
```python
from consoul.ai.tools.implementations import delete_file

# Delete file
result = delete_file.invoke({
    "file_path": "old_module.py"
})

# Preview deletion (dry-run)
result = delete_file.invoke({
    "file_path": "temp/cache.json",
    "dry_run": True
})
# Shows diff: all lines marked as deletions, file not deleted
```

**Response Format:**
```json
{
  "status": "deleted",
  "path": "/absolute/path/to/old_module.py",
  "timestamp": "2025-11-15T10:30:45.123456Z"
}
```

**Security:**
```python
# Blocked: Directory deletion
delete_file.invoke({"file_path": "src/"})
# Error: "Not a file: src/ is a directory"

# Blocked: Path traversal
delete_file.invoke({"file_path": "../../../etc/passwd"})
# Error: "Path traversal detected"

# Blocked: Extension filtering (if configured)
delete_file.invoke({"file_path": "important.db"})
# Error: "Extension .db not allowed"
```

**Common Use Cases:**

- Remove deprecated files
- Clean up temporary files
- Delete generated files before regeneration
- Remove old backups
- Cleanup after refactoring

### append_to_file

Append content to existing files or create new ones.

**Capabilities:**

- Append to end of existing files
- Smart newline handling (adds separator if needed)
- Create file if missing (opt-in via `create_if_missing`)
- CRLF/LF preservation
- Size limit validation (total file size after append)
- Dry-run preview shows appended content

**Risk Level**: CAUTION (modifies files, requires approval)

**Input Schema:**
```python
class AppendToFileInput(BaseModel):
    file_path: str
    content: str
    create_if_missing: bool  # Create file if doesn't exist (default: True)
    dry_run: bool
```

**Example:**
```python
from consoul.ai.tools.implementations import append_to_file

# Append to existing file
result = append_to_file.invoke({
    "file_path": "CHANGELOG.md",
    "content": "\n## v2.0.0\n\n- Added file editing tools\n- Improved security"
})

# Append with newline separator (automatic)
result = append_to_file.invoke({
    "file_path": "logs/app.log",
    "content": "[2025-11-15] Application started"
})
# If file doesn't end with \n, adds \n before appending

# Create new file (create_if_missing=True)
result = append_to_file.invoke({
    "file_path": "notes.txt",
    "content": "First note\n",
    "create_if_missing": True
})

# Prevent creation (create_if_missing=False)
result = append_to_file.invoke({
    "file_path": "missing.txt",
    "content": "Content",
    "create_if_missing": False
})
# Error: "File not found and create_if_missing=False"
```

**Newline Handling:**
```python
# File ends without newline: "line1\nline2"
append_to_file.invoke({"file_path": "test.txt", "content": "line3"})
# Result: "line1\nline2\nline3" (added separator)

# File ends with newline: "line1\nline2\n"
append_to_file.invoke({"file_path": "test.txt", "content": "line3"})
# Result: "line1\nline2\nline3" (no double newline)
```

**Response Format:**
```json
{
  "status": "success",
  "bytes_written": 1536,
  "checksum": "bcd789...",
  "preview": "--- a/CHANGELOG.md\n+++ b/CHANGELOG.md\n@@ -10,0 +10,4 @@\n+\n+## v2.0.0\n+..."
}
```

**Common Use Cases:**

- Add changelog entries
- Append log entries
- Add test cases
- Extend configuration files
- Add documentation sections

## Configuration

### FileEditToolConfig

Configure file editing tools via `FileEditToolConfig` in your profile:

```yaml
profiles:
  default:
    tools:
      enabled: true
      file_edit:
        # Extension filtering
        allowed_extensions:
          - ".py"
          - ".js"
          - ".ts"
          - ".md"
          - ".txt"
          - ".json"
          - ".yaml"
          - ".yml"
          # "" allows extensionless files (Dockerfile, Makefile)

        # Path blocking
        blocked_paths:
          # System defaults
          - "/etc/shadow"
          - "/etc/passwd"
          - "/proc"
          - "/dev"
          - "/sys"
          # CRITICAL: Add secret paths (not in defaults!)
          - "~/.ssh"
          - "~/.aws"
          - "~/.gnupg"

        # Size limits
        max_payload_bytes: 1048576  # 1MB max content size
        max_edits: 50               # Max line edits per operation

        # Overwrite control
        allow_overwrite: false      # Must be true to overwrite existing files

        # Encoding
        default_encoding: "utf-8"   # File encoding for read/write
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_extensions` | list[str] | `[]` (all) | Allowed file extensions (empty = all allowed) |
| `blocked_paths` | list[str] | `["/etc", "/sys", ...]` | Paths that cannot be edited |
| `max_payload_bytes` | int | `1048576` (1MB) | Maximum content size in bytes |
| `max_edits` | int | `50` | Maximum number of line edits per operation |
| `allow_overwrite` | bool | `false` | Allow `create_file` to overwrite existing files |
| `default_encoding` | str | `"utf-8"` | Default file encoding |

### Extension Filtering

**Allow all file types:**
```yaml
file_edit:
  allowed_extensions: []  # Empty list = all extensions allowed
```

**Restrict to specific types:**
```yaml
file_edit:
  allowed_extensions:
    - ".py"    # Python
    - ".js"    # JavaScript
    - ".md"    # Markdown
    - ".txt"   # Text
    - ""       # Extensionless (Dockerfile, Makefile)
```

**Case-insensitive matching:**

- `.py` matches `.PY`, `.Py`, `.pY`
- Extension filtering is case-insensitive

### Path Blocking

**Default blocked paths:**
```python
DEFAULT_BLOCKED_PATHS = [
    "/etc/shadow",  # Shadow password file
    "/etc/passwd",  # User account information
    "/proc",        # Process information
    "/dev",         # Device files
    "/sys",         # Kernel interface
]
```

**⚠️ WARNING**: The defaults do NOT include common secret locations like `~/.ssh`, `~/.aws`, or `~/.gnupg`. You **must** explicitly add these to your configuration for production use.

**Recommended production configuration:**
```yaml
file_edit:
  blocked_paths:
    # System defaults (already included)
    - "/etc/shadow"
    - "/etc/passwd"
    - "/proc"
    - "/dev"
    - "/sys"
    # CRITICAL ADDITIONS for production
    - "~/.ssh"          # SSH keys
    - "~/.aws"          # AWS credentials
    - "~/.gnupg"        # GPG keys
    - "~/.config/gcloud"  # Google Cloud credentials
    # Optional project-specific blocks
    - "/var/www/production"  # Production web root
    - "~/.config/secrets"     # Local secrets
    - "${PROJECT_ROOT}/vendor"  # Third-party code
```

### Size Limits

**Prevent large edits:**
```yaml
file_edit:
  max_payload_bytes: 524288  # 512KB limit
  max_edits: 25              # Max 25 line ranges per edit
```

**Validation:**

- `edit_file_lines`: Total size of all `line_edits` values
- `edit_file_search_replace`: Total size of all `replace` values
- `create_file`: Size of `content` parameter
- `append_to_file`: Size of existing file + new `content`

### Encoding Settings

**UTF-8 (default):**
```yaml
file_edit:
  default_encoding: "utf-8"  # Unicode support
```

**Latin-1 (fallback):**
```yaml
file_edit:
  default_encoding: "latin-1"  # ASCII + extended characters
```

**Note:** Files are always read with UTF-8 first, falling back to Latin-1 if decoding fails.

## Security & Permissions

### Risk Classification

**Risk Levels:**

- Most file editing tools: **CAUTION** (edit_file_lines, edit_file_search_replace, create_file, append_to_file)
- `delete_file`: **DANGEROUS** (destructive operation)

**Approval Requirements:**

- CAUTION tools: Require approval with `balanced` or `paranoid`, auto-approved with `trusting`
- DANGEROUS tools: Always require approval (even with `trusting`), only auto-approved with `unrestricted`

### Path Validation

**Protections:**
1. **Path traversal detection**: Blocks `..` in paths
2. **Absolute path validation**: Checks against blocked paths
3. **Symlink resolution**: Resolves to real path before validation
4. **Directory rejection**: File operations reject directories

**Example:**
```python
# BLOCKED: Path traversal
edit_file_lines.invoke({
    "file_path": "../../../etc/passwd",
    "line_edits": {"1": "hacked"}
})
# Error: "Path traversal detected: .. not allowed"

# BLOCKED: Blocked path
create_file.invoke({
    "file_path": "/etc/malicious.conf",
    "content": "bad content"
})
# Error: "Path is blocked: /etc"

# ALLOWED: Safe relative path
edit_file_lines.invoke({
    "file_path": "src/utils.py",
    "line_edits": {"42": "fixed"}
})
```

### Extension Validation

**Enforcement:**

- Checked AFTER path traversal validation
- Case-insensitive comparison
- Extensionless files require explicit `""` in allowed list

**Example:**
```yaml
# Configuration
file_edit:
  allowed_extensions:
    - ".py"
    - ".md"
```

```python
# ALLOWED
edit_file_lines.invoke({
    "file_path": "src/main.py",  # .py allowed
    "line_edits": {"1": "# Updated"}
})

# BLOCKED
edit_file_lines.invoke({
    "file_path": "config.yaml",  # .yaml not in allowed list
    "line_edits": {"1": "env: prod"}
})
# Error: "Extension .yaml not allowed"

# BLOCKED: Extensionless without explicit permission
edit_file_lines.invoke({
    "file_path": "Dockerfile",
    "line_edits": {"1": "FROM python:3.12"}
})
# Error: "Extensionless files not allowed (add '' to allowed_extensions)"
```

### Approval Workflow

**With TUI (interactive):**
1. AI requests file edit operation
2. Approval modal shows:
   - Tool name and file path
   - Diff preview (if dry-run supported)
   - Risk level: CAUTION
3. User approves or denies
4. If approved, operation executes
5. Result shown in chat interface

**With SDK (programmatic):**
```python
from consoul.ai.tools.approval import ApprovalProvider, ToolApprovalRequest, ToolApprovalResponse

class CustomApprovalProvider(ApprovalProvider):
    async def request_approval(self, request: ToolApprovalRequest) -> ToolApprovalResponse:
        # Custom approval logic
        if request.preview:
            print("Diff preview:\n" + request.preview)

        # Auto-approve Python files
        if request.arguments["file_path"].endswith(".py"):
            return ToolApprovalResponse(approved=True)

        # Deny other files
        return ToolApprovalResponse(
            approved=False,
            reason="Only .py files auto-approved"
        )
```

### Audit Logging

**All file operations logged:**
```jsonl
{"timestamp": "2025-11-15T10:30:45Z", "event_type": "request", "tool_name": "edit_file_lines", "arguments": {"file_path": "src/main.py", "line_edits": {...}}}
{"timestamp": "2025-11-15T10:30:46Z", "event_type": "approval", "tool_name": "edit_file_lines", "decision": true}
{"timestamp": "2025-11-15T10:30:47Z", "event_type": "result", "tool_name": "edit_file_lines", "result": {"status": "success", "bytes_written": 1024, ...}}
```

**Query audit log:**
```bash
# View all file edits
jq 'select(.tool_name | startswith("edit_") or startswith("create_") or startswith("delete_") or startswith("append_"))' \
  ~/.consoul/tool_audit.jsonl

# Find denied operations
jq 'select(.event_type=="denial" and (.tool_name | contains("file")))' \
  ~/.consoul/tool_audit.jsonl
```

## Progressive Matching

### Overview

Progressive matching allows `edit_file_search_replace` to handle variations in whitespace, formatting, and even typos. Three tolerance levels are available:

| Tolerance | Use Case | Matches | Preserves |
|-----------|----------|---------|-----------|
| **strict** | Exact replacement | Character-for-character | N/A (exact match) |
| **whitespace** | Refactoring | Ignores indentation | Original tabs/spaces, CRLF |
| **fuzzy** | Fixing typos | Similarity ≥80% | Original content structure |

### Strict Matching (Default)

**Behavior:**

- Exact character-for-character match
- Whitespace must match exactly
- Line endings must match exactly
- Fastest matching mode

**Use when:**

- You know the exact content
- Replacing constants or literals
- Working with machine-generated code

**Example:**
```python
edit_file_search_replace.invoke({
    "file_path": "config.py",
    "edits": [
        {"search": "DEBUG = True", "replace": "DEBUG = False"}
    ],
    "tolerance": "strict"
})
# Only matches if exactly "DEBUG = True" (no extra spaces)
```

### Whitespace Tolerance

**Behavior:**

- Ignores leading/trailing whitespace on each line
- Ignores differences in indentation
- Preserves original tab/space style
- Preserves original line endings (CRLF/LF)

**Use when:**

- Search block has different indentation than file
- Refactoring code with varying indent levels
- Copying code from documentation

**Example:**
```python
# File contains (with 4-space indent):
"""
    def login(user):
        validate(user)
        return True
"""

# Search with no indent
edit_file_search_replace.invoke({
    "file_path": "auth.py",
    "edits": [
        {
            "search": "def login(user):\n    validate(user)\n    return True",
            "replace": "async def login(user):\n    await validate(user)\n    return True"
        }
    ],
    "tolerance": "whitespace"
})
# Matches despite indentation difference
# Preserves original 4-space indent in replacement
```

**Tab Preservation:**
```python
# File uses tabs: "\tdef foo():\n\t\tpass"
# Search uses spaces: "def foo():\n    pass"

edit_file_search_replace.invoke({
    "edits": [{"search": "def foo():\n    pass", "replace": "def bar():\n    return"}],
    "tolerance": "whitespace"
})
# Matches and preserves tabs: "\tdef bar():\n\t\treturn"
```

**CRLF Preservation:**
```python
# File uses CRLF: "line1\r\nline2\r\n"
# Search uses LF: "line1\nline2"

edit_file_search_replace.invoke({
    "edits": [{"search": "line1\nline2", "replace": "LINE1\nLINE2"}],
    "tolerance": "whitespace"
})
# Matches and preserves CRLF: "LINE1\r\nLINE2\r\n"
```

### Fuzzy Matching

**Behavior:**

- Matches based on similarity score (≥80% default)
- Handles typos in search text
- Shows confidence score in warning
- Suggests similar blocks if no match

**Use when:**

- You have a typo in the search text
- Code has minor formatting differences
- You want "did you mean?" suggestions

**Example:**
```python
# File contains: "def calculate_total(items):"

# Search has typo
edit_file_search_replace.invoke({
    "file_path": "utils.py",
    "edits": [
        {
            "search": "def calculate_totle(items):",  # Typo: "totle"
            "replace": "def calculate_sum(items):"
        }
    ],
    "tolerance": "fuzzy"
})
# Success with warning: "Fuzzy matched with 94% similarity"
```

**Similarity Suggestions:**
```python
# Search text not found
edit_file_search_replace.invoke({
    "edits": [{"search": "def proces_order():", "replace": "..."}],
    "tolerance": "fuzzy"
})
# Error: "Search text 'def proces_order():' not found"
# Did you mean:
#   - def process_order():    (91% similar)
#   - def process_payment():  (85% similar)
```

## Common Workflows

### Workflow 1: Refactoring a Function

**Objective:** Rename function and update signature

```python
from consoul import Consoul

console = Consoul(tools=True)

# Step 1: Find function definition and usages
console.chat("Find all usages of calculate_total() in the project")
# AI uses code_search + find_references

# Step 2: Rename function with whitespace tolerance
console.chat("""
Rename calculate_total() to calculate_sum() in src/utils.py.
The function signature should also accept a 'tax_rate' parameter.
""")
# AI uses edit_file_search_replace with tolerance="whitespace"

# Step 3: Update all call sites
console.chat("Update all calls to calculate_sum() to include tax_rate=0.08")
# AI edits each file with line-based edits
```

### Workflow 2: Batch Configuration Updates

**Objective:** Update config values across multiple files

```python
console.chat("""
Update all YAML files in config/ to set:
- environment: production
- debug: false
- log_level: INFO
""")
# AI uses glob pattern to find files, edit_file_search_replace for each
```

### Workflow 3: Adding Documentation

**Objective:** Add docstrings to undocumented functions

```python
console.chat("""
Find all functions in src/ without docstrings and add comprehensive
docstrings following Google style guide.
""")
# AI uses code_search to find functions, edit_file_lines to add docstrings
```

### Workflow 4: Error Handling

**Objective:** Add try/catch to risky operations

```python
console.chat("""
Review all file I/O operations in src/ and add proper error handling
with try/except blocks. Log errors using the logger module.
""")
# AI uses grep_search to find file operations, edit_file_search_replace to wrap in try/catch
```

### Workflow 5: Type Hints Migration

**Objective:** Add type hints to existing Python code

```python
console.chat("""
Add type hints to all function signatures in src/models.py.
Use typing module for complex types (List, Dict, Optional).
""")
# AI uses edit_file_lines to add type hints while preserving formatting
```

## Troubleshooting

### Common Errors

#### ValidationError: Search text not found

**Problem:** `edit_file_search_replace` can't find the search text

**Causes & Solutions:**

1. **Whitespace differences:**
   ```python
   # Change tolerance from strict to whitespace
   edit_file_search_replace.invoke({
       "edits": [...],
       "tolerance": "whitespace"  # Instead of "strict"
   })
   ```

2. **Typo in search text:**
   ```python
   # Use fuzzy matching
   edit_file_search_replace.invoke({
       "edits": [...],
       "tolerance": "fuzzy"
   })
   # Check "Did you mean?" suggestions in error message
   ```

3. **Content changed since read:**
   ```python
   # Re-read file and try again
   # Or use expected_hash to detect concurrent edits
   ```

#### ValidationError: Overlapping line ranges

**Problem:** `edit_file_lines` edits overlap (e.g., "1-5" and "3-7")

**Solution:** Use non-overlapping ranges
```python
# BAD: Overlapping
{"line_edits": {"1-5": "...", "3-7": "..."}}

# GOOD: Non-overlapping
{"line_edits": {"1-5": "...", "6-10": "..."}}
```

#### ValidationError: Line X exceeds file length

**Problem:** Line number out of bounds

**Solution:** Check file length first
```python
# Read file first to see number of lines
read_file.invoke({"file_path": "test.py"})
# Then edit within bounds
```

#### ValidationError: Extension not allowed

**Problem:** File extension not in allowed list

**Solution:** Update configuration
```yaml
file_edit:
  allowed_extensions:
    - ".py"
    - ".yaml"  # Add missing extension
```

#### ValidationError: Path is blocked

**Problem:** Path in blocked list

**Solution:** Remove from blocklist if safe
```yaml
file_edit:
  blocked_paths:
    # - "/var/www"  # Remove if you need to edit here
```

#### Hash mismatch: File changed since read

**Problem:** Optimistic locking detected concurrent edit

**Solution:** Re-read file and retry
```python
# Get new hash
new_content = read_file.invoke({"file_path": "test.py"})
new_hash = compute_hash(new_content)

# Retry with new hash
edit_file_lines.invoke({
    "file_path": "test.py",
    "line_edits": {...},
    "expected_hash": new_hash
})
```

### Performance Issues

#### Slow search/replace on large files

**Cause:** Large files require full content scan

**Solutions:**
1. Use `edit_file_lines` if you know line numbers
2. Split large files into smaller modules
3. Increase timeout in config

#### Large diff previews

**Cause:** Many changes generate large previews

**Solutions:**
1. Break into multiple smaller edits
2. Use dry_run sparingly
3. Disable preview for batch operations

### Best Practices

#### DO:

✅ Use `dry_run=True` to preview before applying
✅ Start with `tolerance="strict"` and relax as needed
✅ Use `expected_hash` for critical edits
✅ Read file first to understand context
✅ Use line-based edits when you know exact line numbers
✅ Use search/replace for pattern-based changes

#### DON'T:

❌ Edit binary files (use specialized tools)
❌ Bypass security validation
❌ Ignore hash mismatch errors
❌ Use fuzzy matching for exact replacements
❌ Edit system files without understanding risks
❌ Disable approval workflow in production

## See Also

**Other Tools:**

- [Code Search](code-search.md) - Find code before editing it
- [Image Analysis](image-analysis.md) - Review changes visually

**SDK & API:**

- [SDK Tools Overview](../api/tools.md) - Using file editing tools programmatically
- [Tool Configuration](../sdk-tools.md) - Configuring file editing in your code

**Configuration & Security:**

- [Configuration Guide](configuration.md) - Enable/disable file editing
- [Security Policy](../SECURITY.md) - Safety controls and best practices

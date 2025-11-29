# Tools Deep Dive

Master Consoul's 13 built-in tools for file operations, code search, web research, and command execution.

## What are Tools?

**Tools** are functions that the AI can call to interact with your system. When you enable tools, the AI can:

- Search files with grep and code patterns
- Create, edit, and delete files
- Execute shell commands
- Search the web and fetch URLs
- Read Wikipedia articles

Tools transform a chat-only AI into an **agent** capable of autonomous action.

## How Tools Work

Under the hood, Consoul uses LangChain's tool calling system:

1. AI requests a tool call with arguments
2. Consoul executes the tool
3. Tool result is returned to the AI
4. AI incorporates result into its response

Example flow:

```
You: "Find all TODO comments in Python files"
AI: [Calls grep_search tool with pattern="TODO" and glob="*.py"]
Tool: Returns list of TODOs with file paths
AI: "I found 7 TODO comments: src/main.py:42, ..."
```

## Tool Categories

Tools are organized into 4 categories:

| Category | Purpose | Tool Count |
|----------|---------|------------|
| **SEARCH** | Find and read information | 4 tools |
| **FILE_EDIT** | Modify files | 5 tools |
| **WEB** | Access web content | 3 tools |
| **EXECUTE** | Run shell commands | 1 tool |

Enable by category:

```python
from consoul import Consoul

# Only search tools
console = Consoul(tools="search")

# Only web tools
console = Consoul(tools="web")

# Multiple categories
console = Consoul(tools=["search", "web"])
```

## Risk Levels

Every tool is classified by risk:

### SAFE (Read-Only)
No system modifications. Perfect for untrusted AI interactions.

**Tools:** `grep`, `code_search`, `find_references`, `read`, `web_search`, `read_url`, `wikipedia`

```python
console = Consoul(tools="safe")  # Only SAFE tools
```

### CAUTION (File Operations)
Creates/modifies files or executes safe commands. Requires oversight.

**Tools:** `create_file`, `edit_lines`, `edit_replace`, `append_file`, `bash` (safe commands)

```python
console = Consoul(tools="caution")  # SAFE + CAUTION tools
```

### DANGEROUS (Destructive)
Can delete files or run destructive commands. Use with extreme care.

**Tools:** `delete_file`, `bash` (destructive commands like rm, kill)

```python
console = Consoul(tools="dangerous")  # All tools
```

## Tool Catalog

### Search Tools

#### `grep` - Search File Contents

Search file contents using regex patterns.

**Use cases:**
- Find TODO comments
- Search for error messages
- Find specific code patterns

```python
from consoul import Consoul

console = Consoul(tools=["grep"])
console.chat("Find all TODO comments in Python files")
console.chat("Search for 'database' in config files")
console.chat("Find error handling code")
```

**Tool parameters:**
- `pattern` (str): Regex pattern to search
- `path` (str): Directory or file to search (default: current dir)
- `glob` (str): File pattern filter (e.g., "*.py")

**Risk:** SAFE (read-only)

#### `code_search` - Find Code Patterns

Find classes, functions, and methods in code.

**Use cases:**
- Find class definitions
- Locate function implementations
- Discover method usages

```python
from consoul import Consoul

console = Consoul(tools=["code_search"])
console.chat("Find the User class definition")
console.chat("Where is the calculate_total function?")
console.chat("Show me all API route handlers")
```

**Tool parameters:**
- `pattern` (str): Code element to find (class/function name)
- `path` (str): Directory to search (default: current dir)
- `type_filter` (str): Filter by file type (e.g., "python", "javascript")

**Risk:** SAFE (read-only)

#### `find_references` - Find Symbol References

Find all usages of a symbol (function, class, variable).

**Use cases:**
- Impact analysis before refactoring
- Find all callers of a function
- Track variable usage

```python
from consoul import Consoul

console = Consoul(tools=["find_references"])
console.chat("Where is the authenticate() function called?")
console.chat("Find all references to the API_KEY variable")
console.chat("Show me all usages of the User class")
```

**Tool parameters:**
- `symbol` (str): Symbol name to find references for
- `path` (str): Directory to search (default: current dir)

**Risk:** SAFE (read-only)

#### `read` - Read File Contents

Read the full contents of a file.

**Use cases:**
- Examine configuration files
- Read source code
- Check file contents before editing

```python
from consoul import Consoul

console = Consoul(tools=["read"])
console.chat("Show me the contents of config.yaml")
console.chat("Read the README.md file")
console.chat("What's in src/main.py?")
```

**Tool parameters:**
- `file_path` (str): Path to file to read
- `start_line` (int, optional): Start reading from line number
- `end_line` (int, optional): Stop reading at line number

**Risk:** SAFE (read-only)

### File Edit Tools

!!! warning "File Operations"
    File-edit tools modify your filesystem. Always:

    - Work in a git repository with committed changes
    - Review changes before committing
    - Test in a safe directory first
    - Use `tools="safe"` when you don't need file modifications

#### `create_file` - Create New Files

Create a new file with specified content.

**Use cases:**
- Generate boilerplate code
- Create configuration files
- Scaffold project structure

```python
from consoul import Consoul

console = Consoul(tools=["create_file"])
console.chat("Create a basic FastAPI main.py file")
console.chat("Generate a .gitignore for Python projects")
console.chat("Create a README.md with project overview")
```

**Tool parameters:**
- `file_path` (str): Path for new file
- `content` (str): File contents
- `overwrite` (bool): Overwrite if exists (default: False)
- `dry_run` (bool): Preview without creating (default: False)

**Risk:** CAUTION (creates files)

#### `edit_lines` - Edit Specific Lines

Replace specific line ranges in a file.

**Use cases:**
- Fix bugs in specific functions
- Update configuration values
- Modify specific code sections

```python
from consoul import Consoul

console = Consoul(tools=["edit_lines", "read"])
console.chat("Change the API port from 8000 to 8080 in config.py")
console.chat("Fix the typo on line 42 of README.md")
console.chat("Update the version number in setup.py")
```

**Tool parameters:**
- `file_path` (str): File to edit
- `start_line` (int): First line to replace
- `end_line` (int): Last line to replace
- `new_content` (str): Replacement content
- `dry_run` (bool): Preview without editing

**Risk:** CAUTION (modifies files)

#### `edit_replace` - Search and Replace

Find and replace text in files.

**Use cases:**
- Rename variables across files
- Update API endpoints
- Fix repeated typos

```python
from consoul import Consoul

console = Consoul(tools=["edit_replace"])
console.chat("Rename 'old_function' to 'new_function' in all Python files")
console.chat("Replace 'http://api.old.com' with 'https://api.new.com'")
console.chat("Fix the misspelling of 'recieve' to 'receive'")
```

**Tool parameters:**
- `file_path` (str): File to edit
- `old_text` (str): Text to find
- `new_text` (str): Replacement text
- `regex` (bool): Use regex patterns (default: False)
- `dry_run` (bool): Preview without editing

**Risk:** CAUTION (modifies files)

#### `append_file` - Append to Files

Add content to the end of a file.

**Use cases:**
- Add new functions to modules
- Append log entries
- Extend configuration files

```python
from consoul import Consoul

console = Consoul(tools=["append_file"])
console.chat("Add a new test function to tests/test_api.py")
console.chat("Append a new route handler to routes.py")
console.chat("Add .DS_Store to .gitignore")
```

**Tool parameters:**
- `file_path` (str): File to append to
- `content` (str): Content to add
- `dry_run` (bool): Preview without appending

**Risk:** CAUTION (modifies files)

#### `delete_file` - Delete Files

Permanently delete a file.

**Use cases:**
- Remove obsolete files
- Clean up generated files
- Delete temporary files

```python
from consoul import Consoul

console = Consoul(tools=["delete_file"])
console.chat("Delete all .pyc files in the project")
console.chat("Remove obsolete_module.py")
console.chat("Delete temporary files in /tmp")
```

**Tool parameters:**
- `file_path` (str): File to delete
- `confirm` (bool): Require confirmation (default: True)

**Risk:** DANGEROUS (irreversible deletion)

### Web Tools

#### `web_search` - Search the Web

Search the web using a search engine.

**Use cases:**
- Find documentation
- Research libraries and frameworks
- Look up error messages

```python
from consoul import Consoul

console = Consoul(tools=["web_search"])
console.chat("Find the latest FastAPI documentation")
console.chat("Search for Python async best practices 2024")
console.chat("Look up 'ModuleNotFoundError: No module named requests'")
```

**Tool parameters:**
- `query` (str): Search query
- `num_results` (int): Number of results to return (default: 5)

**Risk:** SAFE (read-only web access)

#### `read_url` - Fetch Web Pages

Fetch and parse content from a URL.

**Use cases:**
- Read documentation pages
- Extract article content
- Fetch API documentation

```python
from consoul import Consoul

console = Consoul(tools=["read_url"])
console.chat("Summarize https://docs.python.org/3/library/asyncio.html")
console.chat("Read the FastAPI tutorial and explain key concepts")
console.chat("What does this blog post say about microservices?")
```

**Tool parameters:**
- `url` (str): URL to fetch
- `parse` (bool): Parse and extract main content (default: True)

**Risk:** SAFE (read-only web access)

#### `wikipedia` - Search Wikipedia

Search and read Wikipedia articles.

**Use cases:**
- Research background information
- Get definitions and overviews
- Understand technical concepts

```python
from consoul import Consoul

console = Consoul(tools=["wikipedia"])
console.chat("Explain quantum computing using Wikipedia")
console.chat("What is the history of Python programming language?")
console.chat("Summarize the REST architectural style")
```

**Tool parameters:**
- `query` (str): Search query
- `sentences` (int): Number of sentences to return (default: 3)

**Risk:** SAFE (read-only web access)

### Execute Tools

#### `bash` - Execute Shell Commands

Execute shell commands with dynamic risk assessment.

**Use cases:**
- Run scripts and build tools
- Execute git commands
- Run tests and linters

```python
from consoul import Consoul

console = Consoul(tools=["bash"])
console.chat("Run the test suite with pytest")
console.chat("Check git status")
console.chat("Install dependencies with pip")
```

**Tool parameters:**
- `command` (str): Shell command to execute
- `working_dir` (str): Directory to run command in
- `timeout` (int): Command timeout in seconds

**Risk:** CAUTION-DANGEROUS (depends on command)

**Dynamic Risk Assessment:**

Bash commands are assessed for risk before execution:

| Command Example | Risk Level | Reason |
|-----------------|------------|--------|
| `ls`, `pwd`, `echo` | SAFE | Read-only operations |
| `git status`, `pip install` | CAUTION | Safe but modifies state |
| `rm -rf`, `kill -9`, `sudo` | DANGEROUS | Destructive or privileged |
| `:(){ :\|:& };:` (fork bomb) | BLOCKED | Malicious patterns |

The AI must request user approval for CAUTION+ commands.

## Tool Specification

### Enable All Tools

```python
from consoul import Consoul

console = Consoul(tools=True)  # All 13 tools enabled
```

### Filter by Risk Level

```python
# Only SAFE tools (read-only)
console = Consoul(tools="safe")

# SAFE + CAUTION tools (file operations)
console = Consoul(tools="caution")

# All tools including DANGEROUS
console = Consoul(tools="dangerous")
```

### Filter by Category

```python
# Only search tools
console = Consoul(tools="search")

# Only web tools
console = Consoul(tools="web")

# Only file-edit tools
console = Consoul(tools="file-edit")

# Only execute tools
console = Consoul(tools="execute")

# Multiple categories
console = Consoul(tools=["search", "web"])
```

### Specific Tools

```python
# Exact tools by name
console = Consoul(tools=["bash", "grep", "read"])

# Mix categories and specific tools
console = Consoul(tools=["search", "create_file"])
```

## Custom Tools

Create your own tools using LangChain's `@tool` decorator:

```python
from consoul import Consoul
from langchain_core.tools import tool

@tool
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: Position in Fibonacci sequence (1-indexed)

    Returns:
        The nth Fibonacci number
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Use custom tool
console = Consoul(tools=[calculate_fibonacci, "bash", "grep"])
console.chat("What's the 20th Fibonacci number?")
```

### Custom Tool Requirements

1. **Decorator**: Must use `@tool` from `langchain_core.tools`
2. **Docstring**: Must have a descriptive docstring (AI reads this!)
3. **Type Hints**: Parameters and return value must be typed
4. **Return Type**: Must return `str` or JSON-serializable value

```python
from langchain_core.tools import tool
import json

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the product database for matching items.

    Args:
        query: Search query string
        limit: Maximum number of results (default: 10)

    Returns:
        JSON string with search results including id, name, price
    """
    # Your implementation
    results = db.search(query, limit=limit)
    return json.dumps(results)
```

## Tool Discovery

Automatically discover tools from `.consoul/tools/` directory:

### Directory Structure

```
your_project/
├── .consoul/
│   └── tools/
│       ├── database.py      # Custom database tools
│       ├── api_client.py    # Custom API tools
│       └── helpers.py       # Utility tools
├── main.py
└── README.md
```

### Example Tool File

`.consoul/tools/database.py`:

```python
from langchain_core.tools import tool
import json

@tool
def query_users(email: str) -> str:
    """Query users table by email address.

    Args:
        email: User email to search for

    Returns:
        JSON with user data or error message
    """
    user = db.users.find_one({"email": email})
    if user:
        return json.dumps(user)
    return json.dumps({"error": "User not found"})

@tool
def create_user(email: str, name: str) -> str:
    """Create a new user in the database.

    Args:
        email: User email address
        name: User full name

    Returns:
        JSON with created user data
    """
    user_id = db.users.insert({"email": email, "name": name})
    return json.dumps({"id": user_id, "email": email, "name": name})
```

### Enable Discovery

```python
from consoul import Consoul

# Discover and load all tools from .consoul/tools/
console = Consoul(discover_tools=True)

# Combine with built-in tools
console = Consoul(tools=["bash", "grep"], discover_tools=True)

# Only discovered tools (no built-in)
console = Consoul(tools=False, discover_tools=True)
```

Discovered tools default to `RiskLevel.CAUTION` for safety.

## Security Best Practices

### Principle of Least Privilege

Only grant tools the AI actually needs:

```python
# Good: Specific tools for specific tasks
code_analyzer = Consoul(tools=["grep", "code_search", "read"])

# Bad: All tools when only search is needed
code_analyzer = Consoul(tools=True)
```

### Start with Safe Tools

Test with read-only tools first:

```python
# Phase 1: Develop with safe tools
agent = Consoul(tools="safe")

# Phase 2: Add file operations when needed
agent = Consoul(tools="caution")

# Phase 3: Add destructive tools with extreme care
agent = Consoul(tools="dangerous")
```

### Use Version Control

Always work in a git repository:

```bash
# Before enabling file-edit tools
git status  # Ensure clean working tree
git commit -am "Checkpoint before AI edits"

# After AI makes changes
git diff  # Review all changes
git commit -am "AI-generated changes"  # Or git reset --hard to undo
```

### Review Tool Approvals

Check what the AI wants to do:

```python
# The approval system shows you:
# - Tool name
# - Arguments (file paths, commands, etc.)
# - Risk level
# - Dynamic risk assessment (for bash)

# Approve: AI executes the tool
# Deny: AI cannot use this tool
```

### Monitor Costs

Track API usage when using tools:

```python
console = Consoul(tools=True)
console.chat("Find and fix all TODO comments")

# Check costs
cost = console.last_cost
print(f"Tokens: {cost['total_tokens']}")
print(f"Estimated cost: ${cost['estimated_cost']:.4f}")
```

## Tool Combinations

Common tool combinations for specific tasks:

### Code Analysis
```python
tools = ["grep", "code_search", "find_references", "read"]
```

### Web Research
```python
tools = ["web_search", "read_url", "wikipedia"]
```

### File Management
```python
tools = ["bash", "create_file", "edit_lines", "read"]
```

### Testing & CI
```python
tools = ["bash", "read", "grep"]
```

### Documentation
```python
tools = ["read", "code_search", "create_file", "edit_lines"]
```

## Available Tools Quick Reference

| Tool | Category | Risk | Description |
|------|----------|------|-------------|
| `grep` | SEARCH | SAFE | Search file contents with regex |
| `code_search` | SEARCH | SAFE | Find classes, functions, methods |
| `find_references` | SEARCH | SAFE | Find symbol usages |
| `read` | SEARCH | SAFE | Read file contents |
| `create_file` | FILE_EDIT | CAUTION | Create new files |
| `edit_lines` | FILE_EDIT | CAUTION | Edit specific line ranges |
| `edit_replace` | FILE_EDIT | CAUTION | Search and replace in files |
| `append_file` | FILE_EDIT | CAUTION | Append to files |
| `delete_file` | FILE_EDIT | DANGEROUS | Delete files |
| `web_search` | WEB | SAFE | Search the web |
| `read_url` | WEB | SAFE | Fetch web pages |
| `wikipedia` | WEB | SAFE | Search Wikipedia |
| `bash` | EXECUTE | CAUTION+ | Execute shell commands |

## Next Steps

- **[Tutorial](tutorial.md)** - Learn SDK fundamentals
- **[Building Agents](agents.md)** - Create specialized AI agents
- **[API Reference](reference.md)** - Complete API documentation

Master tools to build powerful agents! 🛠️

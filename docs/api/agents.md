# Building Agentic Agents

Learn how to build specialized AI agents that combine reasoning with tools to accomplish complex tasks autonomously.

## What is an Agent?

An **agent** is an AI system that:

1. **Reasons** about tasks and breaks them into steps
2. **Uses tools** to gather information or take actions
3. **Iterates** until the goal is achieved

In Consoul, agents are simply AI models + tools + good prompts:

```python
from consoul import Consoul

# This is an agent!
agent = Consoul(
    tools=["grep", "code_search", "read"],
    system_prompt="You are a code analysis expert. Help find and explain code."
)

agent.chat("Find all database queries in this project")
```

The AI will:
1. Use `code_search` to find database-related code
2. Use `grep` to search for SQL patterns
3. Use `read` to examine specific files
4. Synthesize findings into a coherent answer

## Agent Design Patterns

### Pattern 1: Search & Analysis Agent

Combines search tools to find and analyze information:

```python
from consoul import Consoul

code_analyzer = Consoul(
    model="gpt-4o",  # Good reasoning for multi-step tasks
    tools=["grep", "code_search", "find_references", "read"],
    system_prompt="""You are a senior software engineer specialized in code analysis.

When analyzing code:
1. First search broadly with code_search
2. Then examine specific files with read
3. Find all usages with find_references
4. Provide concrete examples from the codebase

Be thorough but concise.""",
    temperature=0.3  # Lower temperature for analytical tasks
)

# Use the agent
code_analyzer.chat("How is authentication implemented in this codebase?")
code_analyzer.chat("Find potential security vulnerabilities")
code_analyzer.chat("Where should I add rate limiting?")
```

**When to use**: Code reviews, security audits, understanding unfamiliar codebases

### Pattern 2: File Management Agent

Automates file operations with safety guardrails:

```python
from consoul import Consoul

file_manager = Consoul(
    model="claude-3-5-sonnet-20241022",
    tools=["bash", "create_file", "edit_lines", "read", "append_file"],
    system_prompt="""You are a careful file management assistant.

Rules:
- Always use 'ls' to verify before file operations
- Read files before editing them
- Confirm destructive operations with the user
- Use git status to check for uncommitted changes

Be methodical and explain what you're doing.""",
    temperature=0.2  # Very deterministic for file operations
)

# Use the agent
file_manager.chat("Create a basic FastAPI project structure")
file_manager.chat("Add error handling to all API routes")
file_manager.chat("Organize imports in Python files according to PEP 8")
```

**When to use**: Code generation, refactoring, project scaffolding

!!! danger "File Edit Tools"
    File-edit tools (`create_file`, `edit_lines`, `delete_file`) can modify your codebase. Always:

    - Work in a git repository with committed changes
    - Review changes before committing
    - Start with dry runs or test directories
    - Use `tools="safe"` when you don't need file modifications

### Pattern 3: Web Research Agent

Gathers and synthesizes information from the web:

```python
from consoul import Consoul

researcher = Consoul(
    model="gemini-2.0-flash-exp",  # Good for long documents
    tools=["web_search", "read_url", "wikipedia"],
    system_prompt="""You are a thorough research assistant.

Research methodology:
1. Start with web_search to find authoritative sources
2. Use read_url to examine full articles
3. Cross-reference with wikipedia for background
4. Always cite your sources with URLs

Provide well-organized summaries with citations.""",
    temperature=0.5  # Balanced for research
)

# Use the agent
researcher.chat("Research best practices for Python async error handling in 2024")
researcher.chat("Compare FastAPI vs Flask for microservices")
researcher.chat("What are the latest security considerations for JWT authentication?")
```

**When to use**: Technology research, competitive analysis, learning new topics

### Pattern 4: DevOps Assistant

Combines bash execution with file operations:

```python
from consoul import Consoul

devops = Consoul(
    model="gpt-4o",
    tools=["bash", "read", "edit_lines", "create_file"],
    system_prompt="""You are a DevOps assistant expert in Docker, CI/CD, and deployment.

Best practices:
- Test commands with dry runs first (e.g., docker build --dry-run)
- Check existing configurations before modifying
- Explain what each command does and why
- Follow 12-factor app principles

Be cautious with destructive operations.""",
    temperature=0.3
)

# Use the agent
devops.chat("Create a Dockerfile for this Python application")
devops.chat("Set up GitHub Actions CI/CD for automated testing")
devops.chat("Configure Docker Compose for local development")
```

**When to use**: Infrastructure setup, deployment automation, CI/CD configuration

### Pattern 5: Documentation Agent

Generates and updates documentation:

```python
from consoul import Consoul

doc_writer = Consoul(
    model="claude-3-5-sonnet-20241022",  # Excellent writing quality
    tools=["read", "code_search", "create_file", "edit_lines"],
    system_prompt="""You are a technical documentation expert.

Documentation standards:
- Write clear, concise explanations
- Include code examples from the actual codebase
- Use proper Markdown formatting
- Add docstrings to all public functions
- Follow Google-style docstring format

Prioritize clarity and accuracy.""",
    temperature=0.4
)

# Use the agent
doc_writer.chat("Generate API documentation from the code")
doc_writer.chat("Add docstrings to all functions in src/auth.py")
doc_writer.chat("Create a README with usage examples")
```

**When to use**: Documentation generation, API docs, code comments

## Advanced Agent Techniques

### Multi-Step Reasoning

Guide the agent through complex tasks step-by-step:

```python
from consoul import Consoul

architect = Consoul(
    model="gpt-4o",
    tools=["read", "code_search", "create_file", "edit_lines"],
    system_prompt="""You are a software architect. For complex tasks:

1. ANALYZE: Understand current codebase structure
2. PLAN: Outline the changes needed
3. IMPLEMENT: Make changes incrementally
4. VERIFY: Check that changes are correct

Explain each step before doing it.""",
    temperature=0.4
)

architect.chat("""
Add user authentication to this Flask app:
1. Create a User model
2. Add login/logout routes
3. Implement JWT token generation
4. Add authentication middleware
""")
```

### Error Recovery

Teach agents to handle failures gracefully:

```python
from consoul import Consoul

robust_agent = Consoul(
    model="gpt-4o",
    tools=["bash", "read", "edit_lines"],
    system_prompt="""You are a robust automation assistant.

Error handling:
- If a command fails, read the error message carefully
- Try alternative approaches
- Verify assumptions before retrying
- Ask for help if stuck after 2 attempts

Never give up - find a solution.""",
    temperature=0.3
)

robust_agent.chat("Install dependencies and run tests, fixing any errors")
```

### Domain-Specific Agents

Create experts in specific domains:

```python
from consoul import Consoul

# Security auditor
security_agent = Consoul(
    tools=["grep", "code_search", "read"],
    system_prompt="""You are a security auditor specializing in OWASP Top 10.

Audit checklist:
- SQL injection vulnerabilities
- XSS attack vectors
- CSRF protection
- Authentication weaknesses
- Sensitive data exposure
- Insecure dependencies

Provide severity ratings and remediation advice."""
)

# Performance optimizer
perf_agent = Consoul(
    tools=["grep", "code_search", "read", "bash"],
    system_prompt="""You are a performance optimization expert.

Optimization areas:
- Database query efficiency (N+1 queries, missing indexes)
- Memory leaks and excessive allocations
- Inefficient algorithms (O(n²) → O(n log n))
- Caching opportunities
- Lazy loading vs eager loading

Use profiling tools before suggesting changes."""
)

# API designer
api_agent = Consoul(
    tools=["read", "code_search", "create_file"],
    system_prompt="""You are an API design expert following REST and OpenAPI standards.

Design principles:
- RESTful resource naming
- Proper HTTP methods and status codes
- Versioning strategy
- Pagination and filtering
- Error response format
- OpenAPI/Swagger documentation

Follow industry best practices (JSON:API, HAL, etc.)."""
)
```

## Multi-Agent Coordination

Combine specialized agents for complex workflows:

```python
from consoul import Consoul

class DevelopmentTeam:
    """Simulates a development team with specialized roles."""

    def __init__(self):
        # Architect designs the solution
        self.architect = Consoul(
            tools=["read", "code_search"],
            system_prompt="You are a software architect. Design solutions."
        )

        # Developer implements code
        self.developer = Consoul(
            tools=["create_file", "edit_lines", "bash"],
            system_prompt="You are a developer. Implement features."
        )

        # Reviewer checks quality
        self.reviewer = Consoul(
            tools=["read", "grep", "code_search"],
            system_prompt="You are a code reviewer. Check quality and security."
        )

    def build_feature(self, requirement: str):
        """Coordinate agents to build a feature."""

        # 1. Architect designs
        design = self.architect.chat(f"Design a solution for: {requirement}")
        print(f"📐 Design: {design}\n")

        # 2. Developer implements
        implementation = self.developer.chat(
            f"Implement this design:\n{design}\n\nRequirement: {requirement}"
        )
        print(f"💻 Implementation: {implementation}\n")

        # 3. Reviewer audits
        review = self.reviewer.chat(
            f"Review this implementation:\n{implementation}"
        )
        print(f"✅ Review: {review}\n")

        return {"design": design, "implementation": implementation, "review": review}

# Use the team
team = DevelopmentTeam()
team.build_feature("Add rate limiting to the API")
```

## Production Best Practices

### Logging and Monitoring

Track agent behavior in production:

```python
import logging
from consoul import Consoul

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoredAgent:
    """Agent with comprehensive logging."""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.console = Consoul(**kwargs)
        self.logger = logging.getLogger(f"agent.{name}")

    def execute(self, task: str):
        """Execute task with logging."""
        self.logger.info(f"Starting task: {task}")

        try:
            # Track costs before
            cost_before = self.console.last_cost

            # Execute
            result = self.console.chat(task)

            # Track costs after
            cost_after = self.console.last_cost
            tokens_used = cost_after['total_tokens']
            estimated_cost = cost_after['estimated_cost']

            self.logger.info(
                f"Task completed. Tokens: {tokens_used}, "
                f"Cost: ${estimated_cost:.4f}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Task failed: {e}", exc_info=True)
            raise

# Use it
agent = MonitoredAgent(
    name="code_analyzer",
    tools=["grep", "code_search"],
    system_prompt="Analyze code"
)

agent.execute("Find all TODO comments")
```

### Rate Limiting

Prevent API quota exhaustion:

```python
import time
from consoul import Consoul

class RateLimitedAgent:
    """Agent with rate limiting."""

    def __init__(self, requests_per_minute: int = 10, **kwargs):
        self.console = Consoul(**kwargs)
        self.min_delay = 60.0 / requests_per_minute
        self.last_request = 0

    def chat(self, message: str) -> str:
        """Chat with rate limiting."""
        # Enforce minimum delay between requests
        elapsed = time.time() - self.last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

        self.last_request = time.time()
        return self.console.chat(message)

# Use it (max 10 requests/minute)
agent = RateLimitedAgent(
    requests_per_minute=10,
    tools=["web_search"]
)

for query in queries:
    result = agent.chat(query)  # Auto rate-limited
```

### Graceful Degradation

Handle tool failures elegantly:

```python
from consoul import Consoul

agent = Consoul(
    tools=["bash", "read"],
    system_prompt="""If a tool fails, try alternative approaches:

1. bash fails → read the file directly
2. read fails → use bash cat
3. Both fail → explain the limitation

Never stop trying until you've exhausted all options."""
)

# The agent will try alternatives if tools fail
agent.chat("Show me the contents of config.yaml")
```

### Testing Agents

Write tests for agent behavior:

```python
import pytest
from consoul import Consoul

def test_code_analyzer():
    """Test code analysis agent."""
    agent = Consoul(
        tools=["grep", "code_search"],
        system_prompt="You are a code analyzer."
    )

    # Test basic functionality
    result = agent.chat("Find TODO comments")
    assert "TODO" in result or "no TODO" in result.lower()

    # Test conversation memory
    agent.chat("Remember: focus on security issues")
    result = agent.chat("What should I focus on?")
    assert "security" in result.lower()

def test_agent_with_mocked_tools():
    """Test agent with mocked tool responses."""
    # In production, mock expensive operations
    # Use unittest.mock to mock tool.invoke()
    pass
```

## Real-World Agent Examples

### Automated Code Reviewer

```python
from consoul import Consoul

code_reviewer = Consoul(
    model="claude-3-5-sonnet-20241022",
    tools=["read", "grep", "code_search"],
    system_prompt="""You are a senior code reviewer.

Review checklist:
✓ Code style and PEP 8 compliance
✓ Type hints and docstrings
✓ Error handling
✓ Security vulnerabilities
✓ Performance concerns
✓ Test coverage

Provide constructive feedback with examples.""",
    temperature=0.2
)

# Review a pull request
code_reviewer.chat("Review the changes in src/api/auth.py")
code_reviewer.chat("Are there any security issues?")
code_reviewer.chat("Suggest improvements")
```

### Migration Assistant

```python
from consoul import Consoul

migration_agent = Consoul(
    model="gpt-4o",
    tools=["read", "code_search", "edit_lines", "create_file"],
    system_prompt="""You are a migration specialist.

Migration process:
1. Analyze current implementation
2. Plan migration steps
3. Create compatibility layer
4. Incremental migration
5. Deprecation warnings
6. Final cutover

Maintain backward compatibility during migration.""",
    temperature=0.3
)

# Migrate from SQLAlchemy 1.x to 2.0
migration_agent.chat("Analyze the current SQLAlchemy usage")
migration_agent.chat("Create a migration plan to SQLAlchemy 2.0")
migration_agent.chat("Implement the first migration step")
```

### Dependency Updater

```python
from consoul import Consoul

dep_updater = Consoul(
    model="gpt-4o",
    tools=["bash", "read", "edit_lines"],
    system_prompt="""You are a dependency management expert.

Update process:
1. Check current versions
2. Identify outdated packages
3. Review changelogs for breaking changes
4. Update incrementally (minor → major)
5. Run tests after each update
6. Document breaking changes

Never update all at once - be incremental.""",
    temperature=0.2
)

# Update project dependencies
dep_updater.chat("Check for outdated Python packages")
dep_updater.chat("Update packages without breaking changes")
dep_updater.chat("Create a plan for major version updates")
```

## Key Takeaways

1. **Agents = AI + Tools + Prompts**: Combine them thoughtfully
2. **System prompts matter**: Guide agent behavior explicitly
3. **Start simple**: Basic agent → Add tools → Add sophistication
4. **Error handling**: Teach agents to recover from failures
5. **Monitor production**: Log costs, errors, and performance
6. **Test behavior**: Agents are software - test them!

## Next Steps

- **[Tools Deep Dive](tools.md)** - Master all 13 built-in tools
- **[SDK Tutorial](tutorial.md)** - Learn SDK fundamentals
- **[API Reference](reference.md)** - Complete API documentation

Now build your agent! 🤖

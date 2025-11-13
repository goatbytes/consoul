#!/usr/bin/env python3
"""Custom Tool Development Example for Consoul.

This example demonstrates how to create, register, and use custom tools
with Consoul's tool calling system. It includes complete implementations
of three different tools with varying complexity and risk levels.

Tools implemented:
1. Weather API Tool (SAFE) - Read-only external API calls
2. File Search Tool (SAFE) - Local filesystem search
3. Database Query Tool (SAFE) - Read-only database queries

Usage:
    python examples/custom-tool-example.py

Requirements:
    pip install consoul langchain-core pydantic requests
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field, validator

from consoul.ai.tools import RiskLevel, ToolRegistry
from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.loader import load_config

# =============================================================================
# Example 1: Weather API Tool (Simple, SAFE)
# =============================================================================


class WeatherInput(BaseModel):
    """Input schema for weather tool.

    Pydantic models provide automatic validation and clear error messages
    when the AI provides invalid arguments.
    """

    location: str = Field(
        description="City name or zip code (e.g., 'London', '90210')",
        min_length=1,
        max_length=100,
    )
    units: str = Field(
        default="celsius",
        description="Temperature units: 'celsius' or 'fahrenheit'",
        pattern="^(celsius|fahrenheit)$",
    )

    @validator("location")
    def validate_location(cls, v: str) -> str:  # noqa: N805
        """Validate location string is safe."""
        if not v or not v.strip():
            raise ValueError("Location cannot be empty")

        # Basic sanitization
        v = v.strip()

        # Prevent injection attacks
        if any(char in v for char in ["<", ">", "&", ";"]):
            raise ValueError("Location contains invalid characters")

        return v


@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius") -> str:
    """Get current weather information for a location.

    This tool fetches weather data from a public API and returns
    current conditions including temperature, humidity, and description.

    The tool is marked as SAFE because:
    - It only makes read-only API calls
    - It doesn't modify local system state
    - It has timeout protection
    - Input is validated and sanitized

    Args:
        location: City name or zip code
        units: Temperature units ('celsius' or 'fahrenheit')

    Returns:
        Formatted weather information string

    Raises:
        ValueError: If location or units are invalid
        ToolExecutionError: If weather API is unavailable

    Example:
        >>> result = get_weather("London", "celsius")
        >>> print(result)
        Weather in London:
        Temperature: 18°C
        Conditions: Partly cloudy
        Humidity: 65%
    """
    try:
        # Note: This uses a mock API for demonstration
        # Replace with real weather API (OpenWeatherMap, WeatherAPI, etc.)

        # Example with OpenWeatherMap (requires API key):
        # api_key = os.getenv("OPENWEATHER_API_KEY")
        # url = f"https://api.openweathermap.org/data/2.5/weather"
        # params = {"q": location, "appid": api_key, "units": "metric"}
        # response = requests.get(url, params=params, timeout=10)

        # Mock implementation for demonstration
        print(f"Fetching weather for {location} ({units})...")

        # Simulate API call
        mock_data = {
            "location": location,
            "temperature": 18 if units == "celsius" else 64,
            "conditions": "Partly cloudy",
            "humidity": 65,
            "wind_speed": 12,
        }

        # Format response
        unit_symbol = "°C" if units == "celsius" else "°F"
        result = f"""Weather in {mock_data["location"]}:
Temperature: {mock_data["temperature"]}{unit_symbol}
Conditions: {mock_data["conditions"]}
Humidity: {mock_data["humidity"]}%
Wind Speed: {mock_data["wind_speed"]} km/h"""

        return result

    except requests.RequestException as e:
        raise ToolExecutionError(f"Failed to fetch weather data: {e}") from e
    except Exception as e:
        raise ToolExecutionError(f"Unexpected error: {e}") from e


# =============================================================================
# Example 2: File Search Tool (Medium Complexity, SAFE)
# =============================================================================


class FileSearchInput(BaseModel):
    """Input schema for file search tool."""

    pattern: str = Field(
        description="Filename pattern to search (supports wildcards: *.py, test_*.txt)",
        min_length=1,
    )
    directory: str = Field(
        default=".",
        description="Directory to search in (relative or absolute path)",
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of results to return (1-500)",
    )
    recursive: bool = Field(
        default=True, description="Search subdirectories recursively"
    )

    @validator("directory")
    def validate_directory(cls, v: str) -> str:  # noqa: N805
        """Validate directory path is safe."""
        # Resolve to absolute path
        path = Path(v).resolve()

        # Prevent searching sensitive system directories
        sensitive_dirs = ["/etc", "/sys", "/proc", "/dev", "/root"]
        for sensitive in sensitive_dirs:
            if str(path).startswith(sensitive):
                raise ValueError(f"Cannot search sensitive directory: {sensitive}")

        return str(path)

    @validator("pattern")
    def validate_pattern(cls, v: str) -> str:  # noqa: N805
        """Validate pattern is safe."""
        # Prevent command injection
        if any(char in v for char in [";", "&", "|", "$", "`"]):
            raise ValueError("Pattern contains invalid characters")

        return v


@tool(args_schema=FileSearchInput)
def search_files(
    pattern: str, directory: str = ".", max_results: int = 50, recursive: bool = True
) -> str:
    """Search for files matching a pattern in a directory.

    This tool performs local filesystem searches using glob patterns.
    It's useful for finding files by name or extension.

    The tool is marked as SAFE because:
    - It only reads filesystem metadata (doesn't read file contents)
    - It has safeguards against sensitive directories
    - Results are limited to prevent overwhelming output
    - Input is validated to prevent injection

    Args:
        pattern: Filename pattern (supports wildcards: *.py, test_*)
        directory: Directory to search in (default: current directory)
        max_results: Maximum results to return (default: 50, max: 500)
        recursive: Search subdirectories (default: True)

    Returns:
        List of matching file paths, one per line

    Example:
        >>> result = search_files("*.py", "/home/user/project", max_results=10)
        >>> print(result)
        Found 10 files matching '*.py':
        /home/user/project/main.py
        /home/user/project/utils.py
        ...
    """
    try:
        search_path = Path(directory)

        # Verify directory exists
        if not search_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not search_path.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Perform search
        if recursive:
            matches = list(search_path.rglob(pattern))
        else:
            matches = list(search_path.glob(pattern))

        # Filter to files only (exclude directories)
        files = [p for p in matches if p.is_file()]

        # Limit results
        files = files[:max_results]

        # Format output
        if not files:
            return f"No files found matching '{pattern}' in {directory}"

        result_lines = [f"Found {len(files)} files matching '{pattern}':"]
        for file_path in files:
            result_lines.append(f"  {file_path}")

        if len(matches) > max_results:
            result_lines.append(f"\n(Limited to {max_results} results)")

        return "\n".join(result_lines)

    except Exception as e:
        raise ToolExecutionError(f"File search failed: {e}") from e


# =============================================================================
# Example 3: Database Query Tool (Complex, SAFE)
# =============================================================================


class DatabaseQueryInput(BaseModel):
    """Input schema for database query tool."""

    query: str = Field(description="SQL query to execute (SELECT only)")
    database: str = Field(
        description="Database file path (relative or absolute, .db extension)"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum rows to return (1-1000)",
    )

    @validator("query")
    def validate_readonly(cls, v: str) -> str:  # noqa: N805
        """Ensure query is read-only (SELECT only)."""
        query_upper = v.strip().upper()

        # Only allow SELECT queries
        if not query_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        # Block dangerous keywords (even in SELECT)
        dangerous = [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "REPLACE",
        ]
        for keyword in dangerous:
            if keyword in query_upper:
                raise ValueError(f"Query contains forbidden keyword: {keyword}")

        # Block PRAGMA commands (can change settings)
        if "PRAGMA" in query_upper:
            raise ValueError("PRAGMA commands are not allowed")

        return v

    @validator("database")
    def validate_database_path(cls, v: str) -> str:  # noqa: N805
        """Validate database path is safe."""
        path = Path(v)

        # Must have .db extension
        if path.suffix.lower() not in [".db", ".sqlite", ".sqlite3"]:
            raise ValueError("Database file must have .db/.sqlite extension")

        # Prevent path traversal
        if ".." in str(path):
            raise ValueError("Path cannot contain '..'")

        return str(path)


@tool(args_schema=DatabaseQueryInput)
def query_database(query: str, database: str, limit: int = 100) -> str:
    """Execute a read-only SQL query against a SQLite database.

    This tool allows querying SQLite databases with strict read-only access.
    Only SELECT queries are permitted. Results are formatted as a table
    and limited to prevent overwhelming the AI context.

    The tool is marked as SAFE because:
    - Only SELECT queries are allowed (enforced by validation)
    - Database is opened in read-only mode
    - Results are limited to prevent context overflow
    - Input is thoroughly validated
    - No system state is modified

    Args:
        query: SQL SELECT query to execute
        database: Path to SQLite database file (.db, .sqlite, .sqlite3)
        limit: Maximum number of rows to return (1-1000)

    Returns:
        Query results formatted as a text table with row count

    Raises:
        ValueError: If query is invalid or contains forbidden operations
        ToolExecutionError: If database access fails

    Example:
        >>> result = query_database(
        ...     query="SELECT name, email FROM users WHERE active=1",
        ...     database="app.db",
        ...     limit=50
        ... )
        >>> print(result)
        name           | email
        ------------------------------------------------
        John Doe       | john@example.com
        Jane Smith     | jane@example.com
        ...
        (2 rows returned, limit=50)
    """
    try:
        db_path = Path(database)

        # Verify database exists
        if not db_path.exists():
            raise ValueError(f"Database file not found: {database}")

        # Connect to database in read-only mode
        # URI mode with ?mode=ro ensures read-only access
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()

        # Execute query with LIMIT
        limited_query = f"{query.rstrip(';')} LIMIT {limit}"
        cursor.execute(limited_query)
        rows = cursor.fetchall()

        # Handle empty results
        if not rows:
            conn.close()
            return "Query executed successfully.\n(0 rows returned)"

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Build formatted table
        # Calculate column widths
        col_widths = {col: len(col) for col in columns}
        for row in rows:
            for col in columns:
                value_len = len(str(row[col]))
                col_widths[col] = max(col_widths[col], value_len)

        # Build header
        header = " | ".join(col.ljust(col_widths[col]) for col in columns)
        separator = "-" * len(header)

        # Build rows
        result_lines = [header, separator]
        for row in rows:
            row_str = " | ".join(
                str(row[col]).ljust(col_widths[col]) for col in columns
            )
            result_lines.append(row_str)

        # Add metadata
        result_lines.append("")
        result_lines.append(f"({len(rows)} rows returned, limit={limit})")

        conn.close()
        return "\n".join(result_lines)

    except sqlite3.Error as e:
        raise ToolExecutionError(f"Database error: {e}") from e
    except Exception as e:
        raise ToolExecutionError(f"Query execution failed: {e}") from e


# =============================================================================
# Tool Registration and Usage
# =============================================================================


def register_custom_tools(registry: ToolRegistry) -> None:
    """Register all custom tools with the registry.

    This function should be called during application initialization
    to make custom tools available for AI tool calling.

    Args:
        registry: ToolRegistry instance to register tools with
    """
    # Register weather tool (SAFE - external API, read-only)
    registry.register(
        tool=get_weather,
        risk_level=RiskLevel.SAFE,
        tags=["api", "weather", "external", "readonly"],
        enabled=True,
    )
    print("✓ Registered: get_weather (SAFE)")

    # Register file search tool (SAFE - filesystem read, limited scope)
    registry.register(
        tool=search_files,
        risk_level=RiskLevel.SAFE,
        tags=["filesystem", "search", "readonly"],
        enabled=True,
    )
    print("✓ Registered: search_files (SAFE)")

    # Register database query tool (SAFE - read-only database access)
    registry.register(
        tool=query_database,
        risk_level=RiskLevel.SAFE,
        tags=["database", "query", "readonly", "sqlite"],
        enabled=True,
    )
    print("✓ Registered: query_database (SAFE)")


def demo_tools() -> None:
    """Demonstrate custom tool usage.

    This function shows how to:
    1. Load configuration
    2. Create tool registry
    3. Register custom tools
    4. Execute tools directly
    5. Use tools with AI models (commented example)
    """
    print("=" * 70)
    print("Custom Tool Development Example")
    print("=" * 70)
    print()

    # Load configuration
    print("Loading configuration...")
    config = load_config()
    print(f"✓ Configuration loaded (tools enabled: {config.tools.enabled})")
    print()

    # Create tool registry
    print("Creating tool registry...")
    registry = ToolRegistry(config=config.tools)
    print("✓ Tool registry created")
    print()

    # Register custom tools
    print("Registering custom tools...")
    register_custom_tools(registry)
    print()

    # List all registered tools
    print("Registered tools:")
    tools = registry.list_tools()
    for tool_meta in tools:
        print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")
    print()

    # Demo 1: Weather Tool
    print("=" * 70)
    print("Demo 1: Weather Tool")
    print("=" * 70)
    try:
        result = get_weather("London", "celsius")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Demo 2: File Search Tool
    print("=" * 70)
    print("Demo 2: File Search Tool")
    print("=" * 70)
    try:
        # Search for Python files in current directory
        result = search_files(
            pattern="*.py", directory=".", max_results=10, recursive=False
        )
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Demo 3: Database Query Tool
    print("=" * 70)
    print("Demo 3: Database Query Tool")
    print("=" * 70)
    print("Note: This demo requires a test database.")
    print("Creating test database...")

    # Create test database
    test_db = Path("/tmp/test_consoul.db")
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Create test table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """
    )

    # Insert test data
    cursor.executemany(
        "INSERT INTO users (name, email, active) VALUES (?, ?, ?)",
        [
            ("John Doe", "john@example.com", 1),
            ("Jane Smith", "jane@example.com", 1),
            ("Bob Johnson", "bob@example.com", 0),
            ("Alice Williams", "alice@example.com", 1),
        ],
    )

    conn.commit()
    conn.close()
    print(f"✓ Test database created: {test_db}")
    print()

    try:
        result = query_database(
            query="SELECT name, email FROM users WHERE active=1",
            database=str(test_db),
            limit=10,
        )
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Clean up
    test_db.unlink(missing_ok=True)

    # Example: Using tools with AI model (commented - requires API key)
    print("=" * 70)
    print("AI Model Integration Example")
    print("=" * 70)
    print("Uncomment the code below to test with a real AI model:")
    print()
    print("```python")
    print("from langchain_anthropic import ChatAnthropic")
    print()
    print('model = ChatAnthropic(model="claude-3-5-sonnet-20241022")')
    print("model_with_tools = registry.bind_tools(model)")
    print()
    print('response = model_with_tools.invoke("What\'s the weather in London?")')
    print("print(response.content)")
    print("```")
    print()


# =============================================================================
# Integration with TUI
# =============================================================================


def integrate_with_tui() -> None:
    """Example of integrating custom tools into Consoul TUI.

    Add this code to src/consoul/tui/app.py in the _setup_tool_registry method:

    ```python
    def _setup_tool_registry(self) -> None:
        # Import custom tools
        from consoul.ai.tools.implementations import bash_execute
        from examples.custom_tool_example import (
            get_weather,
            search_files,
            query_database
        )

        # Register built-in tools
        self.tool_registry.register(
            bash_execute,
            risk_level=RiskLevel.CAUTION,
            tags=["system", "bash"]
        )

        # Register custom tools
        self.tool_registry.register(
            get_weather,
            risk_level=RiskLevel.SAFE,
            tags=["api", "weather"]
        )

        self.tool_registry.register(
            search_files,
            risk_level=RiskLevel.SAFE,
            tags=["filesystem", "search"]
        )

        self.tool_registry.register(
            query_database,
            risk_level=RiskLevel.SAFE,
            tags=["database", "query"]
        )
    ```

    Then restart the TUI and ask the AI to use your custom tools:
    - "What's the weather in Tokyo?"
    - "Find all Python test files in the project"
    - "Query the database for active users"
    """
    pass


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for the example."""
    try:
        demo_tools()
        print("=" * 70)
        print("Custom tool example completed successfully!")
        print()
        print("Next steps:")
        print("1. Modify these tools for your use case")
        print("2. Create additional tools following the same pattern")
        print("3. Register tools in your TUI/CLI application")
        print("4. Test with AI model integration")
        print()
        print("See docs/tools.md for comprehensive documentation.")
        print("=" * 70)

    except Exception as e:
        print(f"Error running example: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

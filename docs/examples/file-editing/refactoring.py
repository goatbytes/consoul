"""Multi-file refactoring workflow example.

Demonstrates a complete refactoring workflow using Consoul's file editing
and code search tools:
1. Find function definitions and usages
2. Preview changes with dry-run
3. Apply changes across multiple files
4. Verify results
"""

from consoul import Consoul


def refactor_function_workflow():
    """Complete workflow for refactoring a function across a project."""
    print("=" * 70)
    print("WORKFLOW: Refactor calculate_total() → calculate_sum()")
    print("=" * 70)

    console = Consoul(tools=True)

    # Step 1: Find the function definition
    print("\nStep 1: Locate function definition")
    print("-" * 70)
    response = console.chat("""
    Use code_search to find the definition of calculate_total function.
    """)
    print(f"Result: {response}\n")

    # Step 2: Find all usages
    print("\nStep 2: Find all usages")
    print("-" * 70)
    response = console.chat("""
    Use find_references to locate all calls to calculate_total() in the project.
    """)
    print(f"Result: {response}\n")

    # Step 3: Preview the refactoring
    print("\nStep 3: Preview changes (dry-run)")
    print("-" * 70)
    response = console.chat("""
    Show me a preview of what it would look like to:
    1. Rename calculate_total() to calculate_sum() in src/utils.py
    2. Add a tax_rate parameter with default value 0.08

    Don't make any changes yet, just show the diff.
    """)
    print(f"Preview: {response}\n")

    # Step 4: Apply the rename
    print("\nStep 4: Rename function definition")
    print("-" * 70)
    response = console.chat("""
    Rename calculate_total() to calculate_sum() in src/utils.py and
    add tax_rate: float = 0.08 parameter.
    """)
    print(f"Result: {response}\n")

    # Step 5: Update all call sites
    print("\nStep 5: Update all call sites")
    print("-" * 70)
    response = console.chat("""
    Update all calls to calculate_total() to calculate_sum() across
    the project. Add tax_rate=0.08 argument where needed.
    """)
    print(f"Result: {response}\n")

    # Step 6: Verify changes
    print("\nStep 6: Verify refactoring")
    print("-" * 70)
    response = console.chat("""
    Search for any remaining references to calculate_total to ensure
    we've updated everything.
    """)
    print(f"Verification: {response}\n")

    print("\n" + "=" * 70)
    print("Refactoring workflow completed!")
    print("=" * 70)


def add_type_hints_workflow():
    """Add type hints to all functions in a module."""
    print("\n" + "=" * 70)
    print("WORKFLOW: Add type hints to a module")
    print("=" * 70)

    console = Consoul(tools=True)

    # Step 1: Find functions without type hints
    print("\nStep 1: Find functions missing type hints")
    print("-" * 70)
    response = console.chat("""
    Use code_search to find all function definitions in src/models.py
    """)
    print(f"Result: {response}\n")

    # Step 2: Add type hints systematically
    print("\nStep 2: Add type hints to each function")
    print("-" * 70)
    response = console.chat("""
    For each function in src/models.py, add appropriate type hints:
    - Import typing module types (List, Dict, Optional) if needed
    - Add parameter type annotations
    - Add return type annotations
    - Use whitespace tolerance to preserve formatting

    Start with the first 3 functions, show me the diffs.
    """)
    print(f"Result: {response}\n")

    print("\n" + "=" * 70)
    print("Type hints workflow completed!")
    print("=" * 70)


def error_handling_workflow():
    """Add error handling to risky operations."""
    print("\n" + "=" * 70)
    print("WORKFLOW: Add error handling to file I/O")
    print("=" * 70)

    console = Consoul(tools=True)

    # Step 1: Find file I/O operations
    print("\nStep 1: Find file I/O operations")
    print("-" * 70)
    response = console.chat("""
    Use grep_search to find all file open/read/write operations in src/
    Search for patterns like: open(, .read(, .write(
    """)
    print(f"Result: {response}\n")

    # Step 2: Wrap in try/except
    print("\nStep 2: Add try/except blocks")
    print("-" * 70)
    response = console.chat("""
    For each file I/O operation found:
    1. Wrap in try/except block
    2. Catch IOError and OSError
    3. Log errors using logger.error()
    4. Use whitespace tolerance to preserve indentation

    Start with src/data_loader.py, show me the changes.
    """)
    print(f"Result: {response}\n")

    print("\n" + "=" * 70)
    print("Error handling workflow completed!")
    print("=" * 70)


def documentation_workflow():
    """Add docstrings to undocumented functions."""
    print("\n" + "=" * 70)
    print("WORKFLOW: Add comprehensive docstrings")
    print("=" * 70)

    console = Consoul(tools=True)

    # Step 1: Find functions without docstrings
    print("\nStep 1: Find undocumented functions")
    print("-" * 70)
    response = console.chat("""
    Find all functions in src/api.py that don't have docstrings.
    Use code_search to list them.
    """)
    print(f"Result: {response}\n")

    # Step 2: Add Google-style docstrings
    print("\nStep 2: Add Google-style docstrings")
    print("-" * 70)
    response = console.chat("""
    For each function without a docstring in src/api.py:
    1. Add a Google-style docstring
    2. Include description, Args, Returns, Raises sections
    3. Preserve existing indentation

    Start with the first 2 functions, show me the diffs.
    """)
    print(f"Result: {response}\n")

    print("\n" + "=" * 70)
    print("Documentation workflow completed!")
    print("=" * 70)


def config_migration_workflow():
    """Migrate configuration format across files."""
    print("\n" + "=" * 70)
    print("WORKFLOW: Migrate config format")
    print("=" * 70)

    console = Consoul(tools=True)

    # Step 1: Find all config files
    print("\nStep 1: Find all YAML config files")
    print("-" * 70)
    response = console.chat("""
    Find all .yaml and .yml files in the config/ directory.
    Use bash_execute with find command.
    """)
    print(f"Result: {response}\n")

    # Step 2: Update format in each file
    print("\nStep 2: Update configuration format")
    print("-" * 70)
    response = console.chat("""
    In all YAML files found:
    1. Change environment: dev → environment: development
    2. Change debug: true → debug_mode: true
    3. Add new field: log_level: INFO

    Use edit_file_search_replace with whitespace tolerance.
    Show me the changes for the first file.
    """)
    print(f"Result: {response}\n")

    print("\n" + "=" * 70)
    print("Config migration workflow completed!")
    print("=" * 70)


def main():
    """Run all workflow examples."""
    print("\n" + "=" * 70)
    print("MULTI-FILE REFACTORING WORKFLOWS")
    print("=" * 70)
    print("\nThis script demonstrates complete refactoring workflows:")
    print("1. Function rename with call site updates")
    print("2. Add type hints to a module")
    print("3. Add error handling to risky operations")
    print("4. Add docstrings to undocumented functions")
    print("5. Migrate configuration format")
    print("\nEach workflow combines multiple tools:")
    print("- code_search: Find definitions")
    print("- find_references: Find usages")
    print("- grep_search: Pattern-based search")
    print("- edit_file_search_replace: Smart replacements")
    print("- edit_file_lines: Precise line edits")
    print()

    # Run workflows
    refactor_function_workflow()
    add_type_hints_workflow()
    error_handling_workflow()
    documentation_workflow()
    config_migration_workflow()

    print("\n" + "=" * 70)
    print("All workflows completed!")
    print("=" * 70)
    print("\nBest Practices Demonstrated:")
    print("1. Always search first to understand scope")
    print("2. Preview changes with dry_run before applying")
    print("3. Use appropriate tolerance level (strict/whitespace/fuzzy)")
    print("4. Verify changes after refactoring")
    print("5. Handle errors gracefully")
    print("6. Leverage audit logs for accountability")
    print("\nCheck audit log: ~/.consoul/tool_audit.jsonl")


if __name__ == "__main__":
    main()

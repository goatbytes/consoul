"""Code Search Tools - Working Examples

This file demonstrates practical usage of Consoul's three code search tools:
- grep_search: Fast text-based pattern matching
- code_search: AST-based symbol definition search
- find_references: Symbol usage finder

Run this file directly to see the tools in action:
    python docs/examples/code-search-example.py
"""

from __future__ import annotations

import json
from pathlib import Path

from consoul.ai.tools import code_search, find_references, grep_search


def example_1_basic_grep_search() -> None:
    """Example 1: Find TODO comments in Python files."""
    print("\n" + "=" * 80)
    print("Example 1: Find TODO Comments with grep_search")
    print("=" * 80)

    result = grep_search.invoke(
        {
            "pattern": r"TODO|FIXME|XXX|HACK",
            "glob_pattern": "*.py",
            "path": "src/",
        }
    )

    results = json.loads(result)
    print(f"\nFound {len(results)} TODO comments:\n")

    for match in results[:5]:  # Show first 5
        print(f"  {match['file']}:{match['line']}")
        print(f"    {match['text'].strip()}")


def example_2_find_function_definition() -> None:
    """Example 2: Locate where a function is defined."""
    print("\n" + "=" * 80)
    print("Example 2: Find Function Definition with code_search")
    print("=" * 80)

    result = code_search.invoke(
        {
            "query": "bash_execute",
            "symbol_type": "function",
            "path": "src/",
        }
    )

    results = json.loads(result)

    if results:
        defn = results[0]
        print("\nFunction 'bash_execute' defined at:")
        print(f"  File: {defn['file']}")
        print(f"  Line: {defn['line']}")
        print("\n  Code:")
        print(f"    {defn['text'].strip()}")
    else:
        print("\nFunction not found")


def example_3_find_all_usages() -> None:
    """Example 3: Find all references to a symbol."""
    print("\n" + "=" * 80)
    print("Example 3: Find All Usages with find_references")
    print("=" * 80)

    result = find_references.invoke(
        {
            "symbol": "ToolRegistry",
            "scope": "project",
            "include_definition": True,
        }
    )

    results = json.loads(result)
    print(f"\nFound {len(results)} references to 'ToolRegistry':\n")

    # Separate definition from usages
    definitions = [r for r in results if r.get("is_definition")]
    usages = [r for r in results if not r.get("is_definition")]

    if definitions:
        defn = definitions[0]
        print(f"Definition: {defn['file']}:{defn['line']}")

    print(f"\nUsages ({len(usages)}):")
    for usage in usages[:5]:  # Show first 5
        print(f"  {usage['file']}:{usage['line']} ({usage['type']})")


def example_4_multi_step_workflow() -> None:
    """Example 4: Multi-step search workflow for refactoring analysis."""
    print("\n" + "=" * 80)
    print("Example 4: Refactoring Analysis Workflow")
    print("=" * 80)

    function_name = "grep_search"

    # Step 1: Find definition
    print(f"\nStep 1: Finding definition of '{function_name}'...")
    def_result = code_search.invoke(
        {
            "query": function_name,
            "symbol_type": "function",
            "path": "src/",
        }
    )

    definitions = json.loads(def_result)
    if not definitions:
        print(f"  ❌ Function '{function_name}' not found")
        return

    defn = definitions[0]
    print(f"  ✓ Found at {defn['file']}:{defn['line']}")

    # Step 2: Find all usages
    print(f"\nStep 2: Finding all usages of '{function_name}'...")
    ref_result = find_references.invoke({"symbol": function_name, "scope": "project"})

    references = json.loads(ref_result)
    print(f"  ✓ Found {len(references)} usages")

    # Step 3: Analyze impact
    print("\nStep 3: Impact Analysis")
    files_affected = {ref["file"] for ref in references}
    print(f"  Files affected by changes: {len(files_affected)}")
    print(f"  Total references to update: {len(references)}")

    # Step 4: Group by reference type
    by_type: dict[str, int] = {}
    for ref in references:
        ref_type = ref.get("type", "unknown")
        by_type[ref_type] = by_type.get(ref_type, 0) + 1

    print("\n  References by type:")
    for ref_type, count in by_type.items():
        print(f"    {ref_type}: {count}")


def example_5_combining_tools() -> None:
    """Example 5: Combine grep + code_search for comprehensive search."""
    print("\n" + "=" * 80)
    print("Example 5: Combining grep_search and code_search")
    print("=" * 80)

    search_term = "ToolRegistry"

    # First: Fast text search to find potential matches
    print(f"\nStep 1: Fast text search for '{search_term}'...")
    grep_result = grep_search.invoke(
        {
            "pattern": search_term,
            "path": "src/",
            "glob_pattern": "*.py",
        }
    )

    grep_matches = json.loads(grep_result)
    print(f"  Found {len(grep_matches)} text matches")

    # Second: Semantic search for actual definitions
    print("\nStep 2: Finding semantic definitions...")
    code_result = code_search.invoke(
        {"query": search_term, "symbol_type": "class", "path": "src/"}
    )

    code_matches = json.loads(code_result)
    print(f"  Found {len(code_matches)} class definitions")

    # Analysis
    print("\nAnalysis:")
    print(f"  Text matches ({len(grep_matches)}) include comments, strings, imports")
    print(f"  Semantic matches ({len(code_matches)}) are actual class definitions")


def example_6_cache_performance() -> None:
    """Example 6: Demonstrate cache performance benefit."""
    print("\n" + "=" * 80)
    print("Example 6: Cache Performance Demonstration")
    print("=" * 80)

    import time

    # First search - cache miss (will parse files)
    print("\nFirst search (cache miss):")
    start = time.time()
    _ = code_search.invoke({"query": ".*", "path": "src/consoul/ai/tools/"})
    first_duration = time.time() - start
    print(f"  Duration: {first_duration:.3f}s")

    # Second search - cache hit (uses cached parse)
    print("\nSecond search (cache hit):")
    start = time.time()
    _ = code_search.invoke({"query": ".*", "path": "src/consoul/ai/tools/"})
    second_duration = time.time() - start
    print(f"  Duration: {second_duration:.3f}s")

    # Performance gain
    if second_duration > 0:
        speedup = first_duration / second_duration
        print(f"\n  Cache speedup: {speedup:.1f}x faster")
    else:
        print("\n  Cache speedup: Very fast (< 1ms)")


def example_7_error_handling() -> None:
    """Example 7: Proper error handling patterns."""
    print("\n" + "=" * 80)
    print("Example 7: Error Handling Patterns")
    print("=" * 80)

    from consoul.ai.tools.exceptions import ToolExecutionError

    # Test 1: Invalid path
    print("\nTest 1: Invalid path")
    try:
        grep_search.invoke({"pattern": "foo", "path": "/nonexistent/path"})
    except ToolExecutionError as e:
        print(f"  ✓ Caught expected error: {e}")

    # Test 2: Invalid regex
    print("\nTest 2: Invalid regex pattern")
    try:
        find_references.invoke({"symbol": "[invalid(regex", "scope": "project"})
    except ToolExecutionError as e:
        print(f"  ✓ Caught expected error: {e}")

    # Test 3: Empty results (not an error)
    print("\nTest 3: Empty results (valid)")
    result = code_search.invoke({"query": "NonexistentSymbolXYZ123", "path": "src/"})
    results = json.loads(result)
    print(f"  ✓ Returned empty list: {results}")


def example_8_finding_dead_code() -> None:
    """Example 8: Find potentially unused functions."""
    print("\n" + "=" * 80)
    print("Example 8: Finding Potentially Unused Functions")
    print("=" * 80)

    # Get all functions in a directory
    print("\nStep 1: Finding all functions in implementations/...")
    all_functions = code_search.invoke(
        {
            "query": ".*",
            "symbol_type": "function",
            "path": "src/consoul/ai/tools/implementations/",
        }
    )

    functions = json.loads(all_functions)
    print(f"  Found {len(functions)} functions")

    # Check each for references
    print("\nStep 2: Checking for usages...")
    unused_functions: list[dict] = []

    for func in functions[:5]:  # Check first 5 for demo
        func_name = func["name"]

        # Skip private functions (they may be used locally)
        if func_name.startswith("_"):
            continue

        refs = find_references.invoke(
            {
                "symbol": func_name,
                "scope": "project",
            }
        )

        ref_count = len(json.loads(refs))

        if ref_count == 0:
            unused_functions.append(func)
            print(f"  ⚠️  {func_name} at {func['file']}:{func['line']} - 0 usages")
        else:
            print(f"  ✓ {func_name} - {ref_count} usages")

    if unused_functions:
        print(f"\nFound {len(unused_functions)} potentially unused functions")
    else:
        print("\n✓ All checked functions are in use")


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 80)
    print("CONSOUL CODE SEARCH TOOLS - EXAMPLES")
    print("=" * 80)

    # Check we're in the right directory
    if not Path("src/consoul").exists():
        print("\n❌ Error: Run this script from the consoul project root:")
        print("    python docs/examples/code-search-example.py")
        return

    examples = [
        example_1_basic_grep_search,
        example_2_find_function_definition,
        example_3_find_all_usages,
        example_4_multi_step_workflow,
        example_5_combining_tools,
        example_6_cache_performance,
        example_7_error_handling,
        example_8_finding_dead_code,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Example failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

"""Search/replace with progressive matching example.

Demonstrates the three tolerance levels for edit_file_search_replace:
- strict: Exact character-for-character matching
- whitespace: Ignores indentation differences
- fuzzy: Handles typos and minor variations
"""

from consoul.ai.tools.implementations import edit_file_search_replace


def strict_matching_example():
    """Demonstrate strict (exact) matching."""
    print("=" * 70)
    print("STRICT MATCHING: Exact character-for-character match")
    print("=" * 70)

    # Strict matching requires exact match (including whitespace)
    result = edit_file_search_replace.invoke(
        {
            "file_path": "config.py",
            "edits": [{"search": "DEBUG = True", "replace": "DEBUG = False"}],
            "tolerance": "strict",
            "dry_run": True,  # Preview only
        }
    )

    print(f"Status: {result.get('status')}")
    print(f"Preview:\n{result.get('preview', 'No preview available')}\n")


def whitespace_tolerant_example():
    """Demonstrate whitespace-tolerant matching."""
    print("=" * 70)
    print("WHITESPACE TOLERANCE: Ignores indentation differences")
    print("=" * 70)

    # Search block with no indentation
    search_text = """def login(user):
    validate(user)
    return True"""

    # Replacement with async/await
    replace_text = """async def login(user):
    await validate(user)
    return True"""

    result = edit_file_search_replace.invoke(
        {
            "file_path": "auth.py",
            "edits": [{"search": search_text, "replace": replace_text}],
            "tolerance": "whitespace",  # Ignores indentation differences
            "dry_run": True,
        }
    )

    print(f"Status: {result.get('status')}")
    print("Note: This will match even if the actual file has different indentation")
    print("The replacement will preserve the original tab/space style")
    print(f"\nPreview:\n{result.get('preview', 'No preview available')}\n")


def fuzzy_matching_example():
    """Demonstrate fuzzy matching for typos."""
    print("=" * 70)
    print("FUZZY MATCHING: Handles typos and variations")
    print("=" * 70)

    # Search has a typo: "calculate_totle" instead of "calculate_total"
    result = edit_file_search_replace.invoke(
        {
            "file_path": "utils.py",
            "edits": [
                {
                    "search": "def calculate_totle(items):",  # Intentional typo
                    "replace": "def calculate_sum(items):",
                }
            ],
            "tolerance": "fuzzy",  # Will match with similarity ≥80%
            "dry_run": True,
        }
    )

    print(f"Status: {result.get('status')}")
    if "warnings" in result:
        print(f"Warnings: {result['warnings']}")
    print("Note: Fuzzy matching found 'calculate_total' with 94% similarity")
    print(f"\nPreview:\n{result.get('preview', 'No preview available')}\n")


def tab_preservation_example():
    """Demonstrate tab/space preservation."""
    print("=" * 70)
    print("TAB PRESERVATION: Maintains original indentation style")
    print("=" * 70)

    # File uses tabs, search uses spaces
    result = edit_file_search_replace.invoke(
        {
            "file_path": "legacy.py",  # Uses tabs for indentation
            "edits": [
                {
                    # Search uses spaces (4 spaces)
                    "search": "def process():\n    return data",
                    # Replace uses spaces (4 spaces)
                    "replace": "def process():\n    return transform(data)",
                }
            ],
            "tolerance": "whitespace",  # Ignores tab/space differences
            "dry_run": True,
        }
    )

    print(f"Status: {result.get('status')}")
    print("Note: Original file uses tabs, search uses spaces")
    print("Result will preserve tabs in the replacement")
    print(f"\nPreview:\n{result.get('preview', 'No preview available')}\n")


def crlf_preservation_example():
    """Demonstrate CRLF/LF preservation."""
    print("=" * 70)
    print("CRLF PRESERVATION: Maintains Windows line endings")
    print("=" * 70)

    # File uses CRLF (Windows), search uses LF (Unix)
    result = edit_file_search_replace.invoke(
        {
            "file_path": "windows_file.py",  # Uses CRLF line endings
            "edits": [
                {
                    # Search uses LF (Unix style)
                    "search": "line1\nline2",
                    # Replace uses LF (Unix style)
                    "replace": "LINE1\nLINE2",
                }
            ],
            "tolerance": "whitespace",  # Ignores CRLF/LF differences
            "dry_run": True,
        }
    )

    print(f"Status: {result.get('status')}")
    print("Note: Original file uses CRLF, search uses LF")
    print("Result will preserve CRLF in the replacement")
    print(f"\nPreview:\n{result.get('preview', 'No preview available')}\n")


def multiple_edits_example():
    """Demonstrate multiple replacements in one operation."""
    print("=" * 70)
    print("MULTIPLE EDITS: Batch replacements")
    print("=" * 70)

    result = edit_file_search_replace.invoke(
        {
            "file_path": "api.py",
            "edits": [
                # Rename function
                {
                    "search": "def process_order(order_id):",
                    "replace": "async def process_order(order_id: str):",
                },
                # Update call site
                {
                    "search": "result = process_order(id)",
                    "replace": "result = await process_order(str(id))",
                },
                # Add type annotation
                {
                    "search": "def validate(data):",
                    "replace": "def validate(data: dict) -> bool:",
                },
            ],
            "tolerance": "whitespace",
            "dry_run": True,
        }
    )

    print(f"Status: {result.get('status')}")
    print(f"Number of edits: {len(result.get('edits', []))}")
    print(f"\nPreview:\n{result.get('preview', 'No preview available')}\n")


def similarity_suggestions_example():
    """Demonstrate similarity suggestions when search fails."""
    print("=" * 70)
    print("SIMILARITY SUGGESTIONS: 'Did you mean...?'")
    print("=" * 70)

    try:
        result = edit_file_search_replace.invoke(
            {
                "file_path": "utils.py",
                "edits": [
                    {
                        # Search text with significant typo
                        "search": "def proces_ordr():",
                        "replace": "def process_order_v2():",
                    }
                ],
                "tolerance": "fuzzy",
                "dry_run": True,
            }
        )
        print(f"Status: {result.get('status')}")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nThe error message includes similarity suggestions:")
        print("Did you mean:")
        print("  - def process_order():    (85% similar)")
        print("  - def process_payment():  (80% similar)")


if __name__ == "__main__":
    print("\nFILE EDITING: Progressive Matching Examples")
    print("=" * 70)
    print("This script demonstrates the three tolerance levels:")
    print("1. STRICT - Exact match (default)")
    print("2. WHITESPACE - Ignores indentation, preserves tabs/CRLF")
    print("3. FUZZY - Handles typos with ≥80% similarity")
    print()

    # Run all examples
    strict_matching_example()
    whitespace_tolerant_example()
    fuzzy_matching_example()
    tab_preservation_example()
    crlf_preservation_example()
    multiple_edits_example()
    similarity_suggestions_example()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("1. Use 'strict' when you know exact content")
    print("2. Use 'whitespace' for refactoring with different indentation")
    print("3. Use 'fuzzy' for handling typos or minor variations")
    print("4. Whitespace tolerance preserves tabs/spaces and CRLF/LF")
    print("5. Always use dry_run=True to preview changes first")

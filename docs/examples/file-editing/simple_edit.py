"""Simple file editing example.

Demonstrates basic file editing with Consoul using natural language.
"""

from consoul import Consoul

# Initialize Consoul with tools enabled
console = Consoul(tools=True)

# Example 1: Fix a specific line
print("Example 1: Fix a typo in a specific line")
print("=" * 60)
response = console.chat("""
Fix the typo in line 12 of README.md.
The line says 'pythom' but should say 'python'.
""")
print(f"Response: {response}\n")

# Example 2: Add logging to a function
print("Example 2: Add logging statement")
print("=" * 60)
response = console.chat("""
In src/utils.py, add a logger.info statement at the start of the
calculate_total() function to log the number of items being processed.
""")
print(f"Response: {response}\n")

# Example 3: Update a configuration value
print("Example 3: Update configuration")
print("=" * 60)
response = console.chat("""
Change DEBUG = True to DEBUG = False in config/settings.py
""")
print(f"Response: {response}\n")

# Example 4: Add error handling
print("Example 4: Add error handling")
print("=" * 60)
response = console.chat("""
Wrap the database connection code in src/database.py (lines 42-45)
with a try/except block to catch ConnectionError.
""")
print(f"Response: {response}\n")

# Example 5: Preview before editing (dry-run)
print("Example 5: Preview changes before applying")
print("=" * 60)
response = console.chat("""
Show me what it would look like if we changed the function signature
in src/api.py line 25 from:
    def process_order(order_id):
to:
    async def process_order(order_id: str):

Don't make the change yet, just show me the diff.
""")
print(f"Preview: {response}\n")

# Note: The AI will use the appropriate file editing tools
# (edit_file_lines, edit_file_search_replace) based on the request.
# With permission_policy: balanced, the user will be prompted to
# approve each file modification.

print("\nAll examples completed!")
print("\nNote: With tools enabled and permission_policy: balanced,")
print("you will be prompted to approve each file modification.")
print("Check your audit log: ~/.consoul/tool_audit.jsonl")

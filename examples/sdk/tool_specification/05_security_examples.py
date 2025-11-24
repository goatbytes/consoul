#!/usr/bin/env python3
"""Security and Risk Level Examples.

This example demonstrates risk-based tool filtering and security best practices.
Shows how to control AI capabilities based on trust level and use case.

Risk Levels:
- SAFE: Read-only operations, no system changes
- CAUTION: File operations, command execution (requires oversight)
- DANGEROUS: Reserved for high-risk operations

Run this example:
    python 05_security_examples.py
"""

from consoul import Consoul


def example_safe_tools_only():
    """Maximum security: Only read-only tools."""
    print("\n" + "=" * 60)
    print("Example 1: SAFE Tools Only (Read-Only)")
    print("=" * 60)

    console = Consoul(model="llama", tools="safe", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")
    print("Security level: SAFE (read-only)")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSAFE tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")

        print("\nCapabilities:")
        print("  ✓ Search code and files")
        print("  ✓ Read URLs and search web")
        print("  ✗ Cannot modify files")
        print("  ✗ Cannot execute commands")

        print("\nUse cases:")
        print("  - Untrusted AI interactions")
        print("  - Code exploration and analysis")
        print("  - Research and information gathering")
        print("  - Public-facing AI assistants")


def example_caution_tools():
    """Moderate security: File operations allowed."""
    print("\n" + "=" * 60)
    print("Example 2: CAUTION Tools (SAFE + File Operations)")
    print("=" * 60)

    console = Consoul(model="llama", tools="caution", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")
    print("Security level: CAUTION (read + write)")

    if console.registry:
        tools = console.registry.list_tools()

        safe_tools = [t for t in tools if t.risk_level.value == "safe"]
        caution_tools = [t for t in tools if t.risk_level.value == "caution"]

        print(f"\nSAFE tools ({len(safe_tools)}):")
        for tool_meta in safe_tools:
            print(f"  - {tool_meta.name}")

        print(f"\nCAUTION tools ({len(caution_tools)}):")
        for tool_meta in caution_tools:
            print(f"  - {tool_meta.name}")

        print("\nCapabilities:")
        print("  ✓ All SAFE capabilities")
        print("  ✓ Create, edit, delete files")
        print("  ✓ Execute shell commands")

        print("\nUse cases:")
        print("  - Code generation and refactoring")
        print("  - Automated development tasks")
        print("  - File organization and processing")

        print("\n⚠️  Security notes:")
        print("  - Review AI-generated code before execution")
        print("  - Use version control (git) for safety")
        print("  - Consider sandboxed environments for untrusted code")


def example_graduated_trust():
    """Demonstrate graduated trust levels."""
    print("\n" + "=" * 60)
    print("Example 3: Graduated Trust Levels")
    print("=" * 60)

    scenarios = [
        ("Untrusted source", "safe", "Read-only access only"),
        ("Known AI, untested", "safe", "Safe exploration first"),
        ("Trusted AI, supervised", "caution", "File ops with review"),
        (
            "Fully trusted + version control",
            "caution",
            "Full capabilities with git safety net",
        ),
    ]

    print("\nTrust-based tool selection:\n")
    for scenario, risk_level, description in scenarios:
        print(f"{scenario:30s} → tools='{risk_level:8s}' ({description})")

    print("\nProgressive trust example:")
    print("  1. Start with tools='safe' for new AI interactions")
    print("  2. Evaluate AI behavior and accuracy")
    print("  3. Upgrade to tools='caution' if results are good")
    print("  4. Always use version control as a safety net")


def example_minimal_privilege():
    """Principle of least privilege: Only grant needed tools."""
    print("\n" + "=" * 60)
    print("Example 4: Minimal Privilege (Only What's Needed)")
    print("=" * 60)

    # Scenario: AI needs to search code and create a report file
    console = Consoul(
        model="llama",
        tools=["grep", "code_search", "create_file"],  # Only exactly what's needed
        persist=False,
    )

    print("Scenario: Generate code analysis report")
    print("Required capabilities:")
    print("  - Search code (grep, code_search)")
    print("  - Create report file (create_file)")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nMinimal toolset ({len(tools)} tools):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")

        print("\n✓ Principle of least privilege:")
        print("  - Only grant necessary capabilities")
        print("  - Reduces attack surface")
        print("  - Limits potential damage from errors")
        print("  - Easier to audit AI actions")


def example_safe_with_specific_operations():
    """Search tools + specific file operation."""
    print("\n" + "=" * 60)
    print("Example 5: Specific Safe Tools + File Creation")
    print("=" * 60)

    # Search category + only file creation (not all file operations)
    console = Consoul(
        model="llama",
        tools=["search", "create_file"],  # All search tools + only file creation
        persist=False,
    )

    if console.registry:
        tools = console.registry.list_tools()

        safe_tools = [t for t in tools if t.risk_level.value == "safe"]
        caution_tools = [t for t in tools if t.risk_level.value == "caution"]

        print(f"\nSearch category ({len(safe_tools)} tools) + specific file operation:")
        print(f"  SAFE: {len(safe_tools)} tools (search category)")
        print(
            f"  CAUTION: {len(caution_tools)} tools (only: {', '.join(t.name for t in caution_tools)})"
        )

        print("\nUse case:")
        print("  - AI can search and analyze code (search category)")
        print("  - AI can create report files (specific permission)")
        print("  - AI cannot edit or delete files (not granted)")


def example_category_security():
    """Category-based security controls."""
    print("\n" + "=" * 60)
    print("Example 6: Category-Based Security")
    print("=" * 60)

    print("Categories with different security profiles:\n")

    categories = [
        ("search", "SAFE", "Read-only code exploration"),
        ("web", "SAFE", "Read-only web access"),
        ("file-edit", "CAUTION", "File modifications"),
        ("execute", "CAUTION", "Command execution"),
    ]

    for category, level, description in categories:
        print(f"  {category:12s} ({level:7s}) - {description}")

    print("\nSafe categories combination:")
    console = Consoul(model="llama", tools=["search", "web"], persist=False)

    if console.registry:
        tools = console.registry.list_tools()
        print(f"  tools=['search', 'web'] → {len(tools)} SAFE tools")

    print("\nCaution categories combination:")
    console = Consoul(model="llama", tools=["search", "file-edit"], persist=False)

    if console.registry:
        tools = console.registry.list_tools()
        safe_count = sum(1 for t in tools if t.risk_level.value == "safe")
        caution_count = sum(1 for t in tools if t.risk_level.value == "caution")
        print(
            f"  tools=['search', 'file-edit'] → {safe_count} SAFE + {caution_count} CAUTION tools"
        )


def example_discovered_tools_security():
    """Security considerations for discovered tools."""
    print("\n" + "=" * 60)
    print("Example 7: Discovered Tools Security")
    print("=" * 60)

    print("Important security notes for tool discovery:\n")

    print("1. Default Risk Level:")
    print("   - All discovered tools → RiskLevel.CAUTION")
    print("   - Assumption: Custom tools may modify state")
    print("   - Review custom tools before enabling discovery")

    print("\n2. Discovery Best Practices:")
    print("   - Review all .consoul/tools/ files before enabling discovery")
    print("   - Use version control for .consoul/tools/ directory")
    print("   - Don't enable discovery for untrusted codebases")
    print("   - Consider explicit tool lists instead of discovery")

    print("\n3. Combining Discovery with Filtering:")
    print("   Example: Discover custom tools + only safe built-in tools")
    print("   ```python")
    print("   Consoul(")
    print("       tools='safe',         # Only safe built-in tools")
    print("       discover_tools=True   # Plus custom tools (CAUTION level)")
    print("   )")
    print("   ```")

    print("\n4. Audit Trail:")
    print("   - Enable logging to track tool usage")
    print("   - Review AI actions in version control")
    print("   - Monitor file changes and command execution")


def main():
    """Run all security examples."""
    print("\n" + "=" * 60)
    print("SECURITY AND RISK LEVEL EXAMPLES")
    print("=" * 60)
    print("\nThis example demonstrates security best practices for tool specification.")

    try:
        # Run each example
        example_safe_tools_only()
        example_caution_tools()
        example_graduated_trust()
        example_minimal_privilege()
        example_safe_with_specific_operations()
        example_category_security()
        example_discovered_tools_security()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print("\nSecurity Best Practices Summary:")
        print("\n1. Start Safe:")
        print("   - Begin with tools='safe' for new interactions")
        print("   - Upgrade to 'caution' only when needed")

        print("\n2. Principle of Least Privilege:")
        print("   - Only grant necessary capabilities")
        print("   - Use specific tool lists instead of 'all'")

        print("\n3. Risk Awareness:")
        print("   - SAFE: Read-only, no system changes")
        print("   - CAUTION: File operations, command execution")
        print("   - Review AI actions before executing")

        print("\n4. Safety Nets:")
        print("   - Always use version control (git)")
        print("   - Test in sandboxed environments")
        print("   - Enable audit logging")
        print("   - Review generated code")

        print("\n5. Graduated Trust:")
        print("   - Evaluate AI behavior over time")
        print("   - Increase permissions gradually")
        print("   - Monitor for unexpected actions")

        print("\n6. Discovery Security:")
        print("   - Review custom tools before enabling discovery")
        print("   - Discovered tools default to CAUTION level")
        print("   - Consider explicit lists for sensitive projects")

        print("\nSee docs/sdk-tools.md for complete documentation.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()

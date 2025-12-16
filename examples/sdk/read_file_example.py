#!/usr/bin/env python3
"""read_file Tool SDK Example - File reading with security controls.

Demonstrates how to use the read_file tool with custom configuration,
security policies, and integration with AI models.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/read_file_example.py

Requirements:
    pip install consoul
    pip install consoul[pdf]  # Optional: for PDF support
"""

from consoul.ai.tools import RiskLevel, ToolRegistry
from consoul.ai.tools.implementations import read_file, set_read_config
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config.loader import load_config
from consoul.config.models import ReadToolConfig


def basic_example():
    """Basic read_file usage with configuration from profile."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Load configuration from profile
    config = load_config()

    # Inject read config from profile (IMPORTANT: do this before registration)
    # This ensures tool respects limits defined in your YAML config
    if config.tools.read:
        set_read_config(config.tools.read)

    # Create registry with CLI approval
    registry = ToolRegistry(
        config=config.tools, approval_provider=CliApprovalProvider(verbose=True)
    )

    # Register read_file as SAFE (no approval needed)
    registry.register(
        read_file, risk_level=RiskLevel.SAFE, tags=["filesystem", "readonly"]
    )

    # Use with LangChain model
    from langchain_anthropic import ChatAnthropic

    model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    model_with_tools = registry.bind_to_model(model)

    # AI can now read files
    print("\nAsking AI to read pyproject.toml...\n")
    response = model_with_tools.invoke(
        "Read the pyproject.toml file and tell me the project name"
    )
    print(f"Response: {response.content}\n")


def custom_config_example():
    """Using custom ReadToolConfig for fine-grained control."""
    print("=" * 60)
    print("Example 2: Custom Configuration")
    print("=" * 60)

    # Create custom configuration
    from pathlib import Path

    read_config = ReadToolConfig(
        max_lines_default=500,  # Limit to 500 lines
        max_line_length=1000,  # Truncate long lines
        max_output_chars=20000,  # Cap total output
        allowed_extensions=[".py", ".md", ".txt", ".json"],  # Whitelist
        blocked_paths=[
            "/etc",
            "/proc",
            "/sys",
            str(Path.home() / ".ssh"),
        ],  # Blacklist
        enable_pdf=False,  # Disable PDF support
    )

    # Inject configuration before registration
    set_read_config(read_config)

    config = load_config()
    registry = ToolRegistry(
        config=config.tools, approval_provider=CliApprovalProvider()
    )
    registry.register(read_file, risk_level=RiskLevel.SAFE)

    print("\nConfiguration applied:")
    print(f"  Max lines: {read_config.max_lines_default}")
    print(f"  Max line length: {read_config.max_line_length}")
    print(f"  Max output: {read_config.max_output_chars}")
    print(f"  Allowed extensions: {read_config.allowed_extensions}")
    print(f"  PDF support: {read_config.enable_pdf}\n")


def pdf_example():
    """Reading PDF files (requires pypdf)."""
    print("=" * 60)
    print("Example 3: PDF Support")
    print("=" * 60)

    try:
        import pypdf  # noqa: F401

        # Configure with PDF support
        read_config = ReadToolConfig(
            enable_pdf=True,
            pdf_max_pages=10,  # Limit to 10 pages
            allowed_extensions=[".pdf", ".txt", ".md"],
        )
        set_read_config(read_config)

        config = load_config()
        registry = ToolRegistry(
            config=config.tools, approval_provider=CliApprovalProvider()
        )
        registry.register(read_file, risk_level=RiskLevel.SAFE)

        print("\nPDF support enabled:")
        print(f"  Max pages: {read_config.pdf_max_pages}")
        print(
            "  AI can now read PDF files with: read_file(file_path='doc.pdf', start_page=1, end_page=5)\n"
        )

    except ImportError:
        print("\n⚠️  pypdf not installed. Install with: pip install consoul[pdf]\n")


def headless_example():
    """Headless/automated usage with policy-based approval."""
    print("=" * 60)
    print("Example 4: Headless Usage")
    print("=" * 60)

    from consoul.ai.tools.permissions import PermissionPolicy
    from consoul.config.models import ToolConfig

    # Use TRUSTING policy for headless environments
    # (auto-approves SAFE and CAUTION tools)
    tool_config = ToolConfig(
        enabled=True,
        permission_policy=PermissionPolicy.TRUSTING,
        audit_logging=True,  # Keep audit trail
    )

    registry = ToolRegistry(config=tool_config, approval_provider=CliApprovalProvider())

    # read_file is SAFE, so it will auto-approve with TRUSTING policy
    registry.register(
        read_file, risk_level=RiskLevel.SAFE, tags=["filesystem", "readonly"]
    )

    print("\nHeadless configuration:")
    print(f"  Policy: {tool_config.permission_policy}")
    print(f"  Audit logging: {tool_config.audit_logging}")
    print("  read_file (SAFE) will auto-approve without user prompt\n")


def direct_tool_usage():
    """Direct tool invocation without AI model."""
    print("=" * 60)
    print("Example 5: Direct Tool Usage")
    print("=" * 60)

    # Configure tool
    read_config = ReadToolConfig(max_lines_default=10)
    set_read_config(read_config)

    # Use tool directly
    result = read_file.invoke({"file_path": "pyproject.toml", "offset": 1, "limit": 5})

    print("\nDirect invocation result:")
    print(result)
    print()


def main():
    """Run all examples."""
    import sys

    examples = {
        "1": ("Basic Usage", basic_example),
        "2": ("Custom Configuration", custom_config_example),
        "3": ("PDF Support", pdf_example),
        "4": ("Headless Usage", headless_example),
        "5": ("Direct Tool Usage", direct_tool_usage),
    }

    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice in examples:
            _, func = examples[choice]
            func()
        else:
            print(f"Invalid example number. Choose from: {', '.join(examples.keys())}")
    else:
        # Run all examples
        for _, func in examples.values():
            func()
            print()


if __name__ == "__main__":
    main()

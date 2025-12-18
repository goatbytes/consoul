#!/usr/bin/env python3
"""Domain-Specific SDK Usage - Profile-Free Examples

Demonstrates how to use Consoul SDK for non-coding domains using
explicit parameters instead of profiles. Perfect for legal AI, medical
chatbots, customer support, and other specialized applications.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/domain_specific.py

Requirements:
    pip install consoul

See Also:
    - docs/api/integration-guide.md#domain-specific-context-customization
    - docs/api/integration-guide.md#migration-from-profiles
"""

from consoul import Consoul
from consoul.ai.prompt_builder import build_enhanced_system_prompt


def legal_ai_example():
    """Legal AI assistant for workers' compensation cases."""
    print("=" * 70)
    print("LEGAL AI - Workers' Compensation Assistant")
    print("=" * 70)
    print()

    # Build custom prompt with domain-specific context
    legal_prompt = build_enhanced_system_prompt(
        "You are a workers' compensation legal assistant for California law. "
        "Provide accurate legal guidance based on case precedents and statutes.",
        context_sections={
            "jurisdiction": "California workers' compensation law",
            "recent_precedents": (
                "2024 Key Cases:\n"
                "- Johnson v. ABC Corp: Extended coverage for remote workers\n"
                "- Smith v. Manufacturing Inc: Repetitive stress injuries covered"
            ),
            "practice_area": "Construction industry injury claims",
        },
        include_os_info=False,  # No environment noise
        include_git_info=False,  # No git context
        include_datetime_info=True,  # Timestamp for legal records
        auto_append_tools=False,  # Chat-only mode
    )

    # Create legal AI console
    legal_assistant = Consoul(
        model="gpt-4o",  # Or claude-sonnet-4
        temperature=0.3,  # Low temperature for factual accuracy
        system_prompt=legal_prompt,
        tools=False,  # No code execution tools needed
        persist=True,
        db_path="~/legal-ai/history.db",  # Separate database
        service_tier="flex",  # OpenAI cost optimization
    )

    # Example legal query
    query = "What are the key factors in proving a construction injury claim?"
    response = legal_assistant.chat(query)
    print(f"Query: {query}")
    print(f"\nResponse:\n{response}")
    print()


def medical_chatbot_example():
    """Medical assistant chatbot with patient context."""
    print("=" * 70)
    print("MEDICAL AI - Patient Care Assistant")
    print("=" * 70)
    print()

    # Build medical prompt with patient context
    medical_prompt = build_enhanced_system_prompt(
        "You are a medical assistant providing patient care guidance. "
        "Always prioritize patient safety and recommend consulting healthcare "
        "professionals for serious concerns.",
        context_sections={
            "patient_demographics": "Age: 45, Gender: M, Weight: 180lbs",
            "medical_history": (
                "- Hypertension (diagnosed 2020)\n"
                "- Type 2 Diabetes (diagnosed 2022)\n"
                "- No known drug allergies"
            ),
            "current_medications": (
                "- Metformin 500mg BID\n- Lisinopril 10mg QD\n- Aspirin 81mg QD"
            ),
            "recent_vitals": "BP: 128/82, HR: 72, Temp: 98.6°F",
        },
        include_datetime_info=True,  # Timestamp for medical records
        auto_append_tools=False,
    )

    # Create medical chatbot
    medical_bot = Consoul(
        model="claude-sonnet-4",
        temperature=0.4,  # Balanced for medical accuracy
        system_prompt=medical_prompt,
        tools=False,
        persist=True,
        summarize=True,  # Auto-summarize long consultations
        summarize_threshold=15,
        keep_recent=8,
        summary_model="gpt-4o-mini",  # Cheaper model for summaries
    )

    # Example medical query
    query = "Should I be concerned about occasional dizziness?"
    response = medical_bot.chat(query)
    print(f"Query: {query}")
    print(f"\nResponse:\n{response}")
    print()


def customer_support_example():
    """Customer support bot with product context."""
    print("=" * 70)
    print("CUSTOMER SUPPORT - Enterprise Software")
    print("=" * 70)
    print()

    # Build support prompt with product context
    support_prompt = build_enhanced_system_prompt(
        "You are a customer support agent for TechCorp Enterprise Software Suite. "
        "Provide helpful, friendly support with step-by-step troubleshooting.",
        context_sections={
            "customer_tier": "Premium (24/7 support)",
            "product_line": "Enterprise Software Suite v3.2",
            "account_status": "Active since 2022, 50 user licenses",
            "common_issues": (
                "1. License activation errors\n"
                "2. SSO integration with Azure AD\n"
                "3. API rate limiting (1000 req/min default)\n"
                "4. Database connection timeouts"
            ),
            "recent_tickets": "None open (last ticket closed 30 days ago)",
        },
        include_os_info=False,
        auto_append_tools=False,
    )

    # Create support bot with web search tools
    support_bot = Consoul(
        model="gpt-4o",
        temperature=0.5,
        system_prompt=support_prompt,
        tools=["web_search", "read_url"],  # Only specific tools needed
        persist=False,  # Don't save support conversations
    )

    # Example support query
    query = "We're getting 'Connection timeout' errors when connecting to the database."
    response = support_bot.chat(query)
    print(f"Query: {query}")
    print(f"\nResponse:\n{response}")
    print()


def research_assistant_example():
    """Academic research assistant."""
    print("=" * 70)
    print("RESEARCH AI - Academic Literature Assistant")
    print("=" * 70)
    print()

    # Simple research assistant (no complex context needed)
    research_bot = Consoul(
        model="claude-sonnet-4",
        temperature=0.6,
        system_prompt=(
            "You are an academic research assistant specializing in computer science. "
            "Help researchers find relevant papers, summarize findings, and suggest "
            "research directions. Cite sources when possible."
        ),
        tools=["web_search", "read_url"],  # Enable web research
        persist=True,
        db_path="~/research/history.db",
    )

    # Example research query
    query = "What are the latest advances in transformer architecture optimization?"
    response = research_bot.chat(query)
    print(f"Query: {query}")
    print(f"\nResponse:\n{response}")
    print()


def main():
    """Run all domain-specific examples."""
    print("\n" + "=" * 70)
    print("DOMAIN-SPECIFIC SDK EXAMPLES")
    print("Profile-free Consoul usage for various domains")
    print("=" * 70)
    print()

    # Run examples (comment out as needed)
    legal_ai_example()
    medical_chatbot_example()
    customer_support_example()
    research_assistant_example()

    print("=" * 70)
    print("KEY TAKEAWAYS")
    print("=" * 70)
    print("""
✓ No profiles needed - explicit parameters only
✓ Domain-specific system prompts replace coding defaults
✓ Custom context sections for specialized knowledge
✓ Granular control over environment context
✓ Selective tool usage (or none for chat-only)
✓ Separate databases per application/domain
✓ Cost optimization (service_tier, summary_model)

For more details:
- docs/api/integration-guide.md#domain-specific-context-customization
- docs/api/integration-guide.md#migration-from-profiles
""")


if __name__ == "__main__":
    main()

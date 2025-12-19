#!/usr/bin/env python3
"""CRM Context Provider - Customer Support Example.

Demonstrates dynamic context injection for customer support chatbots using the
ContextProvider protocol. This example simulates a support bot that retrieves
customer information from a CRM system to provide personalized assistance.

Usage:
    export OPENAI_API_KEY=your-key-here
    python examples/sdk/context_providers/crm_context_provider.py

Requirements:
    pip install consoul

See Also:
    - consoul.sdk.protocols.ContextProvider: Protocol definition
    - docs/guides/context-providers.md: Full guide
"""

from __future__ import annotations

from datetime import datetime


class MockCRMSystem:
    """Simulated CRM system for customer support.

    In production, this would connect to Salesforce, HubSpot, Zendesk,
    or a custom CRM database.
    """

    def __init__(self):
        # Simulated customer database
        self.customers = {
            "CUST-9876": {
                "name": "Acme Corporation",
                "tier": "Enterprise",
                "status": "Active",
                "account_since": "2022-01-15",
                "licenses": 50,
                "product": "Enterprise Software Suite v3.2",
                "contact_email": "support@acme-corp.example",
                "support_plan": "24/7 Premium Support",
                "recent_tickets": [
                    {
                        "id": "TICK-1234",
                        "subject": "SSO integration with Azure AD",
                        "status": "Closed",
                        "created": "2024-11-15",
                        "resolved": "2024-11-16",
                        "category": "Integration",
                    },
                    {
                        "id": "TICK-1189",
                        "subject": "API rate limiting questions",
                        "status": "Closed",
                        "created": "2024-10-20",
                        "resolved": "2024-10-20",
                        "category": "API",
                    },
                ],
                "product_usage": {
                    "api_calls_month": 245000,
                    "api_limit": 1000000,
                    "active_users": 47,
                    "license_utilization": 0.94,
                },
                "known_integrations": ["Azure AD", "Slack", "GitHub"],
            },
            "CUST-5432": {
                "name": "StartupTech Inc",
                "tier": "Professional",
                "status": "Active",
                "account_since": "2023-06-01",
                "licenses": 10,
                "product": "Professional Suite v3.0",
                "contact_email": "tech@startuptech.example",
                "support_plan": "Business Hours Support",
                "recent_tickets": [],
                "product_usage": {
                    "api_calls_month": 15000,
                    "api_limit": 100000,
                    "active_users": 8,
                    "license_utilization": 0.80,
                },
                "known_integrations": ["Google Workspace"],
            },
        }

    def get_customer(self, customer_id: str) -> dict | None:
        """Retrieve customer record from CRM.

        Args:
            customer_id: Customer identifier

        Returns:
            Customer data dictionary or None if not found
        """
        return self.customers.get(customer_id)


class CRMContextProvider:
    """Context provider for customer support chatbot with CRM integration.

    Implements the ContextProvider protocol to inject customer-specific
    information into AI system prompts, enabling personalized and
    contextually-aware customer support.

    Example:
        >>> from consoul import Consoul
        >>> crm = MockCRMSystem()
        >>> provider = CRMContextProvider("CUST-9876", crm)
        >>> console = Consoul(
        ...     model="gpt-4o",
        ...     system_prompt="You are a customer support agent...",
        ...     context_providers=[provider],
        ...     tools=["web_search", "read_url"]
        ... )
        >>> response = console.chat("We're having database connection issues.")
    """

    def __init__(self, customer_id: str, crm_system: MockCRMSystem):
        """Initialize CRM context provider.

        Args:
            customer_id: Customer identifier for CRM lookup
            crm_system: CRM system instance
        """
        self.customer_id = customer_id
        self.crm = crm_system

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        """Get customer context from CRM.

        Called by Consoul SDK before building system prompts. Retrieves
        customer account information, support history, product usage, and
        known integrations to provide personalized support.

        Args:
            query: User's current question (enables query-specific context)
            conversation_id: Conversation identifier (for session tracking)

        Returns:
            Dictionary mapping context section names to content strings:
            - customer_account: Account tier, status, and product info
            - support_history: Recent support tickets and resolutions
            - product_usage: API usage, license utilization, active users
            - integrations: Known third-party integrations
            - support_sla: Support plan and response time guarantees
        """
        # Retrieve customer data from CRM
        customer = self.crm.get_customer(self.customer_id)

        if not customer:
            return {
                "error": f"Customer {self.customer_id} not found in CRM",
                "support_notice": (
                    "Please provide your customer ID for personalized support."
                ),
            }

        # Format account information
        account_info = (
            f"**{customer['name']}** ({self.customer_id})\\n"
            f"Tier: {customer['tier']} | Status: {customer['status']}\\n"
            f"Product: {customer['product']}\\n"
            f"Licenses: {customer['licenses']} ({customer['product_usage']['active_users']} active users)\\n"
            f"Customer Since: {customer['account_since']}"
        )

        # Format support history
        recent_tickets = customer["recent_tickets"]
        if recent_tickets:
            ticket_lines = []
            for ticket in recent_tickets[:5]:  # Last 5 tickets
                status_emoji = "✅" if ticket["status"] == "Closed" else "🔄"
                ticket_lines.append(
                    f"{status_emoji} {ticket['id']}: {ticket['subject']} "
                    f"({ticket['category']}, {ticket['status']})"
                )
            support_history = "\n".join(ticket_lines)
        else:
            support_history = "No recent support tickets (excellent!)"

        # Format product usage
        usage = customer["product_usage"]
        usage_percent = (usage["api_calls_month"] / usage["api_limit"]) * 100
        license_percent = usage["license_utilization"] * 100

        product_usage = (
            f"API Usage: {usage['api_calls_month']:,} / {usage['api_limit']:,} "
            f"calls this month ({usage_percent:.1f}%)\\n"
            f"License Utilization: {usage['active_users']} / {customer['licenses']} "
            f"users ({license_percent:.0f}%)"
        )

        # Format integrations
        integrations_str = ", ".join(customer["known_integrations"])

        # Support SLA based on tier
        if customer["tier"] == "Enterprise":
            sla = "24/7 Premium Support - 1 hour response time for critical issues"
        elif customer["tier"] == "Professional":
            sla = "Business Hours Support - 4 hour response time"
        else:
            sla = "Standard Support - 24 hour response time"

        return {
            "customer_account": account_info,
            "support_history": support_history,
            "product_usage": product_usage,
            "known_integrations": integrations_str,
            "support_sla": sla,
            "support_plan": customer["support_plan"],
            "session_info": f"Session ID: {conversation_id or 'N/A'}, "
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        }


def main():
    """Demonstrate customer support AI with CRM context injection."""
    print("=" * 80)
    print("CUSTOMER SUPPORT AI - Enterprise Support with ContextProvider")
    print("=" * 80)
    print()

    # Initialize CRM system
    crm_system = MockCRMSystem()

    # Create CRM context provider for a customer
    crm_provider = CRMContextProvider("CUST-9876", crm_system)

    # Create Consoul instance with context provider
    from consoul import Consoul

    support_bot = Consoul(
        model="gpt-4o",
        temperature=0.5,  # Balanced for helpful and friendly responses
        system_prompt=(
            "You are a customer support agent for TechCorp Enterprise Software Suite. "
            "Provide helpful, friendly support with step-by-step troubleshooting. "
            "Use the customer context provided to personalize your responses. "
            "Prioritize quick resolution and customer satisfaction."
        ),
        context_providers=[crm_provider],  # Dynamic customer context
        tools=["web_search", "read_url"],  # Enable web research for solutions
        persist=False,  # Don't save support conversations
    )

    # Example support queries
    queries = [
        "We're getting 'Connection timeout' errors when connecting to the database.",
        "How do we increase our API rate limit? We're approaching the threshold.",
        "Can you help us set up a new SSO integration with Okta?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"Support Ticket {i}: {query}")
        print("-" * 80)

        # Each query has customer context automatically injected
        response = support_bot.chat(query)

        print(f"Agent Response:\n{response}\n")
        print("=" * 80)
        print()

    # Show what context was injected
    print("CUSTOMER CONTEXT INJECTED:")
    print("-" * 80)
    context = crm_provider.get_context()
    for key, value in context.items():
        if key != "session_info":  # Skip session info for brevity
            print(f"\n{key.upper().replace('_', ' ')}:")
            print(value)
    print()

    print("=" * 80)
    print("KEY FEATURES DEMONSTRATED:")
    print("=" * 80)
    print("""
✓ Customer-specific context from CRM system
✓ Account tier and product information
✓ Support history for pattern recognition
✓ Product usage metrics for proactive support
✓ Known integrations for compatibility advice
✓ SLA awareness for priority handling
✓ Web search tools for finding solutions

PRODUCTION ENHANCEMENTS:
- Real-time ticket creation/updates
- Automatic escalation based on tier/SLA
- Sentiment analysis for customer satisfaction
- Integration with knowledge base
- Multi-language support
- Automated follow-up scheduling
""")


if __name__ == "__main__":
    main()

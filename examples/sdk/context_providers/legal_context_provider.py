#!/usr/bin/env python3
"""Legal AI Context Provider - Workers' Compensation Example.

Demonstrates dynamic context injection for legal AI using the ContextProvider protocol.
This example simulates a workers' compensation legal assistant that queries a case law
database to provide relevant precedents based on user queries.

Usage:
    export OPENAI_API_KEY=your-key-here
    python examples/sdk/context_providers/legal_context_provider.py

Requirements:
    pip install consoul

See Also:
    - consoul.sdk.protocols.ContextProvider: Protocol definition
    - docs/guides/context-providers.md: Full guide
"""

from __future__ import annotations

from datetime import datetime


class MockCaseLawDatabase:
    """Simulated case law database for demonstration purposes.

    In production, this would connect to a real legal database like
    Westlaw, LexisNexis, or a custom case law repository.
    """

    def __init__(self):
        self.cases = {
            "construction": [
                {
                    "name": "Johnson v. ABC Construction",
                    "year": 2024,
                    "citation": "Cal. App. 5th 123",
                    "holding": "Extended workers' comp coverage to include remote "
                    "workers injured while working from construction site trailers.",
                    "relevance": "construction workers, remote work, site injuries",
                },
                {
                    "name": "Martinez v. BuildCo Inc.",
                    "year": 2023,
                    "citation": "Cal. App. 4th 456",
                    "holding": "Established that repetitive stress injuries from "
                    "construction equipment operation qualify for compensation.",
                    "relevance": "construction, repetitive stress, equipment operation",
                },
            ],
            "medical": [
                {
                    "name": "Smith v. County Hospital",
                    "year": 2024,
                    "citation": "Cal. App. 5th 789",
                    "holding": "Healthcare workers exposed to infectious diseases "
                    "during patient care are covered under workers' comp.",
                    "relevance": "healthcare, infectious disease, patient care",
                },
            ],
            "manufacturing": [
                {
                    "name": "Davis v. TechManufacturing LLC",
                    "year": 2023,
                    "citation": "Cal. App. 4th 321",
                    "holding": "Carpal tunnel syndrome from assembly line work "
                    "qualifies as work-related injury.",
                    "relevance": "manufacturing, repetitive motion, carpal tunnel",
                },
            ],
        }

    def search_cases(
        self, query: str | None, jurisdiction: str
    ) -> list[dict[str, str]]:
        """Search cases relevant to the query.

        Args:
            query: User's legal question or None for general context
            jurisdiction: Legal jurisdiction (e.g., "California")

        Returns:
            List of relevant case dictionaries
        """
        if not query:
            # Return general recent cases
            all_cases = []
            for category_cases in self.cases.values():
                all_cases.extend(category_cases)
            return sorted(all_cases, key=lambda c: c["year"], reverse=True)[:3]

        # Simple keyword matching (production would use semantic search)
        query_lower = query.lower()
        relevant = []

        for _category, category_cases in self.cases.items():
            for case in category_cases:
                # Check if query keywords match case relevance or holding
                if any(
                    keyword in query_lower for keyword in case["relevance"].split(", ")
                ) or any(
                    word in case["holding"].lower()
                    for word in query_lower.split()
                    if len(word) > 4
                ):
                    relevant.append(case)

        return relevant[:5]  # Return top 5 matches


class LegalContextProvider:
    """Context provider for workers' compensation legal AI.

    Implements the ContextProvider protocol to inject jurisdiction-specific
    legal context and relevant case law into AI system prompts.

    This enables the AI to provide legally-informed responses based on
    actual case precedents and jurisdiction-specific rules.

    Example:
        >>> from consoul import Consoul
        >>> db = MockCaseLawDatabase()
        >>> provider = LegalContextProvider("California", db)
        >>> console = Consoul(
        ...     model="gpt-4o",
        ...     system_prompt="You are a workers' compensation legal assistant.",
        ...     context_providers=[provider],
        ...     tools=False
        ... )
        >>> response = console.chat("What are the rules for construction injuries?")
    """

    def __init__(self, jurisdiction: str, case_database: MockCaseLawDatabase):
        """Initialize legal context provider.

        Args:
            jurisdiction: Legal jurisdiction (e.g., "California", "New York")
            case_database: Case law database instance
        """
        self.jurisdiction = jurisdiction
        self.db = case_database

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        """Get jurisdiction and case law context.

        Called by Consoul SDK before building system prompts. Searches the
        case law database for cases relevant to the query and formats them
        for injection into the AI's context.

        Args:
            query: User's current question (enables query-aware context)
            conversation_id: Conversation identifier (for stateful providers)

        Returns:
            Dictionary mapping context section names to content strings:
            - jurisdiction: Jurisdiction and practice area
            - relevant_cases: Formatted case precedents
            - legal_notice: Disclaimer about AI limitations
            - last_updated: Timestamp of context generation
        """
        # Search for relevant cases
        cases = self.db.search_cases(query, self.jurisdiction)

        # Format case law for prompt injection
        if cases:
            cases_formatted = "\n\n".join(
                f"**{case['name']}** ({case['year']})\\n"
                f"{case['citation']}\\n"
                f"Holding: {case['holding']}"
                for case in cases
            )
        else:
            cases_formatted = "No specific case precedents found for this query."

        return {
            "jurisdiction": f"{self.jurisdiction} Workers' Compensation Law",
            "relevant_cases": cases_formatted,
            "legal_notice": (
                "This AI provides general legal information only. "
                "Always consult with a licensed attorney for specific legal advice."
            ),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def main():
    """Demonstrate legal AI with dynamic context injection."""
    print("=" * 80)
    print("LEGAL AI - Workers' Compensation Assistant with ContextProvider")
    print("=" * 80)
    print()

    # Initialize case law database
    case_db = MockCaseLawDatabase()

    # Create legal context provider
    legal_provider = LegalContextProvider("California", case_db)

    # Create Consoul instance with context provider
    from consoul import Consoul

    legal_assistant = Consoul(
        model="gpt-4o",
        temperature=0.3,  # Low temperature for legal accuracy
        system_prompt=(
            "You are a workers' compensation legal assistant for California. "
            "Provide accurate guidance based on the case law and statutes "
            "provided in your context. Always cite relevant cases when applicable."
        ),
        context_providers=[legal_provider],  # Dynamic context injection
        tools=False,  # Chat-only mode
        persist=True,
        db_path="~/legal-ai/history.db",
        service_tier="flex",  # OpenAI cost optimization (~50% cheaper)
    )

    # Example queries demonstrating query-aware context
    queries = [
        "What are the key factors in proving a construction injury claim?",
        "Are healthcare workers covered for infectious disease exposure?",
        "How are repetitive stress injuries handled in manufacturing?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"Query {i}: {query}")
        print("-" * 80)

        # Each query gets fresh context based on the question
        response = legal_assistant.chat(query)

        print(f"Response:\n{response}\n")
        print("=" * 80)
        print()

    # Show what context was injected for the last query
    print("CONTEXT INJECTED FOR LAST QUERY:")
    print("-" * 80)
    context = legal_provider.get_context(queries[-1])
    for key, value in context.items():
        print(f"\n{key.upper().replace('_', ' ')}:")
        print(value)
    print()


if __name__ == "__main__":
    main()

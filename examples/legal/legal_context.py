#!/usr/bin/env python3
"""Legal AI Context Provider for Workers' Compensation Cases.

Provides dynamic context injection for legal AI applications, specifically
designed for workers' compensation attorneys in California. Integrates with
the Consoul SDK's ContextProvider protocol.

Features:
- Jurisdiction-specific legal context
- Case law database integration pattern
- Query-aware precedent retrieval
- Compliance disclaimers
- Attorney-client privilege notices

Usage:
    from consoul import Consoul
    from legal_context import LegalContextProvider, MockCaseLawDatabase

    db = MockCaseLawDatabase()
    provider = LegalContextProvider("California", db)

    console = Consoul(
        model="gpt-4o",
        context_providers=[provider],
        tools=["read", "grep"],
    )

    response = console.chat("What are the rules for construction injuries?")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CasePrecedent:
    """A legal case precedent from the database."""

    name: str
    year: int
    citation: str
    holding: str
    relevance: str
    jurisdiction: str = "California"
    practice_area: str = "workers_compensation"

    def format(self) -> str:
        """Format case for prompt injection."""
        return (
            f"**{self.name}** ({self.year})\n"
            f"Citation: {self.citation}\n"
            f"Holding: {self.holding}"
        )


class MockCaseLawDatabase:
    """Simulated case law database for demonstration.

    In production, this would connect to a real legal database such as:
    - Westlaw
    - LexisNexis
    - Fastcase
    - Google Scholar (free)
    - Custom case law repository

    The interface is designed to be easily replaceable with real implementations.
    """

    def __init__(self):
        """Initialize with sample workers' compensation cases."""
        self.cases: list[CasePrecedent] = [
            # Construction injuries
            CasePrecedent(
                name="Johnson v. ABC Construction",
                year=2024,
                citation="Cal. App. 5th 123",
                holding=(
                    "Extended workers' compensation coverage to include remote "
                    "workers injured while working from construction site trailers. "
                    "The court held that temporary work structures are covered "
                    "under the employment premises doctrine."
                ),
                relevance="construction, remote work, site injuries, premises",
            ),
            CasePrecedent(
                name="Martinez v. BuildCo Inc.",
                year=2023,
                citation="Cal. App. 4th 456",
                holding=(
                    "Established that repetitive stress injuries from "
                    "construction equipment operation qualify for compensation "
                    "when employer failed to provide ergonomic training."
                ),
                relevance="construction, repetitive stress, equipment, ergonomics",
            ),
            CasePrecedent(
                name="Williams v. Skyline Builders",
                year=2022,
                citation="Cal. App. 4th 789",
                holding=(
                    "Fall from scaffolding presumed work-related when employee "
                    "was performing assigned duties, even if specific task was "
                    "not explicitly authorized."
                ),
                relevance="construction, falls, scaffolding, scope of employment",
            ),
            # Healthcare injuries
            CasePrecedent(
                name="Smith v. County Hospital",
                year=2024,
                citation="Cal. App. 5th 789",
                holding=(
                    "Healthcare workers exposed to infectious diseases during "
                    "patient care are covered under workers' compensation. "
                    "COVID-19 presumption extended to all patient-facing staff."
                ),
                relevance="healthcare, infectious disease, patient care, COVID",
            ),
            CasePrecedent(
                name="Chen v. Valley Medical Center",
                year=2023,
                citation="Cal. App. 4th 234",
                holding=(
                    "Back injuries from lifting patients qualify for workers' "
                    "compensation even when proper lifting equipment was "
                    "available but not used due to emergency circumstances."
                ),
                relevance="healthcare, lifting injuries, back injuries, emergency",
            ),
            # Manufacturing injuries
            CasePrecedent(
                name="Davis v. TechManufacturing LLC",
                year=2023,
                citation="Cal. App. 4th 321",
                holding=(
                    "Carpal tunnel syndrome from assembly line work qualifies "
                    "as work-related injury when arising from job duties."
                ),
                relevance="manufacturing, repetitive motion, carpal tunnel, assembly",
            ),
            CasePrecedent(
                name="Garcia v. AutoParts Corp",
                year=2022,
                citation="Cal. App. 4th 567",
                holding=(
                    "Hearing loss from factory noise is compensable even when "
                    "employer provided hearing protection, if protection was "
                    "inadequate for actual noise levels."
                ),
                relevance="manufacturing, hearing loss, noise exposure, safety equipment",
            ),
            # Transportation injuries
            CasePrecedent(
                name="Brown v. Express Delivery",
                year=2024,
                citation="Cal. App. 5th 111",
                holding=(
                    "Delivery drivers injured during route deviations for "
                    "personal errands may still be covered if deviation was "
                    "minor and employee was returning to duties."
                ),
                relevance="transportation, delivery, coming and going, deviation",
            ),
            # Mental health claims
            CasePrecedent(
                name="Thompson v. Tech Solutions",
                year=2023,
                citation="Cal. App. 4th 888",
                holding=(
                    "PTSD from workplace violence is compensable as psychiatric "
                    "injury under Labor Code section 3208.3. Predominant cause "
                    "standard applies to claims after six months of employment."
                ),
                relevance="mental health, PTSD, workplace violence, psychiatric injury",
            ),
        ]

    def search_cases(
        self,
        query: str | None,
        jurisdiction: str = "California",
        practice_area: str = "workers_compensation",
        max_results: int = 5,
    ) -> list[CasePrecedent]:
        """Search cases relevant to the query.

        Args:
            query: User's legal question (enables semantic matching)
            jurisdiction: Filter by jurisdiction
            practice_area: Filter by practice area
            max_results: Maximum cases to return

        Returns:
            List of relevant CasePrecedent objects, sorted by relevance
        """
        if not query:
            # Return most recent cases
            return sorted(self.cases, key=lambda c: c.year, reverse=True)[:max_results]

        # Simple keyword matching (production would use semantic search)
        query_lower = query.lower()
        scored_cases: list[tuple[int, CasePrecedent]] = []

        for case in self.cases:
            if case.jurisdiction != jurisdiction:
                continue

            score = 0

            # Check relevance keywords
            relevance_keywords = case.relevance.split(", ")
            for keyword in relevance_keywords:
                if keyword in query_lower:
                    score += 3

            # Check holding text
            holding_words = case.holding.lower().split()
            query_words = [w for w in query_lower.split() if len(w) > 3]
            for word in query_words:
                if word in holding_words:
                    score += 1

            if score > 0:
                scored_cases.append((score, case))

        # Sort by score, then by year
        scored_cases.sort(key=lambda x: (-x[0], -x[1].year))

        return [case for _, case in scored_cases[:max_results]]

    def get_recent_cases(
        self,
        jurisdiction: str = "California",
        practice_area: str = "workers_compensation",
        since_year: int = 2022,
    ) -> list[CasePrecedent]:
        """Get recent cases for general context."""
        return [
            c
            for c in self.cases
            if c.jurisdiction == jurisdiction
            and c.practice_area == practice_area
            and c.year >= since_year
        ]


class LegalContextProvider:
    """Context provider for workers' compensation legal AI.

    Implements the ContextProvider protocol to inject jurisdiction-specific
    legal context and relevant case law into AI system prompts.

    This enables the AI to provide legally-informed responses based on
    actual case precedents and jurisdiction-specific rules.

    Attributes:
        jurisdiction: Legal jurisdiction (e.g., "California")
        practice_area: Area of law (e.g., "workers_compensation")
        db: Case law database instance
        include_disclaimers: Whether to include legal disclaimers
    """

    def __init__(
        self,
        jurisdiction: str = "California",
        case_database: MockCaseLawDatabase | None = None,
        practice_area: str = "workers_compensation",
        include_disclaimers: bool = True,
    ):
        """Initialize legal context provider.

        Args:
            jurisdiction: Legal jurisdiction
            case_database: Case law database (defaults to mock)
            practice_area: Legal practice area
            include_disclaimers: Include compliance disclaimers
        """
        self.jurisdiction = jurisdiction
        self.practice_area = practice_area
        self.db = case_database or MockCaseLawDatabase()
        self.include_disclaimers = include_disclaimers

    def get_context(
        self,
        query: str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, str]:
        """Get jurisdiction and case law context.

        Called by Consoul SDK before building system prompts. Searches the
        case law database for cases relevant to the query and formats them
        for injection into the AI's context.

        Args:
            query: User's current question (enables query-aware context)
            conversation_id: Conversation identifier (for stateful context)

        Returns:
            Dictionary mapping context section names to content:
            - jurisdiction_info: Jurisdiction and practice area
            - relevant_cases: Formatted case precedents
            - procedural_rules: Key procedural information
            - legal_notice: Disclaimers and limitations
            - timestamp: When context was generated
        """
        # Search for relevant cases
        cases = self.db.search_cases(
            query=query,
            jurisdiction=self.jurisdiction,
            practice_area=self.practice_area,
        )

        # Format case law for prompt injection
        if cases:
            cases_formatted = "\n\n".join(case.format() for case in cases)
            cases_section = f"RELEVANT CASE PRECEDENTS:\n\n{cases_formatted}"
        else:
            cases_section = (
                "No specific case precedents found for this query. "
                "Consider searching for related topics or consulting primary sources."
            )

        # Build context dictionary
        context: dict[str, str] = {
            "jurisdiction_info": self._get_jurisdiction_info(),
            "relevant_cases": cases_section,
            "procedural_rules": self._get_procedural_rules(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self.include_disclaimers:
            context["legal_notice"] = self._get_legal_notice()
            context["privilege_notice"] = self._get_privilege_notice()

        return context

    def _get_jurisdiction_info(self) -> str:
        """Get jurisdiction-specific information."""
        if (
            self.jurisdiction == "California"
            and self.practice_area == "workers_compensation"
        ):
            return """CALIFORNIA WORKERS' COMPENSATION LAW

Key Statutes:
- Labor Code Division 4 (Workers' Compensation and Insurance)
- Labor Code Division 4.5 (Workers' Compensation and Insurance: Alternative Dispute Resolution)
- California Code of Regulations, Title 8, Chapter 4.5

Key Agencies:
- Division of Workers' Compensation (DWC)
- Workers' Compensation Appeals Board (WCAB)
- Industrial Medical Council

Statute of Limitations:
- 1 year from date of injury for most claims
- 1 year from date of knowledge for cumulative trauma
- 5 years for death benefits claims"""

        return f"{self.jurisdiction} {self.practice_area.replace('_', ' ').title()} Law"

    def _get_procedural_rules(self) -> str:
        """Get key procedural information."""
        if self.jurisdiction == "California":
            return """CALIFORNIA WORKERS' COMP PROCEDURES

Filing Requirements:
1. DWC-1 (Workers' Compensation Claim Form) within 30 days of injury
2. Application for Adjudication if claim disputed
3. Proof of Service for all filings

Key Deadlines:
- Employer must provide claim form within 1 working day
- 90-day investigation period for employers
- 5-year limitation for petition to reopen

Benefit Types:
- Temporary Disability (TD) - up to 104 weeks
- Permanent Disability (PD) - based on impairment rating
- Medical Treatment - all reasonable and necessary care
- Vocational Rehabilitation - if applicable"""

        return "Consult local rules for procedural requirements."

    def _get_legal_notice(self) -> str:
        """Get legal disclaimer text."""
        return """IMPORTANT LEGAL NOTICE

This AI assistant provides general legal information only. It does NOT:
- Constitute legal advice
- Create an attorney-client relationship
- Replace consultation with a licensed attorney
- Guarantee any particular outcome

The information provided is based on case law and statutes that may be:
- Subject to change
- Inapplicable to specific circumstances
- Incomplete or simplified for general understanding

ALWAYS consult with a qualified workers' compensation attorney for:
- Specific legal advice about your case
- Filing deadlines and procedural requirements
- Strategy and settlement decisions
- Representation before the WCAB"""

    def _get_privilege_notice(self) -> str:
        """Get attorney-client privilege notice."""
        return """CONFIDENTIALITY NOTICE

Communications within this system may be subject to attorney-client privilege
and work product protection. Do not share:
- Client social security numbers
- Complete medical records without redaction
- Settlement authority or negotiation strategy
- Communications from opposing counsel

All interactions are logged for compliance purposes. Sensitive information
is automatically redacted from audit logs."""


def format_context_for_prompt(context: dict[str, str]) -> str:
    """Format context dictionary into a system prompt section.

    Args:
        context: Context dictionary from get_context()

    Returns:
        Formatted string for system prompt injection
    """
    sections = []

    if "jurisdiction_info" in context:
        sections.append(context["jurisdiction_info"])

    if "procedural_rules" in context:
        sections.append(context["procedural_rules"])

    if "relevant_cases" in context:
        sections.append(context["relevant_cases"])

    if "legal_notice" in context:
        sections.append(context["legal_notice"])

    if "privilege_notice" in context:
        sections.append(context["privilege_notice"])

    return "\n\n---\n\n".join(sections)


# ============================================================================
# Example Usage
# ============================================================================


def main():
    """Demonstrate legal context provider usage."""
    print("=" * 70)
    print("Legal AI Context Provider - Workers' Compensation Demo")
    print("=" * 70)
    print()

    # Initialize
    db = MockCaseLawDatabase()
    provider = LegalContextProvider("California", db)

    # Example queries
    queries = [
        "What are the rules for construction site injuries?",
        "Is carpal tunnel covered under workers' comp?",
        "How do I file a claim for workplace violence PTSD?",
        None,  # General context
    ]

    for query in queries:
        print("-" * 70)
        if query:
            print(f"QUERY: {query}")
        else:
            print("GENERAL CONTEXT (no query)")
        print("-" * 70)

        context = provider.get_context(query=query)

        print(f"\nTimestamp: {context['timestamp']}")
        print(f"\nRelevant Cases:\n{context['relevant_cases'][:500]}...")
        print()

    # Show full formatted context
    print("=" * 70)
    print("FULL FORMATTED CONTEXT (for system prompt)")
    print("=" * 70)
    context = provider.get_context(query="construction injury claim")
    formatted = format_context_for_prompt(context)
    print(formatted[:2000] + "..." if len(formatted) > 2000 else formatted)


if __name__ == "__main__":
    main()

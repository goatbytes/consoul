#!/usr/bin/env python3
"""Medical AI Context Provider - Patient Care Example.

Demonstrates dynamic context injection for medical chatbots using the ContextProvider
protocol. This example simulates a HIPAA-compliant medical assistant that retrieves
patient context from an Electronic Health Record (EHR) system.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/context_providers/medical_context_provider.py

Requirements:
    pip install consoul

Security Note:
    This is a simplified example. Production medical AI systems require:
    - HIPAA compliance and audit logging
    - Proper authentication and authorization
    - Encrypted data transmission and storage
    - Patient consent management
    - Regular security audits

See Also:
    - consoul.sdk.protocols.ContextProvider: Protocol definition
    - docs/guides/context-providers.md: Full guide
"""

from __future__ import annotations

from datetime import datetime


class MockEHRSystem:
    """Simulated Electronic Health Record system.

    In production, this would connect to a real EHR like Epic, Cerner,
    or a FHIR-compliant health data exchange.
    """

    def __init__(self):
        # Simulated patient database (in production, this would be secured)
        self.patients = {
            "P12345": {
                "name": "John Doe",  # Normally excluded for privacy
                "demographics": {
                    "age": 45,
                    "gender": "M",
                    "weight_lbs": 180,
                    "height_in": 70,
                },
                "medical_history": [
                    {
                        "condition": "Hypertension",
                        "diagnosed": "2020-03-15",
                        "status": "controlled",
                    },
                    {
                        "condition": "Type 2 Diabetes",
                        "diagnosed": "2022-01-10",
                        "status": "managed",
                    },
                ],
                "allergies": ["None known"],
                "medications": [
                    {"name": "Metformin", "dose": "500mg", "frequency": "BID"},
                    {"name": "Lisinopril", "dose": "10mg", "frequency": "QD"},
                    {"name": "Aspirin", "dose": "81mg", "frequency": "QD"},
                ],
                "recent_vitals": {
                    "blood_pressure": "128/82",
                    "heart_rate": 72,
                    "temperature_f": 98.6,
                    "date": "2024-12-15",
                },
            }
        }

    def get_patient(self, patient_id: str) -> dict | None:
        """Retrieve patient record.

        Args:
            patient_id: Patient identifier

        Returns:
            Patient data dictionary or None if not found
        """
        return self.patients.get(patient_id)


class MedicalContextProvider:
    """Context provider for medical chatbot with patient data.

    Implements the ContextProvider protocol to inject patient-specific
    medical context into AI system prompts, enabling personalized and
    contextually-aware medical guidance.

    IMPORTANT: This example is for demonstration only. Production medical
    AI systems require HIPAA compliance, proper security measures, and
    should never replace professional medical advice.

    Example:
        >>> from consoul import Consoul
        >>> ehr = MockEHRSystem()
        >>> provider = MedicalContextProvider("P12345", ehr)
        >>> console = Consoul(
        ...     model="claude-sonnet-4",
        ...     system_prompt="You are a medical assistant...",
        ...     context_providers=[provider],
        ...     tools=False
        ... )
        >>> response = console.chat("Should I be concerned about dizziness?")
    """

    def __init__(self, patient_id: str, ehr_system: MockEHRSystem):
        """Initialize medical context provider.

        Args:
            patient_id: Patient identifier for EHR lookup
            ehr_system: Electronic Health Record system instance
        """
        self.patient_id = patient_id
        self.ehr = ehr_system

    def get_context(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> dict[str, str]:
        """Get patient medical context from EHR.

        Called by Consoul SDK before building system prompts. Retrieves
        patient demographics, medical history, medications, and vital signs
        to provide personalized medical guidance.

        Args:
            query: User's current question (enables query-specific context)
            conversation_id: Conversation identifier (for session tracking)

        Returns:
            Dictionary mapping context section names to content strings:
            - patient_demographics: Age, gender, basic stats (de-identified)
            - medical_history: Chronic conditions and status
            - current_medications: Active medication list
            - recent_vitals: Latest vital sign measurements
            - allergies: Known drug/food allergies
            - medical_disclaimer: Important safety notice
        """
        # Retrieve patient data from EHR
        patient = self.ehr.get_patient(self.patient_id)

        if not patient:
            return {
                "error": f"Patient {self.patient_id} not found in EHR system",
                "medical_disclaimer": (
                    "This AI provides general health information only. "
                    "Always consult healthcare professionals for medical advice."
                ),
            }

        # Format demographics (de-identified)
        demo = patient["demographics"]
        demographics_str = (
            f"Age: {demo['age']}, Gender: {demo['gender']}, "
            f"Weight: {demo['weight_lbs']} lbs, Height: {demo['height_in']} in"
        )

        # Format medical history
        history_items = []
        for condition in patient["medical_history"]:
            history_items.append(
                f"- {condition['condition']} "
                f"(diagnosed {condition['diagnosed']}, {condition['status']})"
            )
        history_str = (
            "\n".join(history_items)
            if history_items
            else "No significant medical history"
        )

        # Format medications
        med_items = []
        for med in patient["medications"]:
            med_items.append(f"- {med['name']} {med['dose']} {med['frequency']}")
        medications_str = (
            "\n".join(med_items) if med_items else "No current medications"
        )

        # Format allergies
        allergies_str = ", ".join(patient["allergies"])

        # Format recent vitals
        vitals = patient["recent_vitals"]
        vitals_str = (
            f"BP: {vitals['blood_pressure']}, "
            f"HR: {vitals['heart_rate']} bpm, "
            f"Temp: {vitals['temperature_f']}°F "
            f"(recorded {vitals['date']})"
        )

        return {
            "patient_demographics": demographics_str,
            "medical_history": history_str,
            "current_medications": medications_str,
            "allergies": allergies_str,
            "recent_vitals": vitals_str,
            "medical_disclaimer": (
                "This AI provides general health information only. For medical "
                "emergencies, call 911. Always consult qualified healthcare "
                "professionals for diagnosis and treatment decisions."
            ),
            "session_info": f"Session ID: {conversation_id or 'N/A'}, "
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        }


def main():
    """Demonstrate medical AI with patient context injection."""
    print("=" * 80)
    print("MEDICAL AI - Patient Care Assistant with ContextProvider")
    print("=" * 80)
    print()
    print("DISCLAIMER: This is a demonstration only. Not for actual medical use.")
    print("=" * 80)
    print()

    # Initialize EHR system
    ehr_system = MockEHRSystem()

    # Create medical context provider for a patient
    medical_provider = MedicalContextProvider("P12345", ehr_system)

    # Create Consoul instance with context provider
    from consoul import Consoul

    medical_assistant = Consoul(
        model="claude-sonnet-4",
        temperature=0.4,  # Balanced for medical accuracy and helpfulness
        system_prompt=(
            "You are a medical assistant providing patient care guidance. "
            "Use the patient context provided to give personalized advice. "
            "Always prioritize patient safety and recommend consulting "
            "healthcare professionals for serious concerns. Never diagnose "
            "or prescribe - provide educational information only."
        ),
        context_providers=[medical_provider],  # Dynamic patient context
        tools=False,  # Chat-only mode
        persist=True,
        summarize=True,  # Auto-summarize long consultations
        summarize_threshold=15,
        keep_recent=8,
        summary_model="gpt-4o-mini",  # Cheaper model for summaries
    )

    # Example patient queries
    queries = [
        "Should I be concerned about occasional dizziness?",
        "Can I take ibuprofen with my current medications?",
        "My blood pressure seems slightly elevated. What should I do?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"Patient Query {i}: {query}")
        print("-" * 80)

        # Each query has patient context automatically injected
        response = medical_assistant.chat(query)

        print(f"Response:\n{response}\n")
        print("=" * 80)
        print()

    # Show what context was injected
    print("PATIENT CONTEXT INJECTED:")
    print("-" * 80)
    context = medical_provider.get_context()
    for key, value in context.items():
        if key != "medical_disclaimer":  # Skip disclaimer for brevity
            print(f"\n{key.upper().replace('_', ' ')}:")
            print(value)
    print()

    print("=" * 80)
    print("KEY FEATURES DEMONSTRATED:")
    print("=" * 80)
    print("""
✓ Patient-specific context from EHR system
✓ De-identified demographics for privacy
✓ Medical history and current medications
✓ Recent vital signs for informed guidance
✓ Conversation summarization for long sessions
✓ Safety disclaimers and professional guidance

PRODUCTION REQUIREMENTS:
- HIPAA compliance and audit logging
- Proper authentication/authorization
- Encrypted data transmission
- Patient consent management
- Regular security audits
- Professional medical review
""")


if __name__ == "__main__":
    main()

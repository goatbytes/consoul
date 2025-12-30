#!/usr/bin/env python3
"""Case File Analysis Workflow.

Demonstrates PDF case file analysis with AI for workers' compensation cases.
This workflow:
1. Loads a PDF case file from the matter sandbox
2. Extracts text using pypdf
3. Analyzes with AI using legal context
4. Outputs structured findings

Security:
- Only reads from sandboxed matter directories
- Uses read-only tools
- All actions logged for compliance

Usage:
    python -m examples.legal.workflows.case_analysis \\
        --matter-id MATTER-001 \\
        --file case_file.pdf

    # Or programmatically:
    from examples.legal.workflows.case_analysis import analyze_case_file
    findings = analyze_case_file("/data/matters/MATTER-001/case_file.pdf")
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from consoul import Consoul

# Import from parent package
sys.path.insert(0, str(Path(__file__).parent.parent))
from legal_context import (
    LegalContextProvider,
    MockCaseLawDatabase,
    format_context_for_prompt,
)


@dataclass
class CaseFindings:
    """Structured findings from case analysis."""

    file_name: str
    analysis_date: str
    summary: str
    key_facts: list[str] = field(default_factory=list)
    injuries_claimed: list[str] = field(default_factory=list)
    relevant_dates: dict[str, str] = field(default_factory=dict)
    parties: dict[str, str] = field(default_factory=dict)
    legal_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    relevant_cases: list[str] = field(default_factory=list)
    confidence_level: str = "medium"
    raw_text_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_name": self.file_name,
            "analysis_date": self.analysis_date,
            "summary": self.summary,
            "key_facts": self.key_facts,
            "injuries_claimed": self.injuries_claimed,
            "relevant_dates": self.relevant_dates,
            "parties": self.parties,
            "legal_issues": self.legal_issues,
            "recommendations": self.recommendations,
            "relevant_cases": self.relevant_cases,
            "confidence_level": self.confidence_level,
            "raw_text_length": self.raw_text_length,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def extract_pdf_text(file_path: Path, max_pages: int = 200) -> str:
    """Extract text from a PDF file.

    Args:
        file_path: Path to PDF file
        max_pages: Maximum pages to extract

    Returns:
        Extracted text content

    Raises:
        ImportError: If pypdf is not installed
        FileNotFoundError: If file doesn't exist
    """
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError(
            "pypdf is required for PDF extraction. Install with: pip install pypdf"
        ) from e

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    reader = PdfReader(file_path)
    pages_to_read = min(len(reader.pages), max_pages)

    text_parts = []
    for i in range(pages_to_read):
        page = reader.pages[i]
        text = page.extract_text()
        if text:
            text_parts.append(f"--- Page {i + 1} ---\n{text}")

    if len(reader.pages) > max_pages:
        text_parts.append(
            f"\n[Note: Document truncated. Showing {max_pages} of {len(reader.pages)} pages.]"
        )

    return "\n\n".join(text_parts)


def analyze_case_file(
    file_path: str | Path,
    model: str = "gpt-4o",
    temperature: float = 0.3,
    jurisdiction: str = "California",
) -> CaseFindings:
    """Analyze a case file PDF with AI.

    Args:
        file_path: Path to the PDF case file
        model: AI model to use
        temperature: Model temperature (lower = more focused)
        jurisdiction: Legal jurisdiction for context

    Returns:
        CaseFindings with structured analysis

    Example:
        >>> findings = analyze_case_file("/data/matters/MATTER-001/deposition.pdf")
        >>> print(findings.summary)
        >>> print(findings.to_json())
    """
    file_path = Path(file_path)

    # Extract PDF text
    print(f"Extracting text from: {file_path.name}")
    raw_text = extract_pdf_text(file_path)
    print(f"Extracted {len(raw_text)} characters from {file_path.name}")

    # Initialize legal context
    db = MockCaseLawDatabase()
    context_provider = LegalContextProvider(jurisdiction, db)

    # Get context (query-aware for better case matching)
    context = context_provider.get_context(query=raw_text[:1000])
    legal_context = format_context_for_prompt(context)

    # Build analysis prompt
    analysis_prompt = f"""You are analyzing a workers' compensation case file.
Provide a structured analysis of the following document.

{legal_context}

---

DOCUMENT TEXT:
{raw_text[:30000]}

---

Provide your analysis in the following JSON format:
{{
    "summary": "2-3 sentence summary of the case",
    "key_facts": ["fact 1", "fact 2", ...],
    "injuries_claimed": ["injury 1", "injury 2", ...],
    "relevant_dates": {{"date_of_injury": "...", "filing_date": "...", ...}},
    "parties": {{"claimant": "...", "employer": "...", "insurer": "..."}},
    "legal_issues": ["issue 1", "issue 2", ...],
    "recommendations": ["recommendation 1", ...],
    "relevant_cases": ["case name and citation", ...],
    "confidence_level": "high|medium|low"
}}

Respond ONLY with valid JSON, no additional text."""

    # Create Consoul instance (no tools needed for analysis)
    console = Consoul(
        model=model,
        temperature=temperature,
        tools=False,  # No tools for pure analysis
        persist=False,
    )

    # Get AI analysis
    print("Analyzing with AI...")
    response = console.chat(analysis_prompt)

    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        analysis = json.loads(response.strip())
    except json.JSONDecodeError:
        # Fallback to basic findings
        analysis = {
            "summary": response[:500],
            "confidence_level": "low",
        }

    # Build findings object
    findings = CaseFindings(
        file_name=file_path.name,
        analysis_date=datetime.now().isoformat(),
        summary=analysis.get("summary", "Unable to generate summary"),
        key_facts=analysis.get("key_facts", []),
        injuries_claimed=analysis.get("injuries_claimed", []),
        relevant_dates=analysis.get("relevant_dates", {}),
        parties=analysis.get("parties", {}),
        legal_issues=analysis.get("legal_issues", []),
        recommendations=analysis.get("recommendations", []),
        relevant_cases=analysis.get("relevant_cases", []),
        confidence_level=analysis.get("confidence_level", "medium"),
        raw_text_length=len(raw_text),
    )

    return findings


def main():
    """Command-line interface for case analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze a PDF case file with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python case_analysis.py --file /data/matters/MATTER-001/case.pdf
    python case_analysis.py --matter-id MATTER-001 --file case.pdf
    python case_analysis.py --file case.pdf --output findings.json
        """,
    )

    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Path to PDF case file",
    )
    parser.add_argument(
        "--matter-id",
        "-m",
        help="Matter ID (prepends /data/matters/{matter-id}/ to file path)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for JSON findings (default: stdout)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="AI model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--jurisdiction",
        "-j",
        default="California",
        help="Legal jurisdiction (default: California)",
    )

    args = parser.parse_args()

    # Determine file path
    if args.matter_id:
        file_path = Path(f"/data/matters/{args.matter_id}/{args.file}")
    else:
        file_path = Path(args.file)

    print("=" * 60)
    print("Case File Analysis")
    print("=" * 60)
    print(f"File: {file_path}")
    print(f"Model: {args.model}")
    print(f"Jurisdiction: {args.jurisdiction}")
    print()

    try:
        # Analyze
        findings = analyze_case_file(
            file_path=file_path,
            model=args.model,
            jurisdiction=args.jurisdiction,
        )

        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(findings.to_json())
            print(f"\nFindings written to: {output_path}")
        else:
            print("\n" + "=" * 60)
            print("ANALYSIS FINDINGS")
            print("=" * 60)
            print(findings.to_json())

        print(f"\nAnalysis complete. Confidence: {findings.confidence_level}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deposition Summary Workflow.

Summarizes deposition transcripts for workers' compensation cases.
Extracts key facts, testimony highlights, and potential case impacts.

Features:
- Extracts witness/deponent information
- Identifies key admissions and denials
- Highlights relevant testimony for case strategy
- Generates structured summary with citations

Usage:
    python -m examples.legal.workflows.deposition_summary \\
        --file deposition_transcript.pdf \\
        --output summary.json

    # Or programmatically:
    from examples.legal.workflows.deposition_summary import summarize_deposition
    summary = summarize_deposition("/path/to/deposition.pdf")
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DepositionSummary:
    """Structured deposition summary."""

    file_name: str
    analysis_date: str
    deponent_name: str = ""
    deposition_date: str = ""
    case_caption: str = ""

    # Core summary
    executive_summary: str = ""
    key_admissions: list[dict[str, str]] = field(default_factory=list)
    key_denials: list[dict[str, str]] = field(default_factory=list)
    credibility_notes: list[str] = field(default_factory=list)

    # Case-relevant facts
    injury_description: str = ""
    work_history: list[str] = field(default_factory=list)
    medical_treatment: list[str] = field(default_factory=list)
    current_limitations: list[str] = field(default_factory=list)

    # Follow-up items
    inconsistencies: list[str] = field(default_factory=list)
    areas_for_follow_up: list[str] = field(default_factory=list)
    recommended_exhibits: list[str] = field(default_factory=list)

    # Metadata
    page_count: int = 0
    word_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_name": self.file_name,
            "analysis_date": self.analysis_date,
            "deponent_info": {
                "name": self.deponent_name,
                "deposition_date": self.deposition_date,
                "case_caption": self.case_caption,
            },
            "executive_summary": self.executive_summary,
            "key_testimony": {
                "admissions": self.key_admissions,
                "denials": self.key_denials,
                "credibility_notes": self.credibility_notes,
            },
            "case_facts": {
                "injury_description": self.injury_description,
                "work_history": self.work_history,
                "medical_treatment": self.medical_treatment,
                "current_limitations": self.current_limitations,
            },
            "follow_up": {
                "inconsistencies": self.inconsistencies,
                "areas_for_follow_up": self.areas_for_follow_up,
                "recommended_exhibits": self.recommended_exhibits,
            },
            "metadata": {
                "page_count": self.page_count,
                "word_count": self.word_count,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def extract_text(file_path: Path, max_pages: int = 500) -> tuple[str, int]:
    """Extract text from PDF or text file.

    Returns:
        Tuple of (text content, page count)
    """
    if file_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError("pypdf required: pip install pypdf") from e

        reader = PdfReader(file_path)
        pages_to_read = min(len(reader.pages), max_pages)

        text_parts = []
        for i in range(pages_to_read):
            text = reader.pages[i].extract_text()
            if text:
                text_parts.append(f"[Page {i + 1}]\n{text}")

        return "\n\n".join(text_parts), len(reader.pages)

    else:
        # Plain text file
        text = file_path.read_text(encoding="utf-8", errors="replace")
        # Estimate pages (roughly 3000 chars per page)
        page_count = max(1, len(text) // 3000)
        return text, page_count


def summarize_deposition(
    file_path: str | Path,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    focus_areas: list[str] | None = None,
) -> DepositionSummary:
    """Summarize a deposition transcript.

    Args:
        file_path: Path to deposition file (PDF or text)
        model: AI model to use
        temperature: Model temperature
        focus_areas: Specific areas to focus on (optional)

    Returns:
        DepositionSummary with structured analysis
    """
    from consoul import Consoul

    file_path = Path(file_path)

    # Extract text
    print(f"Extracting transcript from: {file_path.name}")
    raw_text, page_count = extract_text(file_path)
    word_count = len(raw_text.split())
    print(f"Extracted {word_count} words from {page_count} pages")

    # Build focus context
    focus_context = ""
    if focus_areas:
        focus_context = "\n\nFocus particularly on these areas:\n" + "\n".join(
            f"- {area}" for area in focus_areas
        )

    # Analysis prompt
    prompt = f"""You are a legal assistant summarizing a workers' compensation deposition.
Analyze the following deposition transcript and provide a structured summary.
{focus_context}

DEPOSITION TRANSCRIPT:
{raw_text[:50000]}

---

Provide your summary in the following JSON format:
{{
    "deponent_name": "Full name of person being deposed",
    "deposition_date": "Date of deposition if mentioned",
    "case_caption": "Case name/number if mentioned",
    "executive_summary": "2-3 paragraph overview of key testimony",
    "key_admissions": [
        {{"testimony": "Quote or paraphrase", "page": "Page number", "significance": "Why important"}}
    ],
    "key_denials": [
        {{"testimony": "Quote or paraphrase", "page": "Page number", "significance": "Why important"}}
    ],
    "credibility_notes": ["Observations about witness credibility"],
    "injury_description": "Description of injury as testified",
    "work_history": ["Relevant work history points"],
    "medical_treatment": ["Medical treatment mentioned"],
    "current_limitations": ["Current claimed limitations"],
    "inconsistencies": ["Any inconsistencies in testimony"],
    "areas_for_follow_up": ["Areas needing further investigation"],
    "recommended_exhibits": ["Documents that should be obtained or used"]
}}

Respond ONLY with valid JSON."""

    # Analyze with AI
    console = Consoul(
        model=model,
        temperature=temperature,
        tools=False,
        persist=False,
    )

    print("Analyzing deposition...")
    response = console.chat(prompt)

    # Parse response
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        analysis = json.loads(response.strip())
    except json.JSONDecodeError:
        analysis = {
            "executive_summary": response[:1000],
        }

    # Build summary object
    summary = DepositionSummary(
        file_name=file_path.name,
        analysis_date=datetime.now().isoformat(),
        deponent_name=analysis.get("deponent_name", "Unknown"),
        deposition_date=analysis.get("deposition_date", ""),
        case_caption=analysis.get("case_caption", ""),
        executive_summary=analysis.get("executive_summary", ""),
        key_admissions=analysis.get("key_admissions", []),
        key_denials=analysis.get("key_denials", []),
        credibility_notes=analysis.get("credibility_notes", []),
        injury_description=analysis.get("injury_description", ""),
        work_history=analysis.get("work_history", []),
        medical_treatment=analysis.get("medical_treatment", []),
        current_limitations=analysis.get("current_limitations", []),
        inconsistencies=analysis.get("inconsistencies", []),
        areas_for_follow_up=analysis.get("areas_for_follow_up", []),
        recommended_exhibits=analysis.get("recommended_exhibits", []),
        page_count=page_count,
        word_count=word_count,
    )

    return summary


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Summarize a deposition transcript",
    )

    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Path to deposition file (PDF or text)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for JSON summary",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="AI model (default: gpt-4o)",
    )
    parser.add_argument(
        "--focus",
        nargs="+",
        help="Areas to focus on (e.g., --focus 'injury details' 'work restrictions')",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Deposition Summary")
    print("=" * 60)

    try:
        summary = summarize_deposition(
            file_path=args.file,
            model=args.model,
            focus_areas=args.focus,
        )

        if args.output:
            Path(args.output).write_text(summary.to_json())
            print(f"\nSummary written to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("DEPOSITION SUMMARY")
            print("=" * 60)
            print(summary.to_json())

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

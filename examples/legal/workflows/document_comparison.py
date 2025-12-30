#!/usr/bin/env python3
"""Document Comparison Workflow.

Compares two legal documents and identifies differences for review.
Useful for comparing contract versions, settlement drafts, or policy changes.

Features:
- Side-by-side comparison of legal documents
- Highlights additions, deletions, and modifications
- Identifies legally significant changes
- Generates structured diff report

Usage:
    python -m examples.legal.workflows.document_comparison \\
        --file1 draft_v1.pdf \\
        --file2 draft_v2.pdf \\
        --output comparison.json
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DocumentChange:
    """A single change between documents."""

    change_type: str  # "addition", "deletion", "modification"
    location: str  # Page/section reference
    original_text: str = ""
    new_text: str = ""
    significance: str = ""  # "high", "medium", "low"
    category: str = ""  # "legal_term", "amount", "date", "party", "general"


@dataclass
class ComparisonReport:
    """Document comparison report."""

    file1_name: str
    file2_name: str
    comparison_date: str

    # Summary
    summary: str = ""
    total_changes: int = 0
    high_significance_changes: int = 0

    # Changes by type
    additions: list[DocumentChange] = field(default_factory=list)
    deletions: list[DocumentChange] = field(default_factory=list)
    modifications: list[DocumentChange] = field(default_factory=list)

    # Analysis
    legal_implications: list[str] = field(default_factory=list)
    review_recommendations: list[str] = field(default_factory=list)

    # Metadata
    file1_word_count: int = 0
    file2_word_count: int = 0
    similarity_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "files": {
                "file1": self.file1_name,
                "file2": self.file2_name,
            },
            "comparison_date": self.comparison_date,
            "summary": self.summary,
            "statistics": {
                "total_changes": self.total_changes,
                "high_significance_changes": self.high_significance_changes,
                "additions_count": len(self.additions),
                "deletions_count": len(self.deletions),
                "modifications_count": len(self.modifications),
                "similarity_ratio": round(self.similarity_ratio, 4),
            },
            "changes": {
                "additions": [
                    {
                        "location": c.location,
                        "text": c.new_text,
                        "significance": c.significance,
                        "category": c.category,
                    }
                    for c in self.additions
                ],
                "deletions": [
                    {
                        "location": c.location,
                        "text": c.original_text,
                        "significance": c.significance,
                        "category": c.category,
                    }
                    for c in self.deletions
                ],
                "modifications": [
                    {
                        "location": c.location,
                        "original": c.original_text,
                        "new": c.new_text,
                        "significance": c.significance,
                        "category": c.category,
                    }
                    for c in self.modifications
                ],
            },
            "analysis": {
                "legal_implications": self.legal_implications,
                "review_recommendations": self.review_recommendations,
            },
            "metadata": {
                "file1_word_count": self.file1_word_count,
                "file2_word_count": self.file2_word_count,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def extract_text(file_path: Path) -> str:
    """Extract text from file."""
    if file_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError("pypdf required: pip install pypdf") from e

        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)

    else:
        return file_path.read_text(encoding="utf-8", errors="replace")


def compute_diff(text1: str, text2: str) -> tuple[list[str], float]:
    """Compute unified diff and similarity ratio.

    Returns:
        Tuple of (diff lines, similarity ratio)
    """
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    # Compute similarity
    matcher = difflib.SequenceMatcher(None, text1, text2)
    similarity = matcher.ratio()

    # Compute unified diff
    diff = list(
        difflib.unified_diff(
            lines1,
            lines2,
            fromfile="Document 1",
            tofile="Document 2",
            lineterm="",
        )
    )

    return diff, similarity


def compare_documents(
    file1_path: str | Path,
    file2_path: str | Path,
    model: str = "gpt-4o",
    temperature: float = 0.2,
) -> ComparisonReport:
    """Compare two legal documents.

    Args:
        file1_path: Path to first document
        file2_path: Path to second document
        model: AI model for analysis
        temperature: Model temperature

    Returns:
        ComparisonReport with detailed analysis
    """
    from consoul import Consoul

    file1_path = Path(file1_path)
    file2_path = Path(file2_path)

    # Extract text
    print(f"Extracting: {file1_path.name}")
    text1 = extract_text(file1_path)
    print(f"Extracting: {file2_path.name}")
    text2 = extract_text(file2_path)

    word_count1 = len(text1.split())
    word_count2 = len(text2.split())
    print(f"Document 1: {word_count1} words, Document 2: {word_count2} words")

    # Compute diff
    print("Computing differences...")
    diff_lines, similarity = compute_diff(text1, text2)
    diff_text = "\n".join(diff_lines[:500])  # Limit for prompt

    # AI analysis
    prompt = f"""You are a legal document reviewer comparing two versions of a document.
Analyze the differences and identify legally significant changes.

DOCUMENT 1 (Original):
{text1[:20000]}

---

DOCUMENT 2 (New Version):
{text2[:20000]}

---

DIFF SUMMARY:
{diff_text}

---

Provide your analysis in the following JSON format:
{{
    "summary": "Overall summary of changes between documents",
    "additions": [
        {{"location": "Section/paragraph", "text": "Added text", "significance": "high|medium|low", "category": "legal_term|amount|date|party|general"}}
    ],
    "deletions": [
        {{"location": "Section/paragraph", "text": "Removed text", "significance": "high|medium|low", "category": "legal_term|amount|date|party|general"}}
    ],
    "modifications": [
        {{"location": "Section/paragraph", "original": "Original text", "new": "New text", "significance": "high|medium|low", "category": "legal_term|amount|date|party|general"}}
    ],
    "legal_implications": ["Implication 1", "Implication 2"],
    "review_recommendations": ["Recommendation 1", "Recommendation 2"]
}}

Focus on:
- Changes to dollar amounts, percentages, or limits
- Changes to dates or deadlines
- Changes to party names or responsibilities
- Changes to legal terms or definitions
- Additions or removals of entire sections

Respond ONLY with valid JSON."""

    console = Consoul(
        model=model,
        temperature=temperature,
        tools=False,
        persist=False,
    )

    print("Analyzing with AI...")
    response = console.chat(prompt)

    # Parse response
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        analysis = json.loads(response.strip())
    except json.JSONDecodeError:
        analysis = {"summary": response[:1000]}

    # Build changes
    additions = [
        DocumentChange(
            change_type="addition",
            location=c.get("location", "Unknown"),
            new_text=c.get("text", ""),
            significance=c.get("significance", "medium"),
            category=c.get("category", "general"),
        )
        for c in analysis.get("additions", [])
    ]

    deletions = [
        DocumentChange(
            change_type="deletion",
            location=c.get("location", "Unknown"),
            original_text=c.get("text", ""),
            significance=c.get("significance", "medium"),
            category=c.get("category", "general"),
        )
        for c in analysis.get("deletions", [])
    ]

    modifications = [
        DocumentChange(
            change_type="modification",
            location=c.get("location", "Unknown"),
            original_text=c.get("original", ""),
            new_text=c.get("new", ""),
            significance=c.get("significance", "medium"),
            category=c.get("category", "general"),
        )
        for c in analysis.get("modifications", [])
    ]

    all_changes = additions + deletions + modifications
    high_sig = sum(1 for c in all_changes if c.significance == "high")

    # Build report
    report = ComparisonReport(
        file1_name=file1_path.name,
        file2_name=file2_path.name,
        comparison_date=datetime.now().isoformat(),
        summary=analysis.get("summary", ""),
        total_changes=len(all_changes),
        high_significance_changes=high_sig,
        additions=additions,
        deletions=deletions,
        modifications=modifications,
        legal_implications=analysis.get("legal_implications", []),
        review_recommendations=analysis.get("review_recommendations", []),
        file1_word_count=word_count1,
        file2_word_count=word_count2,
        similarity_ratio=similarity,
    )

    return report


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Compare two legal documents",
    )

    parser.add_argument(
        "--file1",
        "-a",
        required=True,
        help="Path to first (original) document",
    )
    parser.add_argument(
        "--file2",
        "-b",
        required=True,
        help="Path to second (new) document",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for JSON report",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="AI model (default: gpt-4o)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Document Comparison")
    print("=" * 60)

    try:
        report = compare_documents(
            file1_path=args.file1,
            file2_path=args.file2,
            model=args.model,
        )

        if args.output:
            Path(args.output).write_text(report.to_json())
            print(f"\nReport written to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("COMPARISON REPORT")
            print("=" * 60)
            print(report.to_json())

        print(f"\nSimilarity: {report.similarity_ratio:.1%}")
        print(f"Total changes: {report.total_changes}")
        print(f"High significance: {report.high_significance_changes}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

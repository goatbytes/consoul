"""Legal Workflow Examples for Consoul.

This package contains example workflows for legal industry use cases:

- case_analysis: Analyze PDF case files with AI
- deposition_summary: Summarize deposition transcripts
- document_comparison: Compare legal documents for differences
"""

from .case_analysis import analyze_case_file
from .deposition_summary import summarize_deposition
from .document_comparison import compare_documents

__all__ = [
    "analyze_case_file",
    "compare_documents",
    "summarize_deposition",
]

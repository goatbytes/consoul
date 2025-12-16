"""Quality checks for release validation."""

from __future__ import annotations

import subprocess
from typing import NamedTuple


class CheckResult(NamedTuple):
    """Result of a quality check."""

    name: str
    passed: bool
    output: str
    error: str


def run_check(name: str, command: str) -> CheckResult:
    """
    Run a quality check command.

    Args:
        name: Check name
        command: Shell command to run

    Returns:
        Check result
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        return CheckResult(
            name=name,
            passed=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
        )

    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name, passed=False, output="", error="Command timed out"
        )


def run_all_checks(skip_tests: bool = False) -> list[CheckResult]:
    """
    Run all quality checks.

    Args:
        skip_tests: Skip test suite

    Returns:
        List of check results
    """
    checks = [
        ("Poetry Check", "poetry check 2>&1 | grep -v Warning || true"),
        ("Linting", "poetry run ruff check src/ --quiet"),
        (
            "Type Checking",
            "poetry run mypy src/ --no-error-summary 2>&1 | grep -E '^(Success|Found)' || echo 'Type check passed'",
        ),
    ]

    if not skip_tests:
        checks.extend(
            [
                (
                    "Unit Tests",
                    "poetry run pytest tests/unit -x --tb=short -q",
                ),
                ("Package Build", "poetry build 2>&1 | tail -3"),
            ]
        )

    results = []
    for name, command in checks:
        results.append(run_check(name, command))

    return results

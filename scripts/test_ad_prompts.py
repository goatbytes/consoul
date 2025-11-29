#!/usr/bin/env python3
"""
Test ad prompts against multiple LLM models and save responses.

This script reads prompts from ad_prompts.md, sends them to various LLM models,
and saves the responses in a structured format for analysis.

Usage:
    poetry run python scripts/test_ad_prompts.py
    poetry run python scripts/test_ad_prompts.py --model gpt-4o --prompts 1,5,10
    poetry run python scripts/test_ad_prompts.py --output results.jsonl
"""

import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from consoul.chat.manager import ChatManager
from consoul.config.manager import ConfigurationManager
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def parse_ad_prompts(markdown_path: Path) -> list[dict[str, str]]:
    """Parse ad prompts from the markdown file.

    Returns:
        List of dicts with 'number', 'title', 'prompt', and 'why' fields
    """
    content = markdown_path.read_text()
    prompts = []

    # Match prompts with this pattern:
    # ### N. Title
    # **Prompt:** "prompt text"
    # **Why it's impressive:** reason

    pattern = r'###\s+(\d+)\.\s+(.+?)\n\*\*Prompt:\*\*\s+"(.+?)"\n+\*\*Why it\'s impressive:\*\*\s+(.+?)(?=\n---|$)'

    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        number, title, prompt, why = match.groups()
        prompts.append(
            {
                "number": int(number.strip()),
                "title": title.strip(),
                "prompt": prompt.strip(),
                "why": why.strip(),
            }
        )

    # Also parse one-liner prompts
    # ### 23. "prompt text"
    oneliner_pattern = r'###\s+(\d+)\.\s+"(.+?)"'
    oneliner_matches = re.finditer(oneliner_pattern, content)

    for match in oneliner_matches:
        number, prompt = match.groups()
        if int(number) not in [p["number"] for p in prompts]:
            prompts.append(
                {
                    "number": int(number.strip()),
                    "title": f"One-liner {number}",
                    "prompt": prompt.strip(),
                    "why": "Quick demonstration prompt",
                }
            )

    return sorted(prompts, key=lambda x: x["number"])


async def test_prompt(
    chat_manager: ChatManager, prompt: str, model: str
) -> dict[str, any]:
    """Test a single prompt against a model.

    Args:
        chat_manager: Chat manager instance
        prompt: The prompt to test
        model: Model name to use

    Returns:
        Dict with response, error, and metadata
    """
    try:
        response = ""
        async for chunk in chat_manager.send_message(prompt):
            if hasattr(chunk, "content"):
                response += chunk.content
            else:
                response += str(chunk)

        return {"response": response.strip(), "error": None, "success": True}
    except Exception as e:
        return {"response": None, "error": str(e), "success": False}


async def run_tests(
    prompts: list[dict[str, str]],
    models: list[str],
    output_path: Path,
    prompt_numbers: list[int] | None = None,
):
    """Run all prompt tests and save results.

    Args:
        prompts: List of prompt dicts
        models: List of model names to test
        output_path: Path to save results
        prompt_numbers: Optional list of specific prompt numbers to test
    """
    # Filter prompts if specific numbers requested
    if prompt_numbers:
        prompts = [p for p in prompts if p["number"] in prompt_numbers]

    config_manager = ConfigurationManager()
    results = []

    total_tests = len(prompts) * len(models)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Testing {len(prompts)} prompts across {len(models)} models...",
            total=total_tests,
        )

        for model in models:
            console.print(f"\n[bold cyan]Testing model: {model}[/bold cyan]")

            try:
                chat_manager = ChatManager(
                    config_manager=config_manager, model_name=model
                )

                for prompt_data in prompts:
                    prompt_num = prompt_data["number"]
                    prompt_text = prompt_data["prompt"]

                    console.print(
                        f"  [dim]#{prompt_num}: {prompt_data['title'][:50]}...[/dim]"
                    )

                    result = await test_prompt(chat_manager, prompt_text, model)

                    # Save result
                    result_entry = {
                        "prompt_number": prompt_num,
                        "prompt_title": prompt_data["title"],
                        "prompt": prompt_text,
                        "why_impressive": prompt_data["why"],
                        "model": model,
                        "timestamp": datetime.now().isoformat(),
                        **result,
                    }

                    results.append(result_entry)

                    # Save incrementally
                    with output_path.open("a") as f:
                        f.write(json.dumps(result_entry) + "\n")

                    progress.update(task, advance=1)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

            except Exception as e:
                console.print(f"[bold red]Error with model {model}: {e}[/bold red]")
                progress.update(task, advance=len(prompts))

    console.print(
        f"\n[bold green]✓ Saved {len(results)} results to {output_path}[/bold green]"
    )

    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    for model in models:
        model_results = [r for r in results if r["model"] == model]
        successes = sum(1 for r in model_results if r["success"])
        console.print(f"  {model}: {successes}/{len(model_results)} successful")


def main():
    parser = argparse.ArgumentParser(description="Test ad prompts against LLM models")
    parser.add_argument(
        "--models",
        "-m",
        type=str,
        default="gpt-4o,claude-3-5-sonnet-20241022,gemini-2.0-flash-exp",
        help="Comma-separated list of models to test (default: gpt-4o,claude-3-5-sonnet-20241022,gemini-2.0-flash-exp)",
    )
    parser.add_argument(
        "--prompts",
        "-p",
        type=str,
        help="Comma-separated list of prompt numbers to test (default: all)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="llm_responses/ad_prompt_results.jsonl",
        help="Output file path (default: llm_responses/ad_prompt_results.jsonl)",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="llm_responses/ad_prompts.md",
        help="Input markdown file with prompts (default: llm_responses/ad_prompts.md)",
    )

    args = parser.parse_args()

    # Parse arguments
    models = [m.strip() for m in args.models.split(",")]
    prompt_numbers = None
    if args.prompts:
        prompt_numbers = [int(n.strip()) for n in args.prompts.split(",")]

    # Setup paths
    project_root = Path(__file__).parent.parent
    input_path = project_root / args.input
    output_path = project_root / args.output

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clear output file if it exists
    if output_path.exists():
        console.print(f"[yellow]Clearing existing results in {output_path}[/yellow]")
        output_path.unlink()

    # Parse prompts
    console.print(f"[bold]Reading prompts from {input_path}[/bold]")
    prompts = parse_ad_prompts(input_path)

    if not prompts:
        console.print("[bold red]No prompts found in input file![/bold red]")
        return

    console.print(f"Found {len(prompts)} prompts")

    if prompt_numbers:
        console.print(f"Testing prompts: {', '.join(map(str, prompt_numbers))}")

    # Run tests
    asyncio.run(run_tests(prompts, models, output_path, prompt_numbers))


if __name__ == "__main__":
    main()

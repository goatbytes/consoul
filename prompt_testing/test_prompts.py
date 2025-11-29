#!/usr/bin/env python3
"""Script to test consoul with real-world human prompts.

This script allows you to test Consoul with various prompts and save responses
in multiple formats (JSON, JSONL). Supports custom prompts, system prompts,
and different models.

Usage:
    python test_prompts.py                      # Use default prompts
    python test_prompts.py --preset high-value  # Use high-value preset
    python test_prompts.py --prompts-file my_prompts.json
    python test_prompts.py --help
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path if needed (when running from prompt_testing directory)
try:
    from consoul import Consoul
except ImportError:
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    from consoul import Consoul

# Default prompts - high-value single-response questions
DEFAULT_PROMPTS = [
    # Code Analysis & Debugging
    "Explain what this regex does: ^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}$",
    "What's wrong with this code and how do I fix it? `if (user.role = 'admin')`",
    "Convert this synchronous function to async/await: function fetchData() { return fetch('/api').then(r => r.json()) }",
    # Data Manipulation
    "Generate a Python one-liner to flatten a nested list like [[1,2],[3,[4,5]],[6]]",
    "Write a SQL query to find the 2nd highest salary from an employees table",
    "Create a regex to extract all email addresses from text",
    # Quick Reference
    "What are the main differences between git merge and git rebase?",
    "Explain JavaScript closures with a simple example",
    "What's the difference between TCP and UDP in one paragraph?",
    # Text Processing
    "Rewrite this for a professional email: 'hey just checking if u got my last message about the thing we talked about'",
    "Summarize the key points of the Agile manifesto in bullet points",
    "Convert this to passive voice: 'The team completed the project ahead of schedule'",
    # Problem Solving
    "What's the time complexity of binary search and why?",
    "Give me 3 ways to optimize a slow database query",
    "How do I center a div horizontally and vertically in CSS?",
    # Quick Answers
    "What HTTP status code should I use for 'resource not found'?",
    "Explain the CAP theorem in distributed systems in 2 sentences",
    "What's the difference between authentication and authorization?",
    # Practical Solutions
    "Write a bash one-liner to find all files larger than 100MB",
    "Create a Python function to validate if a string is a valid IPv4 address",
    "Generate a .gitignore for a Python/Django project",
]

# Alternative prompt sets
HIGH_VALUE_PROMPTS = [
    # Instant utility prompts where a single response provides clear value
    "Write a Python function to check if a number is prime",
    "Explain the difference between == and === in JavaScript",
    "Create a regex to validate email addresses",
    "What's the difference between Process and Thread?",
    "Write a SQL query to find duplicate records in a table",
    "Convert this datetime to ISO format: December 25, 2024 3:30 PM EST",
    "Explain REST API status codes: 200, 201, 400, 401, 403, 404, 500",
    "Write a function to reverse a string in Python without using built-in methods",
    "What are the SOLID principles in software development?",
    "Create a responsive CSS grid with 3 columns that collapses to 1 on mobile",
    "Explain Big O notation with examples",
    "Write a Docker command to run a container with port mapping",
    "What's the difference between var, let, and const in JavaScript?",
    "Generate a Python list comprehension to get even numbers from 1-100",
    "Explain how HTTPS works in simple terms",
    "Write a git command to undo the last commit but keep changes",
    "What are the differences between SQL and NoSQL databases?",
    "Create a function to debounce API calls in JavaScript",
    "Explain the MVC architecture pattern",
    "Write a Python decorator to measure function execution time",
]


def run_consoul_chat(prompt: str, console: Consoul) -> dict:
    """Send prompt to Consoul and capture the response.

    Args:
        prompt: The prompt to send to the LLM
        console: Consoul instance to use

    Returns:
        dict with prompt, response, timestamp, and metadata
    """
    try:
        # Get response from Consoul SDK
        response = console.chat(prompt)

        return {
            "prompt": prompt,
            "response": response,
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "model": console.model_name,
            "success": True,
        }
    except Exception as e:
        return {
            "prompt": prompt,
            "response": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "model": getattr(console, "model_name", "unknown"),
            "success": False,
        }


def load_prompts_from_file(filepath: Path) -> list[str]:
    """Load prompts from a JSON file.

    Args:
        filepath: Path to JSON file containing prompts

    Returns:
        List of prompt strings

    Supported formats:
        - Simple array: ["prompt1", "prompt2"]
        - Array of objects: [{"prompt": "text", "category": "..."}, ...]
        - Object with prompts key: {"prompts": ["prompt1", "prompt2"]}
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    # Handle different JSON formats
    if isinstance(data, list):
        if not data:
            return []
        # Check if it's a list of strings or objects
        if isinstance(data[0], str):
            return data
        elif isinstance(data[0], dict) and "prompt" in data[0]:
            return [item["prompt"] for item in data]
        else:
            raise ValueError(f"Unsupported list format in {filepath}")
    elif isinstance(data, dict):
        if "prompts" in data:
            return data["prompts"]
        else:
            raise ValueError(f"JSON object must have 'prompts' key in {filepath}")
    else:
        raise ValueError(f"Unsupported JSON format in {filepath}")


def load_config(config_path: Path = None) -> dict:
    """Load configuration from JSON file.

    Args:
        config_path: Path to config file (default: config.json in script dir)

    Returns:
        Configuration dictionary with defaults for missing keys
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config.json"

    defaults = {
        "model": None,
        "temperature": 0.7,
        "output": "llm_responses",
        "system_prompt_file": None,
        "prompts_file": None,
        "preset": "default",
        "system_prompt": None,
    }

    if not config_path.exists():
        return defaults

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        # Merge with defaults (config overrides defaults)
        return {**defaults, **config}
    except Exception as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        return defaults


def main():
    """Run all prompts through consoul and save results."""
    # Get script directory
    script_dir = Path(__file__).parent

    # Parse command-line arguments FIRST to check for --config
    # We'll do a simple pre-parse to get the config file
    import sys

    config_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]
            break

    # Load appropriate config
    if config_file:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = script_dir / config_path
        config = load_config(config_path)
        print(f"Loaded config from: {config_path}")
    else:
        config = load_config()

    # Parse command-line arguments (these override config)
    parser = argparse.ArgumentParser(
        description="Test Consoul with various prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use config.json defaults
  python test_prompts.py

  # Override config with command-line args
  python test_prompts.py --model gpt-4o

  # Use high-value prompts preset
  python test_prompts.py --preset high-value

  # Load prompts from a JSON file
  python test_prompts.py --prompts-file my_prompts.json

  # Specify model and temperature
  python test_prompts.py --model gpt-4o --temperature 0.5

  # Custom output directory
  python test_prompts.py --output custom_results

  # Use custom system prompt
  python test_prompts.py --system-prompt "You are a concise code assistant."

  # Load system prompt from file
  python test_prompts.py --system-prompt-file system_prompts/expert_system.txt

  # Use custom config file
  python test_prompts.py --config my_config.json

Configuration:
  Create a config.json file in the prompt_testing directory with default settings.
  Command-line arguments override config file settings.

  Example config.json:
  {
    "model": "granite4:3b",
    "temperature": 0.7,
    "output": "output",
    "system_prompt_file": "system_prompts/concise_expert.txt",
    "prompts_file": "example_prompts.json",
    "preset": null
  }

Prompt file formats:
  1. Simple array: ["prompt1", "prompt2", ...]
  2. Array of objects: [{"prompt": "text", "category": "..."}, ...]
  3. Object with prompts: {"prompts": ["prompt1", "prompt2", ...]}
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Config file to use (default: config.json in script directory)",
    )
    parser.add_argument(
        "--prompts-file",
        type=Path,
        default=config.get("prompts_file"),
        help=f"JSON file containing prompts to test (default from config: {config.get('prompts_file')})",
    )
    parser.add_argument(
        "--preset",
        choices=["default", "high-value"],
        default=config.get("preset"),
        help=f"Use a predefined prompt set (default from config: {config.get('preset')})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.get("model"),
        help=f"Model to use (default from config: {config.get('model')})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=config.get("temperature", 0.7),
        help=f"Temperature for model responses (default from config: {config.get('temperature', 0.7)})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(config.get("output", "llm_responses")),
        help=f"Output directory for results (default from config: {config.get('output', 'llm_responses')})",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available prompt presets and exit",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=config.get("system_prompt"),
        help=f"Custom system prompt to use for all responses (default from config: {config.get('system_prompt')})",
    )
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        default=config.get("system_prompt_file"),
        help=f"File containing system prompt to use (default from config: {config.get('system_prompt_file')})",
    )

    args = parser.parse_args()

    # Handle --list-presets
    if args.list_presets:
        print("Available prompt presets:")
        print(f"\n  default ({len(DEFAULT_PROMPTS)} prompts)")
        print("    High-value single-response questions covering:")
        print("    - Code analysis & debugging")
        print("    - Data manipulation")
        print("    - Quick reference")
        print("    - Text processing")
        print("    - Problem solving")
        print(f"\n  high-value ({len(HIGH_VALUE_PROMPTS)} prompts)")
        print("    Instant utility prompts with clear immediate value")
        return

    # Load prompts
    if args.prompts_file:
        # Make path relative to script directory if not absolute
        prompts_path = args.prompts_file
        if not prompts_path.is_absolute():
            prompts_path = script_dir / prompts_path

        if not prompts_path.exists():
            print(f"Error: Prompts file not found: {prompts_path}")
            return
        try:
            prompts = load_prompts_from_file(prompts_path)
            print(f"Loaded {len(prompts)} prompts from {prompts_path}")
        except Exception as e:
            print(f"Error loading prompts file: {e}")
            return
    else:
        # Use preset
        if args.preset == "high-value":
            prompts = HIGH_VALUE_PROMPTS
        else:
            prompts = DEFAULT_PROMPTS
        print(f"Using '{args.preset}' preset with {len(prompts)} prompts")

    # Load system prompt if provided
    system_prompt = None
    if args.system_prompt:
        system_prompt = args.system_prompt
        print(f"Using custom system prompt: {system_prompt[:80]}...")
    elif args.system_prompt_file:
        # Make path relative to script directory if not absolute
        system_prompt_path = args.system_prompt_file
        if not system_prompt_path.is_absolute():
            system_prompt_path = script_dir / system_prompt_path

        if not system_prompt_path.exists():
            print(f"Error: System prompt file not found: {system_prompt_path}")
            return
        try:
            with open(system_prompt_path, encoding="utf-8") as f:
                system_prompt = f.read().strip()
            print(f"Loaded system prompt from: {system_prompt_path}")
            print(f"Preview: {system_prompt[:80]}...")
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            return

    # Create output directory
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configure model parameters
    model_params = {
        "temperature": args.temperature,
    }
    if args.model:
        model_params["model"] = args.model
    if system_prompt:
        model_params["system_prompt"] = system_prompt

    # Initialize Consoul with model parameters
    print("Initializing Consoul...")
    try:
        console = Consoul(
            tools=False,  # Disable tools for faster responses
            persist=False,  # Don't save conversation history
            **{k: v for k, v in model_params.items() if v is not None},
        )
        print(f"Using model: {console.model_name}")
    except Exception as e:
        print(f"Error initializing Consoul: {e}")
        return

    results = []

    print(f"\nTesting {len(prompts)} prompts with consoul...")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] Processing prompt...")
        print(f"Prompt: {prompt[:80]}...")

        # Clear history between prompts to avoid context buildup
        if i > 1:
            console.clear()

        # Get response from consoul
        result = run_consoul_chat(prompt, console)
        results.append(result)

        # Save individual JSON file
        filename = f"response_{i:02d}.json"
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if result["success"]:
            print(f"✓ Success - saved to {filename}")
            print(f"Response preview: {result['response'][:100]}...")
        else:
            print(f"✗ Failed - {result['error']}")

    # Save all results to JSONL
    jsonl_path = output_dir / "all_responses.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # Save summary
    summary = {
        "total_prompts": len(prompts),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "model": console.model_name,
        "model_params": {
            k: v
            for k, v in model_params.items()
            if k != "system_prompt"  # Don't include full system prompt in summary
        },
        "system_prompt_used": bool(system_prompt),
        "timestamp": datetime.now().isoformat(),
    }

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Model: {summary['model']}")
    print(f"Total prompts: {summary['total_prompts']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"\nResults saved to: {output_dir}")
    print(f"  - Individual files: response_01.json - response_{len(prompts):02d}.json")
    print("  - JSONL file: all_responses.jsonl")
    print("  - Summary: summary.json")


if __name__ == "__main__":
    main()

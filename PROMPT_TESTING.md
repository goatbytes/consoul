# Prompt Testing Framework

The `prompt_testing/` directory contains a comprehensive framework for testing and evaluating Consoul with various prompts, models, and configurations.

## Quick Start

```bash
# From project root
cd prompt_testing

# Run with default prompts
python test_prompts.py

# See all options
python test_prompts.py --help

# List available preset prompts
python test_prompts.py --list-presets
```

## What's Included

- **40+ curated prompts** that demonstrate AI value in a single response
- **5 system prompt templates** for different response styles
- **Flexible configuration** for models, temperature, and output
- **Multiple output formats** (JSON, JSONL, summary stats)
- **Comprehensive documentation**

## Common Use Cases

### Test Different Models
```bash
cd prompt_testing
python test_prompts.py --model gpt-4o --output results/gpt4
python test_prompts.py --model claude-3-5-sonnet --output results/claude
```

### Compare System Prompts
```bash
cd prompt_testing
python test_prompts.py \
  --system-prompt-file system_prompts/concise_expert.txt \
  --output results/concise

python test_prompts.py \
  --system-prompt-file system_prompts/beginner_friendly.txt \
  --output results/beginner
```

### Use Custom Prompts
```bash
cd prompt_testing
python test_prompts.py --prompts-file my_custom_prompts.json
```

## Documentation

For complete documentation, see:
- [`prompt_testing/README.md`](prompt_testing/README.md) - Main testing framework docs
- [`prompt_testing/system_prompts/README.md`](prompt_testing/system_prompts/README.md) - System prompt guide

## Example Outputs

Each test run creates:
- Individual JSON files (`response_01.json`, `response_02.json`, etc.)
- Combined JSONL file (`all_responses.jsonl`)
- Summary statistics (`summary.json`)

## Features

✅ Built-in high-value prompt presets
✅ Custom JSON prompt files
✅ System prompt customization
✅ Model comparison testing
✅ Temperature variation testing
✅ Multiple output formats
✅ Comprehensive documentation

## Requirements

- Consoul installed (`pip install -e .` from project root)
- Valid API keys for chosen model providers
- Python 3.9+

---

**Full documentation:** See [`prompt_testing/README.md`](prompt_testing/README.md)

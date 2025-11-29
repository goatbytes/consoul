# Consoul Prompt Testing

A comprehensive testing framework for evaluating Consoul responses with various prompts, models, and system configurations.

## 📁 Directory Structure

```
prompt_testing/
├── test_prompts.py              # Main testing script
├── example_prompts.json         # Simple prompt examples
├── example_prompts_detailed.json # Prompts with metadata
├── system_prompts/              # Pre-configured system prompts
│   ├── README.md                # System prompt documentation
│   ├── concise_expert.txt
│   ├── beginner_friendly.txt
│   ├── code_reviewer.txt
│   ├── senior_engineer.txt
│   └── python_expert.txt
├── .gitignore                   # Ignore test outputs
└── README.md                    # This file
```

## Features

- 📋 **Multiple prompt sources**: Built-in presets or custom JSON files
- 🎯 **High-value prompts**: 40+ carefully curated prompts that demonstrate AI value in a single response
- 🔧 **Configurable**: Choose model, temperature, and output directory via config file or CLI
- ⚙️ **Config file support**: Set defaults in config.json, override with command-line args
- 💾 **Multiple output formats**: Individual JSON files, JSONL, and summary statistics
- 🚀 **Fast**: Uses Consoul SDK directly (no subprocess overhead)

## Quick Start

### Using Config File (Recommended)

The easiest way is to use a config file with your preferred defaults:

```bash
# 1. Copy the example config
cp config.example.json config.json

# 2. Edit config.json with your preferences
# 3. Run with no arguments to use config
python test_prompts.py

# 4. Override config with CLI args when needed
python test_prompts.py --model gpt-4o
```

### Using Command-Line Args Only

```bash
# Use default prompts
python test_prompts.py --preset default

# Use high-value prompts preset
python test_prompts.py --preset high-value

# Load custom prompts from JSON file
python test_prompts.py --prompts-file my_prompts.json

# Specify model and temperature
python test_prompts.py --model gpt-4o --temperature 0.5

# Custom output directory
python test_prompts.py --output results/gpt4_test
```

## Configuration

### Config File Format

Create a `config.json` file in the `prompt_testing` directory:

```json
{
  "model": "granite4:3b",
  "temperature": 0.7,
  "output": "output",
  "system_prompt_file": "system_prompts/concise_expert.txt",
  "prompts_file": "example_prompts.json",
  "preset": null,
  "system_prompt": null
}
```

**Config Keys:**
- `model` - Model to use (e.g., "gpt-4o", "claude-3-5-sonnet", "granite4:3b")
- `temperature` - Response temperature (0.0-2.0)
- `output` - Output directory for results
- `system_prompt_file` - Path to system prompt file (relative to prompt_testing/)
- `prompts_file` - Path to prompts JSON file (relative to prompt_testing/)
- `preset` - Use "default" or "high-value" preset (if prompts_file is null)
- `system_prompt` - Inline system prompt text (overrides system_prompt_file)

### Example Configs

Pre-configured example configs in `configs/`:

**`configs/high_value_test.json`** - Test with high-value prompts and senior engineer perspective:
```json
{
  "preset": "high-value",
  "system_prompt_file": "system_prompts/senior_engineer.txt",
  "temperature": 0.5
}
```

**`configs/beginner_friendly.json`** - Detailed explanations for learners:
```json
{
  "prompts_file": "example_prompts_detailed.json",
  "system_prompt_file": "system_prompts/beginner_friendly.txt",
  "temperature": 0.8
}
```

**Usage:**
```bash
python test_prompts.py --config configs/high_value_test.json
```

## Built-in Prompt Presets

### Default (21 prompts)
High-value single-response questions covering:
- **Code Analysis & Debugging**: Regex explanation, bug fixes, code conversion
- **Data Manipulation**: SQL queries, Python one-liners, regex patterns
- **Quick Reference**: Git commands, language features, protocol differences
- **Text Processing**: Email rewriting, summarization, text transformation
- **Problem Solving**: Algorithms, optimization, CSS layouts

### High-Value (20 prompts)
Instant utility prompts with clear immediate value:
- Programming fundamentals (prime numbers, palindromes, string reversal)
- Language comparisons (==, ===, var/let/const)
- Best practices (SOLID, MVC, Big O notation)
- Common tasks (Docker, Git, SQL, regex)
- Quick references (HTTP status codes, HTTPS, Process vs Thread)

View all presets:
```bash
python test_prompts.py --list-presets
```

## Custom Prompt Files

Create a JSON file with your prompts in one of these formats:

### Format 1: Simple Array
```json
[
  "What is a closure in JavaScript?",
  "Explain the MVC pattern",
  "Write a Python function to reverse a string"
]
```

### Format 2: Array of Objects
```json
[
  {
    "prompt": "What is a closure in JavaScript?",
    "category": "programming",
    "difficulty": "intermediate"
  },
  {
    "prompt": "Explain the MVC pattern",
    "category": "architecture"
  }
]
```

### Format 3: Object with Prompts Key
```json
{
  "prompts": [
    "What is a closure in JavaScript?",
    "Explain the MVC pattern"
  ],
  "metadata": {
    "author": "John Doe",
    "created": "2024-11-28"
  }
}
```

## Command-Line Options

```
--prompts-file PATH              JSON file containing prompts to test
--preset {default,high-value}    Use a predefined prompt set
--model MODEL                    Model to use (e.g., gpt-4o, claude-3-5-sonnet)
--temperature FLOAT              Temperature for responses (0.0-2.0, default: 0.7)
--output PATH                    Output directory (default: llm_responses)
--system-prompt TEXT             Custom system prompt to use
--system-prompt-file PATH        File containing system prompt
--list-presets                   List available presets and exit
-h, --help                       Show help message
```

## Output Files

The script creates three types of output files:

### 1. Individual JSON Files
```
llm_responses/
├── response_01.json
├── response_02.json
└── ...
```

Each file contains:
```json
{
  "prompt": "What is a closure in JavaScript?",
  "response": "A closure is a function that...",
  "error": null,
  "timestamp": "2024-11-28T10:30:45.123456",
  "model": "gpt-4o",
  "success": true
}
```

### 2. JSONL File
```
llm_responses/all_responses.jsonl
```

One JSON object per line (newline-delimited JSON) - ideal for streaming processing.

### 3. Summary File
```json
{
  "total_prompts": 20,
  "successful": 20,
  "failed": 0,
  "model": "gpt-4o",
  "model_params": {
    "temperature": 0.7
  },
  "timestamp": "2024-11-28T10:35:12.345678"
}
```

## Use Cases

### 1. Model Comparison
Test the same prompts with different models:

```bash
python test_prompts.py --model gpt-4o --output results/gpt4
python test_prompts.py --model claude-3-5-sonnet --output results/claude
python test_prompts.py --model granite4:3b --output results/granite
```

### 2. Temperature Testing
Compare responses at different temperatures:

```bash
python test_prompts.py --temperature 0.0 --output results/temp_0.0
python test_prompts.py --temperature 0.7 --output results/temp_0.7
python test_prompts.py --temperature 1.5 --output results/temp_1.5
```

### 3. System Prompt Testing
Test different assistant personalities or behaviors:

```bash
# Concise responses
python test_prompts.py \
  --system-prompt "You are a concise expert. Answer in 2-3 sentences max." \
  --output results/concise

# Beginner-friendly
python test_prompts.py \
  --system-prompt-file system_prompts/beginner_friendly.txt \
  --output results/beginner

# Senior engineer perspective
python test_prompts.py \
  --system-prompt-file system_prompts/senior_engineer.txt \
  --output results/senior
```

### 4. Custom Evaluation
Create domain-specific prompts:

```json
{
  "prompts": [
    "Explain microservices architecture",
    "What is event-driven design?",
    "Compare REST vs GraphQL"
  ]
}
```

```bash
python test_prompts.py --prompts-file architecture_prompts.json
```

### 5. Batch Testing
Test multiple configurations:

```bash
#!/bin/bash
for model in gpt-4o claude-3-5-sonnet granite4:3b; do
  python test_prompts.py --model $model --output "results/${model}"
done
```

### 6. A/B Testing System Prompts
Compare how different system prompts affect response quality:

```bash
# Test concise vs detailed responses
python test_prompts.py \
  --system-prompt-file system_prompts/concise_expert.txt \
  --output results/concise

python test_prompts.py \
  --system-prompt-file system_prompts/senior_engineer.txt \
  --output results/detailed

# Compare results
diff results/concise/summary.json results/detailed/summary.json
```

## Example Workflow

```bash
# 1. List available presets
python test_prompts.py --list-presets

# 2. Test with default prompts using a specific model
python test_prompts.py --model gpt-4o --temperature 0.5

# 3. Review results
cat llm_responses/summary.json
head llm_responses/all_responses.jsonl

# 4. Test with custom prompts
python test_prompts.py --prompts-file my_custom_prompts.json --output custom_results

# 5. Compare models
diff results/gpt4/summary.json results/claude/summary.json
```

## System Prompts

System prompts let you customize the AI's behavior, personality, and response style. Five pre-configured system prompts are included:

### Available System Prompts

| File | Purpose | Use Case |
|------|---------|----------|
| `concise_expert.txt` | Short, direct answers | Quick references, API docs |
| `beginner_friendly.txt` | Patient, detailed explanations | Teaching, tutorials |
| `code_reviewer.txt` | Focus on best practices | Code review, optimization |
| `senior_engineer.txt` | Production-ready advice | Architecture, trade-offs |
| `python_expert.txt` | Pythonic code examples | Python-specific tasks |

### Creating Custom System Prompts

Create a text file with your instructions:

```txt
You are a security-focused code reviewer.

Focus on:
- Authentication and authorization issues
- Input validation and sanitization
- SQL injection and XSS vulnerabilities
- Secure credential handling
- HTTPS and encryption requirements

Provide specific, actionable security recommendations.
```

Use it:
```bash
python test_prompts.py --system-prompt-file system_prompts/security_expert.txt
```

## Tips

1. **Start with presets**: Use `--preset high-value` to see immediate AI value
2. **Use JSONL for analysis**: The `.jsonl` format is perfect for streaming or big data tools
3. **Clear history**: Each prompt gets a fresh context (history is cleared between prompts)
4. **Fast iteration**: Tools are disabled by default for faster responses
5. **Model flexibility**: Auto-detects provider from model name (gpt-4o → OpenAI, claude → Anthropic)
6. **System prompts for consistency**: Use system prompts to ensure consistent response style across all prompts

## Requirements

- Python 3.9+
- Consoul SDK installed (`pip install -e .` from project root)
- Valid API keys for chosen model providers (OpenAI, Anthropic, etc.)

## Troubleshooting

**Error: "Model not found"**
- Check that you have API keys configured for the provider
- Use `--model` with a supported model name

**Error: "No prompts loaded"**
- Verify JSON file format matches one of the supported formats
- Check file path is correct

**Slow responses**
- Tools are already disabled for speed
- Consider using a faster model (e.g., gpt-3.5-turbo vs gpt-4)
- Reduce temperature for more deterministic (faster) responses

## License

Apache-2.0

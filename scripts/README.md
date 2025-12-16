# Consoul Scripts

This directory contains utility scripts for documentation generation, data scraping, and maintenance.

## generate_docs.py

Generates CLI documentation from `consoul describe` output.

### Usage

```bash
# Generate full CLI reference
python scripts/generate_docs.py

# Generate to custom output location
python scripts/generate_docs.py --output docs/cli-reference/index.md

# Generate documentation for specific command
python scripts/generate_docs.py tui --output docs/cli-reference/tui.md

# Use custom template
python scripts/generate_docs.py --template command.md.j2 tui
```

### How It Works

1. Runs `consoul describe` to extract CLI schema as JSON
2. Parses the schema to extract commands, arguments, and options
3. Renders Jinja2 templates with the extracted data
4. Writes formatted Markdown to the specified output file

### Templates

Templates are located in `src/consoul/templates/`:

- `cli_reference.md.j2` - Full CLI reference with all commands
- `command.md.j2` - Individual command page format

### Automation

To automatically regenerate documentation when CLI code changes, consider:

1. **Manual regeneration**: Run the script after CLI changes
2. **Git pre-commit hook**: Auto-regenerate on commit (see below)
3. **CI/CD integration**: Generate docs in your build pipeline

### Git Hook Example

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
# Auto-regenerate CLI documentation before commit

# Detect changes to CLI files
if git diff --cached --name-only | grep -q "src/consoul/__main__.py\|src/consoul/tui/cli.py"; then
    echo "CLI changes detected, regenerating documentation..."
    python scripts/generate_docs.py --output docs/cli-reference/index.md
    git add docs/cli-reference/index.md
fi
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

## consoul describe

The documentation generation relies on the `consoul describe` command, which introspects the Click CLI structure and outputs JSON schema.

### Examples

```bash
# Get full CLI schema
consoul describe

# Get specific command schema
consoul describe tui

# Output to file
consoul describe --output cli-schema.json

# Compact JSON
consoul describe --compact
```

### Schema Format

The JSON schema includes:

- **name**: Command name
- **description**: Command description from docstring
- **type**: "application", "group", or "command"
- **arguments**: List of positional arguments with types and defaults
- **options**: List of flags/options with types, defaults, and choices
- **commands**: Nested subcommands (for groups)

Example:

```json
{
  "name": "consoul",
  "type": "application",
  "commands": [
    {
      "name": "consoul tui",
      "description": "Launch Consoul TUI.",
      "type": "command",
      "arguments": [],
      "options": [
        {
          "name": "theme",
          "description": "Color theme",
          "type": "text",
          "flags": ["--theme"]
        }
      ]
    }
  ]
}
```

## Maintenance

### Updating Templates

Edit templates in `src/consoul/templates/` to change documentation format.

### Adding New Documentation Types

1. Create new Jinja2 template in `src/consoul/templates/`
2. Add rendering function in `src/consoul/utils/docs_generator.py`
3. Update `scripts/generate_docs.py` to support new type

### Troubleshooting

**"Command 'consoul' not found"**
- Install Consoul in development mode: `pip install -e .`
- Or use: `python -m consoul describe`

**"Template not found"**
- Ensure templates exist in `src/consoul/templates/`
- Check template name in script arguments

**"JSON serialization error"**
- This is handled automatically for Click sentinel values
- If you see this, a parameter has a non-serializable default

---

## scrape_ollama_library.py

Comprehensive scraper for extracting model data from ollama.com.

### Features

- 📥 Scrapes all models from ollama.com/library
- 🔍 Extracts detailed model information including:
  - Model descriptions and full names
  - Available tags (versions, quantizations)
  - Pull counts and popularity metrics
  - Capabilities (vision, tools)
  - License information
  - README content
- ⚡ Configurable scraping modes (basic/detailed)
- 🎯 Rate limiting to be respectful of servers
- 📊 Progress tracking for large scrapes
- 💾 JSON output for easy integration

### Usage

**Basic usage** (scrape all models with full details):
```bash
poetry run python scripts/scrape_ollama_library.py
```

**Quick scrape** (basic info only, faster):
```bash
poetry run python scripts/scrape_ollama_library.py --basic
```

**Limited scrape** (first 10 models):
```bash
poetry run python scripts/scrape_ollama_library.py --limit 10
```

**Custom output**:
```bash
poetry run python scripts/scrape_ollama_library.py --output my_models.json --pretty
```

**All options**:
```bash
poetry run python scripts/scrape_ollama_library.py \
    --output ollama_models.json \
    --namespace library \
    --limit 50 \
    --delay 1.5 \
    --pretty
```

### CLI Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--output` | `-o` | `ollama_library_full.json` | Output file path |
| `--namespace` | `-n` | `library` | Namespace to scrape |
| `--limit` | `-l` | None (all) | Max models to scrape |
| `--delay` | `-d` | `1.0` | Delay between requests (seconds) |
| `--basic` | | False | Fast mode (basic info only) |
| `--pretty` | | False | Pretty-print JSON output |

### Output Format

The script outputs a JSON array of model objects:

```json
[
  {
    "name": "llama3.2",
    "full_name": "Meta Llama 3.2",
    "description": "Meta's Llama 3.2 goes small with 1B and 3B models.",
    "url": "https://ollama.com/library/llama3.2",
    "num_pulls": "100M+",
    "num_tags": "12",
    "updated": "2 days ago",
    "license": "Llama 3.2 Community License",
    "tags": [
      {
        "name": "latest",
        "size": "1.9 GB",
        "quantization": "Q4_0",
        "parameters": "3B",
        "updated": ""
      }
    ],
    "supports_vision": false,
    "supports_tools": true,
    "context_length": "128K",
    "family": "llama",
    "readme": "..."
  }
]
```

### Examples

**1. Create a local model descriptions database:**
```bash
# Scrape all models with descriptions
poetry run python scripts/scrape_ollama_library.py \
    --output data/ollama_library.json \
    --pretty

# Use in your code
import json
with open('data/ollama_library.json') as f:
    models = json.load(f)
    descriptions = {m['name']: m['description'] for m in models}
```

**2. Find all vision models:**
```bash
# Scrape and filter
poetry run python scripts/scrape_ollama_library.py --output /tmp/all.json
python -c "
import json
with open('/tmp/all.json') as f:
    models = json.load(f)
vision_models = [m['name'] for m in models if m['supports_vision']]
print('Vision models:', ', '.join(vision_models))
"
```

**3. Get model statistics:**
```bash
poetry run python scripts/scrape_ollama_library.py --basic --output /tmp/stats.json
python -c "
import json
with open('/tmp/stats.json') as f:
    models = json.load(f)
print(f'Total models: {len(models)}')
"
```

### Performance

- **Basic mode**: ~1 second for all models (single page fetch)
- **Detailed mode**: ~3-5 minutes for ~200 models (1s delay between requests)
- **Fast detailed**: ~1-2 minutes with `--delay 0.5` (be careful!)

### Notes

- Be respectful of ollama.com servers - use appropriate delays
- The HTML structure may change - adjust selectors if needed
- Some fields may be empty if not found on the page
- Vision/tools detection is heuristic-based (keyword matching)

### Integration with Consoul

Use the scraped data to enhance local model descriptions:

```python
from consoul.sdk.services.model import ModelService
import json

# Load scraped descriptions
with open('ollama_library_full.json') as f:
    library = json.load(f)
    descriptions = {m['name']: m for m in library}

# Get local models
service = ModelService.from_config()
local_models = service.list_ollama_models()

# Enrich with library data
for model in local_models:
    base_name = model.name.split(':')[0]
    if base_name in descriptions:
        lib_data = descriptions[base_name]
        print(f"{model.name}: {lib_data['description']}")
        print(f"  Vision: {lib_data['supports_vision']}")
        print(f"  Tools: {lib_data['supports_tools']}")
```

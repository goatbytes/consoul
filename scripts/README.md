# Consoul Documentation Scripts

This directory contains scripts for generating and maintaining Consoul documentation.

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

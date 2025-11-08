# Installation

This guide will help you install Consoul on your system.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Installation Methods

### From PyPI (Recommended)

Install the latest stable release from PyPI:

```bash
pip install consoul
```

For development dependencies:

```bash
pip install 'consoul[dev]'
```

### From Source

Clone the repository and install in development mode:

```bash
# Clone the repository
git clone https://github.com/goatbytes/consoul.git
cd consoul

# Install with Poetry
poetry install --with dev,docs,security

# Or install with pip in editable mode
pip install -e '.[dev]'
```

### Using pipx (Isolated Installation)

For an isolated installation that doesn't affect your system Python:

```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Consoul
pipx install consoul
```

## Verify Installation

After installation, verify that Consoul is installed correctly:

```bash
# Check version
consoul --version

# Run help to see available commands
consoul --help
```

## Configuration

### API Keys

Consoul requires API keys for AI providers. Set them as environment variables:

**For Anthropic (Claude):**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**For Google (Gemini):**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

Add these to your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.) to make them permanent:

```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Configuration File

Create a configuration file at `~/.config/consoul/config.yaml`:

```bash
# Create config directory
mkdir -p ~/.config/consoul

# Create basic config file
cat > ~/.config/consoul/config.yaml << EOF
provider: anthropic
model: claude-3-5-sonnet-20241022
theme: dark
save_conversations: true
EOF
```

## Troubleshooting

### Command Not Found

If you get a "command not found" error after installation:

1. Ensure `pip` installs to a directory in your PATH:
   ```bash
   python3 -m pip install --user consoul
   ```

2. Add Python user bin to your PATH:
   ```bash
   # For Linux/macOS
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

### Permission Errors

If you encounter permission errors during installation:

```bash
# Use --user flag to install in your home directory
pip install --user consoul
```

### Python Version Issues

If your default `python` is not 3.10+:

```bash
# Install with python3 explicitly
python3 -m pip install consoul

# Or use pyenv to manage Python versions
pyenv install 3.12.3
pyenv global 3.12.3
```

### Missing Dependencies

If you encounter missing dependency errors:

```bash
# Upgrade pip
pip install --upgrade pip

# Install with all dependencies
pip install --upgrade consoul
```

## Next Steps

- [Quick Start Guide](quickstart.md) – Get started with your first conversation
- [Configuration Guide](user-guide/configuration.md) – Customize Consoul for your workflow
- [User Guide](user-guide/getting-started.md) – Learn all Consoul features

## Uninstallation

To remove Consoul:

```bash
# Standard installation
pip uninstall consoul

# pipx installation
pipx uninstall consoul
```

To remove configuration files:

```bash
rm -rf ~/.config/consoul
```

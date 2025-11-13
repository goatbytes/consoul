# Configuration

Learn how to configure Consoul to match your workflow and preferences.

## Configuration File

Consoul uses a YAML configuration file located at:

```
~/.config/consoul/config.yaml
```

### Creating the Configuration

```bash
# Create config directory
mkdir -p ~/.config/consoul

# Create basic config
cat > ~/.config/consoul/config.yaml << 'EOF'
provider: anthropic
model: claude-3-5-sonnet-20241022
theme: dark
save_conversations: true
EOF
```

## Core Settings

### Provider Configuration

```yaml
# Default provider (anthropic, openai, google)
provider: anthropic

# Default model for the provider
model: claude-3-5-sonnet-20241022

# Provider-specific settings
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet-20241022
    max_tokens: 4096
    temperature: 0.7

  openai:
    api_key: ${OPENAI_API_KEY}
    default_model: gpt-4
    max_tokens: 2048
    temperature: 0.7

  google:
    api_key: ${GOOGLE_API_KEY}
    default_model: gemini-pro
```

### UI Settings

```yaml
# Theme (dark, light, auto)
theme: dark

# Editor for multi-line input (vim, nano, emacs)
editor: vim

# Show timestamps in TUI
show_timestamps: true

# Syntax highlighting
syntax_highlighting: true

# Color scheme
colors:
  primary: cyan
  accent: purple
  error: red
  success: green
```

### Conversation Settings

```yaml
# Save conversations to disk
save_conversations: true

# Maximum number of messages to keep in history
max_history: 50

# Auto-save interval (seconds)
auto_save_interval: 30

# Conversation storage location
conversation_dir: ~/.config/consoul/conversations
```

### Default Behavior

```yaml
# Default temperature (0.0 - 1.0)
temperature: 0.7

# Default max tokens
max_tokens: 2048

# Default system prompt
system_prompt: "You are a helpful AI assistant for developers."

# Stream responses in real-time
stream: true
```

## Environment Variables

### API Keys

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google
export GOOGLE_API_KEY="..."
```

### Configuration Override

```bash
# Override config file location
export CONSOUL_CONFIG_PATH="/custom/path/config.yaml"

# Override conversation directory
export CONSOUL_CONVERSATION_DIR="/custom/conversations"
```

## Provider-Specific Configuration

### Anthropic (Claude)

```yaml
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet-20241022
    max_tokens: 4096
    temperature: 0.7

    # Available models
    models:
      - claude-3-5-sonnet-20241022
      - claude-3-opus-20240229
      - claude-3-sonnet-20240229
      - claude-3-haiku-20240307
```

### OpenAI

```yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    default_model: gpt-4
    max_tokens: 2048
    temperature: 0.7

    # Organization (optional)
    organization: org-...

    # Available models
    models:
      - gpt-4
      - gpt-4-turbo-preview
      - gpt-3.5-turbo
```

### Google (Gemini)

```yaml
providers:
  google:
    api_key: ${GOOGLE_API_KEY}
    default_model: gemini-pro

    # Available models
    models:
      - gemini-pro
      - gemini-pro-vision
```

## Advanced Configuration

### Context Management

```yaml
context:
  # Maximum context size (tokens)
  max_context_size: 100000

  # Maximum file size to include (bytes)
  max_file_size: 1048576  # 1MB

  # File patterns to exclude
  exclude_patterns:
    - "*.pyc"
    - "__pycache__/*"
    - ".git/*"
    - "node_modules/*"
```

### Logging

```yaml
logging:
  # Log level (DEBUG, INFO, WARNING, ERROR)
  level: INFO

  # Log file location
  file: ~/.config/consoul/consoul.log

  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

  # Log to console
  console: false
```

### Performance

```yaml
performance:
  # Enable caching
  cache_enabled: true

  # Cache directory
  cache_dir: ~/.cache/consoul

  # Cache TTL (seconds)
  cache_ttl: 3600

  # Maximum concurrent requests
  max_concurrent_requests: 5
```

### Plugins

```yaml
plugins:
  # Enable plugin system
  enabled: true

  # Plugin directory
  directory: ~/.config/consoul/plugins

  # Auto-load plugins
  auto_load:
    - git_integration
    - code_execution
```

## Command-Line Overrides

Configuration can be overridden via command-line flags:

```bash
# Override provider
consoul chat --provider openai "Your question"

# Override model
consoul chat --model gpt-4 "Your question"

# Override temperature
consoul chat --temperature 0.2 "Your question"

# Override max tokens
consoul chat --max-tokens 1000 "Your question"

# Custom system prompt
consoul chat --system "You are a Python expert" "Your question"
```

## Configuration Profiles

### Creating Profiles

```yaml
# ~/.config/consoul/config.yaml
default_profile: development

profiles:
  development:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
    temperature: 0.7

  production:
    provider: openai
    model: gpt-4
    temperature: 0.5
    max_tokens: 1024

  creative:
    provider: anthropic
    model: claude-3-opus-20240229
    temperature: 0.9
```

### Using Profiles

```bash
# Use specific profile
consoul chat --profile production "Your question"

# Set default profile
consoul config set default_profile creative
```

## Configuration Management

### View Current Configuration

```bash
# Show all settings
consoul config show

# Show specific setting
consoul config get provider
```

### Update Configuration

```bash
# Set a value
consoul config set provider openai

# Set nested value
consoul config set providers.anthropic.temperature 0.8
```

### Reset Configuration

```bash
# Reset to defaults
consoul config reset

# Reset specific setting
consoul config reset theme
```

## Example Configurations

### Minimal Configuration

```yaml
provider: anthropic
model: claude-3-5-sonnet-20241022
```

### Full-Featured Configuration

```yaml
# Core settings
provider: anthropic
model: claude-3-5-sonnet-20241022
theme: dark

# Providers
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet-20241022
    max_tokens: 4096
    temperature: 0.7

  openai:
    api_key: ${OPENAI_API_KEY}
    default_model: gpt-4
    temperature: 0.7

# UI
ui:
  editor: vim
  show_timestamps: true
  syntax_highlighting: true

# Conversations
conversations:
  save: true
  max_history: 100
  auto_save_interval: 30

# Context
context:
  max_context_size: 100000
  max_file_size: 1048576
  exclude_patterns:
    - "*.pyc"
    - "__pycache__/*"
    - ".git/*"

# Logging
logging:
  level: INFO
  file: ~/.config/consoul/consoul.log
```

## Tool Configuration

### Overview

Consoul's tool calling system allows AI models to execute commands and interact with your system with security controls. See the [Tool Calling Guide](../tools.md) for comprehensive documentation.

### Basic Tool Settings

```yaml
tools:
  # Enable/disable tool calling
  enabled: true

  # Permission policy (recommended approach)
  permission_policy: balanced  # paranoid, balanced, trusting, unrestricted

  # Audit logging
  audit_logging: true
  audit_log_file: ~/.consoul/tool_audit.jsonl

  # Tool whitelist (empty = all tools allowed)
  allowed_tools:
    - bash_execute

  # Bash-specific settings
  bash:
    timeout: 30
    allow_directory_change: true
    whitelist:
      - "git status"
      - "ls"
    blocked_commands:
      - "^sudo\\s"
      - "rm\\s+(-[rf]+\\s+)?/"
```

### Permission Policies

| Policy | Description | Use Case |
|--------|-------------|----------|
| **paranoid** | Prompt for every command | Production, maximum security |
| **balanced** ⭐ | Auto-approve SAFE, prompt for CAUTION+ | Recommended default |
| **trusting** | Auto-approve SAFE+CAUTION, prompt DANGEROUS | Development convenience |
| **unrestricted** | Auto-approve all (DANGEROUS) | Testing only |

### Example Configurations

**Development:**
```yaml
tools:
  enabled: true
  permission_policy: balanced
  bash:
    timeout: 60
    whitelist:
      - "git status"
      - "npm test"
      - "make test"
```

**Production:**
```yaml
tools:
  enabled: true
  permission_policy: paranoid
  bash:
    timeout: 30
    allow_directory_change: false
    blocked_commands:
      - "rm"
      - "mv"
      - "chmod"
```

### See Also

- **[Tool Calling Guide](../tools.md)** - Complete documentation
- **[Configuration Examples](../examples/tool-calling-config.yaml)** - Pre-configured templates
- **[Custom Tool Development](../examples/custom-tool-example.py)** - Working examples

## Troubleshooting

### Configuration Not Loading

1. Check file location: `~/.config/consoul/config.yaml`
2. Verify YAML syntax: `python -c "import yaml; yaml.safe_load(open('~/.config/consoul/config.yaml'))"`
3. Check permissions: `ls -la ~/.config/consoul/`

### Environment Variable Issues

```bash
# Check if variable is set
echo $ANTHROPIC_API_KEY

# Verify it's in your shell config
cat ~/.zshrc | grep ANTHROPIC_API_KEY

# Test with explicit variable
ANTHROPIC_API_KEY=your-key consoul chat "test"
```

### Provider Connection Issues

1. Verify API key is correct
2. Check network connectivity
3. Try a different provider
4. Enable debug logging: `consoul config set logging.level DEBUG`

## Next Steps

- [Getting Started](getting-started.md) – Learn basic usage
- [Usage Examples](usage.md) – Common configuration scenarios
- [Tool Calling Guide](../tools.md) – AI command execution
- [API Reference](../api/index.md) – Package documentation

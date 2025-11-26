# TUI Configuration

This guide covers TUI-specific configuration options for customizing the Consoul Terminal User Interface.

## Configuration File

Consoul stores configuration in YAML format:

```
~/.config/consoul/config.yaml
```

### Basic Structure

```yaml
# TUI Configuration
tui:
  # Appearance
  theme: consoul-dark
  show_sidebar: true
  sidebar_width: "20%"
  show_timestamps: true
  show_token_count: true

  # Input
  enable_multiline_input: true
  input_syntax_highlighting: true

  # Performance
  gc_mode: streaming-aware
  gc_interval_seconds: 30.0
  gc_generation: 0
  stream_buffer_size: 200
  stream_debounce_ms: 150
  stream_renderer: markdown

  # Conversation List
  initial_conversation_load: 50
  enable_virtualization: true

  # Behavior
  enable_mouse: true
  vim_mode: false
  auto_generate_titles: true

  # Debug
  debug: false
  log_file: null
```

## Appearance Settings

### Theme

Choose visual theme:

```yaml
tui:
  theme: consoul-dark
```

**Options:**
- `consoul-dark` (default) - Official Consoul dark theme
- `consoul-light` - Official Consoul light theme
- `monokai`, `dracula`, `nord`, `gruvbox`, `tokyo-night`, etc. - Textual built-in themes

[See all available themes →](themes.md)

**Change via Settings**: Press `^comma` → Appearance tab → Theme dropdown

### Sidebar Visibility

Toggle conversation list sidebar:

```yaml
tui:
  show_sidebar: true
```

**Values:**
- `true`: Show sidebar on startup (default)
- `false`: Hide sidebar on startup

**Runtime Toggle**: Press `^b` or click conversation count in header

### Sidebar Width

Control sidebar width:

```yaml
tui:
  sidebar_width: "20%"
```

**Values:**
- Percentage: `"20%"`, `"30%"`, etc.
- Fixed units: `"40"` (characters)
- Min/Max enforced: 20-40 characters

### Timestamps

Show/hide message timestamps:

```yaml
tui:
  show_timestamps: true
```

**Values:**
- `true`: Show timestamp on every message (default)
- `false`: Hide timestamps for cleaner UI

**Display Format:**
```
⏱ 16:13:59
```

**Change via Settings**: Press `^comma` → Appearance tab → Show Timestamps

### Token Count

Show/hide token usage metrics:

```yaml
tui:
  show_token_count: true
```

**Values:**
- `true`: Show token metrics (default)
- `false`: Hide token information

**Display Format:**
```
34.16 tok/sec | 187 tokens | 1.27s to first token
```

**Change via Settings**: Press `^comma` → Appearance tab → Show Token Count

## Input Settings

### Multiline Input

Allow multi-line input with Shift+Enter:

```yaml
tui:
  enable_multiline_input: true
```

**Values:**
- `true`: Shift+Enter creates new line, Enter sends (default)
- `false`: Enter always sends (legacy behavior)

### Input Syntax Highlighting

Enable code highlighting in input area:

```yaml
tui:
  input_syntax_highlighting: true
```

**Values:**
- `true`: Highlight code in input (default)
- `false`: Plain text (faster on slow terminals)

**Features:**
- Auto-detection of code
- Python, JavaScript, Shell, and more
- Theme-aware colors

## Performance Settings

### Garbage Collection Mode

Control Python garbage collection strategy:

```yaml
tui:
  gc_mode: streaming-aware
```

**Options:**
- `streaming-aware`: Pause GC during streaming, collect after (default)
- `auto`: Python's default GC behavior
- `manual`: Periodic GC at intervals

**Recommendation**: Use `streaming-aware` for smoothest streaming

### GC Interval

Seconds between garbage collections (manual/streaming-aware modes):

```yaml
tui:
  gc_interval_seconds: 30.0
```

**Values:**
- Range: 5.0 - 300.0 seconds
- Default: 30.0

**Impact:**
- Lower: More frequent GC, less memory, slight performance hit
- Higher: Less frequent GC, more memory, smoother performance

### GC Generation

Which garbage collection generation to collect:

```yaml
tui:
  gc_generation: 0
```

**Values:**
- `0`: Young objects only (fastest, default)
- `1`: Young + middle-aged objects
- `2`: Full collection (slowest, most thorough)

### Stream Buffer Size

Characters to buffer before rendering:

```yaml
tui:
  stream_buffer_size: 200
```

**Values:**
- Range: 50 - 1000 characters
- Default: 200

**Impact:**
- Lower: More frequent updates, more CPU
- Higher: Fewer updates, smoother, slight delay

### Stream Debounce

Milliseconds to debounce markdown renders:

```yaml
tui:
  stream_debounce_ms: 150
```

**Values:**
- Range: 50 - 500 milliseconds
- Default: 150

**Impact:**
- Lower: More frequent renders, more CPU
- Higher: Fewer renders, smoother, slight delay

### Stream Renderer

Widget type for streaming responses:

```yaml
tui:
  stream_renderer: markdown
```

**Options:**
- `markdown`: Rich markdown rendering (default)
- `richlog`: Simple log-style rendering
- `hybrid`: Mix of both

**Recommendation**: Use `markdown` for best experience

## Conversation List Settings

### Initial Load

Number of conversations to load initially:

```yaml
tui:
  initial_conversation_load: 50
```

**Values:**
- Range: 10 - 200 conversations
- Default: 50

**Impact:**
- Lower: Faster startup, fewer visible conversations
- Higher: Slower startup, more conversations immediately visible

### Virtualization

Use virtual scrolling for large lists:

```yaml
tui:
  enable_virtualization: true
```

**Values:**
- `true`: Virtual scrolling (default) - better performance with many conversations
- `false`: Render all conversations - simpler but slower with 100+ conversations

## Behavior Settings

### Mouse Support

Enable mouse interactions:

```yaml
tui:
  enable_mouse: true
```

**Values:**
- `true`: Mouse clicks and scrolling enabled (default)
- `false`: Keyboard-only mode

### Vim Mode

Enable vim-style navigation:

```yaml
tui:
  vim_mode: false
```

**Values:**
- `true`: Vim keybindings (h/j/k/l navigation)
- `false`: Standard keybindings (default)

**Note**: Vim mode is experimental

### Auto-Generate Titles

Automatically generate conversation titles:

```yaml
tui:
  auto_generate_titles: true
```

**Values:**
- `true`: Auto-generate titles after first exchange (default)
- `false`: Use generic titles

**Configuration Options:**

```yaml
tui:
  auto_generate_titles: true
  auto_title_provider: null      # null = auto-detect from current model
  auto_title_model: null          # null = use provider default
  auto_title_api_key: null        # null = use from env/config
  auto_title_max_tokens: 20
  auto_title_temperature: 0.7
  auto_title_prompt: "Generate a concise 2-8 word title..."
```

**Provider/Model Options:**
- `auto_title_provider`: `openai`, `anthropic`, `google`, `ollama`, or `null`
- `auto_title_model`: Specific model name or `null` for default

## Debug Settings

### Debug Mode

Enable verbose logging:

```yaml
tui:
  debug: false
```

**Values:**
- `true`: Enable debug logging
- `false`: Normal logging (default)

**Impact:**
- True: Detailed logs, helpful for troubleshooting, slower
- False: Essential logs only

### Log File

Custom log file path:

```yaml
tui:
  log_file: null
```

**Values:**
- `null`: Use default (`textual.log` in current directory)
- `"/path/to/file.log"`: Custom log file path

## Complete Example

```yaml
# ~/.config/consoul/config.yaml

tui:
  # Appearance
  theme: consoul-dark
  show_sidebar: true
  sidebar_width: "25%"
  show_timestamps: true
  show_token_count: true

  # Input
  enable_multiline_input: true
  input_syntax_highlighting: true

  # Performance
  gc_mode: streaming-aware
  gc_interval_seconds: 30.0
  gc_generation: 0
  stream_buffer_size: 200
  stream_debounce_ms: 150
  stream_renderer: markdown

  # Conversation List
  initial_conversation_load: 50
  enable_virtualization: true

  # Behavior
  enable_mouse: true
  vim_mode: false
  auto_generate_titles: true
  auto_title_max_tokens: 20
  auto_title_temperature: 0.7

  # Debug
  debug: false
  log_file: null
```

## Environment Variables

Override config with environment variables:

```bash
# Theme
export CONSOUL_THEME=nord

# Debug mode
export CONSOUL_DEBUG=1

# Launch Consoul TUI
consoul tui
```

**Note**: Environment variables override config file values

## Configuration Management

### View Current Config

```bash
# Display current configuration
consoul config show

# Display specific section
consoul config show tui
```

### Edit Config

```bash
# Open config in default editor
consoul config edit

# Open in specific editor
EDITOR=vim consoul config edit
```

### Validate Config

```bash
# Check config syntax
consoul config validate

# Check specific file
consoul config validate ~/.config/consoul/config.yaml
```

**Note**: These CLI commands may be future features - verify availability

## Performance Tuning

### For Slow Terminals

```yaml
tui:
  input_syntax_highlighting: false
  stream_buffer_size: 500
  stream_debounce_ms: 300
  gc_interval_seconds: 60.0
```

### For Fast Terminals / High Performance

```yaml
tui:
  input_syntax_highlighting: true
  stream_buffer_size: 100
  stream_debounce_ms: 50
  gc_interval_seconds: 15.0
```

### For Low Memory

```yaml
tui:
  gc_mode: manual
  gc_interval_seconds: 20.0
  gc_generation: 2  # Full collection
  initial_conversation_load: 25
  enable_virtualization: true
```

### For Maximum Smoothness

```yaml
tui:
  gc_mode: streaming-aware
  stream_buffer_size: 300
  stream_debounce_ms: 200
  stream_renderer: markdown
```

## Troubleshooting

### Config Not Loading

**Problem**: Changes to config file not applied

**Solutions:**

1. Restart Consoul
2. Check YAML syntax:
   ```bash
   consoul config validate
   ```
3. Check file location:
   ```bash
   ls -la ~/.config/consoul/config.yaml
   ```
4. Check file permissions:
   ```bash
   chmod 644 ~/.config/consoul/config.yaml
   ```

### Invalid YAML

**Problem**: Config file has syntax errors

**Common Issues:**

```yaml
# ❌ Wrong: mixed spaces and tabs
tui:
    theme: consoul-dark  # Tab here
  debug: false           # Spaces here

# ✅ Correct: consistent spaces
tui:
  theme: consoul-dark
  debug: false

# ❌ Wrong: missing quotes on special values
tui:
  sidebar_width: 20%

# ✅ Correct: quoted string values
tui:
  sidebar_width: "20%"
```

### Performance Issues

**Problem**: TUI is slow or laggy

**Solutions:**

1. Disable syntax highlighting
2. Increase buffer and debounce values
3. Reduce conversation load
4. Use simpler theme (Consoul Dark)
5. Enable virtualization

**Optimized Config:**
```yaml
tui:
  theme: consoul-dark
  input_syntax_highlighting: false
  stream_buffer_size: 400
  stream_debounce_ms: 250
  initial_conversation_load: 30
  enable_virtualization: true
```

### Memory Issues

**Problem**: High memory usage

**Solutions:**

1. Enable manual GC with short intervals
2. Use full GC generation
3. Reduce conversation load

**Memory-Optimized Config:**
```yaml
tui:
  gc_mode: manual
  gc_interval_seconds: 15.0
  gc_generation: 2
  initial_conversation_load: 25
  enable_virtualization: true
```

## Best Practices

### Organization

Use comments to document your choices:

```yaml
tui:
  # Dark theme for night coding
  theme: consoul-dark

  # Always show sidebar for quick access
  show_sidebar: true

  # Optimized for smooth streaming on M1 Mac
  stream_buffer_size: 200
  stream_debounce_ms: 150
```

### Version Control

Track your config in git:

```bash
cd ~/.config/consoul
git init
git add config.yaml
git commit -m "Initial Consoul config"

# .gitignore
echo "*.log" >> .gitignore
echo "conversations/" >> .gitignore
```

### Backup

Regular backups:

```bash
# Manual backup
cp ~/.config/consoul/config.yaml ~/backups/consoul-config-$(date +%Y%m%d).yaml

# Automated (add to cron)
0 0 * * 0 cp ~/.config/consoul/config.yaml ~/backups/consoul-config-$(date +\%Y\%m\%d).yaml
```

## Configuration Schema Reference

Complete list of all TUI configuration options:

```yaml
tui:
  # Appearance
  theme: string                    # Theme name
  show_sidebar: boolean            # Sidebar visibility
  sidebar_width: string            # CSS width (e.g., "20%", "30")
  show_timestamps: boolean         # Message timestamps
  show_token_count: boolean        # Token metrics

  # Input
  enable_multiline_input: boolean  # Shift+Enter for newline
  input_syntax_highlighting: bool  # Code highlighting in input

  # Performance
  gc_mode: string                  # "auto" | "manual" | "streaming-aware"
  gc_interval_seconds: float       # 5.0 - 300.0
  gc_generation: integer           # 0 | 1 | 2
  stream_buffer_size: integer      # 50 - 1000
  stream_debounce_ms: integer      # 50 - 500
  stream_renderer: string          # "markdown" | "richlog" | "hybrid"

  # Conversation List
  initial_conversation_load: int   # 10 - 200
  enable_virtualization: boolean   # Virtual scrolling

  # Behavior
  enable_mouse: boolean            # Mouse support
  vim_mode: boolean                # Vim keybindings
  auto_generate_titles: boolean    # Auto title generation
  auto_title_provider: string?     # Provider for titles
  auto_title_model: string?        # Model for titles
  auto_title_api_key: string?      # API key for titles
  auto_title_prompt: string        # Title generation prompt
  auto_title_max_tokens: integer   # 5 - 100
  auto_title_temperature: float    # 0.0 - 2.0

  # Debug
  debug: boolean                   # Debug logging
  log_file: string?                # Custom log file path
```

## Next Steps

- [Themes](themes.md) - Choose your theme
- [Interface Guide](interface.md) - Understand the UI
- [Keyboard Shortcuts](keyboard-shortcuts.md) - Master navigation
- [Features](features.md) - Explore capabilities

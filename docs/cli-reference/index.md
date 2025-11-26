# CLI Reference

Complete reference for all Consoul commands and options.

## Table of Contents

- [`consoul chat`](#consoul-chat) - Start an interactive chat session.

- [`consoul describe`](#consoul-describe) - Describe Consoul CLI commands and their schemas.

- [`consoul history`](#consoul-history) - Manage conversation history.

- [`consoul history clear`](#consoul-history-clear) - Delete all conversation history.

- [`consoul history delete`](#consoul-history-delete) - Delete a conversation session.

- [`consoul history export`](#consoul-history-export) - Export conversation(s) to a file.

- [`consoul history import`](#consoul-history-import) - Import conversations from Consoul JSON export.

- [`consoul history list`](#consoul-history-list) - List recent conversation sessions.

- [`consoul history search`](#consoul-history-search) - Search conversation history using full-text search.

- [`consoul history show`](#consoul-history-show) - Show conversation details for a specific session.

- [`consoul history stats`](#consoul-history-stats) - Show conversation history statistics.

- [`consoul history summary`](#consoul-history-summary) - Show conversation summary for a specific session.

- [`consoul init`](#consoul-init) - Initialize a new Consoul configuration file.

- [`consoul preset`](#consoul-preset) - Manage tool presets.

- [`consoul preset list`](#consoul-preset-list) - List all available tool presets (built-in + custom).

- [`consoul tui`](#consoul-tui) - Launch Consoul TUI.

## Global Options

These options can be used with any command:

- `--help` - Show help message and exit
- `--profile PROFILE` - Configuration profile to use (default: default)
- `--list-profiles` - List all available profiles and exit
- `--temperature FLOAT` - Override model temperature (0.0-2.0)
- `--model TEXT` - Override model name
- `--max-tokens INT` - Override maximum tokens to generate

## Commands

### `consoul chat`

Start an interactive chat session.

```bash
consoul chat
```

---

### `consoul describe`

Describe Consoul CLI commands and their schemas.

```bash
consoul describe [command_path] [options]
```

**Arguments:**

- `command_path` -  (optional, default: )
  - Type: `text`

**Options:**

- `-f, --format` - Output format (default: json)
  - Type: `choice`
  - Choices: `json`, `markdown`
  - Default: `json`

- `-o, --output` - Write output to file instead of stdout
  - Type: `path`
  - Default: ``

- `--indent` - JSON indentation spaces (default: 2)
  - Type: `integer`
  - Default: `2`

- `--compact` - Compact JSON output (no indentation)
  - Type: `boolean`

---

### `consoul history`

Manage conversation history.

```bash
consoul history
```

**Subcommands:**

- `clear` - Delete all conversation history.

- `delete` - Delete a conversation session.

- `export` - Export conversation(s) to a file.

- `import` - Import conversations from Consoul JSON export.

- `list` - List recent conversation sessions.

- `search` - Search conversation history using full-text search.

- `show` - Show conversation details for a specific session.

- `stats` - Show conversation history statistics.

- `summary` - Show conversation summary for a specific session.

See individual command documentation for details.

---

### `consoul history clear`

Delete all conversation history.

```bash
consoul history clear [options]
```

**Options:**

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

- `--yes` - Confirm the action without prompting.
  - Type: `boolean`

---

### `consoul history delete`

Delete a conversation session.

```bash
consoul history delete <session_id> [options]
```

**Arguments:**

- `session_id` -  (required)
  - Type: `text`

**Options:**

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

- `--yes` - Confirm the action without prompting.
  - Type: `boolean`

---

### `consoul history export`

Export conversation(s) to a file.

```bash
consoul history export [session_id] <output_file> [options]
```

**Arguments:**

- `session_id` -  (optional, default: )
  - Type: `text`

- `output_file` -  (required)
  - Type: `path`

**Options:**

- `-f, --format` - Output format (default: json)
  - Type: `choice`
  - Choices: `json`, `markdown`, `html`, `csv`
  - Default: `json`

- `--all` - Export all conversations (JSON format only)
  - Type: `boolean`

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul history import`

Import conversations from Consoul JSON export.

```bash
consoul history import <import_file> [options]
```

**Arguments:**

- `import_file` -  (required)
  - Type: `path`

**Options:**

- `--dry_run` - Validate import file without importing
  - Type: `boolean`

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul history list`

List recent conversation sessions.

```bash
consoul history list [options]
```

**Options:**

- `-n, --limit` - Number of conversations to show (default: 10)
  - Type: `integer`
  - Default: `10`

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul history search`

Search conversation history using full-text search.

```bash
consoul history search <query> [options]
```

**Arguments:**

- `query` -  (required)
  - Type: `text`

**Options:**

- `-n, --limit` - Maximum number of results to return (default: 20)
  - Type: `integer`
  - Default: `20`

- `--model` - Filter results by model name
  - Type: `text`
  - Default: ``

- `--after` - Filter results after this date (ISO format: YYYY-MM-DD)
  - Type: `text`
  - Default: ``

- `--before` - Filter results before this date (ISO format: YYYY-MM-DD)
  - Type: `text`
  - Default: ``

- `-c, --context` - Number of surrounding messages to show (default: 2)
  - Type: `integer`
  - Default: `2`

- `-f, --format` - Output format (default: text)
  - Type: `choice`
  - Choices: `text`, `json`
  - Default: `text`

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul history show`

Show conversation details for a specific session.

```bash
consoul history show <session_id> [options]
```

**Arguments:**

- `session_id` -  (required)
  - Type: `text`

**Options:**

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul history stats`

Show conversation history statistics.

```bash
consoul history stats [options]
```

**Options:**

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul history summary`

Show conversation summary for a specific session.

```bash
consoul history summary <session_id> [options]
```

**Arguments:**

- `session_id` -  (required)
  - Type: `text`

**Options:**

- `--db_path` - Path to history database (default: ~/.consoul/history.db)
  - Type: `path`
  - Default: ``

---

### `consoul init`

Initialize a new Consoul configuration file.

```bash
consoul init <config_path>
```

**Arguments:**

- `config_path` -  (required)
  - Type: `path`

---

### `consoul preset`

Manage tool presets.

```bash
consoul preset
```

**Subcommands:**

- `list` - List all available tool presets (built-in + custom).

See individual command documentation for details.

---

### `consoul preset list`

List all available tool presets (built-in + custom).

```bash
consoul preset list
```

---

### `consoul tui`

Launch Consoul TUI.

```bash
consoul tui [options]
```

**Options:**

- `--theme` - Color theme (monokai, dracula, nord, gruvbox)
  - Type: `text`
  - Default: ``

- `--debug` - Enable debug logging
  - Type: `boolean`

- `--log_file` - Debug log file path
  - Type: `path`
  - Default: ``

- `--tools` - Tool specification: 'all', 'none', 'safe', 'caution', 'dangerous', category names (search/file-edit/web/execute), or comma-separated tool names (bash,grep,code_search)
  - Type: `text`
  - Default: ``

- `--preset` - Tool preset: 'readonly', 'development', 'safe-research', 'power-user', or custom preset name. Overrides --tools flag.
  - Type: `text`
  - Default: ``

- `--test_mode` - Test mode (auto-exit)
  - Type: `boolean`

---

## See Also

- [User Guide](../user-guide/getting-started.md) - Getting started with Consoul
- [TUI Guide](../user-guide/tui.md) - Terminal User Interface documentation
- [Configuration](../user-guide/configuration.md) - Configuration reference

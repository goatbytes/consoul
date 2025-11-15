# File Editing Examples

This directory contains working examples demonstrating Consoul's file editing capabilities.

## Examples

### 1. simple_edit.py

Basic file editing with natural language requests.

**What it demonstrates:**
- Fixing specific lines
- Adding logging statements
- Updating configuration values
- Adding error handling
- Preview changes before applying (dry-run)

**Run it:**
```bash
cd docs/examples/file-editing
python simple_edit.py
```

**Key concepts:**
- Natural language file editing
- Line-based edits
- Approval workflow
- Audit logging

### 2. search_replace.py

Progressive matching with tolerance levels.

**What it demonstrates:**
- **Strict matching**: Exact character-for-character
- **Whitespace tolerance**: Ignores indentation differences
- **Fuzzy matching**: Handles typos (≥80% similarity)
- Tab/space preservation
- CRLF/LF preservation
- Multiple edits in one operation
- Similarity suggestions ("Did you mean...?")

**Run it:**
```bash
cd docs/examples/file-editing
python search_replace.py
```

**Key concepts:**
- Progressive matching levels
- Format preservation
- Batch replacements
- Error recovery with suggestions

### 3. refactoring.py

Complete multi-file refactoring workflows.

**What it demonstrates:**
- Function rename with call site updates
- Adding type hints to a module
- Adding error handling to risky operations
- Adding docstrings to undocumented functions
- Migrating configuration format

**Run it:**
```bash
cd docs/examples/file-editing
python refactoring.py
```

**Key concepts:**
- Multi-step workflows
- Combining multiple tools (code_search, find_references, file editing)
- Systematic refactoring approach
- Verification after changes

### 4. config_examples.yaml

Sample configurations for different environments.

**What it contains:**
- Development environment (permissive)
- Production environment (restrictive)
- Balanced environment (recommended)
- Python-only environment
- Web development environment
- Documentation-only environment
- Testing environment (unrestricted)
- Custom project template

**Use it:**
```bash
# Copy a configuration to your profile
cp docs/examples/file-editing/config_examples.yaml ~/.consoul/config.yaml

# Or reference specific sections in your config
```

**Key concepts:**
- Extension filtering
- Path blocking
- Size limits
- Permission policies
- Environment-specific settings

## Prerequisites

Before running these examples:

1. **Install Consoul with tools enabled:**
   ```bash
   pip install consoul
   ```

2. **Set up API keys:**
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

3. **Configure tools in your profile:**
   ```yaml
   # ~/.consoul/config.yaml
   profiles:
     default:
       tools:
         enabled: true
         permission_policy: balanced
   ```

## Understanding the Examples

### Tolerance Levels

| Tolerance | When to Use | Example |
|-----------|-------------|---------|
| `strict` | Exact content known | Replace constants, literals |
| `whitespace` | Refactoring code | Different indentation levels |
| `fuzzy` | Handling typos | "calculate_totle" → "calculate_total" |

### Permission Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `paranoid` | Approve every operation | Production |
| `balanced` | Approve CAUTION+ | Development |
| `trusting` | Auto-approve CAUTION | Trusted environment |
| `unrestricted` | Auto-approve all | Testing only |

### File Edit Tools

| Tool | Purpose | Risk Level |
|------|---------|------------|
| `edit_file_lines` | Edit specific lines/ranges | CAUTION |
| `edit_file_search_replace` | Search and replace | CAUTION |
| `create_file` | Create new files | CAUTION |
| `delete_file` | Delete files | CAUTION |
| `append_to_file` | Append content | CAUTION |

## Safety Tips

✅ **DO:**
- Use `dry_run=True` to preview changes
- Start with `permission_policy: paranoid`
- Review diff previews carefully
- Use version control (git)
- Monitor audit logs
- Test in safe environment first

❌ **DON'T:**
- Use `permission_policy: unrestricted` in production
- Disable audit logging
- Ignore approval prompts
- Edit files without backups
- Allow all extensions in production

## Troubleshooting

### "Search text not found"

**Cause:** Exact match failed

**Solutions:**
1. Try `tolerance="whitespace"` to ignore indentation
2. Try `tolerance="fuzzy"` for typos
3. Check "Did you mean?" suggestions
4. Verify file hasn't changed

### "Extension not allowed"

**Cause:** File extension not in whitelist

**Solution:** Add to `allowed_extensions` in config:
```yaml
tools:
  file_edit:
    allowed_extensions:
      - ".py"
      - ".your_extension"
```

### "Path is blocked"

**Cause:** Path in `blocked_paths` list

**Solution:** Remove from blocklist if safe:
```yaml
tools:
  file_edit:
    blocked_paths:
      # Remove or comment out if needed
      # - "/your/path"
```

## Additional Resources

- [File Editing Guide](../../user-guide/file-editing.md) - Comprehensive documentation
- [Tool Calling](../../tools.md) - Complete tool reference
- [Security](../../../SECURITY.md) - Security best practices
- [Configuration](../../user-guide/configuration.md) - Profile configuration

## Feedback

Found an issue or have a suggestion? Please open an issue:
https://github.com/goatbytes/consoul/issues

# Code Search Troubleshooting

Common issues and solutions for Consoul's code search tools.

## Table of Contents

- [Tool Not Found Errors](#tool-not-found-errors)
- [Language Not Supported](#language-not-supported)
- [Cache Issues](#cache-issues)
- [Performance Problems](#performance-problems)
- [Parsing Errors](#parsing-errors)
- [Empty Results](#empty-results)
- [Permission Errors](#permission-errors)

## Tool Not Found Errors

### Error: "Tool 'grep_search' not found in registry"

**Cause:** Tool not registered with ToolRegistry

**Solution:**
```python
from consoul.ai.tools import ToolRegistry, grep_search, RiskLevel

registry = ToolRegistry(config=config.tools)
registry.register(grep_search, risk_level=RiskLevel.SAFE)
```

**In TUI:** Ensure tools are enabled in config:
```yaml
profiles:
  default:
    tools:
      enabled: true
```

### Error: "ToolExecutionError: ripgrep not found"

**Cause:** grep_search prefers ripgrep but can't find it

**Solution:** Install ripgrep or use grep fallback:
```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
apt-get install ripgrep

# Windows (Scoop)
scoop install ripgrep
```

**Fallback:** grep_search automatically falls back to standard grep if ripgrep not found.

## Language Not Supported

### Error: "Unsupported language for file: *.xyz"

**Cause:** File extension not recognized by tree-sitter

**Supported Extensions:**
- Python: .py
- JavaScript: .js, .jsx
- TypeScript: .ts, .tsx
- Go: .go
- Rust: .rs
- Java: .java
- C/C++: .c, .cpp, .h, .hpp

**Solution:** Only use code_search and find_references on supported file types. Use grep_search for other files.

### How to Check Language Support

```python
from grep_ast import filename_to_lang

# Check if file is supported
lang = filename_to_lang("myfile.py")
if lang:
    print(f"Supported: {lang}")
else:
    print("Not supported - use grep_search instead")
```

## Cache Issues

### Cache Not Working - Still Slow on Repeat Searches

**Symptoms:** code_search and find_references always take full parse time

**Diagnosis:**
```python
from consoul.ai.tools.cache import CodeSearchCache

cache = CodeSearchCache()
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.1%}")  # Should be >50% after warmup
print(f"Hits: {stats.hits}, Misses: {stats.misses}")
```

**Causes & Solutions:**

**1. Cache directory not writable**
```python
from pathlib import Path

cache_dir = Path.home() / ".consoul" / "cache" / "code-search.v1"
print(cache_dir.exists())  # Should be True
print(os.access(cache_dir, os.W_OK))  # Should be True

# Fix permissions
cache_dir.mkdir(parents=True, exist_ok=True)
```

**2. Files changing between searches**
```bash
# Check file modification times
stat src/file.py  # mtime should be stable
```

**3. Running in different processes**
- Cache is per-process
- Solution: Keep searches in same Python session

**4. Cache manually cleared**
```python
# Don't do this unless necessary
cache.invalidate_cache()
```

### Cache Growing Too Large

**Check cache size:**
```python
cache = CodeSearchCache()
stats = cache.get_stats()
print(f"Cache size: {stats.size_bytes / 1024 / 1024:.1f} MB")
```

**Solution:** Configure smaller size limit:
```python
cache = CodeSearchCache(size_limit_mb=50)  # Default is 100MB
```

**Manual cleanup:**
```python
cache.invalidate_cache()  # Clears all entries
```

## Performance Problems

### Searches Taking Too Long (>10s)

**Diagnosis:**
1. Check project size:
```bash
find . -name "*.py" | wc -l  # How many files?
du -sh .  # Total size
```

2. Check if cache is being used:
```python
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.1%}")  # Should be >0% on repeat
```

**Solutions:**

**1. Use narrower scope**
```python
# Slow - searches whole project
find_references.invoke({"symbol": "foo", "scope": "project"})

# Faster - search one directory
find_references.invoke({"symbol": "foo", "scope": "directory", "path": "src/"})

# Fastest - search one file
find_references.invoke({"symbol": "foo", "scope": "file", "path": "src/main.py"})
```

**2. Increase file size limit**
```yaml
tools:
  code_search:
    max_file_size_kb: 2048  # Default is 1024 (1MB)
```

**3. Skip large generated files**
Add to `.gitignore` or filter:
```python
# Skip build directories
code_search.invoke({"query": "Foo", "path": "src/"})  # Not build/
```

**4. Use grep_search for simple patterns**
```python
# Fast text search instead of AST
grep_search.invoke({"pattern": "MyClass"})
```

### grep_search Slower Than Expected

**Diagnosis:**
```bash
which rg  # Should find ripgrep
rg --version  # Check version
```

**Solution:** Install ripgrep for 5-10x speedup:
```bash
brew install ripgrep  # macOS
apt-get install ripgrep  # Ubuntu
```

**Fallback performance:** Standard grep is slower but still functional.

## Parsing Errors

### Error: "Failed to parse AST"

**Symptoms:**
- code_search returns empty results
- find_references shows warning: "Failed to parse file.py"

**Causes:**

**1. Syntax errors in source file**
```python
# File has invalid Python syntax
def foo(  # Missing closing paren
    return 42
```

**Solution:** Fix syntax errors in source files. tree-sitter requires valid syntax.

**2. Tree-sitter language pack issue**
```python
# Check if tree-sitter-language-pack is installed
python -c "import tree_sitter_language_pack; print('OK')"
```

**Solution:** Reinstall dependency:
```bash
pip install --force-reinstall tree-sitter-language-pack>=0.11.0
```

**3. Encoding issues**
```python
# File isn't UTF-8
result = file_path.read_text(encoding="utf-8", errors="ignore")
```

**Solution:** Convert file to UTF-8 or let tools ignore decode errors (automatic).

### Error: "Failed to get parser for language"

**Cause:** Language not supported by tree-sitter

**Solution:** Check supported languages and use grep_search for unsupported files.

## Empty Results

### code_search Returns No Results

**Diagnosis Checklist:**

1. **Verify file exists:**
```bash
ls -la path/to/file.py
```

2. **Check file isn't too large:**
```python
# Default limit is 1MB
file_size_kb = Path("file.py").stat().st_size / 1024
print(f"Size: {file_size_kb:.1f} KB")  # Should be <1024
```

3. **Verify symbol exists:**
```python
# Use grep to confirm symbol is in file
grep_search.invoke({"pattern": "MyClass", "path": "file.py"})
```

4. **Check symbol type:**
```python
# Maybe it's a method, not a function
code_search.invoke({"query": "MyClass", "symbol_type": "method"})
```

5. **Try case-insensitive:**
```python
code_search.invoke({"query": "myclass", "case_sensitive": False})
```

**Common Issues:**

**Symbol is in comment/string:**
- code_search ignores comments and strings
- Solution: Use grep_search instead

**Symbol is imported, not defined:**
- code_search finds definitions, not imports
- Solution: Use find_references to find imports

**Symbol is in unsupported file:**
- Check language support matrix
- Solution: Use grep_search for unsupported languages

### find_references Returns No Results

**Diagnosis:**

1. **Symbol might not be used:**
```python
# Check if symbol is defined but unused (dead code)
code_search.invoke({"query": "MyClass"})  # Finds definition
find_references.invoke({"symbol": "MyClass"})  # Finds usages
```

2. **Symbol name might be different:**
```python
# Case-sensitive by default
find_references.invoke({"symbol": "myclass", "case_sensitive": False})
```

3. **Symbol only used in comments:**
- find_references ignores comments
- Solution: Use grep_search

4. **Scope too narrow:**
```python
# Maybe references are in other directories
find_references.invoke({"symbol": "Foo", "scope": "project"})  # Wider
```

## Permission Errors

### Error: "Permission denied"

**Cause:** No read access to file or directory

**Solution:**
```bash
# Check permissions
ls -la path/to/file

# Fix permissions
chmod +r path/to/file
```

### Error: "Failed to access cache directory"

**Cause:** Cache directory not writable

**Solution:**
```bash
# Create cache directory with correct permissions
mkdir -p ~/.consoul/cache/code-search.v1
chmod 755 ~/.consoul/cache/code-search.v1
```

## Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure Consoul logging
from consoul.ai.tools.implementations import code_search

# Run with debug output
result = code_search.invoke({"query": "Foo"})
# Will show detailed parsing info
```

## Getting Help

If issues persist:

1. **Check version:**
```python
import consoul
print(consoul.__version__)
```

2. **Verify dependencies:**
```bash
pip list | grep -E "tree-sitter|grep-ast|ripgrep"
```

3. **Minimal reproduction:**
```python
from consoul.ai.tools import code_search

# Simplest possible test
result = code_search.invoke({"query": ".*", "path": "."})
print(result)
```

4. **Report issue:**
- GitHub: https://github.com/goatbytes/consoul/issues
- Include: Python version, OS, error message, minimal reproduction

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Tool not found | Enable tools in config.yaml |
| Language not supported | Use grep_search instead |
| Cache not working | Check ~/.consoul/cache permissions |
| Too slow | Use narrower scope, install ripgrep |
| Parsing errors | Check file syntax, verify UTF-8 |
| Empty results | Check file size, try case-insensitive |
| Permission denied | Fix file/directory permissions |

## See Also

- [Code Search Guide](code-search.md) - Comprehensive usage guide
- [Tool Calling Documentation](../tools.md) - Complete tool reference
- [Configuration Guide](configuration.md) - Settings and options

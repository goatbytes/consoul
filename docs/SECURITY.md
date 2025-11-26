# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Consoul, please report it by emailing **security@goatbytes.io**.

**Please do not report security vulnerabilities through public GitHub issues.**

### What to Include

When reporting a vulnerability, please include:

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Any suggested fixes (if you have them)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Varies based on severity and complexity

### Security Best Practices

When using Consoul:

1. **API Keys**: Never commit API keys to version control
   - Use environment variables for sensitive credentials
   - Add `.env` files to `.gitignore`

2. **Dependencies**: Keep dependencies up to date
   - Run `poetry update` regularly
   - Monitor security advisories with `make security`

3. **Code Scanning**: Use provided security tools
   - Run `make security` before commits
   - Review Bandit and Safety reports

4. **Input Validation**: Be cautious with user input
   - Avoid executing arbitrary code from AI responses
   - Sanitize file paths and commands

## Security Scanning

This project uses automated security scanning:

### Bandit (Code Security)

Bandit scans Python code for common security issues:

```bash
# Run Bandit scan
make security

# Generate detailed report
poetry run bandit -r src/ -c pyproject.toml -f json -o bandit-report.json
```

### Safety (Dependency Vulnerabilities)

Safety checks dependencies for known security vulnerabilities:

```bash
# Check dependencies
poetry run safety check

# Generate report
poetry run safety check --save-json safety-report.json
```

### Pre-commit Hooks

Optional security hooks are available:

```bash
# Run all pre-commit hooks including security
pre-commit run --all-files
```

## Automated Scanning

Security scans run automatically:

- **On every pull request**: Bandit and Safety scans
- **On main branch pushes**: Full security audit
- **Weekly**: Scheduled dependency vulnerability scans

## Security Updates

Security patches are released as soon as possible after discovery. Critical vulnerabilities are addressed within:

- **Critical**: 24-48 hours
- **High**: 1 week
- **Medium**: 2 weeks
- **Low**: Next regular release

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged (with permission) in our security advisories.

## File Operations Security

Consoul includes AI-powered file editing capabilities that require special security considerations. Most file editing tools are classified as **Risk Level: CAUTION**, with the exception of `delete_file` which is classified as **Risk Level: DANGEROUS** due to its destructive nature. All file operations require user approval by default.

### Path Validation

File editing tools implement multiple layers of path security:

**1. Path Traversal Protection**
- Blocks `..` in file paths to prevent directory traversal attacks
- Validates resolved absolute paths before operations
- Follows symlinks to validate real destination

**Example:**
```python
# BLOCKED: Path traversal
edit_file_lines({"file_path": "../../../etc/passwd"})
# Error: "Path traversal detected: .. not allowed"

# ALLOWED: Safe relative path
edit_file_lines({"file_path": "src/utils.py"})
```

**2. Blocked Paths**

Default blocked paths (cannot be edited):
- `/etc/shadow` - Shadow password file
- `/etc/passwd` - User account information
- `/proc` - Process information
- `/dev` - Device files
- `/sys` - Kernel interface

**Important**: The defaults do NOT include common secret locations like `~/.ssh`, `~/.aws`, or `~/.gnupg`. You **must** explicitly add these to your configuration for production use.

Recommended blocking via configuration:
```yaml
tools:
  file_edit:
    blocked_paths:
      # System defaults (already included)
      - "/etc/shadow"
      - "/etc/passwd"
      - "/proc"
      - "/dev"
      - "/sys"
      # RECOMMENDED ADDITIONS for production
      - "~/.ssh"          # SSH keys
      - "~/.aws"          # AWS credentials
      - "~/.gnupg"        # GPG keys
      # Optional project-specific blocks
      - "/var/www/production"  # Production code
      - "~/.config/secrets"     # Local secrets
      - "${PROJECT_ROOT}/vendor"  # Third-party dependencies
```

**3. Extension Filtering**

Whitelist allowed file extensions:
```yaml
tools:
  file_edit:
    allowed_extensions:
      - ".py"    # Python source
      - ".js"    # JavaScript
      - ".md"    # Markdown
      - ".txt"   # Text files
      - ""       # Extensionless (Dockerfile, Makefile)
```

Empty list (`[]`) allows all extensions (use with caution).

### File Editing Tools

**Available Tools:**
- `edit_file_lines` - Line-based editing (CAUTION)
- `edit_file_search_replace` - Search/replace with progressive matching (CAUTION)
- `create_file` - File creation with overwrite protection (CAUTION)
- `delete_file` - File deletion (**DANGEROUS** - destructive operation)
- `append_to_file` - Content appending (CAUTION)

**Risk Levels:**
- Most file editing tools: CAUTION (requires approval by default)
- `delete_file`: DANGEROUS (always requires approval, even in trusting mode)

**Security Features:**

1. **Atomic Writes**
   - Temp file created first
   - Atomically renamed to target
   - Prevents corruption on errors

2. **Optimistic Locking**
   - Optional `expected_hash` parameter
   - Detects concurrent modifications
   - Prevents accidental overwrites

3. **Dry-Run Mode**
   - Preview changes before applying
   - Shows unified diff
   - No filesystem modifications

4. **Size Limits**
   - `max_payload_bytes` (default: 1MB)
   - `max_edits` per operation (default: 50)
   - Prevents runaway AI edits

5. **Approval Workflow**
   - User confirmation required (CAUTION level)
   - Shows file path and operation details
   - Displays diff preview when available

6. **Audit Logging**
   - All operations logged
   - Includes file paths and arguments
   - Timestamps and results recorded

### Configuration Best Practices

**Development Environment (More Permissive):**
```yaml
profiles:
  dev:
    tools:
      permission_policy: trusting  # Auto-approve CAUTION tools
      file_edit:
        allowed_extensions: []  # All extensions
        allow_overwrite: true   # Allow file overwrites
        max_payload_bytes: 2097152  # 2MB limit
```

**Production Environment (Restrictive):**
```yaml
profiles:
  prod:
    tools:
      permission_policy: paranoid  # Approve every operation
      file_edit:
        allowed_extensions:
          - ".md"   # Only documentation
          - ".txt"
        blocked_paths:
          # System paths
          - "/etc/shadow"
          - "/etc/passwd"
          - "/proc"
          - "/dev"
          - "/sys"
          - "/var"
          - "/usr"
          # Secrets and credentials (CRITICAL)
          - "~/.ssh"
          - "~/.aws"
          - "~/.gnupg"
          - "~/.config/gcloud"
        allow_overwrite: false  # Prevent overwrites
        max_payload_bytes: 524288  # 512KB limit
        max_edits: 25  # Conservative limit
```

### Threat Model

**Protected Against:**
- ✅ Path traversal attacks (`../../../etc/passwd`)
- ✅ Unauthorized file access (blocked paths)
- ✅ Malicious file types (extension filtering)
- ✅ Large payload attacks (size limits)
- ✅ Concurrent edit conflicts (optimistic locking)
- ✅ File corruption (atomic writes)

**User Responsible For:**
- ⚠️ Reviewing approval prompts carefully
- ⚠️ Validating diff previews before approval
- ⚠️ Configuring appropriate extension whitelist
- ⚠️ Setting restrictive blocked paths
- ⚠️ Using appropriate permission policy
- ⚠️ Monitoring audit logs

### Security Checklist

Before enabling file editing in production:

- [ ] **CRITICAL**: Add `~/.ssh`, `~/.aws`, `~/.gnupg` to `blocked_paths` (not in defaults!)
- [ ] Review and customize complete `blocked_paths` list for your environment
- [ ] Configure `allowed_extensions` whitelist (don't use `[]` in production)
- [ ] Set `allow_overwrite: false` unless necessary
- [ ] Use `permission_policy: balanced` or `paranoid`
- [ ] Enable audit logging (`audit_logging: true`)
- [ ] Test dry-run mode for critical operations
- [ ] Review audit logs regularly
- [ ] Restrict file permissions (`chmod 600` for sensitive files)
- [ ] Use version control (git) for rollback capability
- [ ] Test disaster recovery procedures
- [ ] Understand that `delete_file` is DANGEROUS (not just CAUTION)

### Reporting File Operations Vulnerabilities

If you discover a security vulnerability in file editing tools, please report it immediately to **security@goatbytes.io** with:

1. Description of the vulnerability
2. Steps to reproduce
3. Proof of concept (if applicable)
4. Suggested mitigation

**Do not report security vulnerabilities through public GitHub issues.**

## Additional Resources

- [File Editing Documentation](docs/user-guide/file-editing.md) - Complete usage guide
- [Tool Calling Guide](docs/tools.md) - Security controls and policies
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://pyup.io/safety/)

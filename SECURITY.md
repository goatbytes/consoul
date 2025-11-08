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

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://pyup.io/safety/)

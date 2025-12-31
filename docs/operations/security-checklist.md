# Consoul Security Checklist

Security verification procedures for pre-deployment, ongoing operations, and compliance.

## Table of Contents

- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Weekly Security Checks](#weekly-security-checks)
- [Monthly Security Tasks](#monthly-security-tasks)
- [Security Configuration Reference](#security-configuration-reference)

---

## Pre-Deployment Checklist

Complete all items before deploying to production.

### Authentication

- [ ] **API keys configured**
  ```bash
  # Verify CONSOUL_API_KEYS is set with strong keys
  # Keys should be at least 32 characters, randomly generated
  openssl rand -hex 32  # Generate strong key
  ```

- [ ] **API keys stored in secrets manager** (not environment variables)
  - AWS: Secrets Manager
  - GCP: Secret Manager
  - Azure: Key Vault

- [ ] **Bypass paths reviewed**
  ```bash
  # Only these should bypass authentication
  CONSOUL_BYPASS_PATHS=/health,/ready,/docs,/openapi.json
  ```

### Rate Limiting

- [ ] **Rate limiting enabled**
  ```bash
  CONSOUL_ENABLED=true
  CONSOUL_DEFAULT_LIMITS="30/minute;500/hour"
  ```

- [ ] **Redis configured for distributed rate limiting**
  ```bash
  CONSOUL_RATE_LIMIT_REDIS_URL=redis://redis:6379/0
  ```

- [ ] **Rate limits appropriate for use case**
  | Tier | Limit | Use Case |
  |------|-------|----------|
  | Development | 1000/minute | Testing |
  | Standard | 30/minute | Normal usage |
  | Enterprise | 100/minute | High volume |

### CORS

- [ ] **CORS origins restricted** (no wildcards in production)
  ```bash
  # BAD - allows any origin
  CONSOUL_CORS_ORIGINS="*"

  # GOOD - specific origins only
  CONSOUL_CORS_ORIGINS="https://app.example.com,https://admin.example.com"
  ```

- [ ] **Credentials setting matches origin config**
  ```bash
  # If allowing credentials, MUST specify exact origins
  CONSOUL_CORS_ALLOW_CREDENTIALS=true
  CONSOUL_CORS_ORIGINS="https://app.example.com"  # NOT "*"
  ```

### Network Security

- [ ] **HTTPS enforced** via reverse proxy (nginx, Caddy, ALB)

- [ ] **TLS 1.2+ required** on load balancer

- [ ] **Redis in private subnet/VPC** (not publicly accessible)

- [ ] **Metrics port (9090) not exposed publicly**

### Tool Security

- [ ] **Permission policy configured**
  ```python
  # Options: PARANOID, BALANCED (default), TRUSTING, UNRESTRICTED
  # Use BALANCED or PARANOID for production
  permission_policy=PermissionPolicy.BALANCED
  ```

- [ ] **Blocked commands verified**
  - `sudo` commands blocked
  - `rm -rf /` and variants blocked
  - `chmod 777` blocked
  - Download-and-execute patterns blocked (`curl | sh`)

- [ ] **Whitelist configured** (if needed)
  ```bash
  # ~/.consoul/whitelist.yaml
  # File permissions: 0600 (user read/write only)
  ```

### Secrets Management

- [ ] **LLM API keys in secrets manager**
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`

- [ ] **No secrets in Docker images or source control**

- [ ] **.env files in .gitignore**

### Audit Logging

- [ ] **Audit logging configured**
  ```python
  # At minimum, use FileAuditLogger for production
  audit_logger = FileAuditLogger(Path("/var/log/consoul/audit.jsonl"))
  ```

- [ ] **Audit log storage secured** (encrypted at rest)

- [ ] **Log retention policy defined** (minimum 1 year for compliance)

### Input Validation

- [x] **Request body size limited** (enforced by default: 1MB)
  ```bash
  # Default: 1MB limit enforced by BodySizeLimitMiddleware
  # Customize via environment variable:
  export CONSOUL_MAX_BODY_SIZE=2097152  # 2MB
  # Or disable validation:
  export CONSOUL_VALIDATION_ENABLED=false
  ```

- [ ] **Message length validated** (max 32KB - enforced by Pydantic model)

---

## Weekly Security Checks

Perform these checks every week.

### Authentication Monitoring

- [ ] **Review authentication failures**
  ```bash
  # Check for brute force attempts
  grep "Authentication failed" /var/log/consoul/app.log | \
    awk '{print $NF}' | sort | uniq -c | sort -rn | head -20
  ```

- [ ] **Check for unusual access patterns**
  ```promql
  # Requests by API key (if tracked)
  sum(rate(consoul_request_total[7d])) by (api_key)
  ```

### Rate Limit Review

- [ ] **Check rate limit violations**
  ```bash
  grep "Rate limit exceeded" /var/log/consoul/app.log | wc -l
  ```

- [ ] **Review rate limit by client**
  ```bash
  redis-cli -h REDIS_HOST KEYS "consoul:ratelimit:*" | head -20
  ```

### Tool Execution Audit

- [ ] **Review tool executions**
  ```bash
  # Most frequently used tools
  cat audit.jsonl | jq -r '.tool_name' | sort | uniq -c | sort -rn | head -10
  ```

- [ ] **Check for denied tool requests**
  ```bash
  cat audit.jsonl | jq 'select(.event_type == "denial")' | head -20
  ```

- [ ] **Check for blocked commands**
  ```bash
  cat audit.jsonl | jq 'select(.event_type == "blocked")' | head -20
  ```

### Log Review

- [ ] **Check for errors**
  ```bash
  grep -E "ERROR|CRITICAL" /var/log/consoul/app.log | tail -100
  ```

- [ ] **Verify no PII in logs**
  ```bash
  # Check for common PII patterns
  grep -E "(password|secret|token|api_key)=" /var/log/consoul/app.log
  ```

---

## Monthly Security Tasks

Perform these tasks every month.

### API Key Rotation

See [API Key Rotation Guide](./api-key-rotation.md) for detailed procedures.

- [ ] **Generate new API keys**
  ```bash
  NEW_KEY="sk-$(date +%Y%m)-$(openssl rand -hex 24)"
  ```

- [ ] **Add new key to secrets manager** (alongside old keys)
  ```bash
  # Overlap period: both old and new keys valid
  export CONSOUL_API_KEYS="old-key,new-key"
  ```

- [ ] **Monitor key usage via metrics**
  ```promql
  # Check which keys are still being used
  sum(increase(consoul_api_key_requests_total[24h])) by (api_key_id)
  ```

- [ ] **Notify clients** of key rotation (30-day migration window)

- [ ] **Remove old keys** after migration period
  ```bash
  export CONSOUL_API_KEYS="new-key"
  ```

- [ ] **Verify old key rejected** (401 response)

### Dependency Updates

- [ ] **Check for security vulnerabilities**
  ```bash
  pip-audit
  # or
  safety check
  ```

- [ ] **Update dependencies**
  ```bash
  pip install --upgrade consoul[server]
  ```

- [ ] **Test in staging** before production

### Access Review

- [ ] **Review who has access** to:
  - Cloud console
  - Kubernetes cluster
  - Secrets manager
  - Redis instance

- [ ] **Remove unused access**

- [ ] **Verify service accounts** have minimal permissions

### Audit Log Review

- [ ] **Export audit logs** for long-term storage

- [ ] **Review tool execution patterns**
  ```bash
  # Monthly summary
  cat audit.jsonl | jq -r '[.timestamp, .event_type, .tool_name] | @tsv' | \
    awk '{print $2, $3}' | sort | uniq -c | sort -rn
  ```

- [ ] **Check for anomalies**
  - Unusual tools being executed
  - High error rates
  - After-hours activity

### Configuration Review

- [ ] **Verify production configuration matches security policy**

- [ ] **Check for configuration drift** from baseline

- [ ] **Update documentation** if configuration changed

---

## Security Configuration Reference

### API Key Authentication

**File**: `src/consoul/server/middleware/auth.py`

| Config | Default | Description |
|--------|---------|-------------|
| `CONSOUL_API_KEYS` | `[]` | Comma-separated or JSON array of valid keys |
| `CONSOUL_API_KEY_HEADER` | `X-API-Key` | HTTP header name |
| `CONSOUL_API_KEY_QUERY` | `api_key` | Query parameter name |
| `CONSOUL_BYPASS_PATHS` | `/health,/ready,/docs,/openapi.json` | Unauthenticated paths |

**Security Notes**:
- API keys use set-based lookup (O(1))
- Failed attempts logged with client IP
- Supports multiple keys for rotation

### Rate Limiting

**File**: `src/consoul/server/middleware/rate_limit.py`

| Config | Default | Description |
|--------|---------|-------------|
| `CONSOUL_ENABLED` | `true` | Enable/disable rate limiting |
| `CONSOUL_DEFAULT_LIMITS` | `10 per minute` | Rate limit string |
| `CONSOUL_RATE_LIMIT_REDIS_URL` | `None` | Redis URL for distributed mode |
| `CONSOUL_STRATEGY` | `moving-window` | `fixed-window` or `moving-window` |
| `CONSOUL_KEY_PREFIX` | `consoul:ratelimit` | Redis key prefix |

**Rate Limit Format**:
```
"10/minute"           # 10 requests per minute
"100/hour"            # 100 requests per hour
"10/minute;100/hour"  # Multiple limits (semicolon-separated)
```

### CORS Configuration

**File**: `src/consoul/server/middleware/cors.py`

| Config | Default | Description |
|--------|---------|-------------|
| `CONSOUL_CORS_ORIGINS` | `*` | Allowed origins (RESTRICT in production) |
| `CONSOUL_CORS_ALLOW_CREDENTIALS` | `false` | Allow credentials |
| `CONSOUL_CORS_ALLOW_METHODS` | `*` | Allowed HTTP methods |
| `CONSOUL_CORS_ALLOW_HEADERS` | `*` | Allowed headers |
| `CONSOUL_CORS_MAX_AGE` | `600` | Preflight cache (seconds) |

**Security Rules**:
- Never use `*` with `allow_credentials=true`
- Always specify exact origins in production
- Validation warns on insecure configurations

### Tool Permission Policies

**File**: `src/consoul/ai/tools/permissions/policy.py`

| Policy | SAFE | CAUTION | DANGEROUS | BLOCKED | Recommendation |
|--------|------|---------|-----------|---------|----------------|
| **PARANOID** | Prompt | Prompt | Prompt | Block | Maximum security |
| **BALANCED** | Allow | Prompt | Prompt | Block | **Recommended** |
| **TRUSTING** | Allow | Allow | Prompt | Block | Development |
| **UNRESTRICTED** | Allow | Allow | Allow | Block | Testing only |

**Risk Levels**:
- **SAFE**: Read-only (ls, pwd, git status, cat)
- **CAUTION**: State-modifying (mkdir, cp, mv, git commit)
- **DANGEROUS**: High-impact (rm -rf, dd, kill -9, chmod 777)
- **BLOCKED**: Prohibited (sudo, fork bombs, download-execute)

### Blocked Command Patterns

**File**: `src/consoul/ai/tools/permissions/analyzer.py`

Default blocked patterns:
```python
r"^sudo\s"              # sudo commands
r"rm\s+(-[rf]+\s+)?/"   # rm with root paths
r"dd\s+if="             # disk operations
r"chmod\s+777"          # dangerous permissions
r":\(\)\{.*:\|:.*\};:"  # fork bomb
r"wget.*\|.*bash"       # download-and-execute
r"curl.*\|.*sh"         # download-and-execute
r">\s*/dev/sd[a-z]"     # write to disk devices
r"mkfs"                 # format filesystem
r"fdisk"                # partition operations
```

### PII Redaction

**File**: `src/consoul/sdk/redaction.py`

**Automatically Redacted Fields**:
```python
password, passwd, pwd, secret, api_key, apikey, token,
access_token, refresh_token, auth, authorization,
private_key, privatekey, session_key
```

**Automatically Redacted Patterns**:
- API keys (`sk-`, `pk-`, `key-` prefixes)
- Bearer tokens (`Bearer <token>`)
- JWT tokens (`eyJ...`)
- SSN (`XXX-XX-XXXX`)
- Credit cards (`XXXX-XXXX-XXXX-XXXX`)
- AWS keys (`AKIA...`)
- GitHub tokens (`ghp_`, `ghs_`)
- Email addresses

### Input Validation

**File**: `src/consoul/server/middleware/validation.py`

| Limit | Default | Enforced By Default | Description |
|-------|---------|---------------------|-------------|
| `max_body_size` | 1MB | **Yes** (via `BodySizeLimitMiddleware`) | Maximum request body |
| `session_id` | 1-128 chars | Yes (Pydantic) | Session ID length |
| `message` | 1-32768 chars | Yes (Pydantic) | Message length (32KB) |

Configure body size limit via environment variable: `CONSOUL_MAX_BODY_SIZE=2097152` (2MB).

---

## Security Incident Indicators

### Signs of Attack

| Indicator | Pattern | Response |
|-----------|---------|----------|
| Brute force | Many 401 errors from same IP | Block IP, review logs |
| Credential stuffing | 401 errors with different keys | Rotate all keys |
| Rate limit abuse | Sustained 429 errors | Review rate limits |
| Injection attempt | Unusual characters in logs | Review audit logs |
| Data exfiltration | Large response sizes | Review session activity |

### Response Actions

1. **Immediate**: Block suspicious IP addresses
2. **Short-term**: Rotate affected credentials
3. **Investigation**: Review audit logs
4. **Long-term**: Implement additional controls

See [Incident Response](./incident-response.md) for detailed procedures.

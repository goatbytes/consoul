# Consoul Compliance Documentation

SOC2 control mapping, audit logging features, and security controls documentation.

## Table of Contents

- [SOC2 Control Mapping](#soc2-control-mapping)
- [Audit Logging Features](#audit-logging-features)
- [Data Handling](#data-handling)
- [Security Controls Summary](#security-controls-summary)

---

## SOC2 Control Mapping

Consoul provides features that support SOC2 Trust Service Criteria compliance.

### Security (Common Criteria)

| SOC2 Control | Consoul Feature | Implementation |
|--------------|-----------------|----------------|
| CC6.1 - Logical Access | API Key Authentication | `CONSOUL_API_KEYS` environment variable |
| CC6.2 - Access Revocation | Key Rotation | Remove key from `CONSOUL_API_KEYS`, restart |
| CC6.6 - Unauthorized Access | Rate Limiting | `CONSOUL_DEFAULT_LIMITS` |
| CC6.7 - Data Transmission | HTTPS/TLS | Load balancer TLS termination |
| CC7.1 - Threat Detection | Audit Logging | `AuditLogger` implementations |
| CC7.2 - Anomaly Detection | Prometheus Metrics | `consoul_errors_total`, alert rules |

### Availability

| SOC2 Control | Consoul Feature | Implementation |
|--------------|-----------------|----------------|
| A1.1 - Capacity Planning | Auto-scaling | Cloud provider auto-scaling |
| A1.2 - Environmental Protection | Health Checks | `GET /health`, `GET /ready` |
| A1.3 - Recovery | Redis Persistence | ElastiCache/Memorystore/Azure Cache |

### Confidentiality

| SOC2 Control | Consoul Feature | Implementation |
|--------------|-----------------|----------------|
| C1.1 - Confidential Info ID | PII Redaction | `PiiRedactor` class |
| C1.2 - Data Disposal | Session TTL | `CONSOUL_SESSION_TTL` |

### Processing Integrity

| SOC2 Control | Consoul Feature | Implementation |
|--------------|-----------------|----------------|
| PI1.1 - Input Validation | Request Validation | `RequestValidator` middleware |
| PI1.2 - Processing Accuracy | Tool Filtering | Permission policies |

---

## Audit Logging Features

### AuditEvent Data Model

**File**: `src/consoul/ai/tools/audit.py`

Every tool execution generates an audit event:

```python
@dataclass
class AuditEvent:
    event_type: Literal[
        "request",    # Tool execution requested
        "approval",   # User approved execution
        "denial",     # User denied execution
        "execution",  # Execution started
        "result",     # Execution completed
        "error",      # Execution failed
        "blocked"     # Policy blocked execution
    ]
    tool_name: str              # Name of the tool
    arguments: dict[str, Any]   # Tool arguments
    timestamp: datetime         # UTC timestamp
    correlation_id: str | None  # Request correlation ID
    session_id: str | None      # User session
    user: str | None            # User identifier (multi-tenant)
    decision: bool | None       # Approval decision
    result: str | None          # Tool output
    duration_ms: int | None     # Execution time
    error: str | None           # Error message
    metadata: dict[str, Any]    # Custom context
```

### Built-in Audit Loggers

#### FileAuditLogger (JSONL)

**Use Case**: Simple deployments, log aggregation pipelines

**Format**: One JSON object per line (JSONL/NDJSON)

```python
from consoul.ai.tools.audit import FileAuditLogger
from pathlib import Path

audit_logger = FileAuditLogger(Path("/var/log/consoul/audit.jsonl"))
```

**Sample Output**:
```json
{"timestamp":"2025-12-25T10:30:45.123456Z","event_type":"execution","tool_name":"bash_execute","arguments":{"command":"ls -la"},"session_id":"sess_abc123","user":"user@example.com","duration_ms":150}
{"timestamp":"2025-12-25T10:30:46.234567Z","event_type":"result","tool_name":"bash_execute","arguments":{"command":"ls -la"},"result":"total 64\ndrwxr-xr-x...","duration_ms":150}
```

**Querying**:
```bash
# Recent executions
tail -100 audit.jsonl | jq 'select(.event_type == "execution")'

# Denied requests
cat audit.jsonl | jq 'select(.event_type == "denial")'

# Errors by tool
cat audit.jsonl | jq 'select(.event_type == "error")' | jq -r '.tool_name' | sort | uniq -c

# User activity
cat audit.jsonl | jq 'select(.user == "user@example.com")'
```

#### SQLiteAuditLogger

**Use Case**: Single-instance deployments, queryable local storage

**Schema**:
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT,        -- JSON
    correlation_id TEXT,
    session_id TEXT,
    user_id TEXT,
    decision INTEGER,      -- 1=approved, 0=denied, NULL=N/A
    result TEXT,
    duration_ms INTEGER,
    error TEXT,
    metadata TEXT,         -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON audit_log(timestamp);
CREATE INDEX idx_event_type ON audit_log(event_type);
CREATE INDEX idx_tool_name ON audit_log(tool_name);
CREATE INDEX idx_user_id ON audit_log(user_id);
CREATE INDEX idx_session_id ON audit_log(session_id);
```

**Querying**:
```sql
-- Recent errors
SELECT * FROM audit_log
WHERE event_type = 'error'
ORDER BY timestamp DESC
LIMIT 100;

-- Tool usage by user
SELECT user_id, tool_name, COUNT(*) as count
FROM audit_log
WHERE event_type = 'execution'
GROUP BY user_id, tool_name
ORDER BY count DESC;

-- Average execution time by tool
SELECT tool_name, AVG(duration_ms) as avg_duration
FROM audit_log
WHERE event_type = 'result' AND duration_ms IS NOT NULL
GROUP BY tool_name;

-- Blocked commands
SELECT timestamp, tool_name, arguments, user_id
FROM audit_log
WHERE event_type = 'blocked'
ORDER BY timestamp DESC;
```

#### StructuredAuditLogger (Cloud-Compatible)

**Use Case**: Cloud deployments with log aggregation (CloudWatch, Stackdriver, Splunk)

**Format**: Structured JSON compatible with cloud logging services

```json
{
  "@timestamp": "2025-12-25T10:30:45.123456Z",
  "event": {
    "type": "execution",
    "category": "tool_execution",
    "module": "consoul"
  },
  "tool": {
    "name": "bash_execute",
    "arguments": {"command": "ls -la"}
  },
  "result": {
    "decision": true,
    "output": "total 64\ndrwxr-xr-x...",
    "duration_ms": 150,
    "error": null
  },
  "user": {
    "id": "user@example.com"
  },
  "session": {
    "id": "sess_abc123"
  },
  "metadata": {}
}
```

**CloudWatch Insights Query**:
```
fields @timestamp, event.type, tool.name, user.id
| filter event.category = "tool_execution"
| sort @timestamp desc
| limit 100
```

**Stackdriver Query**:
```
resource.type="cloud_run_revision"
jsonPayload.event.category="tool_execution"
jsonPayload.event.type="blocked"
```

#### MultiAuditLogger (Composite)

**Use Case**: Multiple audit destinations (e.g., file + cloud)

```python
from consoul.ai.tools.audit import MultiAuditLogger, FileAuditLogger

audit_logger = MultiAuditLogger([
    FileAuditLogger(Path("/var/log/consoul/audit.jsonl")),
    CloudAuditLogger(project_id="my-project"),
])
```

- Logs to all backends concurrently
- Failure isolation (one backend failure doesn't affect others)

### Custom Audit Logger

Implement the `AuditLogger` protocol for custom backends:

```python
from consoul.ai.tools.audit import AuditLogger, AuditEvent

class CustomAuditLogger(AuditLogger):
    async def log_event(self, event: AuditEvent) -> None:
        """Log an audit event. Should not raise exceptions."""
        # Send to your backend
        await self.http_client.post(
            "https://audit.example.com/events",
            json={
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "tool_name": event.tool_name,
                "arguments": event.arguments,
                "user": event.user,
                "session_id": event.session_id,
            }
        )
```

---

## Data Handling

### PII Redaction

**File**: `src/consoul/sdk/redaction.py`

Consoul automatically redacts sensitive data in logs and responses.

#### Redacted Field Names

These fields are automatically redacted when found in dictionaries:

```python
REDACTED_FIELDS = {
    "password", "passwd", "pwd",
    "secret", "api_key", "apikey",
    "token", "access_token", "refresh_token",
    "auth", "authorization",
    "private_key", "privatekey",
    "session_key", "credential", "credentials",
}
```

#### Redacted Patterns

These patterns are automatically detected and redacted:

| Pattern | Example | Regex |
|---------|---------|-------|
| API Keys | `sk-1234...` | `(sk|pk|key)-[a-zA-Z0-9]{20,}` |
| Bearer Tokens | `Bearer eyJ...` | `Bearer\s+[^\s]+` |
| JWT Tokens | `eyJhbGci...` | `eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+` |
| SSN | `123-45-6789` | `\d{3}-\d{2}-\d{4}` |
| Credit Cards | `4111-1111-1111-1111` | `\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}` |
| AWS Keys | `AKIA1234...` | `AKIA[A-Z0-9]{16}` |
| GitHub Tokens | `ghp_xxxx...` | `(ghp|ghs|gho|ghu)_[a-zA-Z0-9]{36}` |
| Email Addresses | `user@example.com` | `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` |

#### Usage

```python
from consoul.sdk.redaction import PiiRedactor

redactor = PiiRedactor()

# Redact dictionary
data = {
    "user": "alice",
    "password": "secret123",
    "api_key": "sk-abc123xyz"
}
redacted = redactor.redact_dict(data)
# Result: {"user": "alice", "password": "[REDACTED]", "api_key": "[REDACTED]"}

# Redact string
text = "My API key is sk-abc123xyz and email is user@example.com"
redacted = redactor.redact_string(text)
# Result: "My API key is [REDACTED] and email is [REDACTED]"
```

### Session Data Lifecycle

| Stage | Data | Retention |
|-------|------|-----------|
| Active Session | Conversation history, state | `CONSOUL_SESSION_TTL` (default: 1 hour) |
| Expired Session | Automatically deleted | Immediate |
| Audit Logs | Tool executions, errors | Configurable (recommend: 1 year) |
| Metrics | Aggregated statistics | 13 months |

### Log Retention Recommendations

| Log Type | Retention | Rationale |
|----------|-----------|-----------|
| Application Logs | 30 days | Debugging, troubleshooting |
| Audit Logs | 1 year | Compliance requirement |
| Security Events | 2 years | Security investigations |
| Access Logs | 90 days | Access pattern analysis |
| Metrics | 13 months | Year-over-year comparison |

### Data Encryption

| Data | At Rest | In Transit |
|------|---------|------------|
| API Keys | Secrets Manager (encrypted) | HTTPS/TLS |
| Session Data | Redis (optional TLS) | Internal network |
| Audit Logs | Cloud storage encryption | HTTPS |
| LLM Requests | Provider-dependent | HTTPS/TLS |

---

## Security Controls Summary

### Authentication

| Control | Implementation | Configuration |
|---------|----------------|---------------|
| API Key Auth | Header or query parameter | `CONSOUL_API_KEYS` |
| Multiple Keys | Comma-separated list | `key1,key2,key3` |
| Key Rotation | Add new, remove old | No downtime |
| Bypass Paths | Public endpoints | `/health,/ready,/docs` |

### Authorization

| Control | Implementation | Configuration |
|---------|----------------|---------------|
| Tool Permissions | Policy-based filtering | `PermissionPolicy.BALANCED` |
| Command Blocking | Regex pattern matching | Built-in blocklist |
| Whitelisting | Explicit allow list | `~/.consoul/whitelist.yaml` |

### Rate Limiting

| Control | Implementation | Configuration |
|---------|----------------|---------------|
| Per-Client Limits | Token bucket algorithm | `CONSOUL_DEFAULT_LIMITS` |
| Distributed Limits | Redis backend | `CONSOUL_RATE_LIMIT_REDIS_URL` |
| Multi-Window | Multiple time periods | `30/minute;500/hour` |

### Input Validation

| Control | Implementation | Configuration |
|---------|----------------|---------------|
| Body Size Limit | RequestValidator middleware | Manual setup required (not default) |
| Message Length | Pydantic validation | 32KB max (enforced) |
| JSON Parsing | Strict parsing | Automatic |

### Network Security

| Control | Implementation | Configuration |
|---------|----------------|---------------|
| TLS/HTTPS | Load balancer termination | Required in production |
| CORS | Origin allowlist | `CONSOUL_CORS_ORIGINS` |
| Private Networks | VPC/subnet isolation | Cloud configuration |

### Monitoring & Detection

| Control | Implementation | Configuration |
|---------|----------------|---------------|
| Health Checks | HTTP endpoints | `/health`, `/ready` |
| Metrics | Prometheus | Port 9090 |
| Error Alerting | Prometheus rules | Custom configuration |
| Audit Trail | AuditLogger | Multiple backends |

---

## Compliance Verification Checklist

### Pre-Audit Preparation

- [ ] **Document inventory**
  - List all Consoul deployments
  - Document network topology
  - Document data flows

- [ ] **Access review**
  - List all API keys and their purposes
  - Document who has access to secrets manager
  - Review cloud console access

- [ ] **Audit log export**
  - Export 12 months of audit logs
  - Verify logs are complete (no gaps)
  - Document log retention policy

- [ ] **Security configuration**
  - Document rate limiting settings
  - Document CORS configuration
  - Document tool permission policy
  - Document blocked command patterns

### Evidence Collection

| SOC2 Control | Evidence |
|--------------|----------|
| CC6.1 (Access) | API key configuration, authentication logs |
| CC6.6 (Unauthorized) | Rate limiting config, 429 response logs |
| CC6.7 (Transmission) | TLS certificate, HTTPS enforcement |
| CC7.1 (Detection) | Audit logs, alert configurations |
| A1.2 (Protection) | Health check configs, uptime metrics |

### Audit Interview Topics

Be prepared to discuss:
1. How are API keys managed and rotated?
2. How is unauthorized access prevented?
3. What audit trail exists for tool executions?
4. How is sensitive data protected in logs?
5. What is the incident response process?
6. How are security patches applied?

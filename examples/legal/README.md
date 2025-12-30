# Consoul Legal Industry Production Example

A production-ready deployment template for legal industry AI applications, specifically designed for workers' compensation attorneys analyzing case files.

## Features

- **Document Analysis**: PDF text extraction and AI-powered case analysis
- **Tool Restrictions**: Read-only tools only (no bash, file editing, or web access)
- **Filesystem Sandbox**: Per-matter storage isolation
- **Audit Logging**: Tamper-evident, PII-redacted compliance logs
- **Multi-User Isolation**: Matter-based session separation with Redis
- **Rate Limiting**: Per-API-key rate limits

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- Redis (included in Docker Compose)

### 1. Set Environment Variables

```bash
# Required
export OPENAI_API_KEY=your-openai-key-here
export CONSOUL_API_KEYS=your-api-key-1,your-api-key-2

# Optional
export CONSOUL_CORS_ORIGINS=https://your-app.example.com
export CONSOUL_PORT=8000
```

### 2. Start with Docker Compose

```bash
cd examples/legal
docker-compose up -d
```

### 3. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready
```

### 4. Make API Requests

```bash
# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-1" \
  -d '{
    "message": "Summarize the key facts in the Johnson deposition",
    "matter_id": "MATTER-001"
  }'

# Upload document
curl -X POST http://localhost:8000/upload/MATTER-001 \
  -H "X-API-Key: your-api-key-1" \
  -H "Content-Type: application/pdf" \
  -H "Content-Disposition: attachment; filename=deposition.pdf" \
  --data-binary @deposition.pdf
```

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (no auth) |
| `GET` | `/ready` | Readiness check with dependencies |
| `POST` | `/chat` | Send chat message |
| `POST` | `/upload/{matter_id}` | Upload document |
| `WS` | `/ws/chat/{matter_id}` | WebSocket streaming |

### Authentication

All endpoints except `/health` require API key authentication:

```bash
# Header authentication (recommended)
curl -H "X-API-Key: your-key" http://localhost:8000/chat

# Query parameter (for WebSocket clients)
wscat -c "ws://localhost:8000/ws/chat/MATTER-001?api_key=your-key"
```

### WebSocket Protocol

```javascript
// Connect and authenticate
ws.send(JSON.stringify({type: "auth", api_key: "your-key"}));

// Wait for auth result
// {"type": "auth_result", "success": true}

// Send message
ws.send(JSON.stringify({type: "message", content: "Analyze this case"}));

// Receive response
// {"type": "response", "content": "Based on the case files..."}
// {"type": "done", "tokens": 150, "cost": 0.001, "correlation_id": "abc123"}
```

## Security Configuration

### Tool Restrictions

Only read-only tools are enabled by default:

| Tool | Status | Risk Level |
|------|--------|------------|
| `read` | Allowed | Safe |
| `grep` | Allowed | Safe |
| `bash` | **Blocked** | Dangerous |
| `create_file` | **Blocked** | Caution |
| `edit_lines` | **Blocked** | Caution |
| `web_search` | **Blocked** | Safe but data leak risk |

### Filesystem Sandbox

Documents are isolated per matter:

```
/data/matters/
├── MATTER-001/
│   ├── deposition.pdf
│   └── medical_records.pdf
├── MATTER-002/
│   └── settlement_draft.docx
```

Path traversal attacks are prevented:
- Only `/data/matters/{matter_id}/` paths allowed
- System paths (`/etc`, `/var`, `/home`) blocked
- `..` traversal blocked at validation layer

### Rate Limiting

Default limits (configurable in `config.yaml`):

- 30 requests per minute per API key
- 500 requests per hour per API key

## Compliance & Audit Logging

### Audit Log Format

All actions are logged to `/var/log/consoul/legal_audit.jsonl`:

```json
{
  "timestamp": "2025-12-30T10:30:45.123456+00:00",
  "event_type": "execution",
  "tool_name": "read",
  "arguments": {"path": "/data/matters/MATTER-001/depo.pdf"},
  "correlation_id": "abc123def456",
  "session_id": "MATTER-001",
  "user": "key1234...",
  "decision": true,
  "result": "Read 15000 characters",
  "duration_ms": 250,
  "metadata": {"model": "gpt-4o", "tokens": 1500}
}
```

### PII Redaction

Sensitive fields are automatically redacted:

- Social Security Numbers
- Account numbers
- Credit card numbers
- Passwords and API keys
- Case/docket numbers

### Querying Audit Logs

```bash
# Find all actions by user
jq 'select(.user == "key1234...")' /var/log/consoul/legal_audit.jsonl

# Find all tool executions for a matter
jq 'select(.session_id == "MATTER-001")' /var/log/consoul/legal_audit.jsonl

# Find blocked actions
jq 'select(.event_type == "blocked")' /var/log/consoul/legal_audit.jsonl

# Trace a request by correlation ID
jq 'select(.correlation_id == "abc123")' /var/log/consoul/legal_audit.jsonl

# Count tool usage by type
jq -s 'group_by(.tool_name) | map({tool: .[0].tool_name, count: length})' \
  /var/log/consoul/legal_audit.jsonl
```

## Data Handling & Privacy

### OpenAI Enterprise Controls

For production legal deployments, configure OpenAI appropriately:

1. **Opt-out of training**: Contact OpenAI to opt out of model training on your data
2. **Data retention**: Review OpenAI's data retention policies
3. **Enterprise agreement**: Consider OpenAI Enterprise for additional controls
4. **Azure OpenAI**: For maximum data control, use Azure OpenAI with your own Azure subscription

### Attorney-Client Privilege

**IMPORTANT**: Communications within this system may be subject to attorney-client privilege.

- Do not share API keys with non-privileged parties
- Review all AI outputs before sharing with clients
- Audit logs may be discoverable - consult your ethics counsel

### Client Consent

Before using this system with client data:

1. Obtain written consent for AI-assisted analysis
2. Disclose that data is sent to third-party AI providers
3. Explain data retention and security measures
4. Document consent in client files

## Example Workflows

### Case Analysis

```python
from examples.legal.workflows.case_analysis import analyze_case_file

findings = analyze_case_file(
    file_path="/data/matters/MATTER-001/case_file.pdf",
    model="gpt-4o",
    jurisdiction="California"
)

print(findings.summary)
print(findings.to_json())
```

### Deposition Summary

```python
from examples.legal.workflows.deposition_summary import summarize_deposition

summary = summarize_deposition(
    file_path="/data/matters/MATTER-001/deposition.pdf",
    focus_areas=["injury description", "work restrictions"]
)

print(summary.executive_summary)
```

### Document Comparison

```python
from examples.legal.workflows.document_comparison import compare_documents

report = compare_documents(
    file1_path="/data/matters/MATTER-001/draft_v1.pdf",
    file2_path="/data/matters/MATTER-001/draft_v2.pdf"
)

print(f"Changes: {report.total_changes}")
print(f"High significance: {report.high_significance_changes}")
```

## File Upload Validation

Uploads are validated for:

| Check | Limit |
|-------|-------|
| File size | 50 MB max |
| MIME types | PDF, TXT, DOCX, DOC, RTF |
| Filename | Sanitized (alphanumeric, -, _, .) |

## Troubleshooting

### Common Issues

**Authentication fails (401)**
```bash
# Verify API key is set
echo $CONSOUL_API_KEYS

# Check key format (comma-separated, no spaces)
export CONSOUL_API_KEYS="key1,key2,key3"
```

**Rate limit exceeded (429)**
```bash
# Check current limits in config.yaml
# Adjust rate_limits as needed
```

**File not found**
```bash
# Verify file is in matter sandbox
ls /data/matters/MATTER-001/

# Check file permissions
ls -la /data/matters/MATTER-001/document.pdf
```

**Redis connection failed**
```bash
# Check Redis is running
docker-compose ps redis

# Check Redis connectivity
docker-compose exec redis redis-cli ping
```

### Logs

```bash
# Application logs
docker-compose logs -f consoul-legal

# Audit logs
docker-compose exec consoul-legal \
  tail -f /var/log/consoul/legal_audit.jsonl
```

## Production Deployment Checklist

- [ ] Configure OpenAI enterprise agreement
- [ ] Set strong, unique API keys
- [ ] Configure CORS for production domains
- [ ] Set up log rotation for audit logs
- [ ] Configure backup for audit logs and matter storage
- [ ] Review and customize PII redaction fields
- [ ] Set up monitoring and alerting
- [ ] Document client consent procedures
- [ ] Train staff on proper usage
- [ ] Establish incident response procedures

## Legal Disclaimer

This software is provided for informational purposes only and does not constitute legal advice. The AI-generated analysis should be reviewed by a licensed attorney before use in legal proceedings. No attorney-client relationship is created by using this software.

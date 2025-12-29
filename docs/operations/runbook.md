# Consoul Operations Runbook

Step-by-step procedures for daily operations, monitoring, and troubleshooting.

## Table of Contents

- [Daily Operations](#daily-operations)
- [Health Monitoring](#health-monitoring)
- [Prometheus Metrics](#prometheus-metrics)
- [Alert Configuration](#alert-configuration)
- [Common Procedures](#common-procedures)
- [Troubleshooting](#troubleshooting)
- [Log Analysis](#log-analysis)

---

## Daily Operations

### Morning Checklist

1. **Check service health**
   ```bash
   curl -s http://YOUR_HOST/health | jq
   ```
   Expected response:
   ```json
   {
     "status": "ok",
     "service": "Consoul API",
     "version": "0.4.2",
     "timestamp": "2025-12-25T08:00:00.000000Z",
     "connections": 5
   }
   ```

2. **Check readiness (dependency health)**
   ```bash
   curl -s http://YOUR_HOST/ready | jq
   ```
   Expected response (HTTP 200):
   ```json
   {
     "status": "ready",
     "checks": {"redis": true},
     "timestamp": "2025-12-25T08:00:00.000000Z"
   }
   ```

3. **Review error rates** (last 24 hours)
   ```promql
   sum(rate(consoul_errors_total[24h])) / sum(rate(consoul_request_total[24h])) * 100
   ```

4. **Check p95 latency**
   ```promql
   histogram_quantile(0.95, sum(rate(consoul_request_latency_seconds_bucket[1h])) by (le))
   ```

5. **Review active sessions**
   ```promql
   consoul_active_sessions
   ```

### Log Review Commands

**GCP Cloud Logging:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND severity>=WARNING" \
  --project=YOUR_PROJECT --limit=100
```

**AWS CloudWatch:**
```bash
aws logs filter-log-events \
  --log-group-name /ecs/consoul-api \
  --filter-pattern "?ERROR ?WARNING" \
  --start-time $(date -d '24 hours ago' +%s000)
```

**Azure Log Analytics:**
```kusto
ContainerAppConsoleLogs
| where TimeGenerated > ago(24h)
| where Log contains "ERROR" or Log contains "WARNING"
| order by TimeGenerated desc
| take 100
```

---

## Health Monitoring

### Liveness Probe: GET /health

**Purpose**: Verify the service is running. Always returns HTTP 200 when the process is alive.

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "ok" when running |
| `service` | string | Service name (Consoul API) |
| `version` | string | Package version |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `connections` | int | Active WebSocket connections |

**Kubernetes Config**:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

### Readiness Probe: GET /ready

**Purpose**: Verify dependencies (Redis) are healthy. Returns HTTP 503 if unhealthy.

**Success Response (HTTP 200)**:
```json
{
  "status": "ready",
  "checks": {"redis": true},
  "timestamp": "2025-12-25T08:00:00.000000Z"
}
```

**Failure Response (HTTP 503)**:
```json
{
  "status": "not_ready",
  "checks": {"redis": false},
  "message": "Redis connection failed",
  "timestamp": "2025-12-25T08:00:00.000000Z"
}
```

**Kubernetes Config**:
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

---

## Prometheus Metrics

### Available Metrics

Metrics are exposed on a **separate port** (default: 9090) at `/metrics`.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `consoul_request_total` | Counter | endpoint, method, status, model | Total HTTP requests |
| `consoul_request_latency_seconds` | Histogram | endpoint, method | Request latency distribution |
| `consoul_token_usage_total` | Counter | direction, model, session_id | Token consumption (input/output) |
| `consoul_active_sessions` | Gauge | - | Current WebSocket connections |
| `consoul_tool_executions_total` | Counter | tool_name, status | Tool execution counts |
| `consoul_errors_total` | Counter | endpoint, error_type | Error counts |

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'consoul'
    static_configs:
      - targets: ['consoul-api:9090']
    scrape_interval: 15s
    metrics_path: /metrics
```

### Key PromQL Queries

**Request Rate (requests/second)**:
```promql
sum(rate(consoul_request_total[5m]))
```

**Error Rate (percentage)**:
```promql
sum(rate(consoul_errors_total[5m])) / sum(rate(consoul_request_total[5m])) * 100
```

**Latency Percentiles**:
```promql
# p50
histogram_quantile(0.50, sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le))

# p95
histogram_quantile(0.95, sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le))

# p99
histogram_quantile(0.99, sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le))
```

**Token Usage Rate**:
```promql
sum(rate(consoul_token_usage_total[1h])) by (direction, model)
```

**Active Sessions Over Time**:
```promql
consoul_active_sessions
```

**Tool Execution Success Rate**:
```promql
sum(rate(consoul_tool_executions_total{status="success"}[5m])) /
sum(rate(consoul_tool_executions_total[5m])) * 100
```

---

## Alert Configuration

### Recommended Alert Rules

```yaml
groups:
  - name: consoul
    rules:
      # High error rate
      - alert: ConsoulHighErrorRate
        expr: |
          sum(rate(consoul_errors_total[5m])) /
          sum(rate(consoul_request_total[5m])) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Consoul error rate > 1%"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Critical error rate
      - alert: ConsoulCriticalErrorRate
        expr: |
          sum(rate(consoul_errors_total[5m])) /
          sum(rate(consoul_request_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Consoul error rate > 5%"

      # High latency
      - alert: ConsoulHighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le)
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Consoul p95 latency > 2s"
          description: "p95 latency is {{ $value | humanizeDuration }}"

      # Service unhealthy
      - alert: ConsoulUnhealthy
        expr: up{job="consoul"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Consoul service is down"

      # Redis connection failed
      - alert: ConsoulRedisDown
        expr: |
          probe_success{job="consoul-ready"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Consoul readiness check failing"
          description: "Redis connection may be down"

      # High active sessions
      - alert: ConsoulHighSessions
        expr: consoul_active_sessions > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High number of active sessions"
          description: "{{ $value }} active sessions"
```

### Alert Thresholds

| Metric | Warning | Critical | Rationale |
|--------|---------|----------|-----------|
| Error Rate | > 1% | > 5% | Above 1% impacts user experience |
| p95 Latency | > 2s | > 5s | LLM calls typically 1-3s |
| Active Sessions | > 1000 | > 5000 | Based on capacity planning |
| Health Check | - | Down > 1m | Immediate escalation |

---

## Common Procedures

### Restarting the Service

**Kubernetes**:
```bash
kubectl rollout restart deployment/consoul-api -n production
```

**Docker Compose**:
```bash
docker-compose restart api
```

**ECS**:
```bash
aws ecs update-service --cluster consoul --service consoul-api --force-new-deployment
```

**Cloud Run**:
```bash
gcloud run services update consoul-api --region us-central1 --clear-env-vars FORCE_RESTART
```

### Rotating API Keys

1. **Generate new keys**:
   ```bash
   NEW_KEY=$(openssl rand -hex 32)
   echo "New API key: $NEW_KEY"
   ```

2. **Update secrets manager**:

   **AWS**:
   ```bash
   aws secretsmanager update-secret \
     --secret-id consoul-api-keys \
     --secret-string "old-key,$NEW_KEY"
   ```

   **GCP**:
   ```bash
   echo -n "old-key,$NEW_KEY" | gcloud secrets versions add consoul-api-keys --data-file=-
   ```

   **Azure**:
   ```bash
   az keyvault secret set --vault-name consoul-vault \
     --name api-keys --value "old-key,$NEW_KEY"
   ```

3. **Restart service** to pick up new keys

4. **After clients migrate**, remove old key from the list

### Clearing Rate Limit State

**Warning**: This resets rate limits for all clients.

```bash
# Connect to Redis
redis-cli -h REDIS_HOST

# View rate limit keys
KEYS consoul:ratelimit:*

# Clear all rate limit state
redis-cli -h REDIS_HOST KEYS "consoul:ratelimit:*" | xargs redis-cli -h REDIS_HOST DEL
```

### Viewing Audit Logs

**JSONL File (FileAuditLogger)**:
```bash
# Recent tool executions
tail -100 /var/log/consoul/audit.jsonl | jq 'select(.event_type == "execution")'

# Denied tool requests
cat audit.jsonl | jq 'select(.event_type == "denial")'

# Errors in last hour
cat audit.jsonl | jq 'select(.event_type == "error")' | \
  jq 'select(.timestamp > "'$(date -d '1 hour ago' -Iseconds)'")'
```

**SQLite (SQLiteAuditLogger)**:
```bash
sqlite3 audit.db "SELECT * FROM audit_log WHERE event_type='error' ORDER BY timestamp DESC LIMIT 100"
```

---

## Troubleshooting

### High Error Rate

```
┌─────────────────────────────────────────────────────────────┐
│                    High Error Rate                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │ Check error types       │
              │ in Prometheus           │
              └─────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 401 Errors      │ │ 429 Errors      │ │ 500 Errors      │
│ (Auth failures) │ │ (Rate limited)  │ │ (Server errors) │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ • Check API key │ │ • Adjust limits │ │ • Check logs    │
│ • Verify header │ │ • Clear Redis   │ │ • Check Redis   │
│ • Check bypass  │ │ • Scale service │ │ • Check LLM API │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### High Latency

```
┌─────────────────────────────────────────────────────────────┐
│                    High Latency                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │ Which endpoint is slow? │
              └─────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ /chat endpoint  │ │ /ready endpoint │ │ All endpoints   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ • LLM provider  │ │ • Redis latency │ │ • CPU/memory    │
│   latency       │ │ • Network issue │ │ • Scale up      │
│ • Large context │ │                 │ │ • Add workers   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Redis Connectivity Issues

1. **Check readiness endpoint**:
   ```bash
   curl -s http://YOUR_HOST/ready | jq
   ```

2. **Verify Redis is reachable**:
   ```bash
   redis-cli -h REDIS_HOST ping
   ```

3. **Check connection count**:
   ```bash
   redis-cli -h REDIS_HOST INFO clients | grep connected_clients
   ```

4. **Check memory usage**:
   ```bash
   redis-cli -h REDIS_HOST INFO memory | grep used_memory_human
   ```

5. **View slow queries**:
   ```bash
   redis-cli -h REDIS_HOST SLOWLOG GET 10
   ```

### Authentication Failures

1. **Check for failed auth in logs**:
   ```bash
   # Pattern: "Authentication failed for {client_ip} on {path}"
   grep "Authentication failed" /var/log/consoul/app.log
   ```

2. **Verify API key is set**:
   ```bash
   # Check environment variable
   echo $CONSOUL_API_KEYS
   ```

3. **Test with curl**:
   ```bash
   # Header method
   curl -H "X-API-Key: YOUR_KEY" http://YOUR_HOST/health

   # Query parameter method
   curl "http://YOUR_HOST/health?api_key=YOUR_KEY"
   ```

4. **Verify bypass paths**:
   ```bash
   # These should work without auth
   curl http://YOUR_HOST/health
   curl http://YOUR_HOST/ready
   curl http://YOUR_HOST/docs
   ```

---

## Log Analysis

### Log Patterns to Monitor

| Pattern | Severity | Action |
|---------|----------|--------|
| `Authentication failed` | Warning | Check API key configuration |
| `Rate limit exceeded` | Info | Normal if occasional, investigate if frequent |
| `Redis connection failed` | Error | Check Redis health immediately |
| `Session storage error` | Error | Check Redis connectivity |
| `Tool approval timeout` | Warning | Normal - user didn't approve in time |
| `Chat error for session` | Error | Check LLM provider status |

### Structured Log Queries

**CloudWatch Insights**:
```
fields @timestamp, @message
| filter @message like /ERROR|CRITICAL/
| sort @timestamp desc
| limit 100
```

**Stackdriver**:
```
resource.type="cloud_run_revision"
severity>=ERROR
```

### Log Retention Recommendations

| Log Type | Retention | Rationale |
|----------|-----------|-----------|
| Application logs | 30 days | Debugging, troubleshooting |
| Audit logs | 1 year | Compliance requirement |
| Access logs | 90 days | Security analysis |
| Metrics | 13 months | Year-over-year comparison |

---

## Environment Variables Reference

```bash
# Security
CONSOUL_API_KEYS=key1,key2,key3           # Comma-separated API keys
CONSOUL_API_KEY_HEADER=X-API-Key          # Header name (default)
CONSOUL_BYPASS_PATHS=/health,/ready,/docs # Unauthenticated paths

# Rate Limiting
CONSOUL_ENABLED=true                       # Enable rate limiting
CONSOUL_DEFAULT_LIMITS="30/minute;500/hour" # Rate limits
CONSOUL_RATE_LIMIT_REDIS_URL=redis://...  # Redis for distributed limiting
CONSOUL_STRATEGY=moving-window            # Rate limit strategy

# Sessions
CONSOUL_SESSION_REDIS_URL=redis://...     # Redis for sessions
CONSOUL_SESSION_TTL=3600                  # Session TTL (seconds)
CONSOUL_SESSION_KEY_PREFIX=consoul:session:

# CORS
CONSOUL_CORS_ORIGINS=https://app.example.com
CONSOUL_CORS_ALLOW_CREDENTIALS=true
CONSOUL_CORS_MAX_AGE=600

# Observability
CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true
CONSOUL_OBSERVABILITY_METRICS_PORT=9090
CONSOUL_OBSERVABILITY_OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

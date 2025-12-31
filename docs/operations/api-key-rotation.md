# API Key Rotation Guide

Zero-downtime procedures for rotating API keys, monitoring key usage, and emergency revocation.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Zero-Downtime Rotation Procedure](#zero-downtime-rotation-procedure)
- [Environment Variable Patterns](#environment-variable-patterns)
- [Monitoring Key Usage](#monitoring-key-usage)
- [Emergency Revocation](#emergency-revocation)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

Regular API key rotation is essential for:

- **Security Hygiene**: Limit exposure window if keys are compromised
- **Compliance**: Meet requirements for SOC 2, HIPAA, PCI-DSS
- **Incident Response**: Quickly revoke compromised credentials
- **Employee Offboarding**: Invalidate keys held by departing staff
- **Access Auditing**: Track which keys are actively used

Consoul supports multiple concurrent API keys via the `CONSOUL_API_KEYS` environment variable, enabling zero-downtime rotation.

---

## Prerequisites

Before rotating keys, ensure:

1. **Multiple key support enabled**
   ```bash
   # Verify current configuration supports multiple keys
   echo $CONSOUL_API_KEYS
   # Should be comma-separated or JSON array format
   ```

2. **Redis configured** (for distributed deployments)
   ```bash
   # Rate limiting and sessions require Redis for multi-instance coordination
   CONSOUL_RATE_LIMIT_REDIS_URL=redis://redis:6379/0
   ```

3. **Prometheus metrics enabled** (for monitoring)
   ```bash
   # Verify metrics endpoint is accessible
   curl http://localhost:9090/metrics | grep consoul_api_key
   ```

4. **Client inventory documented**
   - List of all services/applications using each key
   - Contact information for key owners
   - Deployment method for each client

---

## Zero-Downtime Rotation Procedure

### Step 1: Generate New Key

```bash
# Generate a cryptographically secure 32-byte key
NEW_KEY=$(openssl rand -hex 32)
echo "New key: sk-new-${NEW_KEY}"

# Or use a structured format with purpose prefix
NEW_KEY="sk-$(date +%Y%m)-$(openssl rand -hex 24)"
echo "New key: ${NEW_KEY}"
```

### Step 2: Add New Key (Overlap Period Begins)

Add the new key alongside existing keys:

```bash
# Current keys
export CONSOUL_API_KEYS="sk-old-abc123"

# Add new key (comma-separated)
export CONSOUL_API_KEYS="sk-old-abc123,sk-new-xyz789"

# Or JSON format
export CONSOUL_API_KEYS='["sk-old-abc123","sk-new-xyz789"]'
```

### Step 3: Rolling Restart

Restart server instances to pick up the new configuration:

```bash
# Kubernetes
kubectl rollout restart deployment/consoul-api

# Docker Compose
docker-compose up -d --no-deps consoul-api

# Systemd
sudo systemctl reload consoul-api
```

### Step 4: Distribute New Key to Clients

Notify all key users with the new credential:

```markdown
Subject: [ACTION REQUIRED] API Key Rotation - Consoul

The Consoul API key is being rotated. Please update your configuration:

**New Key**: sk-new-xyz789...
**Deadline**: [DATE + 30 days]
**Old Key Revocation**: [DATE + 30 days]

Update your environment:
  export CONSOUL_API_KEY="sk-new-xyz789..."

Contact: platform-team@company.com
```

### Step 5: Monitor Key Usage

Track which keys are being used via Prometheus metrics:

```promql
# Requests per key in the last 24 hours
sum(increase(consoul_api_key_requests_total[24h])) by (api_key_id)

# Keys not used in the last 7 days (candidates for removal)
consoul_api_key_last_used_timestamp < (time() - 7*24*60*60)
```

### Step 6: Remove Old Key (After Grace Period)

Once all clients have migrated (verify via metrics):

```bash
# Remove old key
export CONSOUL_API_KEYS="sk-new-xyz789"

# Rolling restart
kubectl rollout restart deployment/consoul-api
```

### Step 7: Verify Rotation Complete

```bash
# Confirm old key no longer works
curl -H "X-API-Key: sk-old-abc123" https://api.example.com/health
# Should return 401 Unauthorized

# Confirm new key works
curl -H "X-API-Key: sk-new-xyz789" https://api.example.com/health
# Should return 200 OK
```

---

## Environment Variable Patterns

### Comma-Separated Format

Simple format for a few keys:

```bash
export CONSOUL_API_KEYS="key1,key2,key3"
```

### JSON Array Format

Preferred for keys with special characters or programmatic management:

```bash
export CONSOUL_API_KEYS='["sk-abc123","sk-xyz789","sk-def456"]'
```

### Tier Assignment

Assign rate limit tiers to specific keys using glob patterns:

```bash
# Tier configuration
export CONSOUL_API_KEY_TIERS='{
  "sk-premium-*": "premium",
  "sk-standard-*": "standard",
  "sk-internal-*": "unlimited"
}'

# Rate limits per tier
export CONSOUL_TIER_LIMITS='{
  "premium": "100/minute;2000/hour",
  "standard": "30/minute;500/hour",
  "unlimited": "1000/minute"
}'
```

### Secrets Manager Integration

**AWS Secrets Manager**:
```bash
# Fetch keys from Secrets Manager
export CONSOUL_API_KEYS=$(aws secretsmanager get-secret-value \
  --secret-id consoul/api-keys \
  --query SecretString --output text)
```

**GCP Secret Manager**:
```bash
export CONSOUL_API_KEYS=$(gcloud secrets versions access latest \
  --secret=consoul-api-keys)
```

**Azure Key Vault**:
```bash
export CONSOUL_API_KEYS=$(az keyvault secret show \
  --vault-name consoul-vault \
  --name api-keys \
  --query value -o tsv)
```

---

## Monitoring Key Usage

### Prometheus Metrics

Consoul exposes per-key metrics (keys are redacted for security):

| Metric | Type | Description |
|--------|------|-------------|
| `consoul_api_key_requests_total` | Counter | Total requests by API key (redacted) |
| `consoul_api_key_last_used_timestamp` | Gauge | Unix timestamp of last request |

### Example Queries

**Requests by key in the last hour**:
```promql
sum(increase(consoul_api_key_requests_total[1h])) by (api_key_id)
```

**Keys with no activity in 7 days**:
```promql
(time() - consoul_api_key_last_used_timestamp) > 7*24*60*60
```

**Top 10 keys by request volume**:
```promql
topk(10, sum(rate(consoul_api_key_requests_total[24h])) by (api_key_id))
```

**Alert on old key usage after rotation**:
```yaml
# Prometheus alerting rule
groups:
  - name: api-key-rotation
    rules:
      - alert: OldKeyStillInUse
        expr: |
          increase(consoul_api_key_requests_total{api_key_id=~"sk-old.*"}[1h]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Old API key still being used after rotation window"
          description: "Key {{ $labels.api_key_id }} received {{ $value }} requests in the last hour"
```

### Grafana Dashboard

Example panel configurations:

```json
{
  "title": "API Key Usage",
  "type": "timeseries",
  "targets": [
    {
      "expr": "sum(rate(consoul_api_key_requests_total[5m])) by (api_key_id)",
      "legendFormat": "{{ api_key_id }}"
    }
  ]
}
```

---

## Emergency Revocation

When a key is compromised, immediate revocation is required.

### Immediate Revocation Procedure

**Step 1: Remove the compromised key immediately**

```bash
# Remove the key from configuration
export CONSOUL_API_KEYS="remaining-valid-key-1,remaining-valid-key-2"
```

**Step 2: Force restart all instances**

```bash
# Kubernetes - immediate restart
kubectl delete pods -l app=consoul-api

# Docker - force recreate
docker-compose up -d --force-recreate consoul-api

# Systemd - immediate restart
sudo systemctl restart consoul-api
```

**Step 3: Verify key is rejected**

```bash
curl -v -H "X-API-Key: COMPROMISED_KEY" https://api.example.com/chat
# Expected: 401 Unauthorized
```

**Step 4: Generate replacement key**

```bash
NEW_KEY="sk-emergency-$(openssl rand -hex 24)"
export CONSOUL_API_KEYS="${CONSOUL_API_KEYS},${NEW_KEY}"
```

**Step 5: Notify affected parties**

### Client Notification Template

```markdown
Subject: [URGENT] API Key Revoked - Immediate Action Required

Due to a security incident, the following API key has been revoked:
  Key prefix: sk-abc...

**Your service may be impacted if using this key.**

Replacement key: sk-new-xyz...

Please update your configuration immediately.

Contact security@company.com with any questions.
```

### Incident Response Checklist

- [ ] Compromised key identified and documented
- [ ] Key removed from CONSOUL_API_KEYS
- [ ] All server instances restarted
- [ ] Key rejection verified (401 response)
- [ ] Replacement key generated
- [ ] Affected clients identified and notified
- [ ] Incident logged in security system
- [ ] Post-mortem scheduled
- [ ] Rate limit increased temporarily (if DoS concern)

---

## Best Practices

### Rotation Schedule

| Environment | Rotation Frequency | Grace Period |
|-------------|-------------------|--------------|
| Production | 90 days | 30 days |
| Staging | 60 days | 14 days |
| Development | 180 days | 7 days |

### Key Naming Conventions

Use structured prefixes to identify key purpose:

```
sk-{tier}-{environment}-{purpose}-{date}

Examples:
  sk-premium-prod-frontend-202501
  sk-standard-staging-backend-202502
  sk-internal-dev-testing-202503
```

### Security Recommendations

1. **Never log full keys** - Use redacted format (first 6 + last 3 chars)
2. **Store in secrets manager** - Never in environment files or source control
3. **Use separate keys per service** - Easier to revoke individual services
4. **Monitor for anomalies** - Alert on unusual request patterns
5. **Automate rotation** - Schedule regular rotations via CI/CD
6. **Document key owners** - Maintain inventory of who owns each key

### Automation Example

```yaml
# GitHub Actions - Automated Key Rotation
name: Rotate API Keys
on:
  schedule:
    - cron: '0 0 1 */3 *'  # Quarterly

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Generate new key
        run: |
          NEW_KEY="sk-prod-$(date +%Y%m)-$(openssl rand -hex 24)"
          echo "NEW_KEY=${NEW_KEY}" >> $GITHUB_ENV

      - name: Update secrets manager
        run: |
          # Add new key alongside existing
          aws secretsmanager update-secret \
            --secret-id consoul/api-keys \
            --secret-string "[\"${{ env.NEW_KEY }}\",\"${{ secrets.CURRENT_KEY }}\"]"

      - name: Notify team
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "API key rotation initiated. New key prefix: ${NEW_KEY:0:12}..."
            }
```

---

## Troubleshooting

### Key Not Being Accepted

```bash
# Verify key is in configuration
echo $CONSOUL_API_KEYS | grep "your-key-prefix"

# Check server logs for auth failures
kubectl logs -l app=consoul-api | grep "Authentication failed"

# Verify restart completed
kubectl rollout status deployment/consoul-api
```

### Metrics Not Appearing

```bash
# Check if metrics are enabled
curl localhost:9090/metrics | grep consoul_api_key

# Verify prometheus-client is installed
pip show prometheus-client
```

### Rate Limiting Not Applied to New Key

```bash
# Verify tier assignment matches key pattern
echo $CONSOUL_API_KEY_TIERS | jq .

# Check if key matches any tier pattern
# Pattern: "sk-premium-*" should match "sk-premium-abc123"
```

---

## Related Documentation

- [Security Checklist](./security-checklist.md) - Pre-deployment and ongoing security verification
- [Incident Response](./incident-response.md) - Full incident handling procedures
- [Runbook](./runbook.md) - Day-to-day operations guide

---

**Last Updated**: December 2025
**Version**: 1.0
**Ticket**: SOUL-343

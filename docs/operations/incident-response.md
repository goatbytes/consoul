# Consoul Incident Response Guide

Procedures for detecting, triaging, and resolving incidents.

## Table of Contents

- [Severity Levels](#severity-levels)
- [Detection](#detection)
- [Triage Process](#triage-process)
- [Resolution Playbooks](#resolution-playbooks)
- [Post-Mortem Template](#post-mortem-template)
- [Communication Templates](#communication-templates)

---

## Severity Levels

### P1 - Critical

**Definition**: Complete service outage, data breach, or security incident.

**Examples**:
- Service completely unavailable
- Data breach or unauthorized access
- All requests failing
- Security vulnerability actively exploited

**Response Time**: Immediate (< 15 minutes)

**Escalation**: Page on-call, notify leadership

### P2 - High

**Definition**: Significant degradation affecting most users.

**Examples**:
- High error rate (> 5%)
- Severe latency (> 10s p95)
- Partial outage affecting subset of users
- Redis connection intermittent

**Response Time**: < 30 minutes

**Escalation**: Page on-call during business hours

### P3 - Medium

**Definition**: Noticeable issues affecting some users.

**Examples**:
- Elevated error rate (1-5%)
- Increased latency (2-10s p95)
- Rate limiting issues
- Authentication problems for specific keys

**Response Time**: < 2 hours

**Escalation**: Slack notification

### P4 - Low

**Definition**: Minor issues with minimal user impact.

**Examples**:
- Warning-level alerts
- Non-critical errors in logs
- Performance degradation below thresholds

**Response Time**: Next business day

**Escalation**: Ticket creation

---

## Detection

### Automated Detection

#### Prometheus Alerts
```yaml
# P1 - Service Down
- alert: ConsoulServiceDown
  expr: up{job="consoul"} == 0
  for: 1m
  labels:
    severity: P1

# P1 - Readiness Failing
- alert: ConsoulReadinessFailing
  expr: probe_success{job="consoul-ready"} == 0
  for: 2m
  labels:
    severity: P1

# P2 - High Error Rate
- alert: ConsoulHighErrorRate
  expr: |
    sum(rate(consoul_errors_total[5m])) /
    sum(rate(consoul_request_total[5m])) > 0.05
  for: 5m
  labels:
    severity: P2

# P3 - Elevated Error Rate
- alert: ConsoulElevatedErrorRate
  expr: |
    sum(rate(consoul_errors_total[5m])) /
    sum(rate(consoul_request_total[5m])) > 0.01
  for: 10m
  labels:
    severity: P3

# P2 - High Latency
- alert: ConsoulHighLatency
  expr: |
    histogram_quantile(0.95,
      sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le)
    ) > 10
  for: 5m
  labels:
    severity: P2
```

#### Health Check Monitoring
```bash
# External probe every 30 seconds
curl -sf http://YOUR_HOST/health || echo "UNHEALTHY"
curl -sf http://YOUR_HOST/ready || echo "NOT_READY"
```

### Manual Detection

#### Log Patterns Indicating Issues
```bash
# Critical errors
grep -E "CRITICAL|FATAL" /var/log/consoul/app.log

# Connection failures
grep "Redis connection" /var/log/consoul/app.log

# Authentication anomalies
grep "Authentication failed" /var/log/consoul/app.log | \
  awk '{print $NF}' | sort | uniq -c | sort -rn
```

#### Customer Reports
Document customer-reported issues:
- Time of issue
- Error messages seen
- Session ID (if available)
- Steps to reproduce

---

## Triage Process

### Step 1: Assess Scope

```bash
# 1. Check health endpoint
curl -s http://YOUR_HOST/health | jq

# 2. Check readiness endpoint
curl -s http://YOUR_HOST/ready | jq

# 3. Check recent error rate
# (Use Prometheus query or Grafana dashboard)

# 4. Check active sessions
curl -s http://YOUR_HOST/health | jq '.connections'
```

### Step 2: Check Recent Changes

- [ ] Any deployments in last 24 hours?
- [ ] Any configuration changes?
- [ ] Any infrastructure changes?
- [ ] Any dependency updates?

### Step 3: Identify Affected Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Component Health Check                    │
└─────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Consoul API    │ │     Redis       │ │   LLM Provider  │
│                 │ │                 │ │                 │
│ curl /health    │ │ redis-cli ping  │ │ Check provider  │
│ curl /ready     │ │ INFO memory     │ │ status page     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Container logs  │ │ Connection pool │ │ API key valid?  │
│ CPU/memory      │ │ Memory usage    │ │ Rate limited?   │
│ Network         │ │ Slow queries    │ │ Quota exceeded? │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Step 4: Determine Severity

Use the [Severity Levels](#severity-levels) table to classify the incident.

### Step 5: Begin Resolution

Select the appropriate [Resolution Playbook](#resolution-playbooks).

---

## Resolution Playbooks

### Playbook: Service Unavailable (P1)

**Symptoms**: Health endpoint not responding, all requests failing

**Steps**:

1. **Verify the issue**
   ```bash
   curl -v http://YOUR_HOST/health
   # Check for connection refused, timeout, or error response
   ```

2. **Check container/pod status**
   ```bash
   # Kubernetes
   kubectl get pods -n production -l app=consoul-api
   kubectl describe pod POD_NAME -n production

   # Docker
   docker ps -a | grep consoul
   docker logs CONTAINER_ID --tail 100

   # ECS
   aws ecs describe-services --cluster consoul --services consoul-api
   ```

3. **Check resource exhaustion**
   ```bash
   # CPU/Memory
   kubectl top pods -n production

   # Disk
   df -h
   ```

4. **Restart the service**
   ```bash
   # Kubernetes
   kubectl rollout restart deployment/consoul-api -n production

   # Docker
   docker-compose restart api

   # ECS
   aws ecs update-service --cluster consoul --service consoul-api --force-new-deployment
   ```

5. **Verify recovery**
   ```bash
   curl -s http://YOUR_HOST/health | jq
   ```

6. **Document and create post-mortem**

### Playbook: High Latency (P2)

**Symptoms**: p95 latency > 2s, slow responses

**Steps**:

1. **Identify slow endpoints**
   ```promql
   histogram_quantile(0.95,
     sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le, endpoint)
   )
   ```

2. **Check Redis latency**
   ```bash
   redis-cli -h REDIS_HOST --latency
   redis-cli -h REDIS_HOST SLOWLOG GET 10
   ```

3. **Check LLM provider status**
   - [Anthropic Status](https://status.anthropic.com)
   - [OpenAI Status](https://status.openai.com)

4. **Check resource utilization**
   ```bash
   kubectl top pods -n production
   ```

5. **Scale if needed**
   ```bash
   # Kubernetes
   kubectl scale deployment/consoul-api --replicas=5 -n production

   # ECS
   aws ecs update-service --cluster consoul --service consoul-api --desired-count 5
   ```

6. **Monitor recovery**
   ```promql
   histogram_quantile(0.95, sum(rate(consoul_request_latency_seconds_bucket[1m])) by (le))
   ```

### Playbook: High Error Rate (P2/P3)

**Symptoms**: Error rate > 1%, increased 4xx/5xx responses

**Steps**:

1. **Identify error types**
   ```promql
   sum(rate(consoul_errors_total[5m])) by (error_type)
   ```

2. **Check logs for error patterns**
   ```bash
   grep -E "ERROR|Exception" /var/log/consoul/app.log | tail -100
   ```

3. **For 401 errors (authentication)**:
   ```bash
   # Verify API keys are configured
   echo $CONSOUL_API_KEYS

   # Check if keys were rotated recently
   # Test authentication
   curl -H "X-API-Key: YOUR_KEY" http://YOUR_HOST/health
   ```

4. **For 429 errors (rate limiting)**:
   ```bash
   # Check current rate limit state
   redis-cli -h REDIS_HOST KEYS "consoul:ratelimit:*"

   # Adjust limits if needed (via config change)
   ```

5. **For 500 errors (server errors)**:
   ```bash
   # Check logs for stack traces
   grep -A 20 "Traceback" /var/log/consoul/app.log | tail -50

   # Check Redis connectivity
   curl -s http://YOUR_HOST/ready | jq
   ```

6. **Monitor error rate recovery**
   ```promql
   sum(rate(consoul_errors_total[1m])) / sum(rate(consoul_request_total[1m])) * 100
   ```

### Playbook: Redis Connection Issues (P1/P2)

**Symptoms**: Readiness check failing, session errors in logs

**Steps**:

1. **Check readiness endpoint**
   ```bash
   curl -s http://YOUR_HOST/ready | jq
   ```

2. **Verify Redis is accessible**
   ```bash
   redis-cli -h REDIS_HOST ping
   ```

3. **Check Redis health**
   ```bash
   redis-cli -h REDIS_HOST INFO clients
   redis-cli -h REDIS_HOST INFO memory
   redis-cli -h REDIS_HOST INFO stats
   ```

4. **Check network connectivity**
   ```bash
   # From container
   kubectl exec -it POD_NAME -n production -- nc -zv REDIS_HOST 6379
   ```

5. **If Redis is down**, check Redis cluster/instance:
   ```bash
   # AWS ElastiCache
   aws elasticache describe-replication-groups

   # GCP Memorystore
   gcloud redis instances describe INSTANCE_NAME --region=REGION

   # Azure Cache
   az redis show --name REDIS_NAME --resource-group RG_NAME
   ```

6. **If persistent issue**, failover or restart Redis:
   ```bash
   # ElastiCache
   aws elasticache modify-replication-group --replication-group-id ID --primary-cluster-id NEW_PRIMARY

   # Memorystore
   gcloud redis instances failover INSTANCE_NAME --region=REGION
   ```

### Playbook: Security Incident (P1)

**Symptoms**: Unauthorized access, suspicious activity, data breach indicators

**Steps**:

1. **Contain the incident**
   ```bash
   # Block suspicious IPs at load balancer
   # Rotate compromised API keys immediately
   ```

2. **Preserve evidence**
   ```bash
   # Export relevant logs
   kubectl logs deployment/consoul-api -n production --since=24h > incident_logs.txt

   # Export audit logs
   cp /var/log/consoul/audit.jsonl incident_audit.jsonl
   ```

3. **Assess scope**
   - Which API keys were compromised?
   - What data was accessed?
   - How long was access possible?

4. **Rotate all credentials**
   ```bash
   # Generate new API keys
   NEW_KEY=$(openssl rand -hex 32)

   # Update in secrets manager
   # Restart service
   ```

5. **Notify stakeholders**
   - Security team
   - Legal team (if data breach)
   - Affected customers

6. **Create detailed post-mortem**

---

## Post-Mortem Template

```markdown
# Incident Post-Mortem: [INCIDENT TITLE]

**Date**: YYYY-MM-DD
**Duration**: HH:MM (start) - HH:MM (end)
**Severity**: P1/P2/P3
**Author**: [Name]

## Summary

[2-3 sentence summary of what happened and impact]

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | Alert triggered |
| HH:MM | On-call acknowledged |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Service restored |
| HH:MM | All-clear announced |

## Impact

- **Duration**: X minutes/hours
- **Users affected**: X% / X users
- **Revenue impact**: $X (if applicable)
- **SLA impact**: Yes/No

## Root Cause

[Detailed explanation of what caused the incident]

## Detection

- How was the incident detected?
- Was detection timely?
- Could we have detected it sooner?

## Resolution

1. [Step 1 taken to resolve]
2. [Step 2 taken to resolve]
3. [Final step to restore service]

## What Went Well

- [Positive observation 1]
- [Positive observation 2]

## What Went Poorly

- [Negative observation 1]
- [Negative observation 2]

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | YYYY-MM-DD | Open |
| [Action 2] | [Name] | YYYY-MM-DD | Open |

## Lessons Learned

[Key takeaways from this incident]

## Supporting Information

- Link to relevant dashboards
- Link to relevant logs
- Link to related tickets
```

---

## Communication Templates

### Internal Alert

```
🚨 INCIDENT: [SEVERITY] - [Brief Description]

Status: Investigating / Mitigating / Resolved
Impact: [Description of user impact]
Started: HH:MM UTC
Duration: Xm (ongoing)

Current Actions:
- [Action being taken]

Next Update: HH:MM UTC

Incident Lead: [Name]
Thread: [Link]
```

### Status Page Update

```
[Title]: Consoul API [Investigating/Identified/Monitoring/Resolved]

[Body]:
We are currently investigating reports of [issue description].

Affected services: Consoul API
Impact: [Describe user-facing impact]

We will provide updates as we learn more.
```

### Customer Communication

```
Subject: Service Incident - [Date]

Dear Customer,

We are writing to inform you of a service incident that occurred on [date] from [time] to [time] UTC.

What happened:
[Brief, non-technical description of the incident]

Impact:
[Description of how customers were affected]

Resolution:
[What we did to fix it]

Prevention:
[What we're doing to prevent recurrence]

We apologize for any inconvenience this may have caused. If you have any questions, please contact support@example.com.

Sincerely,
[Team Name]
```

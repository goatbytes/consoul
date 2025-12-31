# Consoul Operations Documentation

Production operations guides for deploying and operating Consoul in enterprise environments.

## Quick Reference

| Task | Document | Command |
|------|----------|---------|
| Check service health | [Runbook](./runbook.md#health-monitoring) | `curl http://HOST/health` |
| Pre-deployment review | [Security Checklist](./security-checklist.md#pre-deployment) | - |
| Handle an incident | [Incident Response](./incident-response.md) | - |
| Scale infrastructure | [Scaling Guide](./scaling-guide.md) | - |
| Compliance audit | [Compliance](./compliance.md) | - |

## Documents

### [Runbook](./runbook.md)
Daily operations procedures, monitoring setup, Prometheus metrics, alert configuration, and troubleshooting guides.

### [Security Checklist](./security-checklist.md)
Pre-deployment, weekly, and monthly security verification procedures. Covers API authentication, rate limiting, CORS, tool filtering, and secrets management.

### [Incident Response](./incident-response.md)
Severity levels, detection methods, triage procedures, resolution playbooks, and post-mortem template.

### [Scaling Guide](./scaling-guide.md)
Horizontal and vertical scaling procedures, cloud-specific configuration (GCP, AWS, Azure), capacity planning, and zero-downtime deployments.

### [Compliance](./compliance.md)
SOC2 control mapping, audit logging features, data handling policies, and security controls documentation.

### [Multi-Tenancy](../deployment/multi-tenancy.md)
Session namespace isolation, per-tenant rate limiting, deployment patterns, and security boundaries for multi-tenant deployments.

## Audience

This documentation is intended for:
- **Platform Engineers**: Infrastructure provisioning and scaling
- **Site Reliability Engineers**: Monitoring, alerting, incident response
- **Security Teams**: Compliance verification, security reviews
- **DevOps Engineers**: Deployment automation, configuration management

## Prerequisites

Before operating Consoul in production, ensure you have:

1. **Access to infrastructure**
   - Cloud provider console (GCP, AWS, or Azure)
   - Kubernetes cluster or container orchestrator
   - Redis instance for sessions and rate limiting

2. **Monitoring stack**
   - Prometheus for metrics scraping
   - Grafana or equivalent for dashboards
   - Alertmanager for notifications

3. **Credentials**
   - API keys for Consoul authentication
   - Cloud secrets manager access
   - LLM provider API keys (Anthropic, OpenAI)

## Environment Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Environment                        │
│                                                                  │
│  ┌──────────┐    ┌───────────────┐    ┌─────────────────────┐   │
│  │  Client  │───▶│  Load Balancer │───▶│   Consoul API       │   │
│  │ (HTTPS)  │    │   (HTTPS/TLS) │    │   (Port 8000)       │   │
│  └──────────┘    └───────────────┘    └─────────────────────┘   │
│                                               │                  │
│                         ┌─────────────────────┼─────────────┐    │
│                         │                     │             │    │
│                         ▼                     ▼             ▼    │
│                  ┌───────────┐         ┌───────────┐  ┌────────┐│
│                  │   Redis   │         │ Prometheus│  │  LLM   ││
│                  │ (Sessions)│         │ (Metrics) │  │Provider││
│                  └───────────┘         └───────────┘  └────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Endpoints

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `GET /health` | Liveness probe | No |
| `GET /ready` | Readiness probe (checks Redis) | No |
| `POST /chat` | HTTP chat endpoint | Yes |
| `WS /ws/chat/{session_id}` | WebSocket streaming | Yes |
| `GET :9090/metrics` | Prometheus metrics | No (separate port) |

## Emergency Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | _[Configure]_ | PagerDuty/Opsgenie |
| Security Team | _[Configure]_ | Slack #security |
| Platform Team | _[Configure]_ | Slack #platform |

---

**Last Updated**: December 2025
**Version**: 1.0

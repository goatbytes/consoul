# Consoul Cloud Deployment

Deploy Consoul API to GCP, AWS, or Azure in under 30 minutes using Terraform.

## Quick Start

Choose your cloud provider:

| Cloud | Deploy Time | Monthly Cost | Scale to Zero |
|-------|-------------|--------------|---------------|
| [GCP Cloud Run](./gcp/) | ~15 min | $40-90 | Yes |
| [AWS ECS Fargate](./aws/) | ~25 min | $85-110 | No |
| [Azure Container Apps](./azure/) | ~20 min | $30-80 | Yes |

### One-Command Deployment

```bash
# GCP
cd gcp && chmod +x quickstart.sh && ./quickstart.sh

# AWS
cd aws && chmod +x quickstart.sh && ./quickstart.sh

# Azure
cd azure && chmod +x quickstart.sh && ./quickstart.sh
```

## Prerequisites

- **Terraform** >= 1.5 ([install](https://terraform.io/downloads))
- **Docker** ([install](https://docs.docker.com/get-docker/))
- Cloud CLI:
  - GCP: [gcloud](https://cloud.google.com/sdk/docs/install)
  - AWS: [aws](https://aws.amazon.com/cli/)
  - Azure: [az](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)

## Architecture

All deployments include:

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Provider                           │
│                                                              │
│  ┌──────────┐    ┌───────────────┐    ┌─────────────────┐   │
│  │  Client  │───▶│   Container   │───▶│  Managed Redis  │   │
│  │ (HTTPS)  │    │   Service     │    │                 │   │
│  └──────────┘    └───────────────┘    └─────────────────┘   │
│                         │                                    │
│                  ┌──────┴──────┐                            │
│                  │   Secrets   │                            │
│                  │   Manager   │                            │
│                  └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Component | GCP | AWS | Azure |
|-----------|-----|-----|-------|
| Container | Cloud Run | ECS Fargate | Container Apps |
| Redis | Memorystore | ElastiCache | Azure Cache |
| Secrets | Secret Manager | Secrets Manager | Key Vault |
| Registry | GCR | ECR | ACR |
| Load Balancer | Managed | ALB | Managed |

## Cost Comparison

### Minimal Setup (Development/Testing)

| Resource | GCP | AWS | Azure |
|----------|-----|-----|-------|
| Container Service | $0-20 | $15-30 | $0-20 |
| Redis (Basic) | $35 | $15 | $17 |
| Load Balancer | Included | $20 | Included |
| Networking | $5 | $35 (NAT) | $5 |
| Registry | Free | Free | $5 |
| **Total** | **$40-60** | **$85-100** | **$27-47** |

### Production Setup (High Availability)

| Resource | GCP | AWS | Azure |
|----------|-----|-----|-------|
| Container (2+ instances) | $50-100 | $60-120 | $50-100 |
| Redis (HA) | $70 | $50 | $50 |
| Load Balancer | Included | $20 | Included |
| Networking | $20 | $70 | $20 |
| **Total** | **$140-190** | **$200-260** | **$120-170** |

*Costs are estimates and vary by region, usage, and configuration.*

## Configuration

### Environment Variables

All deployments configure these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection | Auto-configured |
| `CONSOUL_API_KEYS` | API authentication | From secrets |
| `CONSOUL_CORS_ORIGINS` | CORS origins | `*` |
| `CONSOUL_DEFAULT_LIMITS` | Rate limits | `30/minute;500/hour` |
| `CONSOUL_SESSION_TTL` | Session TTL | `3600` |
| `CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED` | Metrics | `true` |

### Optional LLM API Keys

Add these to your `terraform.tfvars`:

```hcl
openai_api_key    = "sk-..."
anthropic_api_key = "sk-ant-..."
google_api_key    = "AIza..."
```

## Scaling

### Auto-Scaling Comparison

| Feature | GCP | AWS | Azure |
|---------|-----|-----|-------|
| Scale to Zero | Yes | No | Yes |
| Min Instances | 0 | 1 | 0 |
| Max Instances | 1000 | 10 (configurable) | 300 |
| Scaling Metric | Requests/CPU | CPU | HTTP Requests |
| Cold Start | ~2-5s | N/A | ~3-8s |

### Recommended Settings

**Development:**
- Min: 0, Max: 2
- Scale to zero enabled

**Production:**
- Min: 2, Max: 10
- No scale to zero (faster response)

## Health Checks

All deployments include:

```bash
# Liveness probe (container is running)
GET /health

# Readiness probe (dependencies ready)
GET /ready
```

Configure your orchestrator/load balancer to use these endpoints.

## Security

### Default Security Features

- API key authentication required
- HTTPS enforced (automatic certificates)
- Redis in private subnet/VPC
- Secrets in cloud secrets manager
- Non-root container user

### Production Recommendations

1. **CORS**: Set specific origins (not `*`)
2. **API Keys**: Use strong, unique keys
3. **Rate Limits**: Tune for your use case
4. **Network**: Use VPC/private networking
5. **Monitoring**: Enable logging and alerting

## Monitoring

### Prometheus Metrics

Consoul exposes metrics on port 9090:

- `consoul_request_total` - Request count
- `consoul_request_latency_seconds` - Latency
- `consoul_token_usage_total` - Token usage
- `consoul_errors_total` - Error count

### Cloud-Native Monitoring

| Feature | GCP | AWS | Azure |
|---------|-----|-----|-------|
| Logs | Cloud Logging | CloudWatch | Log Analytics |
| Metrics | Cloud Monitoring | CloudWatch | Azure Monitor |
| Tracing | Cloud Trace | X-Ray | App Insights |

## Cleanup

Each provider has cleanup instructions:

```bash
# From the provider directory
terraform destroy
```

**Warning:** This deletes all resources including Redis data.

## Troubleshooting

### Common Issues

**Container not starting:**
- Check logs in cloud console
- Verify Docker image was pushed
- Check health endpoint returns 200

**Redis connection failed:**
- Verify VPC/network configuration
- Check security groups/firewall
- Ensure Redis is running

**API key rejected:**
- Verify secret was created
- Check environment variable injection
- Test with: `curl -H 'X-API-Key: YOUR_KEY' URL/health`

### Getting Help

1. Check provider-specific README in each directory
2. Review Terraform output for errors
3. Check cloud provider logs
4. Open an issue on GitHub

## Directory Structure

```
deployment/cloud/
├── README.md                 # This file
├── shared/
│   ├── Dockerfile           # Multi-stage production build
│   └── entrypoint.sh        # Container entrypoint
├── gcp/
│   ├── main.tf              # Cloud Run + Memorystore
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── quickstart.sh
│   └── README.md
├── aws/
│   ├── main.tf              # ECS Fargate + ElastiCache
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── quickstart.sh
│   └── README.md
└── azure/
    ├── main.tf              # Container Apps + Azure Cache
    ├── variables.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    ├── quickstart.sh
    └── README.md
```

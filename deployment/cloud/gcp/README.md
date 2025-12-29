# Consoul GCP Deployment

Deploy Consoul API to Google Cloud Platform using Cloud Run and Memorystore Redis.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Google Cloud                          │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │   Client    │───▶│  Cloud Run   │───▶│ Memorystore│  │
│  │  (HTTPS)    │    │  (Consoul)   │    │   Redis    │  │
│  └─────────────┘    └──────────────┘    └────────────┘  │
│                            │                             │
│                     ┌──────┴──────┐                     │
│                     │   Secret    │                     │
│                     │   Manager   │                     │
│                     └─────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [Terraform >= 1.5](https://terraform.io/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- GCP Project with billing enabled

## Quick Start

### Option 1: Automated Deployment

```bash
chmod +x quickstart.sh
./quickstart.sh
```

### Option 2: Manual Deployment

1. **Authenticate with GCP:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Build and push Docker image:**
   ```bash
   # From project root
   gcloud auth configure-docker gcr.io
   docker build -f deployment/cloud/shared/Dockerfile -t gcr.io/YOUR_PROJECT/consoul-api:latest .
   docker push gcr.io/YOUR_PROJECT/consoul-api:latest
   ```

3. **Configure Terraform:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

4. **Deploy:**
   ```bash
   terraform init
   terraform apply
   ```

5. **Test:**
   ```bash
   curl -H "X-API-Key: YOUR_API_KEY" $(terraform output -raw service_url)/health
   ```

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `project_id` | GCP Project ID |
| `region` | Deployment region (default: us-central1) |
| `api_keys` | List of API keys for authentication |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `min_instances` | 0 | Minimum instances (0 = scale to zero) |
| `max_instances` | 10 | Maximum instances |
| `cpu` | 1 | CPU per instance |
| `memory` | 512Mi | Memory per instance |
| `redis_tier` | BASIC | Redis tier (BASIC or STANDARD_HA) |
| `redis_memory_gb` | 1 | Redis memory in GB |
| `cors_origins` | * | CORS allowed origins |
| `rate_limits` | 30/minute;500/hour | Rate limiting |

### LLM API Keys (Optional)

```hcl
openai_api_key    = "sk-..."
anthropic_api_key = "sk-ant-..."
google_api_key    = "AIza..."
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| Cloud Run (scale to zero) | $0-50 |
| Memorystore Basic 1GB | ~$35 |
| VPC Connector | ~$7 |
| Networking | ~$5 |
| **Total** | **~$47-97** |

*Costs vary based on usage. Cloud Run charges per request and compute time.*

## Scaling

Cloud Run auto-scales based on:
- CPU utilization (target: 80%)
- Concurrent requests (default: 80 per instance)
- Min/max instance limits

### Scale to Zero

Set `min_instances = 0` for cost savings. First request after idle has ~2-5s cold start.

### High Availability

For production, consider:
- `min_instances = 1` (eliminates cold starts)
- `redis_tier = "STANDARD_HA"` (Redis high availability)
- Multiple regions with Cloud Load Balancing

## Monitoring

### Cloud Run Metrics

- Request count and latency
- Instance count
- Memory utilization
- Error rates

Access via: GCP Console → Cloud Run → Service → Metrics

### Prometheus Metrics

Consoul exposes Prometheus metrics on port 9090. Configure Cloud Monitoring for scraping.

### Health Endpoints

```bash
# Liveness (always available)
curl $SERVICE_URL/health

# Readiness (checks Redis)
curl $SERVICE_URL/ready
```

## Troubleshooting

### Service Not Starting

Check Cloud Run logs:
```bash
gcloud run services logs read consoul-api-prod --region=us-central1
```

### Redis Connection Issues

Verify VPC connector:
```bash
gcloud compute networks vpc-access connectors describe consoul-api-connector \
  --region=us-central1
```

### Permission Denied

Ensure service account has secret access:
```bash
gcloud secrets get-iam-policy consoul-api-prod-api-keys
```

### Cold Start Latency

If cold starts are too slow:
1. Set `min_instances = 1`
2. Reduce container image size
3. Optimize startup code

## Cleanup

```bash
terraform destroy
```

This removes:
- Cloud Run service
- Memorystore Redis instance
- VPC connector and network
- Secret Manager secrets

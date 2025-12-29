# Consoul Azure Deployment

Deploy Consoul API to Microsoft Azure using Container Apps and Azure Cache for Redis.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Microsoft Azure                            │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐   │
│  │   Client    │───▶│  Container   │───▶│   Azure Cache      │   │
│  │  (HTTPS)    │    │    Apps      │    │   for Redis        │   │
│  └─────────────┘    └──────────────┘    └────────────────────┘   │
│                            │                                      │
│                     ┌──────┴──────┐                              │
│                     │  Key Vault  │                              │
│                     └─────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform >= 1.5](https://terraform.io/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- Azure Subscription with permissions for Container Apps, ACR, Redis Cache, Key Vault

## Quick Start

### Option 1: Automated Deployment

```bash
chmod +x quickstart.sh
./quickstart.sh
```

### Option 2: Manual Deployment

1. **Login to Azure:**
   ```bash
   az login
   az account set --subscription "Your Subscription Name"
   ```

2. **Configure Terraform:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Deploy infrastructure:**
   ```bash
   terraform init
   terraform apply
   ```

4. **Build and push Docker image:**
   ```bash
   # Login to ACR
   az acr login --name $(terraform output -raw acr_login_server | cut -d. -f1)

   # Build and push (from project root)
   docker build -f deployment/cloud/shared/Dockerfile \
       -t $(terraform output -raw acr_login_server)/consoul-api:latest .
   docker push $(terraform output -raw acr_login_server)/consoul-api:latest
   ```

5. **Re-apply to update container:**
   ```bash
   terraform apply
   ```

6. **Test:**
   ```bash
   curl -H "X-API-Key: YOUR_API_KEY" $(terraform output -raw service_url)/health
   ```

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `location` | Azure region (default: eastus) |
| `api_keys` | List of API keys for authentication |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cpu` | 0.5 | CPU cores per container |
| `memory` | 1Gi | Memory per container |
| `min_replicas` | 0 | Min replicas (0 = scale to zero) |
| `max_replicas` | 10 | Max replicas |
| `redis_sku` | Basic | Redis SKU (Basic, Standard, Premium) |
| `redis_capacity` | 0 | Redis capacity (0-6) |
| `cors_origins` | * | CORS allowed origins |
| `rate_limits` | 30/minute;500/hour | Rate limiting |

### LLM API Keys (Optional)

```hcl
openai_api_key    = "sk-..."
anthropic_api_key = "sk-ant-..."
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| Container Apps (scale to zero) | $0-50 |
| Azure Cache Basic C0 (250MB) | ~$17 |
| Container Registry Basic | ~$5 |
| Log Analytics | ~$5 |
| **Total** | **~$27-77** |

*Costs vary based on usage. Container Apps charges per vCPU-second and memory.*

## Scaling

### Auto-Scaling Configuration

Container Apps auto-scales based on HTTP requests:
- Scale out when concurrent requests > 80 per replica
- Scale to zero when no traffic (if `min_replicas = 0`)
- Max 10 replicas (configurable)

### Manual Scaling

```bash
# Update min/max replicas
az containerapp update \
    --name consoul-api-prod \
    --resource-group consoul-api-prod-rg \
    --min-replicas 2 \
    --max-replicas 20
```

### High Availability

For production HA:
1. Set `min_replicas = 2`
2. Use `redis_sku = "Standard"` or `"Premium"` for replication
3. Consider zone redundancy (Premium Redis)

## Monitoring

### Container App Logs

```bash
# Stream logs
az containerapp logs show \
    --name consoul-api-prod \
    --resource-group consoul-api-prod-rg \
    --follow

# Query logs in Log Analytics
az monitor log-analytics query \
    --workspace $(terraform output -raw log_analytics_workspace) \
    --analytics-query "ContainerAppConsoleLogs | take 100"
```

### Azure Monitor Metrics

Key metrics available in Azure Portal:
- Request count
- Response time
- Replica count
- CPU/Memory percentage

### Application Insights (Optional)

For enhanced monitoring, add Application Insights instrumentation.

### Health Endpoints

```bash
# Liveness (always available)
curl https://CONTAINER_APP_URL/health

# Readiness (checks Redis)
curl https://CONTAINER_APP_URL/ready
```

## HTTPS

Container Apps provides automatic HTTPS with a managed certificate. The service URL is always HTTPS.

For custom domain:
1. Add custom domain in Azure Portal
2. Configure managed certificate or bring your own

## Troubleshooting

### Container Not Starting

Check revision status:
```bash
az containerapp revision list \
    --name consoul-api-prod \
    --resource-group consoul-api-prod-rg \
    --output table
```

View logs:
```bash
az containerapp logs show \
    --name consoul-api-prod \
    --resource-group consoul-api-prod-rg
```

### Redis Connection Issues

Verify Redis is running:
```bash
az redis show \
    --name consoulapiprodredis \
    --resource-group consoul-api-prod-rg \
    --query provisioningState
```

Common issues:
- SSL required (Azure Redis requires SSL by default)
- Firewall rules (Container Apps should have access)

### Image Pull Failures

Ensure ACR credentials are correct:
```bash
az acr login --name $(terraform output -raw acr_login_server | cut -d. -f1)
docker push $IMAGE_URL
```

### Slow Cold Starts

Optimize by:
1. Set `min_replicas = 1`
2. Reduce Docker image size
3. Optimize application startup

## Cleanup

```bash
terraform destroy
```

This removes:
- Container App and Environment
- Azure Container Registry
- Azure Cache for Redis
- Key Vault (soft-deleted)
- Resource Group

**Note:** Key Vault enters soft-delete for 7 days. To permanently delete:
```bash
az keyvault purge --name $(terraform output -raw key_vault_name)
```

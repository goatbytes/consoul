# Consoul Scaling Guide

Procedures for scaling Consoul horizontally and vertically across cloud providers.

## Table of Contents

- [Scaling Overview](#scaling-overview)
- [Prerequisites for Scaling](#prerequisites-for-scaling)
- [Horizontal Scaling](#horizontal-scaling)
- [Vertical Scaling](#vertical-scaling)
- [Cloud-Specific Scaling](#cloud-specific-scaling)
- [Capacity Planning](#capacity-planning)
- [Zero-Downtime Deployments](#zero-downtime-deployments)

---

## Scaling Overview

### Architecture for Scale

```
┌─────────────────────────────────────────────────────────────────┐
│                   Scaled Production Setup                       │
│                                                                  │
│  ┌──────────┐    ┌───────────────┐    ┌─────────────────────┐   │
│  │  Client  │───▶│ Load Balancer │───▶│   Consoul API       │   │
│  │ (HTTPS)  │    │               │    │   Instance 1        │   │
│  └──────────┘    │               │───▶│   Instance 2        │   │
│                  │               │    │   Instance 3        │   │
│                  │               │───▶│   Instance N        │   │
│                  └───────────────┘    └─────────────────────┘   │
│                                               │                  │
│                         ┌─────────────────────┴─────────────┐    │
│                         │        Shared State (Redis)       │    │
│                         │                                   │    │
│                         │  ┌───────────┐   ┌───────────┐   │    │
│                         │  │  Sessions │   │Rate Limits│   │    │
│                         │  └───────────┘   └───────────┘   │    │
│                         └───────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Scaling Dimensions

| Dimension | Horizontal | Vertical |
|-----------|------------|----------|
| Method | Add more instances | Increase CPU/memory per instance |
| Benefit | Higher throughput, redundancy | Lower latency, simpler |
| Requirement | Redis for shared state | Larger instance types |
| Cost | Linear with instances | Diminishing returns |
| Complexity | Higher (distributed state) | Lower |

---

## Prerequisites for Scaling

### Required: Redis for Shared State

Horizontal scaling requires Redis for:
1. **Session storage** - Sessions accessible from any instance
2. **Rate limiting** - Limits enforced across all instances

**Configuration**:
```bash
# Both should point to the same or clustered Redis
CONSOUL_SESSION_REDIS_URL=redis://redis-cluster:6379/1
CONSOUL_RATE_LIMIT_REDIS_URL=redis://redis-cluster:6379/0
```

### Why Redis is Required

Without Redis, each instance:
- Maintains its own sessions (session lost on routing change)
- Enforces its own rate limits (limits multiplied by instance count)

```
❌ Without Redis (DON'T DO THIS):
Instance 1: 30 req/min limit  ─┐
Instance 2: 30 req/min limit  ─┼─▶ User gets 90 req/min (3 × 30)
Instance 3: 30 req/min limit  ─┘

✅ With Redis:
Instance 1 ─┐
Instance 2 ─┼─▶ Shared rate limit ─▶ User gets 30 req/min
Instance 3 ─┘
```

---

## Horizontal Scaling

### Adding Instances

**Kubernetes**:
```bash
# Scale to 5 replicas
kubectl scale deployment/consoul-api --replicas=5 -n production

# Verify
kubectl get pods -n production -l app=consoul-api
```

**Docker Swarm**:
```bash
docker service scale consoul-api=5
```

**Manual/VMs**:
1. Deploy new instance with same configuration
2. Add to load balancer target group
3. Wait for health checks to pass

### Auto-Scaling Configuration

**Kubernetes HPA**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: consoul-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: consoul-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Load Balancer Health Checks

Configure health checks to use the `/health` endpoint:

```yaml
# Target Group Health Check (AWS ALB)
HealthCheckPath: /health
HealthCheckPort: 8000
HealthCheckProtocol: HTTP
HealthyThresholdCount: 2
UnhealthyThresholdCount: 3
HealthCheckIntervalSeconds: 30
HealthCheckTimeoutSeconds: 10
```

### Session Affinity

**Not required** when using Redis for sessions. Any instance can serve any request.

If you must use session affinity (not recommended):
```yaml
# Kubernetes Service
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600
```

---

## Vertical Scaling

### Sizing Recommendations

| Workload | vCPU | Memory | Workers | Concurrent Sessions |
|----------|------|--------|---------|---------------------|
| Development | 0.5 | 1 GB | 1 | 10 |
| Small | 1 | 2 GB | 2 | 50 |
| Medium | 2 | 4 GB | 4 | 200 |
| Large | 4 | 8 GB | 8 | 500 |
| Enterprise | 8+ | 16 GB+ | 16 | 1000+ |

### Worker Configuration

General guideline: **2-4 workers per CPU core**

```bash
# Uvicorn with 4 workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# Or use Gunicorn for process management
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Uvicorn Production Settings

```bash
uvicorn app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop \
  --http httptools \
  --lifespan on \
  --timeout-keep-alive 30 \
  --graceful-timeout 60
```

### Container Resource Limits

**Kubernetes**:
```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

**Docker**:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

---

## Cloud-Specific Scaling

### GCP Cloud Run

**Auto-Scaling Configuration**:
```hcl
# Terraform
resource "google_cloud_run_v2_service" "consoul" {
  template {
    scaling {
      min_instance_count = 0   # Scale to zero
      max_instance_count = 10
    }

    containers {
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
    }

    max_instance_request_concurrency = 80
  }
}
```

**Manual Scaling**:
```bash
gcloud run services update consoul-api \
  --region us-central1 \
  --min-instances 2 \
  --max-instances 20 \
  --concurrency 80 \
  --cpu 2 \
  --memory 4Gi
```

**Scaling Behavior**:
- Scale-to-zero: Yes (cost savings when idle)
- Scale trigger: Concurrent requests
- Cold start: ~2-5 seconds

### AWS ECS Fargate

**Auto-Scaling Configuration**:
```hcl
# Terraform
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

**Manual Scaling**:
```bash
aws ecs update-service \
  --cluster consoul \
  --service consoul-api \
  --desired-count 5

# Update task definition for vertical scaling
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json
```

**Scaling Behavior**:
- Scale-to-zero: No (minimum 1 task always running)
- Scale trigger: CPU utilization
- Scale response: 60-120 seconds

### Azure Container Apps

**Auto-Scaling Configuration**:
```hcl
# Terraform
resource "azurerm_container_app" "consoul" {
  template {
    min_replicas = 0   # Scale to zero
    max_replicas = 10

    container {
      cpu    = 2.0
      memory = "4Gi"
    }
  }

  ingress {
    target_port = 8000
  }
}

# Scale rule based on HTTP requests
resource "azurerm_container_app_scale_rule" "http" {
  name             = "http-scaling"
  container_app_id = azurerm_container_app.consoul.id

  custom {
    type = "http"
    metadata = {
      concurrentRequests = "80"
    }
  }
}
```

**Manual Scaling**:
```bash
az containerapp update \
  --name consoul-api \
  --resource-group consoul-rg \
  --min-replicas 2 \
  --max-replicas 20 \
  --cpu 2.0 \
  --memory 4Gi
```

**Scaling Behavior**:
- Scale-to-zero: Yes
- Scale trigger: HTTP concurrent requests
- Cold start: ~3-8 seconds

---

## Capacity Planning

### Request Rate Estimation

```
Daily Active Users × Requests per User per Day
─────────────────────────────────────────────── = Peak Requests per Second
              Peak Hours × 3600
```

**Example**:
- 10,000 daily active users
- 50 requests per user per day
- Peak hours: 8 hours
- Safety factor: 2x

```
(10,000 × 50) × 2
───────────────── = ~35 requests per second
    8 × 3600
```

### Instance Sizing

| Requests/sec | Instances (Medium) | Instances (Large) |
|--------------|--------------------|--------------------|
| 10 | 1 | 1 |
| 50 | 2-3 | 1-2 |
| 100 | 4-5 | 2-3 |
| 500 | 15-20 | 8-10 |
| 1000 | 30-40 | 15-20 |

### Redis Sizing

**Memory Estimation**:
```
Session Size × Max Concurrent Sessions × Safety Factor = Redis Memory

Example:
10 KB × 10,000 sessions × 2 = 200 MB
```

**Recommended Redis Sizes**:

| Concurrent Sessions | Redis Size |
|---------------------|------------|
| < 1,000 | 250 MB (Basic) |
| 1,000 - 10,000 | 1 GB |
| 10,000 - 100,000 | 6 GB |
| > 100,000 | 26 GB+ (Cluster) |

### Token Usage Planning

Estimate monthly token usage:
```
Users × Messages per Day × Avg Tokens per Message × 30 days

Example:
1,000 users × 20 messages × 500 tokens × 30 = 300M tokens/month
```

---

## Zero-Downtime Deployments

### Rolling Update Strategy

**Kubernetes**:
```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%        # Allow 25% extra pods during update
      maxUnavailable: 0    # Never reduce below desired count
```

**ECS**:
```hcl
deployment_configuration {
  maximum_percent         = 200  # Allow double capacity during update
  minimum_healthy_percent = 100  # Never go below current capacity
}
```

### Health Check Requirements

Ensure health checks are configured for:
1. **Load balancer** - Routes traffic only to healthy instances
2. **Container orchestrator** - Manages pod/task lifecycle
3. **Readiness probe** - Gates traffic until dependencies ready

**Kubernetes Example**:
```yaml
spec:
  containers:
    - name: consoul-api
      livenessProbe:
        httpGet:
          path: /health
          port: 8000
        initialDelaySeconds: 10
        periodSeconds: 30
        failureThreshold: 3

      readinessProbe:
        httpGet:
          path: /ready
          port: 8000
        initialDelaySeconds: 5
        periodSeconds: 10
        failureThreshold: 3

      # Graceful shutdown
      lifecycle:
        preStop:
          exec:
            command: ["/bin/sh", "-c", "sleep 10"]
```

### Graceful Shutdown

Consoul handles graceful shutdown via FastAPI lifespan:

1. Stop accepting new connections
2. Finish processing in-flight requests
3. Close Redis connections
4. Exit cleanly

**Uvicorn Configuration**:
```bash
--graceful-timeout 60  # Wait up to 60s for in-flight requests
```

### Blue-Green Deployments

For major changes, use blue-green deployment:

1. Deploy new version alongside current (green)
2. Run smoke tests against new version
3. Switch load balancer to new version
4. Monitor for issues
5. Keep old version for quick rollback
6. Terminate old version after validation

```bash
# AWS ALB example
aws elbv2 modify-listener \
  --listener-arn LISTENER_ARN \
  --default-actions Type=forward,TargetGroupArn=NEW_TARGET_GROUP_ARN
```

### Rollback Procedure

**Kubernetes**:
```bash
# View rollout history
kubectl rollout history deployment/consoul-api -n production

# Rollback to previous version
kubectl rollout undo deployment/consoul-api -n production

# Rollback to specific revision
kubectl rollout undo deployment/consoul-api -n production --to-revision=3
```

**ECS**:
```bash
# Update to previous task definition
aws ecs update-service \
  --cluster consoul \
  --service consoul-api \
  --task-definition consoul-api:PREVIOUS_REVISION
```

---

## Monitoring During Scaling

### Key Metrics to Watch

During scaling events, monitor:

```promql
# Request rate per instance
sum(rate(consoul_request_total[1m])) by (instance)

# Error rate during scaling
sum(rate(consoul_errors_total[1m])) / sum(rate(consoul_request_total[1m]))

# Latency changes
histogram_quantile(0.95, sum(rate(consoul_request_latency_seconds_bucket[1m])) by (le))

# Active sessions distribution
consoul_active_sessions
```

### Scaling Event Checklist

- [ ] Monitor error rate during scale-out
- [ ] Verify new instances pass health checks
- [ ] Check request distribution across instances
- [ ] Monitor Redis connection count
- [ ] Verify rate limiting works correctly
- [ ] Check session continuity (no dropped sessions)

# Consoul AWS Deployment

Deploy Consoul API to Amazon Web Services using ECS Fargate and ElastiCache Redis.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Amazon Web Services                        │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐   │
│  │   Client    │───▶│     ALB      │───▶│   ECS Fargate      │   │
│  │  (HTTPS)    │    │              │    │   (Consoul)        │   │
│  └─────────────┘    └──────────────┘    └─────────┬──────────┘   │
│                                                    │              │
│                     ┌──────────────┐    ┌─────────▼──────────┐   │
│                     │   Secrets    │    │    ElastiCache     │   │
│                     │   Manager    │    │      Redis         │   │
│                     └──────────────┘    └────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- [AWS CLI v2](https://aws.amazon.com/cli/)
- [Terraform >= 1.5](https://terraform.io/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- AWS Account with permissions for ECS, ECR, ElastiCache, VPC, Secrets Manager

## Quick Start

### Option 1: Automated Deployment

```bash
chmod +x quickstart.sh
./quickstart.sh
```

### Option 2: Manual Deployment

1. **Configure AWS CLI:**
   ```bash
   aws configure
   # Or use environment variables:
   # export AWS_ACCESS_KEY_ID=...
   # export AWS_SECRET_ACCESS_KEY=...
   # export AWS_REGION=us-east-1
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
   # Get ECR login
   aws ecr get-login-password --region us-east-1 | \
       docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

   # Build and push (from project root)
   docker build -f deployment/cloud/shared/Dockerfile \
       -t $(terraform output -raw ecr_repository_url):latest .
   docker push $(terraform output -raw ecr_repository_url):latest
   ```

5. **Update ECS service:**
   ```bash
   aws ecs update-service \
       --cluster $(terraform output -raw ecs_cluster_name) \
       --service $(terraform output -raw ecs_service_name) \
       --force-new-deployment
   ```

6. **Test:**
   ```bash
   curl -H "X-API-Key: YOUR_API_KEY" $(terraform output -raw service_url)/health
   ```

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `aws_region` | AWS region (default: us-east-1) |
| `api_keys` | List of API keys for authentication |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cpu` | 512 | Fargate CPU units |
| `memory` | 1024 | Fargate memory (MB) |
| `min_capacity` | 1 | Min tasks for auto-scaling |
| `max_capacity` | 10 | Max tasks for auto-scaling |
| `cpu_target` | 70 | CPU % target for scaling |
| `redis_node_type` | cache.t3.micro | ElastiCache instance type |
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
| ECS Fargate (0.5 vCPU, 1GB) | ~$15-30 |
| Application Load Balancer | ~$20 |
| ElastiCache cache.t3.micro | ~$15 |
| NAT Gateway | ~$35 |
| Data Transfer | ~$5-10 |
| **Total** | **~$90-110** |

*Costs vary based on usage and region.*

## Scaling

### Auto-Scaling Configuration

ECS auto-scales based on CPU utilization:
- Scale out when CPU > 70% (configurable)
- Scale in after 5 minutes below threshold
- Min 1, Max 10 tasks (configurable)

### Manual Scaling

```bash
# Scale to specific count
aws ecs update-service \
    --cluster consoul-api-prod \
    --service consoul-api-prod \
    --desired-count 3
```

### High Availability

For production HA:
1. Deploy across multiple AZs (default)
2. Increase `min_capacity` to 2+
3. Use `cache.r6g.large` for Redis
4. Consider RDS for persistent storage

## Monitoring

### CloudWatch Logs

```bash
# Tail logs
aws logs tail /ecs/consoul-api-prod --follow

# Search logs
aws logs filter-log-events \
    --log-group-name /ecs/consoul-api-prod \
    --filter-pattern "ERROR"
```

### CloudWatch Metrics

Key metrics to monitor:
- `ECS/CPUUtilization` - Container CPU usage
- `ECS/MemoryUtilization` - Container memory usage
- `ApplicationELB/RequestCount` - Request throughput
- `ApplicationELB/TargetResponseTime` - Latency

### Container Insights

Container Insights is enabled by default. View in CloudWatch:
- Container-level CPU/memory
- Network I/O
- Storage I/O

### Health Endpoints

```bash
# Liveness (always available)
curl http://ALB_DNS/health

# Readiness (checks Redis)
curl http://ALB_DNS/ready
```

## HTTPS Setup

The default deployment uses HTTP. For HTTPS:

1. **Request ACM Certificate:**
   ```bash
   aws acm request-certificate \
       --domain-name api.example.com \
       --validation-method DNS
   ```

2. **Add HTTPS listener to ALB** (modify main.tf):
   ```hcl
   resource "aws_lb_listener" "https" {
     load_balancer_arn = aws_lb.main.arn
     port              = "443"
     protocol          = "HTTPS"
     ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
     certificate_arn   = "arn:aws:acm:..."

     default_action {
       type             = "forward"
       target_group_arn = aws_lb_target_group.main.arn
     }
   }
   ```

3. **Configure Route 53** (optional):
   ```bash
   # Create A record pointing to ALB
   ```

## Troubleshooting

### Service Not Starting

Check ECS task status:
```bash
aws ecs describe-tasks \
    --cluster consoul-api-prod \
    --tasks $(aws ecs list-tasks --cluster consoul-api-prod --query 'taskArns[0]' --output text)
```

### Container Failing Health Check

Check logs:
```bash
aws logs tail /ecs/consoul-api-prod --since 10m
```

Common issues:
- Redis connection timeout (check security groups)
- Missing environment variables
- Insufficient memory

### Redis Connection Issues

Verify security group allows traffic:
```bash
aws ec2 describe-security-groups \
    --group-ids $(terraform output -raw redis_security_group_id) \
    --query 'SecurityGroups[0].IpPermissions'
```

### Slow Cold Starts

Optimize by:
1. Reduce Docker image size
2. Increase `min_capacity` to 1+
3. Use provisioned concurrency (Lambda) or warm pools

## Cleanup

```bash
terraform destroy
```

This removes:
- ECS cluster and service
- ALB and target group
- ElastiCache cluster
- VPC and networking
- ECR repository
- Secrets Manager secrets
- CloudWatch log group

**Note:** ECR images are not automatically deleted. Clean up manually:
```bash
aws ecr delete-repository --repository-name consoul-api --force
```

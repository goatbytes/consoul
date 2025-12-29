# AWS Deployment Outputs

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "service_url" {
  description = "Service URL (HTTP)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.main.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.main.name
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "health_check_command" {
  description = "Command to test the health endpoint"
  value       = "curl http://${aws_lb.main.dns_name}/health"
}

output "test_command" {
  description = "Command to test the API (replace YOUR_API_KEY)"
  value       = "curl -H 'X-API-Key: YOUR_API_KEY' http://${aws_lb.main.dns_name}/health"
}

output "docker_push_commands" {
  description = "Commands to build and push Docker image"
  value       = <<-EOT
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.main.repository_url}
    docker build -f deployment/cloud/shared/Dockerfile -t ${aws_ecr_repository.main.repository_url}:latest .
    docker push ${aws_ecr_repository.main.repository_url}:latest
  EOT
}

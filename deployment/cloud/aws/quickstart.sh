#!/bin/bash
# Consoul AWS Deployment - Quick Start
# Deploys ECS Fargate + ElastiCache Redis in under 30 minutes

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${BLUE}"
echo "========================================"
echo "  Consoul AWS Deployment"
echo "========================================"
echo -e "${NC}"

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------
check_prereqs() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    local missing=()

    command -v aws >/dev/null 2>&1 || missing+=("aws CLI (https://aws.amazon.com/cli/)")
    command -v terraform >/dev/null 2>&1 || missing+=("terraform (https://terraform.io/downloads)")
    command -v docker >/dev/null 2>&1 || missing+=("docker (https://docs.docker.com/get-docker/)")

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing prerequisites:${NC}"
        for tool in "${missing[@]}"; do
            echo "  - $tool"
        done
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        echo -e "${RED}AWS credentials not configured. Run: aws configure${NC}"
        exit 1
    fi

    echo -e "${GREEN}All prerequisites met!${NC}"
}

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
configure() {
    echo ""
    echo -e "${YELLOW}Configuration${NC}"
    echo "-------------"

    # Region
    REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-east-1")}"
    read -rp "AWS Region [$REGION]: " input
    REGION="${input:-$REGION}"

    # API Key
    if [ -z "${CONSOUL_API_KEY:-}" ]; then
        API_KEY=$(openssl rand -hex 32)
        echo -e "${YELLOW}Generated API Key: ${API_KEY}${NC}"
        echo -e "${RED}Save this key - it won't be shown again!${NC}"
    else
        API_KEY="$CONSOUL_API_KEY"
        echo "Using provided API key from CONSOUL_API_KEY"
    fi

    # Get account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

    # Confirm
    echo ""
    echo "Deployment Configuration:"
    echo "  Account: $ACCOUNT_ID"
    echo "  Region:  $REGION"
    echo ""
    read -rp "Continue with deployment? [Y/n]: " confirm
    if [[ "${confirm:-Y}" =~ ^[Nn] ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
}

# -----------------------------------------------------------------------------
# Deploy Infrastructure First (for ECR)
# -----------------------------------------------------------------------------
deploy_infrastructure() {
    echo ""
    echo -e "${YELLOW}Deploying infrastructure with Terraform...${NC}"

    cd "$SCRIPT_DIR"

    # Initialize Terraform
    terraform init

    # Create tfvars file
    cat > terraform.tfvars <<EOF
aws_region = "$REGION"
api_keys   = ["$API_KEY"]
EOF

    # Apply infrastructure (this creates ECR repository)
    terraform apply -auto-approve

    # Get ECR repository URL
    ECR_URL=$(terraform output -raw ecr_repository_url)
    echo -e "${GREEN}Infrastructure deployed!${NC}"
}

# -----------------------------------------------------------------------------
# Build and Push Docker Image
# -----------------------------------------------------------------------------
build_and_push() {
    echo ""
    echo -e "${YELLOW}Building and pushing Docker image...${NC}"

    # Login to ECR
    aws ecr get-login-password --region "$REGION" | \
        docker login --username AWS --password-stdin "$ECR_URL"

    # Build from project root
    cd "$PROJECT_ROOT"
    docker build \
        -f deployment/cloud/shared/Dockerfile \
        -t "$ECR_URL:latest" \
        .

    # Push to ECR
    docker push "$ECR_URL:latest"

    echo -e "${GREEN}Image pushed: $ECR_URL:latest${NC}"
}

# -----------------------------------------------------------------------------
# Update ECS Service
# -----------------------------------------------------------------------------
update_service() {
    echo ""
    echo -e "${YELLOW}Updating ECS service...${NC}"

    cd "$SCRIPT_DIR"

    # Force new deployment
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    SERVICE_NAME=$(terraform output -raw ecs_service_name)

    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME" \
        --force-new-deployment \
        --region "$REGION" \
        >/dev/null

    echo "Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$REGION"

    # Get outputs
    SERVICE_URL=$(terraform output -raw service_url)

    echo ""
    echo -e "${GREEN}========================================"
    echo "  Deployment Complete!"
    echo "========================================${NC}"
    echo ""
    echo -e "Service URL: ${BLUE}$SERVICE_URL${NC}"
    echo -e "API Key:     ${YELLOW}$API_KEY${NC}"
    echo ""
    echo "Test with:"
    echo -e "  ${GREEN}curl -H 'X-API-Key: $API_KEY' $SERVICE_URL/health${NC}"
    echo ""
    echo "View logs:"
    echo -e "  ${BLUE}aws logs tail /ecs/consoul-api-prod --follow --region $REGION${NC}"
    echo ""
    echo "To destroy:"
    echo -e "  ${RED}cd $SCRIPT_DIR && terraform destroy${NC}"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    check_prereqs
    configure
    deploy_infrastructure
    build_and_push
    update_service
}

main "$@"

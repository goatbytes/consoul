#!/bin/bash
# Consoul GCP Deployment - Quick Start
# Deploys Cloud Run + Memorystore Redis in under 30 minutes

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
echo "  Consoul GCP Deployment"
echo "========================================"
echo -e "${NC}"

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------
check_prereqs() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    local missing=()

    command -v gcloud >/dev/null 2>&1 || missing+=("gcloud CLI (https://cloud.google.com/sdk/docs/install)")
    command -v terraform >/dev/null 2>&1 || missing+=("terraform (https://terraform.io/downloads)")
    command -v docker >/dev/null 2>&1 || missing+=("docker (https://docs.docker.com/get-docker/)")

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing prerequisites:${NC}"
        for tool in "${missing[@]}"; do
            echo "  - $tool"
        done
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

    # Project ID
    PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "")}"
    if [ -z "$PROJECT_ID" ]; then
        read -rp "Enter GCP Project ID: " PROJECT_ID
    else
        read -rp "GCP Project ID [$PROJECT_ID]: " input
        PROJECT_ID="${input:-$PROJECT_ID}"
    fi

    # Region
    REGION="${GCP_REGION:-us-central1}"
    read -rp "Region [$REGION]: " input
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

    # Confirm
    echo ""
    echo "Deployment Configuration:"
    echo "  Project: $PROJECT_ID"
    echo "  Region:  $REGION"
    echo ""
    read -rp "Continue with deployment? [Y/n]: " confirm
    if [[ "${confirm:-Y}" =~ ^[Nn] ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
}

# -----------------------------------------------------------------------------
# Enable APIs
# -----------------------------------------------------------------------------
enable_apis() {
    echo ""
    echo -e "${YELLOW}Enabling required GCP APIs...${NC}"

    gcloud services enable \
        run.googleapis.com \
        redis.googleapis.com \
        secretmanager.googleapis.com \
        vpcaccess.googleapis.com \
        containerregistry.googleapis.com \
        compute.googleapis.com \
        --project="$PROJECT_ID"

    echo -e "${GREEN}APIs enabled!${NC}"
}

# -----------------------------------------------------------------------------
# Build and Push Docker Image
# -----------------------------------------------------------------------------
build_and_push() {
    echo ""
    echo -e "${YELLOW}Building and pushing Docker image...${NC}"

    IMAGE_URL="gcr.io/$PROJECT_ID/consoul-api:latest"

    # Configure Docker for GCR
    gcloud auth configure-docker gcr.io --quiet

    # Build from project root
    cd "$PROJECT_ROOT"
    docker build \
        -f deployment/cloud/shared/Dockerfile \
        -t "$IMAGE_URL" \
        .

    # Push to GCR
    docker push "$IMAGE_URL"

    echo -e "${GREEN}Image pushed: $IMAGE_URL${NC}"
}

# -----------------------------------------------------------------------------
# Deploy with Terraform
# -----------------------------------------------------------------------------
deploy() {
    echo ""
    echo -e "${YELLOW}Deploying infrastructure with Terraform...${NC}"

    cd "$SCRIPT_DIR"

    # Initialize Terraform
    terraform init

    # Create tfvars file
    cat > terraform.tfvars <<EOF
project_id = "$PROJECT_ID"
region     = "$REGION"
api_keys   = ["$API_KEY"]
image_url  = "$IMAGE_URL"
EOF

    # Apply
    terraform apply -auto-approve

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
    echo "To destroy:"
    echo -e "  ${RED}cd $SCRIPT_DIR && terraform destroy${NC}"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    check_prereqs
    configure
    enable_apis
    build_and_push
    deploy
}

main "$@"

#!/bin/bash
# Consoul Azure Deployment - Quick Start
# Deploys Container Apps + Azure Cache for Redis in under 30 minutes

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
echo "  Consoul Azure Deployment"
echo "========================================"
echo -e "${NC}"

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------
check_prereqs() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    local missing=()

    command -v az >/dev/null 2>&1 || missing+=("az CLI (https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)")
    command -v terraform >/dev/null 2>&1 || missing+=("terraform (https://terraform.io/downloads)")
    command -v docker >/dev/null 2>&1 || missing+=("docker (https://docs.docker.com/get-docker/)")

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing prerequisites:${NC}"
        for tool in "${missing[@]}"; do
            echo "  - $tool"
        done
        exit 1
    fi

    # Check Azure login
    if ! az account show &>/dev/null; then
        echo -e "${YELLOW}Not logged into Azure. Running: az login${NC}"
        az login
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

    # Location
    LOCATION="${AZURE_LOCATION:-eastus}"
    read -rp "Azure Location [$LOCATION]: " input
    LOCATION="${input:-$LOCATION}"

    # API Key
    if [ -z "${CONSOUL_API_KEY:-}" ]; then
        API_KEY=$(openssl rand -hex 32)
        echo -e "${YELLOW}Generated API Key: ${API_KEY}${NC}"
        echo -e "${RED}Save this key - it won't be shown again!${NC}"
    else
        API_KEY="$CONSOUL_API_KEY"
        echo "Using provided API key from CONSOUL_API_KEY"
    fi

    # Get subscription info
    SUBSCRIPTION=$(az account show --query name -o tsv)
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)

    # Confirm
    echo ""
    echo "Deployment Configuration:"
    echo "  Subscription: $SUBSCRIPTION"
    echo "  Location:     $LOCATION"
    echo ""
    read -rp "Continue with deployment? [Y/n]: " confirm
    if [[ "${confirm:-Y}" =~ ^[Nn] ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
}

# -----------------------------------------------------------------------------
# Deploy Infrastructure First (for ACR)
# -----------------------------------------------------------------------------
deploy_infrastructure() {
    echo ""
    echo -e "${YELLOW}Deploying infrastructure with Terraform...${NC}"

    cd "$SCRIPT_DIR"

    # Initialize Terraform
    terraform init

    # Create tfvars file
    cat > terraform.tfvars <<EOF
location = "$LOCATION"
api_keys = ["$API_KEY"]
EOF

    # Apply infrastructure (this creates ACR)
    terraform apply -auto-approve

    # Get ACR info
    ACR_NAME=$(terraform output -raw acr_login_server | cut -d. -f1)
    ACR_SERVER=$(terraform output -raw acr_login_server)

    echo -e "${GREEN}Infrastructure deployed!${NC}"
}

# -----------------------------------------------------------------------------
# Build and Push Docker Image
# -----------------------------------------------------------------------------
build_and_push() {
    echo ""
    echo -e "${YELLOW}Building and pushing Docker image...${NC}"

    # Login to ACR
    az acr login --name "$ACR_NAME"

    # Build from project root
    cd "$PROJECT_ROOT"
    docker build \
        -f deployment/cloud/shared/Dockerfile \
        -t "$ACR_SERVER/consoul-api:latest" \
        .

    # Push to ACR
    docker push "$ACR_SERVER/consoul-api:latest"

    echo -e "${GREEN}Image pushed: $ACR_SERVER/consoul-api:latest${NC}"
}

# -----------------------------------------------------------------------------
# Update Container App
# -----------------------------------------------------------------------------
update_app() {
    echo ""
    echo -e "${YELLOW}Updating Container App...${NC}"

    cd "$SCRIPT_DIR"

    # Re-apply to update container app with new image
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
    echo "View logs:"
    echo -e "  ${BLUE}az containerapp logs show -n consoul-api-prod -g consoul-api-prod-rg${NC}"
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
    update_app
}

main "$@"

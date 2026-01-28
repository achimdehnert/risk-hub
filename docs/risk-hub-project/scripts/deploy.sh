#!/bin/bash
# =============================================================================
# risk-hub Deployment Script
# =============================================================================
#
# Usage:
#   ./scripts/deploy.sh [environment] [version]
#
# Examples:
#   ./scripts/deploy.sh staging latest
#   ./scripts/deploy.sh prod v1.2.3
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Arguments
ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"

# Config
REGISTRY="ghcr.io"
IMAGE_PREFIX="bfagent/risk-hub"
ANSIBLE_DIR="infra/ansible"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  risk-hub Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Version:     ${YELLOW}${VERSION}${NC}"
echo ""

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Invalid environment. Use: dev, staging, or prod${NC}"
    exit 1
fi

# Confirm production deployment
if [ "$ENVIRONMENT" == "prod" ]; then
    echo -e "${RED}WARNING: You are about to deploy to PRODUCTION!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Step 1: Build and push Docker image
echo ""
echo -e "${GREEN}Step 1: Building Docker image...${NC}"
docker build -t "${REGISTRY}/${IMAGE_PREFIX}-app:${VERSION}" \
    --target production \
    -f infra/docker/app/Dockerfile .

echo -e "${GREEN}Step 2: Pushing Docker image...${NC}"
docker push "${REGISTRY}/${IMAGE_PREFIX}-app:${VERSION}"

# Step 3: Run Ansible deployment
echo ""
echo -e "${GREEN}Step 3: Running Ansible deployment...${NC}"
cd "${ANSIBLE_DIR}"

ansible-playbook \
    -i "inventory/${ENVIRONMENT}" \
    playbooks/site.yml \
    --tags deploy \
    -e "app_version=${VERSION}" \
    -e "app_force_restart=true"

# Step 4: Verify deployment
echo ""
echo -e "${GREEN}Step 4: Verifying deployment...${NC}"

# Get Load Balancer IP from Terraform
LB_IP=$(cd ../terraform && terraform output -raw load_balancer_ip 2>/dev/null || echo "unknown")

if [ "$LB_IP" != "unknown" ]; then
    echo "Checking health endpoint..."
    sleep 10
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://${LB_IP}/health/" || echo "000")
    
    if [ "$HTTP_CODE" == "200" ]; then
        echo -e "${GREEN}✅ Deployment successful!${NC}"
        echo -e "   Load Balancer IP: ${LB_IP}"
    else
        echo -e "${RED}⚠️  Health check returned: ${HTTP_CODE}${NC}"
        echo "   Please verify deployment manually."
    fi
else
    echo "Could not determine Load Balancer IP. Please verify deployment manually."
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete${NC}"
echo -e "${GREEN}========================================${NC}"

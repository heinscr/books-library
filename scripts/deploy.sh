#!/bin/bash

# Deployment script for Books Library application
# Provides consistent deployment for frontend and backend

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load deployment configuration
if [ -f ".deploy-config" ]; then
    echo -e "${YELLOW}📄 Loading deployment configuration...${NC}"
    source .deploy-config
else
    echo -e "${RED}❌ Error: .deploy-config file not found${NC}"
    echo "Please create .deploy-config with deployment settings"
    exit 1
fi

# Override with environment variables if provided
AWS_PROFILE=${AWS_PROFILE:-craig-dev}
AWS_REGION=${AWS_REGION:-us-east-2}

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --frontend          Deploy frontend only"
    echo "  --backend           Deploy backend only"
    echo "  --all               Deploy both frontend and backend (default)"
    echo "  --invalidate        Invalidate CloudFront cache after frontend deployment"
    echo "  --no-invalidate     Skip CloudFront invalidation"
    echo "  --help              Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_PROFILE         AWS profile to use (default: ${AWS_PROFILE})"
    echo "  FRONTEND_BUCKET     Frontend S3 bucket (default: ${FRONTEND_BUCKET})"
    echo "  FRONTEND_PATH       Path in bucket (default: ${FRONTEND_PATH})"
    echo ""
    echo "Examples:"
    echo "  $0 --frontend                    # Deploy frontend only"
    echo "  $0 --backend                     # Deploy backend only"
    echo "  $0 --all --invalidate            # Deploy all and invalidate cache"
    echo "  AWS_PROFILE=prod $0 --frontend   # Deploy with different profile"
}

# Parse arguments
DEPLOY_FRONTEND=false
DEPLOY_BACKEND=false
INVALIDATE_CACHE=${AUTO_INVALIDATE:-true}

if [ $# -eq 0 ]; then
    DEPLOY_FRONTEND=true
    DEPLOY_BACKEND=true
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --frontend)
            DEPLOY_FRONTEND=true
            shift
            ;;
        --backend)
            DEPLOY_BACKEND=true
            shift
            ;;
        --all)
            DEPLOY_FRONTEND=true
            DEPLOY_BACKEND=true
            shift
            ;;
        --invalidate)
            INVALIDATE_CACHE=true
            shift
            ;;
        --no-invalidate)
            INVALIDATE_CACHE=false
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Display configuration
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}📦 Books Library Deployment${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "Configuration:"
echo "  AWS Profile: ${AWS_PROFILE}"
echo "  AWS Region: ${AWS_REGION}"
echo "  Frontend Bucket: s3://${FRONTEND_BUCKET}/${FRONTEND_PATH}/"
echo "  Deploy Frontend: ${DEPLOY_FRONTEND}"
echo "  Deploy Backend: ${DEPLOY_BACKEND}"
echo "  Invalidate Cache: ${INVALIDATE_CACHE}"
echo ""

# Deploy Backend
if [ "$DEPLOY_BACKEND" = true ]; then
    echo -e "${YELLOW}🔧 Deploying Backend...${NC}"
    echo ""

    echo "Building SAM application..."
    sam build

    echo ""
    echo "Deploying Lambda functions..."
    sam deploy --profile ${AWS_PROFILE} --region ${AWS_REGION}

    echo ""
    echo -e "${GREEN}✅ Backend deployment complete${NC}"
    echo ""
fi

# Deploy Frontend
if [ "$DEPLOY_FRONTEND" = true ]; then
    echo -e "${YELLOW}🎨 Deploying Frontend...${NC}"
    echo ""

    # Sync frontend files
    echo "Syncing frontend files to S3..."
    aws s3 sync frontend/ s3://${FRONTEND_BUCKET}/${FRONTEND_PATH}/ \
        --profile ${AWS_PROFILE} \
        --region ${AWS_REGION} \
        --delete

    # Sync API docs
    echo "Syncing API documentation..."
    aws s3 sync docs/ s3://${FRONTEND_BUCKET}/${FRONTEND_PATH}/api-docs/ \
        --profile ${AWS_PROFILE} \
        --region ${AWS_REGION} \
        --exclude "*.md"

    echo ""
    echo -e "${GREEN}✅ Frontend deployment complete${NC}"
    echo ""

    # Invalidate CloudFront cache
    if [ "$INVALIDATE_CACHE" = true ]; then
        echo -e "${YELLOW}♻️  Invalidating CloudFront cache...${NC}"
        echo ""

        if [ -n "$CLOUDFRONT_DIST_1" ]; then
            echo "Invalidating distribution: ${CLOUDFRONT_DIST_1}"
            aws cloudfront create-invalidation \
                --distribution-id ${CLOUDFRONT_DIST_1} \
                --paths "/*" \
                --profile ${AWS_PROFILE} \
                --output text --query 'Invalidation.Id'
        fi

        if [ -n "$CLOUDFRONT_DIST_2" ]; then
            echo "Invalidating distribution: ${CLOUDFRONT_DIST_2}"
            aws cloudfront create-invalidation \
                --distribution-id ${CLOUDFRONT_DIST_2} \
                --paths "/*" \
                --profile ${AWS_PROFILE} \
                --output text --query 'Invalidation.Id'
        fi

        echo ""
        echo -e "${GREEN}✅ Cache invalidation initiated${NC}"
        echo -e "${YELLOW}⏳ Note: Cache invalidation takes 3-5 minutes to complete${NC}"
        echo ""
    fi
fi

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$DEPLOY_FRONTEND" = true ]; then
    echo "Frontend URL: ${CLOUDFRONT_URL}/"
    echo "API Docs: ${CLOUDFRONT_URL}/api-docs/"
fi

if [ "$DEPLOY_BACKEND" = true ]; then
    echo ""
    echo "View backend status:"
    echo "  sam list stack-outputs --profile ${AWS_PROFILE}"
fi

echo ""

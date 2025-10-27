# Deployment Guide

This guide covers deploying updates to the Books Library application using the unified deployment script.

> **First-time setup?** See [`TERRAFORM_SETUP.md`](TERRAFORM_SETUP.md) for automated infrastructure provisioning or [`MANUAL_DEPLOYMENT.md`](MANUAL_DEPLOYMENT.md) for manual setup.

## Overview

The unified deployment script ([`scripts/deploy.sh`](../scripts/deploy.sh)) provides a consistent way to deploy frontend and backend changes using centralized configuration.

## Configuration

### One-Time Setup

1. Copy the example configuration:
```bash
cp .deploy-config.example .deploy-config
```

2. Edit `.deploy-config` with your values:
```bash
# AWS Configuration
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-2

# S3 Buckets
FRONTEND_BUCKET=your-frontend-bucket
FRONTEND_PATH=books-app
BOOKS_BUCKET=your-books-bucket

# CloudFront Distributions
CLOUDFRONT_DIST_1=YOUR_DISTRIBUTION_ID_1
CLOUDFRONT_DIST_2=YOUR_DISTRIBUTION_ID_2
CLOUDFRONT_URL=https://your-distribution.cloudfront.net

# Deployment Options
AUTO_INVALIDATE=true
```

**Where to find these values:**
- AWS profile: `aws configure list-profiles`
- S3 buckets: `aws s3 ls` or Terraform outputs
- CloudFront distributions: `aws cloudfront list-distributions` or Terraform outputs
- CloudFront URL: Check your CloudFront distributions in AWS Console

**Important:** `.deploy-config` is in `.gitignore` and should never be committed (contains environment-specific values).

## Deployment Commands

### Deploy Frontend Only
```bash
./scripts/deploy.sh --frontend
```

Deploys:
- Frontend files to S3
- API documentation to S3

### Deploy Backend Only
```bash
./scripts/deploy.sh --backend
```

Deploys:
- Lambda functions via SAM
- API Gateway
- DynamoDB tables

### Deploy Everything
```bash
./scripts/deploy.sh --all
```

Deploys both frontend and backend.

### With Cache Invalidation
```bash
./scripts/deploy.sh --frontend --invalidate
```

Adds CloudFront cache invalidation after deployment. Cache invalidation takes 3-5 minutes to propagate.

## Common Workflows

### Frontend Changes
```bash
# Make changes to frontend files
./scripts/deploy.sh --frontend --invalidate
# Wait 3-5 minutes for cache to clear
```

### Backend Changes
```bash
# Make changes to Lambda functions
./scripts/deploy.sh --backend
# Changes are live immediately
```

### Full Deployment
```bash
# Deploy everything with cache invalidation
./scripts/deploy.sh --all --invalidate
```

## Verification

After deployment, the script displays:
- Frontend URL
- API Docs URL
- Backend status command

Visit the URLs to verify your changes are live.

## Troubleshooting

### "Error: .deploy-config file not found"
Solution: Copy and configure `.deploy-config.example` to `.deploy-config`

### "Access Denied" errors
Solution:
- Verify AWS profile has necessary permissions
- Check `AWS_PROFILE` in `.deploy-config` is correct
- Run `aws sts get-caller-identity --profile YOUR_PROFILE` to verify

### CloudFront still shows old version
Solution:
- Ensure you used `--invalidate` flag
- Wait 3-5 minutes for cache invalidation to complete
- Check invalidation status:
  ```bash
  aws cloudfront get-invalidation \
    --distribution-id YOUR_DIST_ID \
    --id INVALIDATION_ID \
    --profile YOUR_PROFILE
  ```

### SAM deployment fails
Solution:
- Ensure `sam build` completes successfully first
- Check `template.yaml` for syntax errors
- Verify SAM CLI is installed: `sam --version`

## Advanced Usage

### Environment-Specific Deployments

For multiple environments (dev, staging, prod), create separate config files:

```bash
# Development
.deploy-config.dev

# Staging
.deploy-config.staging

# Production
.deploy-config.prod
```

Modify the script to load the appropriate config:
```bash
# Edit scripts/deploy.sh temporarily or create wrapper scripts
cp .deploy-config.prod .deploy-config
./scripts/deploy.sh --all --invalidate
```

### Manual S3 Sync (Not Recommended)

If you need to manually sync specific files:
```bash
source .deploy-config
aws s3 sync frontend/ s3://${FRONTEND_BUCKET}/${FRONTEND_PATH}/ \
  --profile ${AWS_PROFILE} \
  --region ${AWS_REGION}
```

However, the deployment script is preferred as it handles all necessary steps correctly.

## Related Documentation

- [`TERRAFORM_SETUP.md`](TERRAFORM_SETUP.md) - First-time infrastructure setup
- [`MANUAL_DEPLOYMENT.md`](MANUAL_DEPLOYMENT.md) - Manual deployment without deployment script
- [`CONFIGURATION.md`](CONFIGURATION.md) - Configuration file reference
- [`../scripts/README.md`](../scripts/README.md) - All available scripts

## Benefits of Unified Deployment

- **Single source of truth**: All deployment settings in `.deploy-config`
- **Consistent paths**: No more deployment path confusion
- **Automatic invalidation**: Optional CloudFront cache clearing
- **Clear output**: Color-coded status messages
- **Flexible**: Deploy frontend, backend, or both
- **Safe**: Uses tested deployment commands

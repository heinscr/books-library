# Configuration Guide

> **Quick Start**: If you're using Terraform for infrastructure setup, see [`TERRAFORM_SETUP.md`](TERRAFORM_SETUP.md) for the complete automated workflow. This guide covers configuration details for both Terraform and manual setups.

This document explains how to configure the Books Library application for your environment.

## Security Notice

⚠️ **IMPORTANT**: Never commit files containing actual credentials or API keys to version control.

All configuration files with actual values are included in `.gitignore`:
- `samconfig.toml` - SAM deployment configuration
- `frontend/config.js` - Frontend API configuration
- `.deploy-config` - Deployment script configuration
- `.env` files - Environment variables

## Configuration Files

### 1. SAM Configuration (`samconfig.toml`)

**Setup:**
```bash
# Copy the example file
cp samconfig.toml.example samconfig.toml

# Edit with your values
nano samconfig.toml
```

**Required Parameters:**
- `BucketName` - Your S3 bucket name (e.g., `my-books-bucket`)
- `CognitoUserPoolId` - Your Cognito User Pool ID (e.g., `us-east-1_XXXXXXXXX`)
- `CognitoUserPoolArn` - Your Cognito User Pool ARN
- `CognitoClientId` - Your Cognito App Client ID

**Example:**
```toml
parameter_overrides = [
    "BucketName=my-books-bucket",
    "CognitoUserPoolId=us-east-1_AbCdEfGhI",
    "CognitoUserPoolArn=arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI",
    "CognitoClientId=1abc2def3ghi4jkl5mno6pqr"
]
```

### 2. Frontend Configuration (`frontend/config.js`)

**Setup:**
```bash
# Copy the example file
cp frontend/config.js.example frontend/config.js

# Edit with your values
nano frontend/config.js
```

**Required Values:**
```javascript
const COGNITO_CONFIG = {
    userPoolId: 'us-east-1_AbCdEfGhI',
    clientId: '1abc2def3ghi4jkl5mno6pqr',
    region: 'us-east-1'
};

const API_URL = 'https://abc123.execute-api.us-east-2.amazonaws.com/Prod/books';
```

**Where to find these values:**
- After running `sam deploy`, the API URL is in the outputs
- Cognito values are from your AWS Cognito User Pool

### 3. Deployment Configuration (`.deploy-config`)

**Setup:**
```bash
# Copy the example file
cp .deploy-config.example .deploy-config

# Edit with your values
nano .deploy-config
```

**Required Values:**
- `AWS_PROFILE` - AWS CLI profile name
- `AWS_REGION` - AWS region (e.g., `us-east-2`)
- `FRONTEND_BUCKET` - S3 bucket for frontend
- `FRONTEND_PATH` - Path within bucket (e.g., `books-app`)
- `BOOKS_BUCKET` - S3 bucket for book storage
- `CLOUDFRONT_DIST_1` - Primary CloudFront distribution ID
- `CLOUDFRONT_DIST_2` - Secondary CloudFront distribution ID (if applicable)
- `CLOUDFRONT_URL` - CloudFront URL (e.g., `https://abc123.cloudfront.net`)
- `AUTO_INVALIDATE` - Automatic cache invalidation (true/false)

**Example:**
```bash
AWS_PROFILE=my-profile
AWS_REGION=us-east-2
FRONTEND_BUCKET=my-bucket
FRONTEND_PATH=books-app
CLOUDFRONT_DIST_1=E1234567890ABC
CLOUDFRONT_URL=https://d1234abcd.cloudfront.net
AUTO_INVALIDATE=true
```

**Usage:**
See [`DEPLOYMENT.md`](DEPLOYMENT.md) for deployment using this configuration.

### 4. Script Configuration

The helper scripts (`scripts/configure-s3-trigger.sh` and `scripts/migrate-books.py`) use environment variables:

```bash
# Set environment variables for scripts
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-east-2
export S3_BUCKET=my-books-bucket
export BOOKS_PREFIX=books/
export DYNAMODB_TABLE=Books

# Run scripts
./scripts/configure-s3-trigger.sh
python3 scripts/migrate-books.py
```

## Quick Start Configuration

### Step 1: Create AWS Resources

First, create your Cognito User Pool and S3 bucket manually or use existing ones.

### Step 2: Configure SAM

```bash
cp samconfig.toml.example samconfig.toml
# Edit samconfig.toml with your values
```

### Step 3: Deploy Backend

```bash
sam build
sam deploy
```

Note the outputs - you'll need the API URL.

### Step 4: Configure Frontend

```bash
cp frontend/config.js.example frontend/config.js
# Edit frontend/config.js with:
# - Cognito User Pool ID and Client ID
# - API URL from SAM deploy outputs
```

### Step 5: Deploy Frontend

```bash
aws s3 cp frontend/ s3://YOUR_BUCKET/books-app/ --recursive
```

### Step 6: Configure S3 Trigger

```bash
cd scripts
export S3_BUCKET=your-bucket-name
./configure-s3-trigger.sh
# When prompted, enter the S3TriggerFunction ARN from SAM outputs
```

### Step 7: Migrate Existing Books

```bash
export S3_BUCKET=your-bucket-name
python3 migrate-books.py
```

## Environment-Specific Configurations

For multiple environments (dev, staging, prod), create separate configuration files:

```bash
# Development
samconfig.dev.toml
frontend/config.dev.js

# Staging
samconfig.staging.toml
frontend/config.staging.js

# Production
samconfig.prod.toml
frontend/config.prod.js
```

Deploy with specific config:
```bash
sam deploy --config-file samconfig.dev.toml
```

## Troubleshooting

### "Parameter validation failed"
- Check that all required parameters are set in `samconfig.toml`
- Verify parameter values match AWS resource formats

### "Access Denied" errors
- Ensure your AWS credentials have necessary permissions
- Check that bucket names and ARNs are correct

### Frontend can't connect to API
- Verify API URL in `frontend/config.js` matches SAM outputs
- Check CORS settings in `template.yaml`
- Ensure Cognito configuration is correct

## Security Best Practices

1. **Never commit** `samconfig.toml` or `frontend/config.js` to version control
2. **Use IAM roles** with least privilege for Lambda functions
3. **Rotate credentials** regularly
4. **Enable CloudTrail** for audit logging
5. **Use AWS Secrets Manager** for sensitive configuration in production

## Getting Configuration Values

### Cognito User Pool ID
```bash
aws cognito-idp list-user-pools --max-results 20
```

### S3 Bucket Name
```bash
aws s3 ls
```

### API Gateway URL
```bash
# After deployment
sam list endpoints --stack-name your-stack-name
```

### Lambda Function ARN
```bash
aws lambda list-functions --query "Functions[?contains(FunctionName, 'S3Trigger')].FunctionArn"
```

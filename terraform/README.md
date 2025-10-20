# Terraform Infrastructure Setup

This directory contains Terraform configuration to automate the setup of AWS infrastructure for the Books Library application.

## What Gets Created

Terraform will automatically provision:

### S3 Buckets
- **Books Bucket**: Stores book covers and uploaded files
  - Versioning enabled
  - CORS configured for web access
  - Private by default
- **Frontend Bucket**: Hosts the static website
  - Static website hosting enabled
  - Public read access
  - Versioning enabled

### DynamoDB Tables
- **Books**: Main table for book metadata
  - AuthorIndex GSI for querying by author
- **UserBooks**: Tracks user read status
- **Authors**: Stores author information

### Cognito
- **User Pool**: Manages user authentication
  - Email-based authentication
  - Password policy configured
  - Custom `isAdmin` attribute
- **User Pool Client**: Client application configuration
- **Optional Domain**: For hosted UI (if configured)

### IAM
- **Lambda Execution Role**: Permissions for Lambda functions
  - Basic Lambda execution
  - DynamoDB read/write access
  - S3 read/write access

## Prerequisites

1. **Install Terraform**: [Download here](https://www.terraform.io/downloads)
   ```bash
   # Verify installation
   terraform version
   ```

2. **AWS Credentials**: Configure AWS CLI
   ```bash
   aws configure
   # Or use a specific profile
   export AWS_PROFILE=your-profile-name
   ```

3. **Permissions**: Ensure your AWS credentials have permissions to create:
   - S3 buckets
   - DynamoDB tables
   - Cognito resources
   - IAM roles and policies

## Quick Start

### 1. Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:
```hcl
# Required: S3 bucket names must be globally unique
books_bucket_name    = "my-unique-books-bucket-name"
frontend_bucket_name = "my-unique-frontend-bucket-name"

# Optional: Use a specific AWS profile
aws_profile = "your-profile-name"

# Optional: Change environment
environment = "prod"
```

### 2. Initialize Terraform

```bash
terraform init
```

This downloads the required AWS provider.

### 3. Review the Plan

```bash
terraform plan
```

This shows what resources will be created without making changes.

### 4. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted to create the resources.

### 5. Save Outputs

After apply completes, Terraform will display important outputs:
- S3 bucket names
- DynamoDB table names
- Cognito User Pool ID and Client ID
- Configuration values for SAM and frontend

You can view outputs anytime:
```bash
terraform output
```

Get specific output:
```bash
terraform output cognito_user_pool_id
terraform output samconfig_parameters
```

## Configuration After Terraform

### Update samconfig.toml

Use the Terraform outputs to configure SAM:

```bash
# Get values from Terraform
terraform output samconfig_parameters

# Update samconfig.toml with these values
nano ../samconfig.toml
```

### Update frontend/config.js

```bash
# Get values from Terraform
terraform output frontend_config

# Update frontend config
nano ../frontend/config.js
```

### Deploy Lambda Functions

```bash
cd ..
sam build
sam deploy
```

### Deploy Frontend

```bash
# Get frontend bucket name
FRONTEND_BUCKET=$(cd terraform && terraform output -raw frontend_bucket_name)

# Upload frontend files
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/
```

### Configure S3 Trigger

```bash
cd scripts
export S3_BUCKET=$(cd ../terraform && terraform output -raw books_bucket_name)
./configure-s3-trigger.sh
```

## Multiple Environments

Create separate variable files for each environment:

```bash
# Development
cp terraform.tfvars.example terraform.tfvars.dev

# Production
cp terraform.tfvars.example terraform.tfvars.prod
```

Apply with specific variable file:
```bash
terraform apply -var-file="terraform.tfvars.dev"
terraform apply -var-file="terraform.tfvars.prod"
```

Or use workspaces:
```bash
terraform workspace new dev
terraform workspace new prod

terraform workspace select dev
terraform apply

terraform workspace select prod
terraform apply
```

## Managing Resources

### View Current State

```bash
# List all resources
terraform state list

# Show specific resource
terraform state show aws_s3_bucket.books
```

### Update Resources

1. Modify `terraform.tfvars` or `*.tf` files
2. Run `terraform plan` to review changes
3. Run `terraform apply` to apply changes

### Destroy Resources

**Warning**: This deletes all created resources!

```bash
# Review what will be destroyed
terraform plan -destroy

# Destroy all resources
terraform destroy
```

## Important Variables

### Required Variables
- `books_bucket_name`: Must be globally unique across all AWS accounts
- `frontend_bucket_name`: Must be globally unique across all AWS accounts

### Common Variables
```hcl
# AWS Configuration
aws_region  = "us-east-2"
aws_profile = "your-profile"
environment = "dev"

# S3 Buckets (must be globally unique)
books_bucket_name    = "my-books-123456"
frontend_bucket_name = "my-frontend-123456"

# CORS Origins
cors_allowed_origins = ["http://localhost:8000"]

# DynamoDB
enable_point_in_time_recovery = true  # Enable for production

# Cognito
cognito_callback_urls = ["http://localhost:8000"]
cognito_domain_prefix = "my-books-app"  # Optional
```

## Outputs Reference

### Configuration Outputs
- `samconfig_parameters`: Values for samconfig.toml
- `frontend_config`: Values for frontend/config.js

### Resource Outputs
- `books_bucket_name`: S3 bucket for books
- `frontend_bucket_website_url`: Frontend website URL
- `cognito_user_pool_id`: Cognito User Pool ID
- `cognito_client_id`: Cognito Client ID
- `lambda_execution_role_arn`: IAM role for Lambda

### Summary Output
- `setup_complete`: Full summary with next steps

## Troubleshooting

### "BucketAlreadyExists"
S3 bucket names must be globally unique. Change bucket names in `terraform.tfvars`.

### "AccessDenied" or "UnauthorizedOperation"
Your AWS credentials lack required permissions. Ensure your IAM user/role has:
- `s3:*`
- `dynamodb:*`
- `cognito-idp:*`
- `iam:*` (for role creation)

### "Error locking state"
Another terraform process is running. Wait or remove the lock:
```bash
terraform force-unlock <lock-id>
```

### Review Existing Resources
```bash
# Show what currently exists
terraform state list

# Get details of specific resource
terraform show
```

## Cost Estimation

Typical monthly costs (us-east-2):
- **S3**: ~$0.023/GB storage + data transfer
- **DynamoDB**: Pay-per-request (free tier: 25 GB storage, 2.5M reads)
- **Cognito**: Free for up to 50,000 MAUs
- **Lambda**: Covered by SAM deployment

Estimated: **$1-5/month** for low-traffic personal use (mostly free tier)

## Security Best Practices

1. **Never commit `terraform.tfvars`** - Contains sensitive values
2. **Use remote state** for production (S3 backend with encryption)
3. **Enable MFA** for AWS account
4. **Review IAM policies** - Use least privilege
5. **Enable CloudTrail** - Audit all API calls
6. **Backup state files** - Store securely

## Advanced: Remote State

For team collaboration, use S3 backend:

Create `backend.tf`:
```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "books-library/terraform.tfstate"
    region         = "us-east-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

## Next Steps

After running Terraform:
1. ✅ Infrastructure created
2. Update `samconfig.toml` with Terraform outputs
3. Deploy Lambda: `sam build && sam deploy`
4. Update `frontend/config.js`
5. Deploy frontend to S3
6. Configure S3 trigger for Lambda
7. Create Cognito users

## Support

For issues:
1. Check `terraform plan` output carefully
2. Review AWS CloudFormation console for errors
3. Check AWS service quotas
4. Verify IAM permissions

## Cleaning Up

To remove all infrastructure:
```bash
terraform destroy
```

**Note**: This does NOT delete:
- S3 bucket contents (must empty first)
- CloudWatch logs
- Cognito users

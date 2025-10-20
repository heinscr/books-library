# Terraform Quick Reference

## Initial Setup

```bash
# 1. Copy example configuration
cd terraform
cp terraform.tfvars.example terraform.tfvars

# 2. Edit with your values (IMPORTANT: bucket names must be globally unique)
nano terraform.tfvars

# 3. Initialize Terraform
terraform init
```

## Common Commands

```bash
# View what will be created/changed
terraform plan

# Apply changes (create/update infrastructure)
terraform apply

# Apply without confirmation prompt
terraform apply -auto-approve

# Destroy all infrastructure
terraform destroy

# View current outputs
terraform output

# View specific output
terraform output cognito_user_pool_id
terraform output -raw books_bucket_name  # Raw format (no quotes)

# List all resources
terraform state list

# Show details of specific resource
terraform state show aws_s3_bucket.books

# Validate configuration
terraform validate

# Format configuration files
terraform fmt
```

## Output Values You'll Need

```bash
# Save all outputs to file
terraform output > ../terraform-outputs.txt

# Get individual values for use in scripts
export BOOKS_BUCKET=$(terraform output -raw books_bucket_name)
export FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
export USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export CLIENT_ID=$(terraform output -raw cognito_client_id)
```

## Working with Multiple Environments

### Option 1: Separate Variable Files

```bash
# Development
terraform apply -var-file="terraform.tfvars.dev"

# Production
terraform apply -var-file="terraform.tfvars.prod"
```

### Option 2: Workspaces

```bash
# Create workspaces
terraform workspace new dev
terraform workspace new prod

# List workspaces
terraform workspace list

# Switch workspace
terraform workspace select dev
terraform apply

terraform workspace select prod
terraform apply

# Show current workspace
terraform workspace show
```

## Troubleshooting

```bash
# Unlock state (if locked due to crash)
terraform force-unlock <lock-id>

# Refresh state from AWS
terraform refresh

# Import existing resource
terraform import aws_s3_bucket.books existing-bucket-name

# Show current state
terraform show

# Remove resource from state (without deleting)
terraform state rm aws_s3_bucket.books

# View Terraform version
terraform version

# View provider versions
terraform providers
```

## Before SAM Deployment

After `terraform apply` succeeds, update your `samconfig.toml`:

```bash
# Get values
terraform output samconfig_parameters

# Edit SAM config
cd ..
nano samconfig.toml

# Use these parameter overrides:
parameter_overrides = [
    "BucketName=<books_bucket_name>",
    "CognitoUserPoolId=<cognito_user_pool_id>",
    "CognitoUserPoolArn=<cognito_user_pool_arn>",
    "CognitoClientId=<cognito_client_id>"
]
```

## Before Frontend Deployment

Update `frontend/config.js`:

```bash
# Get values
cd terraform
terraform output frontend_config

# Edit frontend config
cd ../frontend
nano config.js

# Use these values:
const COGNITO_CONFIG = {
    userPoolId: '<user_pool_id>',
    clientId: '<client_id>',
    region: '<region>'
};
```

## Cleanup

```bash
# DANGER: This deletes everything!

# 1. Empty S3 buckets first (Terraform can't delete non-empty buckets)
BOOKS_BUCKET=$(terraform output -raw books_bucket_name)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
aws s3 rm s3://$BOOKS_BUCKET --recursive
aws s3 rm s3://$FRONTEND_BUCKET --recursive

# 2. Destroy infrastructure
terraform destroy
```

## Common Issues

### Issue: "BucketAlreadyExists"
**Solution:** Bucket names must be globally unique. Change in `terraform.tfvars`:
```hcl
books_bucket_name = "my-unique-name-12345"
```

### Issue: "Error acquiring the state lock"
**Solution:** Another terraform process is running, or crashed. Force unlock:
```bash
terraform force-unlock <lock-id from error message>
```

### Issue: "Error: Invalid provider configuration"
**Solution:** Check AWS credentials:
```bash
aws sts get-caller-identity
# or
export AWS_PROFILE=your-profile-name
```

### Issue: Can't delete bucket - not empty
**Solution:** Empty bucket first:
```bash
aws s3 rm s3://bucket-name --recursive
```

## Best Practices

1. **Always run `terraform plan` before `apply`**
2. **Use version control** - commit `.tf` files, NOT `.tfvars` or state files
3. **Use remote state** for team collaboration
4. **Use workspaces or separate directories** for multiple environments
5. **Tag resources** for cost tracking
6. **Enable state locking** (automatic with S3 backend)
7. **Backup state files** regularly

## Integration with Other Tools

### After Terraform - Deploy with SAM

```bash
cd ..
sam build
sam deploy --profile craig-dev
```

### After Terraform - Deploy Frontend

```bash
FRONTEND_BUCKET=$(cd terraform && terraform output -raw frontend_bucket_name)
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/
```

### Get Frontend URL

```bash
cd terraform
terraform output frontend_bucket_website_url
```

## Version Compatibility

- **Terraform**: >= 1.0
- **AWS Provider**: ~> 5.0
- **AWS CLI**: >= 2.0 (for manual operations)

Check versions:
```bash
terraform version
aws --version
```

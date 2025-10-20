# Terraform Setup - Summary

## What Was Created

This Terraform configuration automates the creation of all AWS infrastructure needed for the Books Library application.

### 📁 Files Created

```
terraform/
├── main.tf                      # Main infrastructure definitions
├── variables.tf                 # Input variable declarations
├── outputs.tf                   # Output values after apply
├── terraform.tfvars.example     # Example configuration
├── .gitignore                   # Ignore state and sensitive files
├── README.md                    # Comprehensive documentation
└── QUICK_REFERENCE.md           # Quick command reference
```

### 🏗️ Infrastructure Components

**S3 Buckets (2)**
- Books bucket - Stores uploaded book files (.zip)
  - Versioning enabled
  - CORS configured
  - Private access (presigned URLs)
- Frontend bucket - Hosts static website
  - Static website hosting
  - Public read access
  - Versioning enabled

**DynamoDB Tables (3)**
- Books - Main book metadata
  - GSI: AuthorIndex for querying by author
- UserBooks - Per-user read status
- Authors - Author information

**Cognito**
- User Pool - Authentication
  - Email-based login
  - Password policy
  - Custom isAdmin attribute
- User Pool Client - Application configuration
- Optional Domain - Hosted UI

**IAM**
- Lambda Execution Role
  - DynamoDB permissions
  - S3 permissions
  - CloudWatch Logs permissions

### 💰 Cost Estimate

Monthly costs (typical personal use):
- **S3**: ~$0.50 - $2 (storage + requests)
- **DynamoDB**: Free tier covers most use (25GB, 2.5M reads)
- **Cognito**: Free (up to 50,000 MAUs)
- **Lambda**: Free tier covers most use (1M requests)

**Total: $1-5/month** for light personal use

## Quick Start

### 1. Configure
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit bucket names (must be globally unique)
```

### 2. Deploy Infrastructure
```bash
terraform init
terraform plan
terraform apply
```

### 3. Save Outputs
```bash
terraform output > ../terraform-outputs.txt
```

### 4. Configure SAM
Use Terraform outputs to update `samconfig.toml`:
```bash
terraform output samconfig_parameters
```

### 5. Deploy Backend
```bash
cd ..
sam build
sam deploy --profile craig-dev
```

### 6. Configure Frontend
Update `frontend/config.js` with Terraform outputs:
```bash
cd terraform
terraform output frontend_config
```

### 7. Deploy Frontend
```bash
FRONTEND_BUCKET=$(cd terraform && terraform output -raw frontend_bucket_name)
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/ --profile craig-dev
```

## Using the Makefile

Even easier - use the included Makefile:

```bash
# Full deployment (everything)
make deploy-all AWS_PROFILE=craig-dev

# Individual steps
make deploy-infra     # Terraform only
make deploy-backend   # SAM only
make deploy-frontend  # Frontend only

# Utilities
make create-admin-user
make test
make status
make info
```

## Key Features

✅ **Automated Setup** - One command creates all infrastructure
✅ **Repeatable** - Destroy and recreate anytime
✅ **Version Controlled** - Infrastructure as code
✅ **Multiple Environments** - Easy dev/staging/prod separation
✅ **Cost Effective** - Uses pay-per-use services
✅ **Secure** - Follows AWS best practices
✅ **Well Documented** - Comprehensive README files

## Benefits Over Manual Setup

| Aspect | Manual | Terraform |
|--------|--------|-----------|
| **Time** | 30-60 min | 5 min |
| **Errors** | Common | Rare |
| **Repeatability** | Manual notes | Automated |
| **Team Sharing** | Documentation | Code |
| **Cleanup** | Error-prone | One command |
| **Cost** | Same | Same |

## Important Notes

### Security
- ⚠️ Never commit `terraform.tfvars` to git
- ⚠️ State files contain sensitive data - secure them
- ✅ Use IAM roles with least privilege
- ✅ Enable MFA on AWS account

### Bucket Names
- Must be globally unique across ALL AWS accounts
- Use a unique prefix: `your-name-books-prod-abc123`
- Can't be changed after creation (requires destroy/recreate)

### State Management
- Default: Local state file (single developer)
- Production: Use S3 backend with DynamoDB locking
- Team: Share state via S3 (see terraform/README.md)

## Workflow Examples

### New Environment
```bash
# Copy config for new environment
cp terraform.tfvars.example terraform.tfvars.prod
nano terraform.tfvars.prod

# Deploy
terraform apply -var-file="terraform.tfvars.prod"
```

### Update Infrastructure
```bash
# Modify terraform.tfvars or *.tf files
terraform plan    # Review changes
terraform apply   # Apply changes
```

### Destroy Everything
```bash
# Empty S3 buckets
aws s3 rm s3://$(terraform output -raw books_bucket_name) --recursive
aws s3 rm s3://$(terraform output -raw frontend_bucket_name) --recursive

# Destroy infrastructure
terraform destroy
```

## Outputs Reference

After `terraform apply`, these outputs are available:

### For SAM Configuration
```bash
terraform output samconfig_parameters
```
Returns:
- BucketName
- CognitoUserPoolId
- CognitoUserPoolArn
- CognitoClientId

### For Frontend Configuration
```bash
terraform output frontend_config
```
Returns:
- userPoolId
- clientId
- region

### URLs
```bash
terraform output frontend_bucket_website_url  # Your app URL
```

### All Outputs
```bash
terraform output                    # All outputs
terraform output -json             # JSON format
terraform output > outputs.txt     # Save to file
```

## Troubleshooting

### "BucketAlreadyExists"
Bucket name taken - change in terraform.tfvars

### "AccessDenied"
Check AWS credentials:
```bash
aws sts get-caller-identity --profile craig-dev
```

### "Error locking state"
Another terraform running - wait or force unlock:
```bash
terraform force-unlock <lock-id>
```

### Resources Already Exist
Import existing resources:
```bash
terraform import aws_s3_bucket.books existing-bucket-name
```

## Next Steps

After Terraform deployment:

1. ✅ **Update SAM config** - Use terraform outputs
2. ✅ **Deploy Lambda** - `sam build && sam deploy`
3. ✅ **Configure S3 trigger** - Run configure-s3-trigger.sh
4. ✅ **Update frontend config** - Use terraform outputs
5. ✅ **Deploy frontend** - Sync to S3
6. ✅ **Create users** - Admin and regular users
7. ✅ **Test** - Log in and upload books

## Documentation

- 📖 **terraform/README.md** - Full documentation (60+ sections)
- 📝 **terraform/QUICK_REFERENCE.md** - Command cheat sheet
- 🚀 **docs/TERRAFORM_SETUP.md** - Complete workflow guide
- ⚙️ **Makefile** - Automated deployment scripts

## Support

Issues? Check:
1. Terraform plan output
2. AWS Console - CloudFormation
3. terraform/README.md - Troubleshooting section
4. State: `terraform state list`

## Best Practices

✅ Always run `terraform plan` before `apply`
✅ Use version control for `.tf` files
✅ Never commit `.tfvars` or state files
✅ Use workspaces for multiple environments
✅ Enable remote state for teams
✅ Tag resources for cost tracking
✅ Back up state files

## Comparison with SAM

| Feature | SAM | Terraform |
|---------|-----|-----------|
| Lambda Functions | ✅ | ❌ (use SAM) |
| S3 Buckets | ❌ | ✅ |
| DynamoDB | Limited | ✅ Full |
| Cognito | ❌ | ✅ |
| IAM Roles | ✅ | ✅ |
| API Gateway | ✅ | ❌ (use SAM) |

**Best approach:** Use both!
- Terraform: Infrastructure (S3, DynamoDB, Cognito, IAM)
- SAM: Lambda functions and API Gateway

This is exactly what we've set up! 🎉

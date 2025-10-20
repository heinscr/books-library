# Complete Setup Workflow with Terraform

This guide walks through the complete setup process using Terraform for infrastructure provisioning.

## Overview

The setup process consists of three main phases:

1. **Infrastructure Provisioning** (Terraform) - Create AWS resources
2. **Backend Deployment** (SAM) - Deploy Lambda functions
3. **Frontend Deployment** (S3) - Upload web application

## Phase 1: Infrastructure Provisioning

### Step 1.1: Install Terraform

```bash
# macOS
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform version
```

### Step 1.2: Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
# REQUIRED: Must be globally unique across ALL AWS accounts
books_bucket_name    = "my-books-library-prod-abc123"
frontend_bucket_name = "my-books-frontend-prod-abc123"

# Optional: Specify AWS profile
aws_profile = "craig-dev"

# Environment
environment = "prod"

# Cognito callback URLs (update with your domain after frontend deployment)
cognito_callback_urls = [
  "http://localhost:8000",
  "http://my-books-frontend-prod-abc123.s3-website.us-east-2.amazonaws.com"
]

cognito_logout_urls = [
  "http://localhost:8000",
  "http://my-books-frontend-prod-abc123.s3-website.us-east-2.amazonaws.com"
]
```

### Step 1.3: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Create the infrastructure
terraform apply
# Type 'yes' when prompted
```

This creates:
- ✅ 2 S3 buckets (books + frontend)
- ✅ 3 DynamoDB tables (Books, UserBooks, Authors)
- ✅ Cognito User Pool + Client
- ✅ IAM roles for Lambda

### Step 1.4: Save Configuration Values

```bash
# Save all outputs to a file
terraform output > ../terraform-outputs.txt

# Or get specific values
terraform output cognito_user_pool_id
terraform output cognito_client_id
terraform output books_bucket_name
terraform output frontend_bucket_name
```

**Important Values to Note:**
- Cognito User Pool ID
- Cognito Client ID
- Books bucket name
- Frontend bucket name
- Frontend website URL

## Phase 2: Backend Deployment (SAM)

### Step 2.1: Configure SAM

```bash
cd ..  # Back to project root
cp samconfig.toml.example samconfig.toml
```

Edit `samconfig.toml` using Terraform outputs:
```toml
[default.deploy.parameters]
stack_name = "books-library-prod"
region = "us-east-2"
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
    "BucketName=<books_bucket_name from terraform>",
    "CognitoUserPoolId=<cognito_user_pool_id from terraform>",
    "CognitoUserPoolArn=<cognito_user_pool_arn from terraform>",
    "CognitoClientId=<cognito_client_id from terraform>"
]
```

### Step 2.2: Build and Deploy Lambda Functions

```bash
# Build
sam build

# Deploy (use --profile if not using default AWS credentials)
sam deploy --profile craig-dev

# Note the API Gateway URL from outputs
```

**Save the API Gateway URL** - you'll need it for frontend configuration.

### Step 2.3: Configure S3 Trigger

```bash
cd scripts

# Set environment variables
export S3_BUCKET=$(cd ../terraform && terraform output -raw books_bucket_name)
export AWS_PROFILE=craig-dev

# Run configuration script
./configure-s3-trigger.sh
# When prompted, paste the S3TriggerFunction ARN from sam deploy outputs
```

## Phase 3: Frontend Deployment

### Step 3.1: Configure Frontend

```bash
cd ../frontend
cp config.js.example config.js
```

Edit `config.js` using Terraform outputs and SAM outputs:
```javascript
const COGNITO_CONFIG = {
    userPoolId: '<cognito_user_pool_id from terraform>',
    clientId: '<cognito_client_id from terraform>',
    region: 'us-east-2'  // Match your AWS region
};

const API_URL = '<API Gateway URL from sam deploy>/books';
```

### Step 3.2: Deploy Frontend to S3

```bash
# Get frontend bucket name from Terraform
FRONTEND_BUCKET=$(cd ../terraform && terraform output -raw frontend_bucket_name)

# Upload all frontend files
aws s3 sync . s3://$FRONTEND_BUCKET/ --profile craig-dev

# Verify
aws s3 ls s3://$FRONTEND_BUCKET/ --profile craig-dev
```

### Step 3.3: Get Frontend URL

```bash
cd ../terraform
terraform output frontend_bucket_website_url
```

Visit this URL in your browser!

## Phase 4: User Management

### Step 4.1: Create Admin User

```bash
# Get Cognito User Pool ID
USER_POOL_ID=$(cd terraform && terraform output -raw cognito_user_pool_id)

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --temporary-password TempAdmin123! \
  --profile craig-dev

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --password MySecurePass123! \
  --permanent \
  --profile craig-dev
```

### Step 4.2: Create Admin Group and Add User

```bash
# Create admins group
aws cognito-idp create-group \
  --user-pool-id $USER_POOL_ID \
  --group-name admins \
  --description "Administrators with upload and delete permissions" \
  --profile craig-dev

# Add user to admins group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --group-name admins \
  --profile craig-dev

# Set custom admin attribute (optional, for additional checks)
aws cognito-idp admin-update-user-attributes \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --user-attributes Name=custom:isAdmin,Value=true \
  --profile craig-dev
```

### Step 4.3: Create Regular Users

```bash
# Create regular user (no admin group)
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username user@example.com \
  --temporary-password TempUser123! \
  --profile craig-dev

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username user@example.com \
  --password UserSecurePass123! \
  --permanent \
  --profile craig-dev
```

## Phase 5: Populate Books (Optional)

### Step 5.1: Upload Books

```bash
# Get books bucket name
BOOKS_BUCKET=$(cd terraform && terraform output -raw books_bucket_name)

# Upload a book
aws s3 cp "Ernest Cline - Ready Player One.zip" \
  s3://$BOOKS_BUCKET/books/ \
  --profile craig-dev
```

**Note:** The S3 trigger will automatically add books to DynamoDB.

### Step 5.2: Migrate Existing Books

If you have existing books in another bucket:

```bash
cd scripts
export S3_BUCKET=$BOOKS_BUCKET
export SOURCE_BUCKET=my-old-books-bucket
python3 migrate-books.py
```

### Step 5.3: Populate Authors Table

```bash
cd scripts
export AWS_PROFILE=craig-dev
python3 populate-authors.py
```

## Complete Environment Variables Reference

For easy script execution, set these variables:

```bash
# Export all important values
export AWS_PROFILE=craig-dev
export AWS_REGION=us-east-2
export BOOKS_BUCKET=$(cd terraform && terraform output -raw books_bucket_name)
export FRONTEND_BUCKET=$(cd terraform && terraform output -raw frontend_bucket_name)
export USER_POOL_ID=$(cd terraform && terraform output -raw cognito_user_pool_id)
export CLIENT_ID=$(cd terraform && terraform output -raw cognito_client_id)

# Save to a file for later use
cat > .env.local << EOF
export AWS_PROFILE=craig-dev
export AWS_REGION=us-east-2
export BOOKS_BUCKET=$BOOKS_BUCKET
export FRONTEND_BUCKET=$FRONTEND_BUCKET
export USER_POOL_ID=$USER_POOL_ID
export CLIENT_ID=$CLIENT_ID
EOF

# Source it when needed
source .env.local
```

## Verification Checklist

After completing all phases, verify:

- [ ] Terraform infrastructure created successfully
- [ ] SAM deployment completed with API Gateway URL
- [ ] S3 trigger configured on books bucket
- [ ] Frontend deployed to S3
- [ ] Frontend URL accessible in browser
- [ ] Admin user created and added to admins group
- [ ] Can log in to frontend
- [ ] Can upload books (as admin)
- [ ] Can view books list
- [ ] Can download books
- [ ] Can mark books as read
- [ ] Can edit book metadata (as admin)
- [ ] Can delete books (as admin)

## Troubleshooting

### Terraform Issues

**"BucketAlreadyExists":**
```bash
# Bucket names must be globally unique - change in terraform.tfvars
books_bucket_name = "my-unique-name-$(uuidgen | tr '[:upper:]' '[:lower:]')"
```

**See current resources:**
```bash
cd terraform
terraform state list
terraform show
```

### SAM Deployment Issues

**"Unable to locate credentials":**
```bash
sam deploy --profile craig-dev
```

**"Parameter validation failed":**
- Verify all parameters in `samconfig.toml` match Terraform outputs

### Frontend Issues

**"Cannot reach API":**
- Verify API_URL in `config.js` matches SAM output
- Check CORS configuration in API Gateway
- Verify Cognito configuration

**"Authentication failed":**
- Verify Cognito User Pool ID and Client ID
- Check callback URLs in Cognito match your frontend URL

### S3 Trigger Issues

**Books not appearing after upload:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/books-library-prod-S3TriggerFunction --follow

# Manually test trigger
aws lambda invoke \
  --function-name books-library-prod-S3TriggerFunction \
  --payload file://test-event.json \
  response.json
```

## Updating the Deployment

### Update Infrastructure

```bash
cd terraform
# Modify terraform.tfvars or *.tf files
terraform plan
terraform apply
```

### Update Lambda Functions

```bash
cd ..
sam build
sam deploy --profile craig-dev
```

### Update Frontend

```bash
cd frontend
aws s3 sync . s3://$FRONTEND_BUCKET/ --profile craig-dev
```

## Destroying Everything

⚠️ **Warning:** This deletes all resources and data!

```bash
# Delete S3 bucket contents first
aws s3 rm s3://$BOOKS_BUCKET --recursive --profile craig-dev
aws s3 rm s3://$FRONTEND_BUCKET --recursive --profile craig-dev

# Delete SAM stack
sam delete --stack-name books-library-prod --profile craig-dev

# Delete Terraform infrastructure
cd terraform
terraform destroy
```

## Cost Optimization

**Development:**
```hcl
# terraform.tfvars
enable_point_in_time_recovery = false  # Save on DynamoDB costs
```

**Production:**
```hcl
# terraform.tfvars
enable_point_in_time_recovery = true   # Enable backups
```

Consider:
- S3 Lifecycle policies to move old files to Glacier
- DynamoDB on-demand pricing for variable traffic
- CloudFront for frontend (better performance + caching)
- Enable S3 Intelligent-Tiering

## Next Steps

1. **Custom Domain:** Set up Route 53 + CloudFront
2. **CI/CD:** GitHub Actions for automated deployments
3. **Monitoring:** CloudWatch dashboards and alarms
4. **Backups:** Enable automated DynamoDB backups
5. **Security:** Review IAM policies, enable MFA
6. **Testing:** Run integration tests against deployed environment

## Support

See detailed documentation:
- [`terraform/README.md`](../terraform/README.md) - Infrastructure details
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - Manual deployment guide
- [`CONFIGURATION.md`](CONFIGURATION.md) - Configuration reference
- [`TESTING.md`](TESTING.md) - Testing guide

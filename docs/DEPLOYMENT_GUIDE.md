# Deployment Guide

> **Note**: This guide describes manual deployment steps. For automated infrastructure setup, see [`TERRAFORM_SETUP.md`](TERRAFORM_SETUP.md) which provides a complete, automated workflow using Terraform + SAM.

## Deployment Options

### Option A: Automated with Terraform (Recommended)
See [`TERRAFORM_SETUP.md`](TERRAFORM_SETUP.md) for:
- Automated infrastructure provisioning
- Complete step-by-step workflow
- One-command deployment with Makefile
- Best practices and cost optimization

### Option B: Manual Deployment (This Guide)
This guide covers manual deployment steps for users who:
- Already have infrastructure set up
- Want fine-grained control
- Are updating an existing deployment

---

## Manual Deployment Overview

```bash
# If using a named profile (not default), set the environment variable
export AWS_PROFILE=your-profile-name

# Verify your AWS identity
aws sts get-caller-identity

# The scripts will use the profile from:
# 1. AWS_PROFILE environment variable (if set)
# 2. default profile (if AWS_PROFILE not set)
```

## Prerequisites
- AWS SAM CLI installed and configured
- AWS CLI configured with your AWS profile
- Python 3.12 (for migration script)
- boto3 installed (`pip install boto3`)

## Step-by-Step Deployment

### 1. Build the SAM Application
```bash
cd /home/craig/projects/books
sam build
```

This compiles the Lambda functions and prepares them for deployment.

### 2. Deploy to AWS
```bash
sam deploy
```

This will:
- Create the DynamoDB `Books` table
- Deploy all Lambda functions (BooksFunction, GetBookFunction, UpdateBookFunction, S3TriggerFunction)
- Update the API Gateway with PATCH endpoint

**Important**: Note the outputs, especially:
- API URL
- S3TriggerFunction ARN (needed for S3 configuration)

### 3. Configure S3 Trigger (Manual Step)
Since the S3 bucket already exists, we need to manually configure the trigger:

```bash
./scripts/configure-s3-trigger.sh
```

When prompted, enter the S3TriggerFunction ARN from the SAM deployment outputs.

This script will:
- Grant S3 permission to invoke the Lambda function
- Configure S3 bucket notifications to trigger on .zip uploads in `books/` folder

### 4. Migrate Existing Books to DynamoDB
Run the migration script to populate DynamoDB with books currently in S3:

```bash
python3 scripts/migrate-books.py
```

This will:
- Scan all .zip files in `s3://YOUR_BUCKET/books/`
- Create DynamoDB records for each book
- Extract author from filename if format is "Author - Title.zip"
- Skip books that already exist in DynamoDB

### 5. Deploy Updated Frontend

**Option A: Using Makefile (recommended)**
```bash
# With Terraform installed
make update-frontend AWS_PROFILE=your-profile

# Without Terraform
make update-frontend AWS_PROFILE=your-profile FRONTEND_BUCKET=your-bucket
```

**Option B: Manual deployment**
```bash
# Upload frontend files
aws s3 sync frontend/ s3://YOUR_BUCKET/books-app/ --profile your-profile

# Upload API docs (optional)
aws s3 sync docs/ s3://YOUR_BUCKET/books-app/api-docs/ --exclude "*.md" --profile your-profile

# Get CloudFront distribution ID
aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[?DomainName=='YOUR_BUCKET.s3.amazonaws.com']].Id" --output text

# Invalidate CloudFront cache (replace <DIST_ID> with actual ID)
aws cloudfront create-invalidation \
    --distribution-id <DIST_ID> \
    --paths "/books-app/*"
```

### 6. Verify Deployment

#### Test API Endpoints
```bash
# Get API URL from SAM outputs
API_URL="https://xxx.execute-api.us-east-2.amazonaws.com/Prod"

# Get a Cognito token (login via web UI and check localStorage.idToken)
TOKEN="your-id-token"

# Test list books
curl -H "Authorization: $TOKEN" $API_URL/books

# Test get book
curl -H "Authorization: $TOKEN" $API_URL/books/SomeBook

# Test update read status
curl -X PATCH \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"read": true}' \
    $API_URL/books/SomeBook
```

#### Test S3 Trigger
Upload a test book to verify automatic DynamoDB population:

```bash
# Upload a test book
aws s3 cp /path/to/test-book.zip s3://YOUR_BUCKET/books/

# Check DynamoDB for the new record
aws dynamodb get-item \
    --table-name Books \
    --key '{"id": {"S": "test-book"}}' \
    --region us-east-2
```

#### Test Frontend
1. Navigate to https://your-domain.com
2. Login with your Cognito credentials
3. Verify books are displayed with:
   - Book name
   - Author (if available)
   - Created date
   - Read toggle
4. Test marking a book as read
5. Refresh page - read status should persist
6. Test downloading a book

## Rollback Plan

If issues occur, you can rollback:

### Rollback Frontend Only
```bash
# Revert to previous version from git
git checkout HEAD~1 frontend/app.js frontend/styles.css

# Deploy old version
aws s3 sync frontend/ s3://YOUR_BUCKET/books-app/ --profile your-profile

# Invalidate cache
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/books-app/*" --profile your-profile
```

### Rollback Entire Stack
```bash
# Delete the SAM stack
sam delete --stack-name books

# Or delete via CloudFormation
aws cloudformation delete-stack --stack-name books --region us-east-2

# Note: DynamoDB table will be deleted (data loss)
# Consider backing up DynamoDB before rollback if needed
```

## Troubleshooting

### Books not appearing in UI
- Check DynamoDB table has records: `aws dynamodb scan --table-name Books --region us-east-2`
- Check Lambda logs: CloudWatch → Log Groups → `/aws/lambda/books-BooksFunction-*`
- Check browser console for API errors
- Verify token is valid (not expired)

### S3 Trigger not working
- Check Lambda permissions: `aws lambda get-policy --function-name <function-arn>`
- Check S3 bucket notification config: `aws s3api get-bucket-notification-configuration --bucket YOUR_BUCKET`
- Check Lambda logs after uploading: CloudWatch → `/aws/lambda/books-S3TriggerFunction-*`

### Read status not saving
- Check CORS headers include PATCH method
- Check browser console for 401/403 errors
- Verify UpdateBookFunction has DynamoDB write permissions
- Check Lambda logs: `/aws/lambda/books-UpdateBookFunction-*`

### API Gateway 403 errors
- Verify Cognito token in Authorization header
- Check token not expired (1 hour lifetime)
- Verify API Gateway authorizer configuration

## Performance Considerations

### DynamoDB
- **Billing Mode**: PAY_PER_REQUEST (on-demand)
  - No capacity planning needed
  - Pay per request
  - Good for variable/unpredictable traffic
  - Consider switching to PROVISIONED if traffic is consistent and high

### Lambda
- **Memory**: All functions set to 128 MB (minimum)
  - Adjust if needed based on CloudWatch metrics
  - Monitor Duration and Memory Used metrics

### API Gateway
- **Throttling**: Default AWS limits
  - 10,000 requests per second
  - 5,000 concurrent requests
  - Should be sufficient for personal library

## Cost Estimates

Assuming 10 books, 100 reads/month, 10 downloads/month:

- **DynamoDB**: 
  - Storage: $0.25/GB/month × 0.001 GB = ~$0.00
  - Reads: $0.25/million × 100 = ~$0.00
  - Writes: $1.25/million × 10 = ~$0.00
  - **Total: < $0.01/month**

- **Lambda**:
  - 110 invocations/month
  - 128 MB memory × 100ms avg duration
  - **Total: < $0.01/month** (within free tier)

- **API Gateway**:
  - 110 requests/month
  - **Total: < $0.01/month** (within free tier)

**Estimated Total: < $0.05/month** (mostly S3 and CloudFront)

## Next Steps

After successful deployment:

1. **Monitor CloudWatch Logs** for first 24 hours
2. **Backup DynamoDB** if you want to preserve read status
   - Use AWS Backup or on-demand backups
3. **Add more metadata** to books as needed (author, tags, etc.)
4. **Consider adding**:
   - Search functionality
   - Filtering by author/read status
   - Book covers via metadata
   - Reading statistics

## Maintenance

### Regular Tasks
- **Monitor DynamoDB table size**: Should grow slowly
- **Check Lambda errors**: Review CloudWatch Logs weekly
- **Update books**: Use S3 upload (triggers automatic DynamoDB update)

### Backup Strategy
```bash
# Create on-demand backup
aws dynamodb create-backup \
    --table-name Books \
    --backup-name Books-Backup-$(date +%Y%m%d) \
    --region us-east-2

# Enable point-in-time recovery (continuous backups)
aws dynamodb update-continuous-backups \
    --table-name Books \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --region us-east-2
```

### Cleanup (if needed)
```bash
# Delete all items in DynamoDB (keep table)
# WARNING: This deletes all data!
aws dynamodb scan --table-name Books --attributes-to-get "id" --region us-east-2 \
    --query "Items[*].id.S" --output text | \
    xargs -I {} aws dynamodb delete-item --table-name Books --key '{"id":{"S":"{}"}}' --region us-east-2
```

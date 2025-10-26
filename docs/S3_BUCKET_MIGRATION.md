# S3 Bucket Migration Guide

This document describes the migration from the old S3 bucket structure to a dedicated bucket for the Books Library application.

## Migration Overview

**Date:** October 19, 2025  
**Old Bucket:** `s3://old-bucket/books/`  
**New Bucket:** `s3://new-bucket/books/`  
**Status:** ✅ Completed

## Why Migrate?

The books were originally stored in a shared bucket alongside other application data. This migration moves them to a dedicated bucket for:

1. **Better organization** - Clear separation of book storage from other resources
2. **Easier management** - Dedicated bucket policies and access controls
3. **Improved scalability** - Independent bucket configuration and limits
4. **Cleaner infrastructure** - Single-purpose buckets are easier to maintain

## What Was Migrated

- **175 book files** (.zip format) copied to new bucket
- **174 DynamoDB records** updated with new S3 URLs
- **Lambda functions** redeployed with new bucket configuration
- **Bucket policies** configured for presigned URL access
- **CORS configuration** added for browser uploads
- **S3 trigger** configured for auto-ingestion

## Migration Steps Performed

### 1. Create New Bucket
```bash
aws s3 mb s3://new-bucket --region us-east-2
```

### 2. Copy Files to New Bucket
```bash
aws s3 sync \
  s3://old-bucket/books/ \
  s3://new-bucket/books/ \
  --region us-east-2
```

**Result:** 175 files successfully copied

### 3. Update DynamoDB Records
Used migration script to update all S3 URLs in the Books table:
```bash
OLD_BUCKET=old-bucket NEW_BUCKET=new-bucket AWS_REGION=us-east-2 \
  python3 scripts/migrate-bucket.py
```

**Result:** 174 book records updated

### 4. Update Lambda Configuration
Updated `samconfig.toml`:
```toml
parameter_overrides = [
    "BucketName=new-bucket",
    # ... other params
]
```

Deployed Lambda functions:
```bash
sam build && sam deploy
```

### 5. Configure Bucket Permissions

#### Public Access Block Settings
```bash
aws s3api put-public-access-block \
  --bucket new-bucket \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

#### Bucket Policy
Created policy to allow:
- Lambda execution roles to generate presigned URLs
- Public access via presigned URLs (REST-QUERY-STRING auth)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowLambdaPresignedUrls",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::918213481336:role/bbbbbbabd-GetBookFunctionRole-*"
                ]
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::new-bucket/books/*"
        },
        {
            "Sid": "AllowPublicReadViaPresignedUrl",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::new-bucket/books/*",
            "Condition": {
                "StringEquals": {
                    "s3:authType": "REST-QUERY-STRING"
                }
            }
        }
    ]
}
```

#### CORS Configuration
```json
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT"],
            "AllowedOrigins": ["*"]
        }
    ]
}
```

### 6. Configure S3 Trigger
Set up Lambda trigger for automatic book ingestion when files are uploaded to the new bucket.

## Code Changes

### Lambda Handler Updates
1. **Regional Endpoint Configuration** - S3 client now configured with `endpoint_url` to generate presigned URLs with regional endpoints from the start, avoiding signature mismatches
2. **Simplified Code** - Removed unnecessary URL string manipulation and debug logging
3. **Documentation** - Updated comments and documentation

### Key Fix: Regional Endpoint
**Problem:** Generic S3 endpoints (`bucket.s3.amazonaws.com`) cause redirects to regional endpoints, breaking presigned URL signatures.

**Solution:** Configure the S3 client to use the regional endpoint from the start:
```python
# Initialize S3 client with regional endpoint
s3_client = boto3.client(
    "s3", 
    region_name="us-east-2",
    endpoint_url="https://s3.us-east-2.amazonaws.com",
    config=Config(signature_version="s3v4")
)
```

This ensures presigned URLs are generated with the correct endpoint, so signatures are valid without any URL manipulation.

## Issues Encountered and Resolved

### 1. Presigned URL Signature Mismatches
**Symptom:** Downloads failed with `SignatureDoesNotMatch` error

**Root Cause:** Presigned URLs were generated with generic endpoint but bucket exists in specific region, causing redirects that invalidate signatures

**Fix:** Configure S3 client with regional endpoint URL so presigned URLs are generated correctly from the start

### 2. CORS Policy Blocks on Upload
**Symptom:** Browser uploads failed with CORS policy error

**Root Cause:** New bucket had no CORS configuration

**Fix:** Applied CORS rules to allow GET and PUT from any origin

### 3. Bucket Policy Missing
**Symptom:** Presigned URLs couldn't be accessed even with correct signatures

**Root Cause:** New bucket had no bucket policy allowing presigned URL access

**Fix:** Created bucket policy explicitly allowing presigned URL access

## Verification

### Backend Tests
All 58 unit tests passing:
```bash
.venv/bin/python -m pytest tests/test_handler.py -v
# Result: 58 passed
```

### Manual Testing
- ✅ Books list loads correctly
- ✅ Book downloads work via presigned URLs
- ✅ Book uploads work via presigned PUT URLs
- ✅ Metadata updates work correctly
- ✅ Auto-ingestion triggers on new uploads

## Rollback Procedure

If needed, rollback can be performed by:

1. Reverting `samconfig.toml` to old bucket name
2. Running migration script in reverse:
   ```bash
   OLD_BUCKET=new-bucket NEW_BUCKET=old-bucket AWS_REGION=us-east-2 \
     python3 scripts/migrate-bucket.py
   ```
3. Redeploying Lambda functions
4. Updating bucket policies on old bucket

## Future Considerations

### Old Bucket Cleanup
The old bucket still contains the original files. After confirming the migration is stable:

```bash
# List files in old location
aws s3 ls s3://old-bucket/books/ --recursive

# Optional: Delete old files (BE CAREFUL!)
# aws s3 rm s3://old-bucket/books/ --recursive
```

⚠️ **Note:** Keep old files for at least 30 days as a backup before deletion.

### Cost Optimization
- Consider lifecycle policies for old book versions
- Implement S3 Intelligent-Tiering for infrequently accessed books
- Monitor bucket storage growth and costs

## Tools and Scripts

### Migration Script
`scripts/migrate-bucket.py` - Automates DynamoDB URL updates

**Usage:**
```bash
OLD_BUCKET=your-old-bucket NEW_BUCKET=your-new-bucket AWS_REGION=us-east-2 \
  python3 scripts/migrate-bucket.py
```

**Features:**
- Scans all books in DynamoDB
- Identifies books needing migration
- Confirms before making changes
- Reports success/failure counts
- Handles errors gracefully

## Related Documentation

- [Configuration Guide](CONFIGURATION.md) - SAM and frontend configuration
- [Manual Deployment Guide](MANUAL_DEPLOYMENT.md) - Lambda deployment process
- [Scripts README](scripts/README.md) - All available scripts including migration

## Lessons Learned

1. **Regional Endpoints Matter** - Always use regional S3 endpoints for presigned URLs
2. **Bucket Policies Are Required** - Even with IAM permissions, bucket policies are needed for presigned URL access
3. **CORS Configuration** - Must be explicitly set on new buckets for browser uploads
4. **Test Presigned URLs** - Always test the full URL flow (generation → access) after migration
5. **Public Access Settings** - Default AWS settings block public access, which prevents presigned URLs from working

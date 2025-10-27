# Scripts Directory

This directory contains helper scripts for deploying and maintaining the Books Library application.

## Deployment

### `deploy.sh`
Unified deployment script for consistent frontend and backend deployment.

**Quick Usage:**
```bash
# Setup (one-time)
cp .deploy-config.example .deploy-config
# Edit .deploy-config with your values

# Deploy
./scripts/deploy.sh --frontend --invalidate
./scripts/deploy.sh --backend
./scripts/deploy.sh --all --invalidate
```

**For complete deployment guide, see [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)**

---

## Maintenance Scripts

### `populate-authors.py`
Automatically populates missing author names in DynamoDB by looking up book metadata from Google Books API and Open Library API.

**Usage:**
```bash
# Dry run - see what would be updated without making changes
pipenv run python scripts/populate-authors.py --dry-run --profile YOUR_PROFILE

# Actually update the database
pipenv run python scripts/populate-authors.py --profile YOUR_PROFILE

# Use default AWS profile
pipenv run python scripts/populate-authors.py
```

**Features:**
- Scans all books in DynamoDB for missing authors
- Queries Google Books API first, falls back to Open Library
- Rate-limited to be respectful of APIs (1 request/second)
- Shows progress with clear output
- Provides summary of successes and failures
- Lists books that couldn't be found for manual review

**Notes:**
- Success rate is typically 99%+
- Multi-volume works may need manual updates (e.g., "Volume 1 of 3")
- Requires `requests` library: `pipenv install --dev`

**When to run:**
- After uploading many books without author metadata
- After initial migration from S3
- Periodically to fill in missing information

---

### `configure-s3-trigger.sh`
Configures S3 bucket notifications to trigger the Lambda function when books are uploaded.

**Usage:**
```bash
# Use defaults (profile: default, region: us-east-2, bucket: YOUR_BUCKET)
./configure-s3-trigger.sh

# Use custom AWS profile
AWS_PROFILE=my-profile ./configure-s3-trigger.sh

# Override all settings
AWS_PROFILE=prod AWS_REGION=us-west-2 S3_BUCKET=my-books ./configure-s3-trigger.sh
```

**Environment Variables:**
- `AWS_PROFILE`: AWS profile name (default: `default`)
- `AWS_REGION`: AWS region (default: `us-east-2`)
- `S3_BUCKET`: S3 bucket name (default: `YOUR_BUCKET`)

**When to run:**
- After initial SAM deployment
- When changing the S3 bucket
- When recreating the Lambda function

---

### `migrate-books.py`
Migrates existing books from S3 to DynamoDB.

**Usage:**
```bash
# Use defaults
python3 migrate-books.py

# Use custom AWS profile
AWS_PROFILE=my-profile python3 migrate-books.py

# Override all settings
AWS_PROFILE=prod \
AWS_REGION=us-west-2 \
S3_BUCKET=my-books \
BOOKS_PREFIX=books/ \
DYNAMODB_TABLE=Books \
python3 migrate-books.py
```

**Environment Variables:**
- `AWS_PROFILE`: AWS profile name (default: `default`)
- `AWS_REGION`: AWS region (default: `us-east-2`)
- `S3_BUCKET`: S3 bucket name (default: `YOUR_BUCKET`)
- `BOOKS_PREFIX`: S3 prefix for books (default: `books/`)
- `DYNAMODB_TABLE`: DynamoDB table name (default: `Books`)

**When to run:**
- After initial DynamoDB table deployment
- To populate table with existing books in S3
- To re-sync if DynamoDB table is recreated

### `backfill-covers.py`
Backfills book cover images from Google Books API for existing books.

**Usage:**
```bash
# Use defaults
export AWS_PROFILE=your-profile
python3 backfill-covers.py

# With verbose output
python3 backfill-covers.py --verbose
```

**Features:**
- Queries Google Books API for cover images
- Updates DynamoDB with cover URLs
- Skips books that already have covers
- Rate limiting to avoid API throttling
- Progress reporting

**When to run:**
- After initial migration of books without covers
- Periodically to update missing cover images
- After author metadata corrections

---

### `lint.sh`
Runs code quality checks and linting on the codebase.

**Usage:**
```bash
./lint.sh
```

**Checks:**
- Python code style (ruff)
- Type checking (pyright)
- Import sorting
- Code formatting

**When to run:**
- Before committing code changes
- As part of CI/CD pipeline
- Before pull requests

---

### `migrate-bucket.py`
Migrates S3 URLs in DynamoDB when moving books to a new S3 bucket.

**Usage:**
```bash
# Set environment variables with your bucket names
OLD_BUCKET=my-old-bucket NEW_BUCKET=my-new-bucket AWS_REGION=us-east-2 python3 migrate-bucket.py

# With venv
OLD_BUCKET=my-old-bucket NEW_BUCKET=my-new-bucket AWS_REGION=us-east-2 .venv/bin/python scripts/migrate-bucket.py
```

**Environment Variables:**
- `OLD_BUCKET`: Source bucket name (required)
- `NEW_BUCKET`: Destination bucket name (required)
- `AWS_REGION`: AWS region (default: us-east-2)
- `DYNAMODB_TABLE`: DynamoDB table name (default: Books)

**What it does:**
1. Scans all books in DynamoDB
2. Identifies books with old bucket URLs
3. Confirms migration with user
4. Updates each book's `s3_url` field to point to new bucket
5. Reports success/failure counts

**When to run:**
- After copying books to a new S3 bucket
- Before deploying Lambda functions with new bucket configuration
- When consolidating multiple buckets

**What it does:**
1. Scans all `.zip` files in S3 bucket under the specified prefix
2. Creates DynamoDB records for each book with metadata:
   - `id`: Filename without .zip extension
   - `s3_url`: Full S3 URL
   - `name`: Human-friendly name (from filename)
   - `author`: Extracted from filename if format is "Author - Title.zip"
   - `size`: File size in bytes
   - `created`: S3 LastModified timestamp
   - `read`: Defaults to `false`
3. Skips books that already exist in DynamoDB
4. Prints summary of migration results

**Requirements:**
- Python 3.x
- boto3: `pip install boto3`
- AWS credentials configured

---

## Common Workflows

### Initial Deployment
```bash
# 1. Deploy SAM stack
sam build
sam deploy

# 2. Configure S3 trigger (when prompted, enter Lambda ARN from SAM outputs)
./scripts/configure-s3-trigger.sh

# 3. Migrate existing books
python3 scripts/migrate-books.py
```

### Using Custom AWS Profile
```bash
# Set profile for entire session
export AWS_PROFILE=my-profile

# Then run commands normally
sam deploy
./scripts/configure-s3-trigger.sh
python3 scripts/migrate-books.py
```

### Testing Migration (Dry Run)
The migration script doesn't have a dry-run mode, but you can:

1. Check what books would be migrated:
```bash
aws s3 ls s3://YOUR_BUCKET/books/ --recursive | grep ".zip$"
```

2. Check current DynamoDB contents:
```bash
aws dynamodb scan --table-name Books --region us-east-2
```

3. Run migration (it skips existing books automatically)
```bash
python3 scripts/migrate-books.py
```

### Re-running Migration
Safe to run multiple times - the script automatically skips books that already exist in DynamoDB:

```bash
python3 scripts/migrate-books.py
```

Expected output:
```
⏭️  Skipping (already exists): Book1.zip
⏭️  Skipping (already exists): Book2.zip
✅ Migrated: Book3.zip
```

## Troubleshooting

### Permission Errors
Ensure your AWS profile has necessary permissions:
- S3: `s3:ListBucket`, `s3:GetObject`
- DynamoDB: `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:Scan`
- Lambda: `lambda:AddPermission`, `lambda:GetPolicy`
- S3 Notifications: `s3:PutBucketNotification`, `s3:GetBucketNotification`

### Script Not Executable
```bash
chmod +x scripts/configure-s3-trigger.sh scripts/migrate-books.py
```

### Python boto3 Not Found
```bash
pip install boto3
# or
pip3 install boto3
```

### AWS Profile Not Found
```bash
# List available profiles
aws configure list-profiles

# Set correct profile
export AWS_PROFILE=your-profile-name
```

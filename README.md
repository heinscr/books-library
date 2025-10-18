# Books Library - Serverless Book Management System

A serverless book management system built with AWS Lambda, API Gateway, Cognito, DynamoDB, S3, and CloudFront. Upload books to S3, browse them through a web interface, and download via secure presigned URLs. Book metadata is stored in DynamoDB for fast access and persistent read status tracking.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  your-domain.com (CloudFront + S3)                              │
│  ├─ Frontend: Vanilla JS SPA with Cognito auth                  │
│  └─ Serves from: s3://YOUR_BUCKET/books-app/                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ (Authenticated API Calls)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  API Gateway (REST API)                                         │
│  ├─ Authorization: AWS Cognito (JWT tokens)                     │
│  └─ Routes:                                                     │
│     ├─ GET /books - List all books with metadata                │
│     ├─ GET /books/{id} - Get presigned download URL             │
│     └─ PATCH /books/{id} - Update book metadata (read status)   │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ BooksFunction│  │GetBookFunc   │  │UpdateBookFunc│
│ (List books) │  │ (Download)   │  │(Update meta) │
└──────────────┘  └──────────────┘  └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                ┌──────────────────────┐
                │  DynamoDB Table      │
                │  Books (metadata)    │
                │  ├─ id, name, author │
                │  ├─ size, created    │
                │  └─ read status      │
                └──────────────────────┘
                            
┌──────────────────────┐           ┌──────────────────────┐
│  S3 Bucket           │ ─trigger─>│ S3TriggerFunction    │
│  YOUR_BUCKET/books/  │           │ (Auto-add to DB)     │
│  (Private .zip files)│           └──────────────────────┘
└──────────────────────┘
```

## ✨ Features

### Frontend
- 📱 Clean, responsive web interface
- 🔐 AWS Cognito authentication with auto token refresh
- 📚 Auto-loading book list on login
- ⬇️ One-click downloads via presigned URLs
- ✅ Read/Unread status tracking (synced with backend)
- 📊 File size display in MB
- 👤 Author extraction from "Author - Title.zip" format
- 🎨 Modern card-based grid layout
- 🔔 Toast notifications (no layout shift)

### Backend
- 🚀 Serverless architecture (AWS Lambda + DynamoDB)
- 🔒 Cognito-protected API endpoints
- 📦 DynamoDB for fast metadata access (no S3 listing required)
- 🔗 Generates secure presigned URLs (1-hour expiration)
- 🛡️ Path traversal protection
- 📊 Sorted by date (newest first)
- 🌐 CORS enabled for cross-origin requests
- ⚡ Auto-ingestion: S3 trigger automatically adds new books to DynamoDB
- 💾 Persistent read status across devices

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Python 3.12+
- An S3 bucket for storing books
- A Cognito User Pool set up

### 1. Configure AWS Profile

```bash
# If using a named profile (not default), set the environment variable
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-east-2  # or your preferred region

# Verify your AWS identity
aws sts get-caller-identity
```

### 2. Clone and Configure

```bash
git clone https://github.com/heinscr/books-library.git
cd books-library
```

**Configuration:**
See [`CONFIGURATION.md`](CONFIGURATION.md) for detailed setup instructions.

Quick setup:
```bash
# 1. Copy and configure SAM deployment settings
cp samconfig.toml.example samconfig.toml
# Edit samconfig.toml with your AWS resource values

# 2. Copy and configure frontend
cp frontend/config.js.example frontend/config.js
# Edit frontend/config.js with your Cognito and API details
```

### 3. Deploy Backend

```bash
# Build the SAM application
sam build

# Deploy (first time use --guided, after that just sam deploy)
sam deploy --guided
```

Note the API endpoint URL from the outputs.

### 4. Configure S3 Trigger and Migrate Data

```bash
# Configure S3 to trigger Lambda on book uploads
# You'll be prompted for the S3TriggerFunction ARN from the deployment
cd scripts
AWS_PROFILE=your-profile-name AWS_REGION=us-east-2 ./configure-s3-trigger.sh

# Migrate existing books from S3 to DynamoDB
AWS_PROFILE=your-profile-name AWS_REGION=us-east-2 python3 migrate-books.py
```

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

### 5. Configure Frontend

Update `frontend/app.js` with your values:
```javascript
const COGNITO_CONFIG = {
    userPoolId: 'YOUR_USER_POOL_ID',
    clientId: 'YOUR_CLIENT_ID',
    region: 'YOUR_COGNITO_REGION'  // Usually us-east-1
};

const API_URL = 'YOUR_API_GATEWAY_URL/books';  // From sam deploy output
```

### 6. Upload Frontend to S3

```bash
aws s3 cp frontend/ s3://YOUR_BUCKET/books-app/ --recursive

# If using CloudFront, invalidate the cache
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### 7. Add Books

Upload `.zip` files to your S3 bucket (they'll auto-populate in DynamoDB via S3 trigger):
```bash
aws s3 cp "Author - Book Title.zip" s3://YOUR_BUCKET/books/
```

**Filename Format**: For author extraction, use: `"Author Name - Book Title.zip"`

### 8. Create Users

```bash
aws cognito-idp admin-create-user \
  --user-pool-id YOUR_USER_POOL_ID \
  --username user@example.com \
  --temporary-password TempPass123!

aws cognito-idp admin-set-user-password \
  --user-pool-id YOUR_USER_POOL_ID \
  --username user@example.com \
  --password YourPassword123! \
  --permanent
```

## 📁 Project Structure

```
.
├── gateway_backend/          # Lambda function code
│   ├── handler.py           # API handlers (list, get, update, S3 trigger)
│   └── __init__.py
├── frontend/                # Web interface
│   ├── index.html          # Main HTML
│   ├── app.js              # JavaScript logic with Cognito auth
│   └── styles.css          # Styling
├── scripts/                # Deployment helper scripts
│   ├── configure-s3-trigger.sh  # Set up S3 Lambda trigger
│   ├── migrate-books.py         # Migrate S3 books to DynamoDB
│   └── README.md                # Scripts documentation
├── tests/                  # Unit tests
│   └── test_handler.py
├── template.yaml           # SAM CloudFormation template
├── samconfig.toml         # SAM deployment config
├── Pipfile                # Python dependencies
├── DEPLOYMENT_GUIDE.md    # Detailed deployment instructions
├── DYNAMODB_MIGRATION.md  # DynamoDB migration documentation
└── README.md              # This file
```

## 🔧 API Endpoints

### GET /books
Lists all books from DynamoDB with complete metadata.

**Headers:**
- `Authorization`: Cognito JWT token

**Response:**
```json
[
  {
    "id": "Book Title",
    "name": "Book Title",
    "author": "Author Name",
    "size": 1048576,
    "created": "2025-10-17T12:00:00+00:00",
    "read": false,
    "s3_url": "s3://bucket/books/Book Title.zip"
  }
]
```

### GET /books/{id}
Generates a presigned URL for downloading a specific book and returns metadata.

**Headers:**
- `Authorization`: Cognito JWT token

**Path Parameters:**
- `id`: Book ID (URL-encoded, matches DynamoDB id field)

**Response:**
```json
{
  "id": "Book Title",
  "name": "Book Title",
  "author": "Author Name",
  "size": 1048576,
  "created": "2025-10-17T12:00:00+00:00",
  "read": false,
  "downloadUrl": "https://s3.amazonaws.com/...",
  "expiresIn": 3600
}
```

### PATCH /books/{id}
Updates book metadata (currently supports read status).

**Headers:**
- `Authorization`: Cognito JWT token

**Path Parameters:**
- `id`: Book ID (URL-encoded)

**Body:**
```json
{
  "read": true
}
```

**Response:**
```json
{
  "id": "Book Title",
  "name": "Book Title",
  "read": true,
  ...
}
```

## 🧪 Testing

Run unit tests:
```bash
python -m pytest tests/
```

## 🔒 Security Features

- ✅ Cognito authentication required for all endpoints
- ✅ S3 books folder is private (no public access)
- ✅ Downloads use presigned URLs (time-limited)
- ✅ Path traversal protection in book IDs
- ✅ CORS properly configured
- ✅ JWT tokens stored in localStorage

## 🎨 Frontend Features

### Read/Unread Tracking
- Click the circle icon to mark books as read (✓)
- Read books have lower opacity and green border
- **Status syncs with backend** (persists across devices)
- Updates via PATCH API call to DynamoDB

### File Size Display
- Shows book size in MB (e.g., "245.5 MB")
- Extracted from S3 metadata during upload
- Helps manage storage and download expectations

### Author Display
- Automatically extracted from filename format: "Author - Title.zip"
- Displays below book title
- Falls back gracefully if no author in filename

### Clean UX
- Toast notifications (no page jumps)
- Instant toggle updates (optimistic UI)
- Download icon centered in cards
- Responsive grid layout
- Auto token refresh (no login interruptions)

## 📝 Configuration

### S3 Bucket Structure
```
your-bucket/
├── books/              # Private book files (.zip)
│   ├── book1.zip
│   └── book2.zip
└── books-app/          # Public web interface
    ├── index.html
    ├── app.js
    └── styles.css
```

### Cognito Setup
1. Create a User Pool
2. Create an App Client (without client secret)
3. Configure App Client settings:
   - Enable USER_PASSWORD_AUTH flow
   - Set OAuth flows (optional)

### CloudFront (Optional)
For custom domain and HTTPS:
1. Create CloudFront distribution
2. Set S3 as origin with OAC
3. Point custom domain via Route 53

## 🛠️ Development

### Local Testing
```bash
# Start SAM local API
sam local start-api

# Run tests
python -m pytest tests/ -v
```

### Deploy Updates
```bash
# Backend
sam build && sam deploy

# Frontend
aws s3 sync frontend/ s3://YOUR_BUCKET/books-app/
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

## 📊 AWS Resources Used

- **Lambda**: 4 functions (list, get, update, S3 trigger)
- **API Gateway**: REST API with Cognito authorizer
- **DynamoDB**: Books table for metadata (PAY_PER_REQUEST billing)
- **Cognito**: User Pool for authentication
- **S3**: Storage for books (.zip files) and frontend
- **CloudFront**: CDN for frontend delivery (optional)
- **IAM**: Roles and policies for Lambda
- **S3 Event Notifications**: Triggers Lambda on new uploads

## 🤝 Contributing

This is a personal project, but feel free to fork and adapt for your needs!

## 📄 License

MIT License - feel free to use this project however you like.

## 🙏 Acknowledgments

Built with AWS SAM, inspired by the need for a simple personal book library.

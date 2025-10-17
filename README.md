# Books Library - Serverless Book Management System

A serverless book management system built with AWS Lambda, API Gateway, Cognito, S3, and CloudFront. Upload books to S3, browse them through a web interface, and download via secure presigned URLs.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  books.crackpow.com (CloudFront + S3)                          │
│  ├─ Frontend: Vanilla JS SPA with Cognito auth                │
│  └─ Serves from: s3://crackpow/books-app/                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ (Authenticated API Calls)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  API Gateway (REST API)                                         │
│  ├─ Authorization: AWS Cognito (JWT tokens)                    │
│  └─ Routes:                                                     │
│     ├─ GET /books - List all books with metadata               │
│     └─ GET /books/{id} - Get presigned download URL            │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌──────────────────────┐   ┌──────────────────────┐
│  Lambda Function     │   │  Lambda Function     │
│  BooksFunction       │   │  GetBookFunction     │
│  (List handler)      │   │  (Download handler)  │
└──────────────────────┘   └──────────────────────┘
                │                       │
                └───────────┬───────────┘
                            ▼
                ┌──────────────────────┐
                │  S3 Bucket           │
                │  crackpow/books/     │
                │  (Private .zip files)│
                └──────────────────────┘
```

## ✨ Features

### Frontend
- 📱 Clean, responsive web interface
- 🔐 AWS Cognito authentication
- 📚 Auto-loading book list on login
- ⬇️ One-click downloads via presigned URLs
- ✅ Read/Unread status tracking (localStorage)
- 🎨 Modern card-based grid layout
- 🔔 Toast notifications (no layout shift)

### Backend
- 🚀 Serverless architecture (AWS Lambda)
- 🔒 Cognito-protected API endpoints
- 📦 Lists books from S3 with metadata (size, date)
- 🔗 Generates secure presigned URLs (1-hour expiration)
- 🛡️ Path traversal protection
- 📊 Sorted by date (newest first)
- 🌐 CORS enabled for cross-origin requests

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Python 3.12+
- An S3 bucket for storing books
- A Cognito User Pool set up

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd books
```

Update `template.yaml` with your values:
- `CognitoUserPoolId`
- `CognitoUserPoolArn`
- `BUCKET_NAME` (S3 bucket)

### 2. Deploy Backend

```bash
sam build
sam deploy --guided
```

Note the API endpoint URL from the outputs.

### 3. Configure Frontend

Update `frontend/app.js` with your values:
```javascript
const COGNITO_CONFIG = {
    userPoolId: 'YOUR_USER_POOL_ID',
    clientId: 'YOUR_CLIENT_ID',
    region: 'YOUR_REGION'
};

const API_URL = 'YOUR_API_GATEWAY_URL/books';
```

### 4. Upload Frontend to S3

```bash
aws s3 cp frontend/ s3://YOUR_BUCKET/books-app/ --recursive
```

### 5. Add Books

Upload `.zip` files to your S3 bucket:
```bash
aws s3 cp mybook.zip s3://YOUR_BUCKET/books/
```

### 6. Create Users

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
│   ├── handler.py           # API handlers (list & download)
│   └── __init__.py
├── frontend/                # Web interface
│   ├── index.html          # Main HTML
│   ├── app.js              # JavaScript logic
│   └── styles.css          # Styling
├── tests/                  # Unit tests
│   └── test_handler.py
├── template.yaml           # SAM CloudFormation template
├── samconfig.toml         # SAM deployment config
├── Pipfile                # Python dependencies
└── README.md              # This file
```

## 🔧 API Endpoints

### GET /books
Lists all `.zip` files in the S3 books folder.

**Headers:**
- `Authorization`: Cognito JWT token

**Response:**
```json
[
  {
    "name": "book1.zip",
    "size": 1048576,
    "lastModified": "2025-10-17T12:00:00Z"
  }
]
```

### GET /books/{id}
Generates a presigned URL for downloading a specific book.

**Headers:**
- `Authorization`: Cognito JWT token

**Path Parameters:**
- `id`: Book filename (URL-encoded)

**Response:**
```json
{
  "bookId": "book1.zip",
  "downloadUrl": "https://s3.amazonaws.com/...",
  "expiresIn": 3600
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
- Status persists in browser localStorage

### Clean UX
- Toast notifications (no page jumps)
- Instant toggle updates (no reload)
- Download icon centered in cards
- Responsive grid layout

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

- **Lambda**: 2 functions (list, download)
- **API Gateway**: REST API with Cognito authorizer
- **Cognito**: User Pool for authentication
- **S3**: Storage for books and frontend
- **CloudFront**: CDN for frontend delivery
- **IAM**: Roles and policies for Lambda

## 🤝 Contributing

This is a personal project, but feel free to fork and adapt for your needs!

## 📄 License

MIT License - feel free to use this project however you like.

## 🙏 Acknowledgments

Built with AWS SAM, inspired by the need for a simple personal book library.

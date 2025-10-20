# Books Library - Serverless Book Management System

A full-featured serverless book management system built with AWS Lambda, API Gateway, Cognito, DynamoDB, S3, and CloudFront. Upload books via web interface, manage metadata, download securely, and track reading progress - all with authentication and real-time updates.

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
│  ├─ Authorization: AWS Cognito (JWT tokens + groups)            │
│  └─ Routes:                                                     │
│     ├─ GET /books - List all books with per-user read status    │
│     ├─ GET /books/{id} - Get presigned download URL             │
│     ├─ PATCH /books/{id} - Update book metadata & read status   │
│     ├─ DELETE /books/{id} - Delete book (admins only)           │
│     ├─ POST /upload - Get presigned URL for S3 upload           │
│     └─ POST /upload/metadata - Set author after upload          │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼──────────────┬─────────────┬──────────────┐
        ▼                   ▼              ▼             ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐
│BooksFunction │  │GetBookFunc   │  │UpdateBook  │  │DeleteBook│  │Upload      │
│(List books)  │  │(Download)    │  │(Edit meta) │  │(Admin)   │  │(Presigned) │
└──────────────┘  └──────────────┘  └────────────┘  └──────────┘  └────────────┘
        │                   │              │              │              │
        └───────────────────┼──────────────┼──────────────┼──────────────┘
                            ▼              ▼              │
                ┌──────────────────────┐   │              │
                │  DynamoDB Tables     │   │              │
                │  ┌─────────────────┐ │   │              │
                │  │ Books (global)  │◄┼───┤              │
                │  │ • id, name      │ │   │              │
                │  │ • author, series│ │   │              │
                │  │ • size, created │ │   │        ┌─────▼────────────────┐
                │  └─────────────────┘ │   │        │SetMetadataFunction   │
                │  ┌─────────────────┐ │   │        │(Set author on upload)│
                │  │ UserBooks       │◄┼───┘        └──────────────────────┘
                │  │ • userId+bookId │ │
                │  │ • read (boolean)│ │
                │  └─────────────────┘ │
                └──────────────────────┘
                            ▲              
                            │              
┌──────────────────────┐    │              
│  S3 Bucket           │────┘
│  YOUR_BUCKET/books/  │
│  (Private .zip files)│
└──────────────────────┘
         │
         │ (trigger on upload)
         ▼
┌──────────────────────┐
│ S3TriggerFunction    │
│ (Auto-add to DB)     │
└──────────────────────┘
```

## ✨ Features

### Frontend
- 📱 Clean, responsive web interface with modern design
- 🔐 AWS Cognito authentication with auto token refresh
- 👤 **Per-user read tracking** - Each user maintains their own reading progress
- 🛡️ **Role-based permissions** - Admin-only delete and upload functionality via Cognito groups
-  Auto-loading book list on login
- ⬇️ One-click downloads via presigned URLs
- 📤 **Web-based book upload** with drag-and-drop support (up to 5GB, admins only)
- 🤖 **Smart metadata lookup** - Auto-populates author and series from Google Books API
- 📝 **Book editor modal** - Click any book to view/edit details
- ✏️ **Inline metadata editing** - Update author, series name, and series order
- 📚 **Series support** - Track book series with name and order fields
- 🗑️ **Delete books** - Remove from both S3 and DynamoDB with confirmation (admins only)
- ✅ Read/Unread status tracking per user (synced with backend)
- 📊 File size display (MB/GB) with smart formatting
- 👤 Author extraction from "Author - Title.zip" format
- 🎨 Modern card-based grid layout with hover effects
- 🔔 Toast notifications (no layout shift)
- 📈 Real-time upload progress with MB/GB tracking
- 🔍 Filter controls (hide read books, group by author)
- 💾 Persistent state across sessions

### Backend
- 🚀 Serverless architecture (AWS Lambda + DynamoDB)
- 🔒 Cognito-protected API endpoints (all operations authenticated)
- 👥 **Per-user book tracking** - UserBooksTable stores individual user data
- 🛡️ **Admin authorization** - Delete and upload operations require "admins" group membership
- 📦 Two-table design: Books (global metadata) + UserBooks (per-user data)
- 🔗 Generates secure presigned URLs (1-hour expiration)
- 📤 **Presigned PUT URL generation** for direct S3 uploads (up to 5GB, admins only)
- 🏷️ **Post-upload metadata endpoint** for author and series attribution (admins only)
- 🗑️ **Safe deletion** from both DynamoDB tables and S3 (admins only)
- ✏️ **Metadata updates** (author, read status, name, series name/order)
- 🛡️ Path traversal protection and input validation
- 📊 Sorted by date (newest first)
- 🌐 CORS enabled for cross-origin requests
- ⚡ Auto-ingestion: S3 trigger automatically adds new books to DynamoDB

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Python 3.12+
- An S3 bucket for storing books
- A Cognito User Pool set up

### Runtime & Dependencies

**Lambda Runtime:**
- **Python**: 3.12
- **boto3**: Provided by AWS Lambda runtime (~1.34.x, AWS managed)
- **botocore**: Provided by AWS Lambda runtime (~1.34.x, AWS managed)

**Local Development:**
- **boto3**: 1.40.55 (pinned in `requirements.txt` and `Pipfile`)
- **botocore**: 1.40.55 (pinned, dependency of boto3)
- **pytest**: Latest (dev dependency)

**Note:** Lambda runtime includes boto3/botocore by default. The pinned versions in `requirements.txt` are for local development consistency. Lambda will use its own managed versions, which are typically slightly behind the latest release but are automatically updated by AWS.

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
See [`CONFIGURATION.md`](docs/CONFIGURATION.md) for detailed setup instructions.

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

See [`DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) for detailed instructions.

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

### 9. (Optional) Set Up Admin Users

To grant delete permissions, add users to the "admins" group:

```bash
# Create the admins group
aws cognito-idp create-group \
  --user-pool-id YOUR_USER_POOL_ID \
  --group-name admins \
  --description "Administrators with delete permissions"

# Add a user to the admins group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id YOUR_USER_POOL_ID \
  --username admin@example.com \
  --group-name admins
```

Users in the "admins" group will see and can use the delete button in the book details modal. Regular users will not see the delete option.

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
├── docs/                  # Documentation
│   ├── api-docs.html      # Swagger UI for API
│   ├── openapi.yaml       # OpenAPI 3.0 specification
│   ├── CONFIGURATION.md   # Setup instructions
│   ├── DEPLOYMENT_GUIDE.md    # Detailed deployment instructions
│   ├── DYNAMODB_MIGRATION.md  # DynamoDB migration documentation
│   ├── S3_BUCKET_MIGRATION.md # S3 bucket migration guide
│   ├── USER_TRACKING_GUIDE.md # Per-user tracking feature guide
│   ├── TESTING.md         # Testing guide
│   └── TEST_STATUS.md     # Current test status
└── README.md              # This file
```

## 🔧 API Endpoints

### GET /books
Lists all books from DynamoDB with complete metadata and per-user read status.

**Headers:**
- `Authorization`: Cognito JWT token

**Response:**
```json
{
  "books": [
    {
      "id": "Book Title",
      "name": "Book Title",
      "author": "Author Name",
      "size": 1048576,
      "created": "2025-10-17T12:00:00+00:00",
      "read": false,
      "s3_url": "s3://bucket/books/Book Title.zip"
    }
  ],
  "isAdmin": true
}
```

**Notes:**
- `read` status is per-user (stored in UserBooksTable)
- `isAdmin` indicates if the user is in the "admins" Cognito group

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
Updates book metadata and per-user read status.

**Headers:**
- `Authorization`: Cognito JWT token

**Path Parameters:**
- `id`: Book ID (URL-encoded)

**Body:**
```json
{
  "read": true,
  "author": "Updated Author Name",
  "name": "Updated Book Title",
  "series_name": "Series Name",
  "series_order": 1
}
```

**Notes:**
- `read` status is stored per-user in UserBooksTable
- Book metadata (author, name, series) is stored globally in Books table

**Response:**
```json
{
  "id": "Book Title",
  "name": "Book Title",
  "author": "Updated Author Name",
  "read": true,
  ...
}
```

### DELETE /books/{id}
Permanently deletes a book from S3 and both DynamoDB tables (Books and UserBooks).

**Authorization:**
- Requires user to be in the "admins" Cognito group
- Returns 403 Forbidden if user is not an admin

**Headers:**
- `Authorization`: Cognito JWT token

**Path Parameters:**
- `id`: Book ID (URL-encoded)

**Response:**
```json
{
  "message": "Book deleted successfully",
  "bookId": "Book Title"
}
```

**Error Responses:**
- `404 Not Found` - Book doesn't exist
- `400 Bad Request` - Missing book ID
- `500 Internal Server Error` - S3 or DynamoDB error

### POST /upload
Generates a presigned PUT URL for uploading books directly to S3 (up to 5GB).

**Authorization:**
- Requires user to be in the "admins" Cognito group
- Returns 403 Forbidden if user is not an admin

**Headers:**
- `Authorization`: Cognito JWT token

**Body:**
```json
{
  "filename": "Book Title.zip",
  "fileSize": 459816876,
  "author": "Author Name"
}
```

**Response:**
```json
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "method": "PUT",
  "filename": "Book Title.zip",
  "s3Key": "books/Book Title.zip",
  "expiresIn": 3600
}
```

### POST /upload/metadata
Sets metadata (author, series name, series order) on a book after S3 upload completes. The frontend automatically calls Google Books API to fetch metadata when a file is selected, then sends it here.

**Authorization:**
- Requires user to be in the "admins" Cognito group
- Returns 403 Forbidden if user is not an admin

**Headers:**
- `Authorization`: Cognito JWT token

**Body:**
```json
{
  "bookId": "Book Title",
  "author": "Author Name",
  "series_name": "The Great Series",
  "series_order": 3
}
```

**Response:**
```json
{
  "message": "Metadata updated successfully",
  "bookId": "Book Title",
  "author": "Author Name",
  "series_name": "The Great Series",
  "series_order": 3
}
```

**Notes:**
- All fields except `bookId` are optional
- `series_order` must be an integer between 1 and 100 if provided
- Frontend uses Google Books API to auto-populate fields when file is selected
- Supports multiple regex patterns to extract series info from book titles

## 🧪 Testing & Code Quality

**Comprehensive test coverage** with 47 backend unit tests and E2E frontend tests.

### Backend Unit Tests

```bash
# Install dependencies
pipenv install --dev

# Run all backend tests
PYTHONPATH=. pipenv run pytest

# Run specific test file
PYTHONPATH=. pipenv run pytest tests/test_handler.py -v

# Run with coverage (requires pytest-cov)
PYTHONPATH=. pipenv run pytest --cov=gateway_backend --cov-report=term-missing
```

**Coverage:** 58 tests covering all Lambda handlers including edge cases with special characters (apostrophes, quotes, etc.) and comprehensive series field validation

### End-to-End (E2E) Tests

Frontend tests using Playwright to verify complete user workflows.

```bash
# One-time setup: Install Playwright browsers
pipenv run playwright install chromium

# Install system dependencies (Linux only)
sudo apt-get install libnspr4 libnss3 libasound2t64

# Run E2E tests (headless)
PYTHONPATH=. pipenv run pytest -m e2e

# Run with visible browser (debugging)
PYTHONPATH=. pipenv run pytest -m e2e --headed

# Run specific E2E test
PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py::TestBookGrid::test_page_loads -v
```

**Coverage:** Smoke tests for page load, book display, filtering, and special character handling. See `tests/e2e/README.md` for details.

### Code Quality Tools

The project uses modern Python linting and formatting tools configured in `pyproject.toml`:

**Format code with Black:**
```bash
# Check formatting
pipenv run black --check gateway_backend/ tests/

# Auto-format
pipenv run black gateway_backend/ tests/
```

**Lint with Ruff:**
```bash
# Check for linting issues
pipenv run ruff check gateway_backend/ tests/

# Auto-fix issues
pipenv run ruff check --fix gateway_backend/ tests/
```

**Type check with MyPy (optional):**
```bash
pipenv run mypy gateway_backend/ tests/
```

**Run all quality checks:**
```bash
# Run format, lint, and test checks
./scripts/lint.sh

# Include type checking
./scripts/lint.sh --with-mypy
```

**Test Configuration:**
- Uses `pytest.ini` for consistent test execution
- Verbose output with colored results
- Short traceback format for easier debugging
- Automatic test discovery in `tests/` directory

**Test Coverage:**
- ✅ All 7 Lambda handlers (100% coverage)
- ✅ 58 tests total (all passing)
- ✅ Upload functionality (7 tests)
- ✅ Metadata updates (11 tests including series fields)
- ✅ Delete operations (7 tests)
- ✅ List/Get/Update operations (24 tests including series)
- ✅ S3 trigger processing (5 tests)

**Test Categories:**
- Happy path scenarios
- Error handling
- Input validation
- Edge cases and race conditions
- Authentication checks
- Service error handling

## 🔒 Security Features

- ✅ Cognito authentication required for all endpoints
- ✅ S3 books folder is private (no public access)
- ✅ Downloads use presigned URLs (1-hour expiration)
- ✅ Uploads use presigned URLs (60-minute expiration for large files)
- ✅ Path traversal protection in book IDs
- ✅ Input validation on all user-provided data
- ✅ Authorization checks on destructive operations (delete)
- ✅ CORS properly configured
- ✅ JWT tokens with automatic refresh

## 🎨 Frontend Features

### Book Upload
- Click the **"📤 Upload Book"** button (visible when authenticated)
- Select a `.zip` file (up to 5GB)
- **Automatic metadata lookup** via Google Books API:
  - Extracts book title from filename
  - Fetches author, series name, and series order
  - Auto-populates fields (only if empty)
  - Supports multiple series format patterns:
    - `(Series Book 1)` → extracts "Series" and order 1
    - `Series, Book 1` → extracts "Series" and order 1
    - `Book 1 of Series` → extracts "Series" and order 1
    - `Series #1` → extracts "Series" and order 1
  - Shows status messages during lookup
- Optionally edit author, series name, and series order
- Real-time progress bar with size tracking (MB/GB)
- Automatic retry logic for metadata updates
- Books appear in list immediately after upload
- XMLHttpRequest for reliable large file uploads

### Book Details Editor
- Click any book card to open the details modal
- View complete book information (title, date, size, author, series)
- **Edit author and series fields** inline with save button
- **Series badge display**: Shows "Series Name #N" on book cards
- Changes sync to backend immediately
- No page refresh needed

### Delete Books
- Click **"🗑️ Delete Book"** button in details modal
- Two-step confirmation (button + browser dialog)
- **Permanent deletion** warning
- Removes from both S3 storage and DynamoDB
- Immediate UI update after deletion

### Read/Unread Tracking
- Click the circle icon (○/✓) to toggle read status
- Read books have lower opacity and green border
- **Status syncs with backend** (persists across devices)
- Updates via PATCH API call to DynamoDB

### File Size Display
- Shows book size in MB or GB (e.g., "245.5 MB" or "2.34 GB")
- Extracted from S3 metadata during upload
- Smart formatting based on file size

### Author Display
- Automatically extracted from filename format: "Author - Title.zip"
- Automatically fetched from Google Books API on upload
- Displays below book title
- **Editable** via book details modal
- Falls back gracefully if no author

### Series Support
- Track books that are part of a series
- **Series name** (string, up to 500 chars)
- **Series order** (integer, 1-100)
- Auto-populated from Google Books API when uploading
- Displayed as blue badge on book cards: "Series Name #3"
- **Intelligent sorting** when grouped by author:
  - Books in same series sort by series_order
  - Series books appear before non-series books
  - Different series sort alphabetically
  - Fallback to title sort

### Clean UX
- Toast notifications (no page jumps)
- Instant toggle updates (optimistic UI)
- Click-anywhere-to-edit book cards (except download/read icons)
- Responsive grid layout
- Auto token refresh (no login interruptions)
- Filter controls (hide read books, group by author)

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

- **Lambda**: 7 functions
  - BooksFunction (list all books)
  - GetBookFunction (get book + download URL)
  - UpdateBookFunction (update metadata)
  - DeleteBookFunction (delete from S3 + DynamoDB)
  - UploadFunction (generate presigned upload URL)
  - SetUploadMetadataFunction (set author after upload)
  - S3TriggerFunction (auto-ingest uploads)
- **API Gateway**: REST API with Cognito authorizer
  - 6 authenticated endpoints (GET, POST, PATCH, DELETE)
  - CORS enabled for cross-origin requests
- **DynamoDB**: Books table for metadata
  - PAY_PER_REQUEST billing mode
  - Attributes: id, name, author, size, created, read, s3_url
- **Cognito**: User Pool for authentication
  - JWT token-based auth
  - Auto token refresh
- **S3**: Dual-purpose storage
  - Private bucket for books (.zip files, up to 5GB each)
  - Public bucket/prefix for frontend (CloudFront origin)
  - Event notifications for auto-ingestion
- **CloudFront**: CDN for frontend delivery (optional but recommended)
  - HTTPS support
  - Custom domain support
  - Edge caching for fast global access
- **IAM**: Roles and policies for Lambda
  - Least-privilege access
  - Service-specific permissions

**Estimated Monthly Cost:** $0-5 for personal use (mostly S3 storage)

## 🤝 Contributing

This is a personal project, but feel free to fork and adapt for your needs!

## 📄 License

MIT License - feel free to use this project however you like.

## 🙏 Acknowledgments

Built with AWS SAM, inspired by the need for a simple personal book library with full CRUD capabilities.

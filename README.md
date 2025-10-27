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
│     ├─ POST /upload - Get presigned URL with S3 tags            │
│     └─ POST /upload/metadata - Manual metadata update (legacy)  │
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
│ (Read S3 tags &      │
│  Auto-add to DB)     │
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
- 🏷️ **S3 object tagging** - Metadata attached atomically during upload (no race conditions!)
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
- 🔍 **Search & filter** - Real-time search across titles, authors, and series names
- 🎯 Filter controls (hide read books, group by author)
- 💾 Persistent state across sessions
- 🖼️ **Automatic book covers** - Fetches cover images from Google Books API
- 🎨 **Visual book cards** - 80x120px cover thumbnails with gradient backgrounds
- 🔄 **Smart cover updates** - Automatically refreshes covers when author changes
- 📐 **Blank placeholders** - Clean empty state for books without covers
- ♿ **WCAG 2.1 Accessibility** - Full keyboard navigation, screen reader support, ARIA labels
- ⌨️ **Keyboard shortcuts** - Tab/Shift+Tab navigation, Enter/Space activation, Escape to close
- 🎯 **Focus management** - Modal focus trapping, visible focus indicators, skip links
- 🔊 **Screen reader friendly** - Semantic HTML5, live regions, descriptive labels

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
- 🖼️ **Automatic cover fetching** - Queries Google Books API for cover images
- 🔄 **Smart cover updates** - Automatically refreshes covers when author metadata changes
- 🧹 **Cover cleanup** - Removes cover URLs when fetch fails (prevents stale data)
- 📚 **Modular utilities** - Reusable cover and DynamoDB helpers with 100% test coverage

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Python 3.12+
- (Optional) Terraform for automated infrastructure setup

### Deployment Options

**Choose your deployment method:**

📦 **[Option A: Automated with Terraform](docs/TERRAFORM_SETUP.md)** (Recommended)
- One command creates all infrastructure
- Automated setup of S3, DynamoDB, Cognito, IAM
- See [`docs/TERRAFORM_SETUP.md`](docs/TERRAFORM_SETUP.md) for complete guide
- See [`terraform/README.md`](terraform/README.md) for Terraform details

🔧 **Option B: Manual Setup**
- Manual AWS Console or CLI setup
- More control over individual resources
- See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for detailed instructions

### Quick Start (Terraform)

```bash
# 1. Deploy infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit bucket names (must be globally unique)
terraform init && terraform apply

# 2. Configure and deploy backend
cd ..
cp samconfig.toml.example samconfig.toml
# Update samconfig.toml with Terraform outputs
sam build && sam deploy --profile your-profile

# 3. Configure S3 trigger
cd scripts && ./configure-s3-trigger.sh

# 4. Deploy frontend
cp frontend/config.js.example frontend/config.js
# Update frontend/config.js with Terraform outputs
FRONTEND_BUCKET=$(cd ../terraform && terraform output -raw frontend_bucket_name)
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/

# 5. Create admin user
make create-admin-user AWS_PROFILE=your-profile
```

**Or use the Makefile for even simpler deployment:**
```bash
make deploy-all AWS_PROFILE=your-profile
make create-admin-user AWS_PROFILE=your-profile
```

See [`docs/TERRAFORM_SETUP.md`](docs/TERRAFORM_SETUP.md) for the complete step-by-step guide.

### Deploying Updates

After initial setup, use the unified deployment script for consistent deployments:

```bash
# Setup (one-time)
cp .deploy-config.example .deploy-config
# Edit .deploy-config with your AWS settings

# Deploy frontend changes
./scripts/deploy.sh --frontend --invalidate

# Deploy backend changes
./scripts/deploy.sh --backend

# Deploy everything
./scripts/deploy.sh --all --invalidate
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete deployment guide.

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

## 📁 Project Structure

```
.
├── gateway_backend/          # Lambda function code (modular architecture)
│   ├── handler.py           # Main entry point for Lambda functions
│   ├── config.py            # Centralized configuration
│   ├── handlers/            # Modular request handlers
│   │   ├── admin_handlers.py    # Admin operations (upload, delete)
│   │   ├── book_handlers.py     # Book operations (list, get, update)
│   │   └── s3_handlers.py       # S3 trigger processing
│   ├── utils/               # Shared utilities (100% test coverage)
│   │   ├── auth.py              # Authentication & authorization
│   │   ├── cover.py             # Google Books API cover fetching
│   │   ├── dynamodb.py          # DynamoDB operations
│   │   ├── response.py          # HTTP response formatting
│   │   └── validation.py        # Input validation & sanitization
│   ├── requirements.txt     # Python dependencies for Lambda
│   └── README.md            # Backend documentation
├── frontend/                # Web interface (modular architecture)
│   ├── index.html          # Main HTML structure (semantic HTML5 + ARIA)
│   ├── app.js              # Application initialization
│   ├── config.js.example   # Frontend configuration template
│   ├── css/                # Modular CSS components
│   │   ├── main.css            # CSS entry point (imports all modules)
│   │   ├── base.css            # Base styles & variables
│   │   ├── layout.css          # Layout & grid system
│   │   ├── header.css          # Header & navigation
│   │   ├── cards.css           # Book card components
│   │   ├── modals.css          # Modal dialogs
│   │   ├── forms.css           # Form inputs & controls
│   │   ├── buttons.css         # Button styles
│   │   ├── alerts.css          # Notifications & toasts
│   │   ├── accessibility.css   # Accessibility features (WCAG 2.1)
│   │   └── uncategorized.css   # Misc styles
│   ├── js/                 # Modular JavaScript
│   │   ├── auth.js             # Cognito authentication
│   │   ├── api.js              # API request handling
│   │   ├── bookCard.js         # Book card rendering (keyboard accessible)
│   │   ├── bookDetails.js      # Book details modal (focus trapping)
│   │   ├── bookRenderer.js     # Book list rendering & sorting
│   │   ├── filters.js          # Filter controls (ARIA state management)
│   │   ├── upload.js           # File upload with Google Books API
│   │   ├── accessibility.js    # Accessibility utilities (focus trapping, keyboard nav)
│   │   ├── ui.js               # UI utilities & toasts
│   │   └── utils.js            # Helper functions
│   ├── styles.css          # Legacy CSS (imports css/main.css)
│   └── favicon.svg         # Site icon
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # Core infrastructure definitions
│   ├── variables.tf       # Input variables
│   ├── outputs.tf         # Output values
│   ├── terraform.tfvars.example  # Configuration template
│   ├── README.md          # Terraform documentation
│   ├── QUICK_REFERENCE.md # Command cheat sheet
│   └── SUMMARY.md         # Quick overview
├── scripts/                # Deployment & utility scripts
│   ├── deploy.sh                # Unified deployment script (frontend/backend)
│   ├── configure-s3-trigger.sh  # Set up S3 Lambda trigger
│   ├── migrate-books.py         # Migrate S3 books to DynamoDB
│   ├── migrate-bucket.py        # S3 bucket migration tool
│   ├── populate-authors.py      # Populate Authors table
│   ├── backfill-covers.py       # Backfill book covers from Google Books
│   ├── lint.sh                  # Code quality checks
│   └── README.md                # Scripts documentation
├── tests/                  # Test suite (170 tests total)
│   ├── test_handler.py    # Backend unit tests (82 tests)
│   ├── test_utils.py      # Utility module tests (38 tests, 100% coverage)
│   └── e2e/               # End-to-end frontend tests (50 tests, Playwright)
│       ├── test_authentication.py  # Login/logout tests (12 tests)
│       ├── test_book_grid.py       # Display/filtering tests (13 tests)
│       ├── test_book_operations.py # Modal/editing/delete tests (25 tests)
│       ├── conftest.py             # Test fixtures & authentication
│       └── README.md               # E2E test documentation
├── docs/                  # Documentation
│   ├── DEPLOYMENT.md           # Unified deployment guide (deploy.sh)
│   ├── TERRAFORM_SETUP.md      # Complete Terraform workflow guide
│   ├── CONFIGURATION.md        # Configuration reference
│   ├── MANUAL_DEPLOYMENT.md    # Manual deployment guide (alternative to Terraform)
│   ├── DYNAMODB_MIGRATION.md   # DynamoDB migration documentation
│   ├── S3_BUCKET_MIGRATION.md  # S3 bucket migration guide
│   ├── USER_TRACKING_GUIDE.md  # Per-user tracking feature guide
│   ├── TESTING.md              # Testing guide (170 tests)
│   ├── E2E_TEST_SETUP.md       # E2E setup & troubleshooting
│   ├── api-docs.html           # Swagger UI for API
│   └── openapi.yaml            # OpenAPI 3.0 specification
├── template.yaml           # SAM CloudFormation template
├── samconfig.toml.example # SAM deployment config template
├── .deploy-config.example # Deployment script config template
├── .env.example           # E2E test credentials template
├── run-e2e-tests.sh       # E2E test runner script
├── Makefile               # Automated deployment commands
├── Pipfile                # Python dependencies (local dev + testing)
├── Pipfile.lock           # Locked dependency versions
├── pyproject.toml         # Python project config (Black, Ruff, MyPy)
├── pytest.ini             # Pytest configuration
├── LICENSE                # MIT License
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
Generates a presigned PUT URL for uploading books directly to S3 (up to 5GB). **Now supports S3 object tagging** to automatically set metadata during upload.

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
  "author": "Author Name",
  "series_name": "The Great Series",
  "series_order": 1
}
```

**Response:**
```json
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "method": "PUT",
  "filename": "Book Title.zip",
  "s3Key": "books/Book Title.zip",
  "expiresIn": 3600,
  "author": "Author Name",
  "series_name": "The Great Series",
  "series_order": 1
}
```

**How S3 Tagging Works:**
1. Client sends metadata (author, series_name, series_order) in the initial POST request
2. Backend generates presigned URL with S3 object tags embedded
3. Client uploads file to S3 with tags automatically attached
4. S3 trigger Lambda reads tags and creates DynamoDB record with metadata
5. **No separate metadata endpoint call needed!**

**Notes:**
- All metadata fields are optional
- `series_order` must be an integer between 1 and 100 if provided
- Frontend uses Google Books API to auto-populate fields when file is selected
- Supports multiple regex patterns to extract series info from book titles
- Tags are attached atomically during upload, eliminating race conditions

### POST /upload/metadata
**Legacy endpoint** - Sets metadata on a book after S3 upload completes. This endpoint is maintained for backward compatibility and manual metadata updates, but is **no longer used in the primary upload flow** (metadata is now set via S3 object tags).

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
- Use this endpoint to update metadata after initial upload

## 🧪 Testing & Code Quality

**Test Coverage: 170 tests** ✅
- Backend Unit Tests: 120 tests (93% code coverage)
- E2E Tests: 50 tests (Playwright)

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

**Coverage:** 120 tests (93% coverage) covering:
- All Lambda handlers (list, get, update, delete, upload, S3 trigger)
- Edge cases with special characters (apostrophes, quotes, etc.)
- Comprehensive input validation (series fields, string lengths, type checking)
- Book cover fetching and metadata updates
- DynamoDB utility functions

### End-to-End (E2E) Tests

Frontend tests using Playwright to verify complete user workflows.

**Coverage:** 50 E2E tests covering:
- Authentication (login, logout, user menu) - 12 tests
- Book grid display and filtering - 13 tests
- Book operations (edit, delete, download) - 25 tests
  - Includes 7 new tests for overflow menu delete functionality
- Keyboard navigation and accessibility

```bash
# One-time setup: Install Playwright browsers
pipenv run playwright install chromium

# Install system dependencies (Linux only)
sudo apt-get install libnspr4 libnss3 libasound2t64

# Configure test credentials
cp .env.example .env
# Edit .env and set TEST_USER_EMAIL and TEST_USER_PASSWORD

# Run E2E tests (recommended - uses helper script)
./run-e2e-tests.sh

# Run with visible browser (debugging)
./run-e2e-tests.sh --headed

# Or run directly with pytest
PYTHONPATH=. pipenv run pytest -m e2e
```

See [docs/TESTING.md](docs/TESTING.md) and [tests/e2e/README.md](tests/e2e/README.md) for detailed test documentation.

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
- Real-time search across titles, authors, and series
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

**With Terraform installed:**
```bash
# Backend
make update-backend AWS_PROFILE=your-profile

# Frontend (includes API docs)
make update-frontend AWS_PROFILE=your-profile
```

**Without Terraform:**
```bash
# Backend
sam build && sam deploy --profile your-profile

# Frontend and API docs
make update-frontend AWS_PROFILE=your-profile FRONTEND_BUCKET=your-bucket

# Or manually
aws s3 sync frontend/ s3://YOUR_BUCKET/books-app/ --profile your-profile
aws s3 sync docs/ s3://YOUR_BUCKET/books-app/api-docs/ --exclude "*.md" --profile your-profile
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*" --profile your-profile
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

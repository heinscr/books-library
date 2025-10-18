# DynamoDB Migration Summary

## Overview
Migrated the Books Library application from S3-based book listing to DynamoDB-based metadata management.

## Architecture Changes

### Before
- Books API listed files directly from S3 bucket
- No metadata storage (only S3 object properties: size, lastModified)
- Read status stored only in browser localStorage
- No author information

### After
- Books API queries DynamoDB for book metadata
- S3 only used for actual file storage and presigned URLs
- Read status synced with backend
- Support for author, custom names, and persistent metadata

## Database Schema

### DynamoDB Table: `BooksTable`
- **Partition Key**: `id` (String) - Unique identifier for each book (filename without .zip)
- **Attributes**:
  - `s3_url` (String) - S3 URL in format `s3://bucket/key`
  - `name` (String) - Human-friendly book name
  - `created` (String) - ISO 8601 timestamp
  - `read` (Boolean) - Read status flag
  - `size` (Number) - File size in bytes
  - `author` (String, optional) - Author name
- **Billing Mode**: PAY_PER_REQUEST (on-demand pricing)
- **Stream**: Enabled (NEW_AND_OLD_IMAGES) for future triggers

## New API Endpoints

### GET /books
- **Purpose**: List all books
- **Response**: Array of book objects with metadata from DynamoDB
- **Changes**: Returns `id`, `name`, `created`, `read`, `size`, `author` instead of `name`, `size`, `lastModified`

### GET /books/{id}
- **Purpose**: Get download URL and metadata for specific book
- **Response**: Book metadata + presigned S3 URL
- **Changes**: Looks up book in DynamoDB first, then generates presigned URL

### PATCH /books/{id} (NEW)
- **Purpose**: Update book metadata
- **Body**: JSON with fields to update (e.g., `{ "read": true }`)
- **Response**: Updated book object
- **Auth**: Requires valid Cognito token

## Lambda Functions

### BooksFunction (Updated)
- Lists all books from DynamoDB
- Scans table with pagination support
- Returns sorted list (newest first)

### GetBookFunction (Updated)
- Looks up book metadata from DynamoDB
- Generates presigned S3 URL for download
- Returns both metadata and download URL

### UpdateBookFunction (NEW)
- Updates book metadata in DynamoDB
- Supports updating: `read`, `author`, `name`
- Uses conditional update (book must exist)

### S3TriggerFunction (NEW)
- Triggered when .zip file uploaded to `s3://YOUR_BUCKET/books/`
- Automatically creates DynamoDB record
- Parses author from filename if format is "Author - Title.zip"
- Generates friendly name from filename
- Captures file size from S3 event

## Frontend Changes

### app.js Updates
1. **Book Display**
   - Shows `id`, `name`, `created`, `size`, `author` from API
   - Displays file size in MB
   - Added author display when available

2. **Read Status**
   - Changed from localStorage to backend PATCH request
   - Optimistic UI update with error rollback
   - Token refresh support for PATCH requests

3. **Download Function**
   - Uses book `id` instead of `name`
   - Gets friendly name from API response

### styles.css Updates
- Added `.book-author` style for author display
- Maintains existing card layout and read indicator

## Deployment Steps

1. **Deploy Infrastructure**
   ```bash
   sam build
   sam deploy
   ```

2. **Note**: S3 bucket reference issue
   - `BooksBucket` resource defined but bucket already exists
   - May need to remove `BooksBucket` resource and use existing bucket
   - S3 trigger will need manual configuration or use existing bucket reference

3. **Populate DynamoDB**
   - Option 1: Upload books trigger S3TriggerFunction automatically
   - Option 2: Manual migration script to populate from existing S3 books

4. **Deploy Frontend**
   ```bash
   aws s3 cp frontend/app.js s3://YOUR_BUCKET/books-app/ --profile YOUR_PROFILE
   aws s3 cp frontend/styles.css s3://YOUR_BUCKET/books-app/ --profile YOUR_PROFILE
   aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/app.js" "/styles.css" --profile YOUR_PROFILE
   ```

## Migration Considerations

### Data Migration
Since this is a schema change, existing books in S3 won't automatically appear in the UI until they're added to DynamoDB. Options:

1. **Re-upload books** - Trigger S3TriggerFunction
2. **Migration script** - Create one-time script to scan S3 and populate DynamoDB
3. **Manual entry** - Add records via AWS Console

### Backward Compatibility
- Read status from localStorage won't carry over
- Users will need to re-mark books as read

## Testing Checklist

- [ ] Deploy SAM template successfully
- [ ] Verify DynamoDB table created
- [ ] Upload test book to S3 books/
- [ ] Verify S3TriggerFunction creates DynamoDB record
- [ ] Test GET /books returns book list
- [ ] Test GET /books/{id} generates presigned URL
- [ ] Test PATCH /books/{id} updates read status
- [ ] Test frontend displays books correctly
- [ ] Test read toggle syncs with backend
- [ ] Test download functionality
- [ ] Test token refresh during PATCH request

## Future Enhancements

1. **Search and Filter**
   - Add DynamoDB GSI on author
   - Filter by read status
   - Search by book name

2. **Additional Metadata**
   - Add tags/categories
   - Add description
   - Add cover image URL

3. **Batch Operations**
   - Mark all as read/unread
   - Bulk delete

4. **Analytics**
   - DynamoDB Streams to track reads
   - Reading statistics

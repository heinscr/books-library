# Gateway Backend

Lambda functions for the Books Library API.

## Handler Functions

**Total: 7 Lambda functions**
- `list_handler` - List all books
- `get_book_handler` - Get book and download URL
- `update_book_handler` - Update book metadata
- `delete_book_handler` - Delete book from DynamoDB and S3
- `upload_handler` - Generate presigned upload URL
- `set_upload_metadata_handler` - Set author after upload
- `s3_trigger_handler` - Auto-populate from S3 events

### `list_handler(event, context)`
Lists all books from DynamoDB with complete metadata.

**Returns:**
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

### `get_book_handler(event, context)`
Gets book metadata from DynamoDB and generates a presigned URL for downloading.

**Parameters:**
- `id` (path): Book ID (URL-encoded, matches DynamoDB id field)

**Returns:**
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

### `update_book_handler(event, context)`
Updates book metadata in DynamoDB (e.g., read status).

**Parameters:**
- `id` (path): Book ID (URL-encoded)
- Body: JSON with fields to update (e.g., `{"read": true}`)

**Returns:**
```json
{
  "id": "Book Title",
  "name": "Book Title",
  "read": true,
  ...
}
```

### `delete_book_handler(event, context)`
Deletes a book from both DynamoDB and S3.

**Parameters:**
- `id` (path): Book ID (URL-encoded)

**Returns:**
```json
{
  "message": "Book deleted successfully",
  "id": "Book Title"
}
```

**Features:**
- Removes from DynamoDB first, then S3
- Gracefully handles missing S3 files (e.g., books without s3_url)
- Returns 404 if book doesn't exist in DynamoDB
- Permanent deletion with no recovery option

### `upload_handler(event, context)`
Generates a presigned PUT URL for uploading books directly to S3.

**Parameters:**
- Body: JSON with `filename` (required), `fileSize` (optional), `author` (optional)

**Returns:**
```json
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "method": "PUT",
  "filename": "Book Title.zip",
  "s3Key": "books/Book Title.zip",
  "expiresIn": 3600
}
```

**Features:**
- Supports files up to 5GB
- 60-minute expiration for large uploads
- Author field passed through (used by metadata endpoint)
- Validates .zip file extension

### `set_upload_metadata_handler(event, context)`
Sets metadata (author) on a book after S3 upload completes.

**Parameters:**
- Body: JSON with `bookId` (required) and `author` (optional)

**Returns:**
```json
{
  "message": "Metadata updated successfully",
  "bookId": "Book Title",
  "author": "Author Name"
}
```

**Features:**
- Called by frontend after S3 upload
- Updates DynamoDB record with author field
- Returns 404 if book not found (S3 trigger hasn't processed yet)
- Validates author length (max 500 characters)

### `s3_trigger_handler(event, context)`
S3 event trigger that auto-populates DynamoDB when books are uploaded.

**Triggered by:** S3 ObjectCreated events in the books/ prefix
**Creates:** DynamoDB record with extracted metadata (name, author, size, created date)
**Features:** URL-decodes filenames (handles spaces and special characters)

## Environment Variables

- `BUCKET_NAME`: S3 bucket name (default: your-bucket-name)
- `BOOKS_PREFIX`: S3 prefix for books (default: books/)
- `BOOKS_TABLE`: DynamoDB table name (set by SAM template)

## Security

- Cognito JWT authentication required for API endpoints
- S3 signature version 4 for presigned URLs
- Path traversal protection
- URL decoding for filenames with spaces
- DynamoDB write operations isolated to S3 trigger function

## Testing

See `../tests/test_handler.py` for unit tests.

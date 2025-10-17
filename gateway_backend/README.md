# Gateway Backend

Lambda functions for the Books Library API.

## Handler Functions

### `list_handler(event, context)`
Lists all `.zip` files in the S3 books folder with metadata.

**Returns:**
```json
[
  {
    "name": "book.zip",
    "size": 1048576,
    "lastModified": "2025-10-17T12:00:00Z"
  }
]
```

### `get_book_handler(event, context)`
Generates a presigned URL for downloading a specific book.

**Parameters:**
- `id` (path): Book filename (URL-encoded)

**Returns:**
```json
{
  "bookId": "book.zip",
  "downloadUrl": "https://s3.amazonaws.com/...",
  "expiresIn": 3600
}
```

## Environment Variables

- `BUCKET_NAME`: S3 bucket name
- `BOOKS_PREFIX`: S3 prefix for books (default: `books/`)

## Security

- Cognito JWT authentication required
- S3 signature version 4 for presigned URLs
- Path traversal protection
- URL decoding for filenames with spaces

## Testing

See `../tests/test_handler.py` for unit tests.

"""
Lambda handlers for Books API

This module serves as the entry point for all Lambda functions.
It re-exports handlers from their respective modules for Lambda function configuration.

Architecture:
- API Gateway -> Lambda -> DynamoDB (for metadata)
- API Gateway -> Lambda -> S3 (for presigned download/upload URLs)
- S3 Event -> Lambda -> DynamoDB (for auto-ingestion)
- Frontend -> upload_handler -> S3 direct upload -> s3_trigger_handler -> set_upload_metadata_handler

Handlers:
1. list_handler: Lists all books from DynamoDB with user-specific read status
2. get_book_handler: Gets book metadata and generates presigned S3 download URL
3. update_book_handler: Updates book metadata (e.g., read status, author, series)
4. delete_book_handler: Deletes book from both DynamoDB and S3 (admin only)
5. upload_handler: Generates presigned S3 upload URL for authenticated admin users
6. set_upload_metadata_handler: Sets author/series metadata after upload completes (admin only)
7. s3_trigger_handler: Auto-populates DynamoDB when books are uploaded to S3

Updated: 2025-10-23 - Refactored into modular structure
"""

# Re-export handlers for Lambda function configuration
# Support both local development (gateway_backend.X) and Lambda deployment (X)
try:
    # Lambda deployment (files are in root, not in gateway_backend/)
    from handlers.admin_handlers import delete_book_handler, upload_handler
    from handlers.book_handlers import (
        get_book_handler,
        list_handler,
        update_book_handler,
    )
    from handlers.s3_handlers import s3_trigger_handler, set_upload_metadata_handler
    from config import books_table, s3_client, user_books_table
except ImportError:
    # Local development / testing (with gateway_backend package structure)
    from gateway_backend.handlers.admin_handlers import delete_book_handler, upload_handler
    from gateway_backend.handlers.book_handlers import (
        get_book_handler,
        list_handler,
        update_book_handler,
    )
    from gateway_backend.handlers.s3_handlers import s3_trigger_handler, set_upload_metadata_handler
    from gateway_backend.config import books_table, s3_client, user_books_table

# Make handlers available at module level for Lambda
__all__ = [
    "list_handler",
    "get_book_handler",
    "update_book_handler",
    "delete_book_handler",
    "upload_handler",
    "set_upload_metadata_handler",
    "s3_trigger_handler",
    # Also export config for tests
    "books_table",
    "user_books_table",
    "s3_client",
]

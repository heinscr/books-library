# Per-User Book Tracking and Role-Based Access Control

## Overview

This application supports per-user book tracking and role-based permissions:

1. **Per-User Read Status**: Each Cognito user has their own tracking of which books they've read
2. **Admin Role for Deletions and Uploads**: Only users in the "admins" Cognito group can delete or upload books
3. **Data Separation**: Global book metadata (title, author, series) is separate from user-specific data (read status)

## Architecture

### Database Tables

#### Books Table (Global Metadata)
- **Partition Key**: `id` (string)
- **Attributes**: `name`, `author`, `series_name`, `series_order`, `s3_url`, `size`, `created`
- **Purpose**: Stores book metadata shared across all users

#### UserBooks Table (User-Specific Data)
- **Partition Key**: `userId` (string) - Cognito user sub
- **Sort Key**: `bookId` (string) - References Books table
- **Attributes**: `read` (boolean), `updated` (timestamp)
- **Purpose**: Tracks per-user read status for each book

### Authorization Model

- **Authentication**: Cognito JWT tokens with claims
  - `sub`: Unique user ID
  - `email`: User email
  - `cognito:groups`: Array of group memberships
  
- **Authorization**: Cognito groups-based RBAC
  - Users in the **"admins"** group can delete and upload books
  - All authenticated users can view and update their own read status
  - Non-admin users won't see delete or upload buttons in the UI

## API Changes

### List Books (GET /books)

**Old Response:**
```json
[
  {
    "id": "book-123",
    "name": "Example Book",
    "read": true,
    ...
  }
]
```

**New Response:**
```json
{
  "books": [
    {
      "id": "book-123",
      "name": "Example Book",
      "read": true,  // User-specific read status
      ...
    }
  ],
  "isAdmin": false  // Whether current user can delete books
}
```

### Get Book (GET /books/{id})

- Now returns user-specific `read` status instead of global status
- Requires authentication

### Update Book (PUT /books/{id})

**Request Body:**
```json
{
  "read": true,              // Updates UserBooks table (user-specific)
  "author": "New Author",    // Updates Books table (global)
  "series_name": "Series",   // Updates Books table (global)
  "series_order": 1          // Updates Books table (global)
}
```

- Separates user-specific fields from book metadata
- Updates both tables as needed

### Delete Book (DELETE /books/{id})

- **Authorization Required**: User must be in "admins" Cognito group
- Returns **403 Forbidden** if user is not an admin
- Deletes book from S3, all UserBooks entries, and Books table

## Setup Instructions

### 1. Deploy Infrastructure

Deploy the updated SAM template:

```bash
sam build
sam deploy
```

This creates the new UserBooks table and updates Lambda function permissions.

### 2. Create Admin Group

Create the "admins" group in Cognito:

**Using AWS CLI:**
```bash
aws cognito-idp create-group \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --group-name admins \
  --description "Administrators with delete permissions"
```

**Using AWS Console:**
1. Go to Amazon Cognito → User Pools
2. Select your user pool
3. Navigate to "Groups" tab
4. Click "Create group"
5. Group name: `admins`
6. Click "Create group"

### 3. Add Users to Admin Group

Add users who should have delete permissions:

**Using AWS CLI:**
```bash
aws cognito-idp admin-add-user-to-group \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --username <USERNAME_OR_EMAIL> \
  --group-name admins
```

**Using AWS Console:**
1. Go to Amazon Cognito → User Pools → Your pool
2. Navigate to "Users" tab
3. Click on a user
4. Click "Add user to group"
5. Select "admins" group

### 4. Deploy Frontend

Deploy the updated frontend to S3:

```bash
# Assuming you have a deployment script
aws s3 sync frontend/ s3://your-frontend-bucket/ --exclude "config.js.example"
```

## User Experience

### Regular Users
- See all books in the library
- Can mark books as read/unread (only affects their own view)
- Cannot delete books
- Don't see delete buttons in book details modal

### Admin Users
- See all books in the library
- Can mark books as read/unread (only affects their own view)
- Can delete books from the library
- See delete buttons in book details modal

### Read Status Isolation
- When User A marks a book as "read", it doesn't affect User B's view
- Each user maintains their own reading progress
- The book metadata (title, author, series) remains the same for everyone

## Migration Notes

### Existing Data
- Existing books in the Books table remain unchanged
- The old global `read` field is ignored by the new code
- UserBooks table starts empty
- Users will need to re-mark books as read (their personal tracking)

### No Data Migration Required
- Old data is preserved but not migrated
- No risk to existing book records
- UserBooks entries are created on-demand when users update read status

## Testing

### Test User-Specific Read Status
1. Log in as User A
2. Mark a book as "read"
3. Log out
4. Log in as User B
5. Verify the same book shows as "unread"

### Test Admin Permissions
**Delete permissions:**
1. Log in as a regular user (not in admins group)
2. Open a book's details modal
3. Verify no delete button is visible
4. Log out
5. Log in as an admin user (in admins group)
6. Open a book's details modal
7. Verify delete button is visible
8. Test deleting a book

**Upload permissions:**
1. Log in as a regular user (not in admins group)
2. Verify upload button is not visible
3. Log out
4. Log in as an admin user (in admins group)
5. Verify upload button is visible
6. Test uploading a book

### Test API Authorization
**Regular user trying to delete (should fail):**
```bash
# Get ID token for regular user
curl -X DELETE https://your-api.com/books/book-123 \
  -H "Authorization: <REGULAR_USER_TOKEN>"
# Should return 403 Forbidden
```

**Admin user deleting (should succeed):**
```bash
# Get ID token for admin user
curl -X DELETE https://your-api.com/books/book-123 \
  -H "Authorization: <ADMIN_USER_TOKEN>"
# Should return 200 OK
```

**Regular user trying to upload (should fail):**
```bash
# Get ID token for regular user
curl -X POST https://your-api.com/upload \
  -H "Authorization: <REGULAR_USER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.zip", "fileSize": 1000}'
# Should return 403 Forbidden
```

**Admin user uploading (should succeed):**
```bash
# Get ID token for admin user
curl -X POST https://your-api.com/upload \
  -H "Authorization: <ADMIN_USER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.zip", "fileSize": 1000}'
# Should return 200 OK with presigned URL
```

## Troubleshooting

### Users can't mark books as read
- Check CloudWatch logs for authentication errors
- Verify USER_BOOKS_TABLE environment variable is set on Lambda functions
- Verify Lambda functions have DynamoDB permissions for UserBooks table

### Delete or upload buttons not showing for admins
- Verify user is in the "admins" Cognito group
- Check browser console for errors
- Verify frontend is getting `isAdmin: true` in list response
- Check that ID token includes `cognito:groups` claim

### 403 Forbidden when deleting or uploading
- Verify user is in "admins" group (check Cognito console)
- Verify ID token is not expired
- Check CloudWatch logs for authorization failures
- Verify `cognito:groups` claim is present in JWT

### UserBooks entries not being deleted
- Check CloudWatch logs for delete handler
- Verify scan permissions on UserBooks table
- Check for any DynamoDB errors in logs

## Code References

### Backend (handler.py)
- `_get_user_id(event)`: Extract user ID from JWT claims
- `_get_user_groups(event)`: Extract Cognito groups from JWT claims
- `_is_admin(event)`: Check if user is in admins group
- `list_handler`: Returns books with per-user read status + isAdmin flag
- `get_book_handler`: Returns book with user-specific read status
- `update_book_handler`: Separates user data from book metadata updates
- `delete_book_handler`: Requires admin role, cleans up UserBooks entries
- `upload_handler`: Requires admin role, generates presigned S3 upload URL
- `set_upload_metadata_handler`: Requires admin role, sets metadata after upload

### Frontend (app.js)
- `fetchBooks()`: Handles new response format with isAdmin flag, shows/hides upload button
- `showBookDetailsModal()`: Shows/hides delete button based on admin status
- `showUploadModal()`: Checks admin status before showing upload modal
- `uploadBook()`: Checks admin status before allowing upload
- `window.isUserAdmin`: Global flag for current user's admin status

### Infrastructure (template.yaml)
- `UserBooksTable`: DynamoDB table definition
- Lambda function environment variables: `USER_BOOKS_TABLE`
- Lambda function policies: DynamoDBCrudPolicy for UserBooks table

#!/usr/bin/env python3
"""
Migrate S3 URLs in DynamoDB from old bucket to new bucket.

Usage:
    OLD_BUCKET=my-old-bucket NEW_BUCKET=my-new-bucket AWS_REGION=us-east-2 python3 migrate-bucket.py

Configuration:
    Set OLD_BUCKET and NEW_BUCKET via environment variables or create a local
    config file (not tracked in git) with the bucket names.
"""

import boto3
import os
import sys

# Configuration from environment variables
OLD_BUCKET = os.environ.get("OLD_BUCKET")
NEW_BUCKET = os.environ.get("NEW_BUCKET")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Books")
REGION = os.environ.get("AWS_REGION", "us-east-2")

# Validate required configuration
if not OLD_BUCKET or not NEW_BUCKET:
    print("❌ Error: OLD_BUCKET and NEW_BUCKET environment variables are required")
    print("\nUsage:")
    print("  OLD_BUCKET=my-old-bucket NEW_BUCKET=my-new-bucket python3 migrate-bucket.py")
    sys.exit(1)

def migrate_s3_urls():
    """Update all S3 URLs in DynamoDB from old bucket to new bucket."""
    
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print(f"🔍 Scanning {TABLE_NAME} table for books with old bucket URLs...")
    
    # Scan all items
    response = table.scan()
    items = response.get("Items", [])
    
    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    
    print(f"📚 Found {len(items)} total books in DynamoDB")
    
    # Filter items that need migration
    items_to_migrate = []
    for item in items:
        s3_url = item.get("s3_url", "")
        if s3_url.startswith(f"s3://{OLD_BUCKET}/"):
            items_to_migrate.append(item)
    
    print(f"🔄 {len(items_to_migrate)} books need migration")
    
    if not items_to_migrate:
        print("✅ No migration needed! All books already use the new bucket.")
        return
    
    # Confirm before proceeding
    print(f"\nThis will update S3 URLs from:")
    print(f"  s3://{OLD_BUCKET}/books/... → s3://{NEW_BUCKET}/books/...")
    
    response = input("\nProceed with migration? [y/N]: ")
    if response.lower() != "y":
        print("❌ Migration cancelled")
        sys.exit(0)
    
    # Update each item
    updated_count = 0
    failed_count = 0
    
    for item in items_to_migrate:
        book_id = item["id"]
        old_url = item["s3_url"]
        new_url = old_url.replace(f"s3://{OLD_BUCKET}/", f"s3://{NEW_BUCKET}/")
        
        try:
            table.update_item(
                Key={"id": book_id},
                UpdateExpression="SET s3_url = :new_url",
                ExpressionAttributeValues={":new_url": new_url},
                ConditionExpression="attribute_exists(id)"
            )
            updated_count += 1
            print(f"✅ Updated: {book_id}")
        except Exception as e:
            failed_count += 1
            print(f"❌ Failed to update {book_id}: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"✅ Migration complete!")
    print(f"   Updated: {updated_count} books")
    if failed_count > 0:
        print(f"   Failed: {failed_count} books")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        migrate_s3_urls()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

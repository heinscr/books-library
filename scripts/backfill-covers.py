#!/usr/bin/env python3
"""
Backfill book cover URLs from Google Books API into DynamoDB.

This script:
1. Scans all books in the Books table
2. For each book without a coverImageUrl, calls Google Books API
3. Updates the DynamoDB record with the cover URL

Usage:
    python3 scripts/backfill-covers.py

Environment variables:
    AWS_REGION: AWS region (default: us-east-2)
    DYNAMODB_TABLE: DynamoDB table name (default: Books)
"""

import boto3
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Optional

# Configuration
REGION = os.environ.get("AWS_REGION", "us-east-2")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Books")
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 0.5  # seconds (to avoid hitting API rate limits)


def fetch_cover_url(title: str, author: Optional[str] = None) -> Optional[str]:
    """
    Fetch book cover image URL from Google Books API.

    Args:
        title: Book title
        author: Optional author name for better matching

    Returns:
        Cover image URL or None if not found
    """
    # Build search query
    query = title
    if author:
        query = f"{title} {author}"

    # Clean up common filename artifacts
    query = query.replace("_", " ").replace("-", " ")

    # Call Google Books API
    url = f"{GOOGLE_BOOKS_API}?q={urllib.parse.quote(query)}&maxResults=1"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())

            if data.get("items") and len(data["items"]) > 0:
                volume_info = data["items"][0].get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})

                # Try to get highest quality image
                # Available: thumbnail, smallThumbnail, medium, large, extraLarge
                cover_url = (
                    image_links.get("medium") or
                    image_links.get("thumbnail") or
                    image_links.get("smallThumbnail")
                )

                if cover_url:
                    # Upgrade to HTTPS if needed
                    cover_url = cover_url.replace("http://", "https://")
                    return cover_url

    except Exception as e:
        print(f"  ⚠️  API error: {str(e)}")
        return None

    return None


def main():
    """Main backfill logic."""
    print("=" * 60)
    print("📚 Book Cover Backfill Script")
    print("=" * 60)
    print(f"Region: {REGION}")
    print(f"Table: {TABLE_NAME}")
    print()

    # Initialize DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    # Scan all books
    print("🔍 Scanning DynamoDB for books...")
    response = table.scan()
    items = response.get("Items", [])

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    print(f"📊 Found {len(items)} total books")
    print()

    # Track statistics
    stats = {
        "total": len(items),
        "already_has_cover": 0,
        "cover_added": 0,
        "cover_not_found": 0,
        "errors": 0
    }

    # Process each book
    for i, item in enumerate(items, 1):
        book_id = item.get("id", "unknown")
        title = item.get("name", "")
        author = item.get("author")

        print(f"[{i}/{len(items)}] Processing: {book_id}")

        # Skip if already has cover
        if item.get("coverImageUrl"):
            print(f"  ⏭️  Already has cover - skipping")
            stats["already_has_cover"] += 1
            continue

        # Fetch cover URL from Google Books API
        print(f"  🔍 Searching Google Books for: {title}")
        if author:
            print(f"     by {author}")

        cover_url = fetch_cover_url(title, author)

        if cover_url:
            # Update DynamoDB
            try:
                table.update_item(
                    Key={"id": book_id},
                    UpdateExpression="SET coverImageUrl = :url",
                    ExpressionAttributeValues={":url": cover_url},
                    ConditionExpression="attribute_exists(id)"
                )
                print(f"  ✅ Added cover: {cover_url[:60]}...")
                stats["cover_added"] += 1
            except Exception as e:
                print(f"  ❌ Failed to update DynamoDB: {str(e)}")
                stats["errors"] += 1
        else:
            print(f"  ⚠️  No cover found")
            stats["cover_not_found"] += 1

        # Rate limiting
        if i < len(items):
            time.sleep(DELAY_BETWEEN_REQUESTS)

        print()

    # Print summary
    print("=" * 60)
    print("📊 Backfill Summary:")
    print("=" * 60)
    print(f"Total books:           {stats['total']}")
    print(f"Already had cover:     {stats['already_has_cover']}")
    print(f"Cover added:           {stats['cover_added']}")
    print(f"Cover not found:       {stats['cover_not_found']}")
    print(f"Errors:                {stats['errors']}")
    print("=" * 60)

    if stats["cover_added"] > 0:
        print()
        print("✅ Backfill completed successfully!")
        print(f"   Added {stats['cover_added']} cover images")
    elif stats["already_has_cover"] == stats["total"]:
        print()
        print("ℹ️  All books already have covers - nothing to do")
    else:
        print()
        print("⚠️  Backfill completed with some books missing covers")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

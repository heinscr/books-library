#!/usr/bin/env python3
"""
Populate missing author names in DynamoDB by looking up book metadata.

This script:
1. Scans all books in the DynamoDB Books table
2. Identifies books with missing or empty author fields
3. Looks up book metadata using Google Books API
4. Updates the author field in DynamoDB

Note: Some books may not be found by the APIs, particularly:
- Multi-volume works (e.g., "The Power Broker, Volume 1 of 3" by Robert Caro)
  Tip: These can be manually updated with the correct author name
- Very recent publications
- Books with unusual titles or formatting

Usage:
    python scripts/populate-authors.py [--dry-run] [--profile PROFILE]
"""

import argparse
import sys
import time
from typing import Optional
from urllib.parse import quote

import boto3
import requests


def get_book_metadata_google(book_title: str) -> Optional[str]:
    """
    Look up book metadata using Google Books API.
    
    Args:
        book_title: The title of the book to search for
        
    Returns:
        Author name if found, None otherwise
    """
    try:
        # Clean up the title (remove file extensions if present)
        clean_title = book_title.replace(".zip", "").strip()
        
        # Google Books API endpoint
        url = f"https://www.googleapis.com/books/v1/volumes?q={quote(clean_title)}&maxResults=1"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("totalItems", 0) > 0:
            items = data.get("items", [])
            if items:
                volume_info = items[0].get("volumeInfo", {})
                authors = volume_info.get("authors", [])
                if authors:
                    # Join multiple authors with commas
                    author = ", ".join(authors)
                    print(f"  ✓ Found author: {author}")
                    return author
        
        print(f"  ✗ No author found")
        return None
        
    except requests.RequestException as e:
        print(f"  ✗ API error: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return None


def get_book_metadata_openlibrary(book_title: str) -> Optional[str]:
    """
    Look up book metadata using Open Library API (alternative).
    
    Args:
        book_title: The title of the book to search for
        
    Returns:
        Author name if found, None otherwise
    """
    try:
        clean_title = book_title.replace(".zip", "").strip()
        
        # Open Library API endpoint
        url = f"https://openlibrary.org/search.json?title={quote(clean_title)}&limit=1"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("num_found", 0) > 0:
            docs = data.get("docs", [])
            if docs:
                authors = docs[0].get("author_name", [])
                if authors:
                    author = ", ".join(authors[:2])  # Limit to first 2 authors
                    print(f"  ✓ Found author: {author}")
                    return author
        
        print(f"  ✗ No author found")
        return None
        
    except requests.RequestException as e:
        print(f"  ✗ API error: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return None


def populate_authors(dry_run: bool = False, profile: Optional[str] = None) -> None:
    """
    Main function to populate missing authors in DynamoDB.
    
    Args:
        dry_run: If True, only show what would be updated without making changes
        profile: AWS profile name to use
    """
    # Initialize AWS session
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    dynamodb = session.resource("dynamodb", region_name="us-east-2")
    books_table = dynamodb.Table("Books")
    
    print("🔍 Scanning DynamoDB for books with missing authors...")
    print()
    
    # Scan the table
    response = books_table.scan()
    items = response.get("Items", [])
    
    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = books_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    
    print(f"📚 Found {len(items)} books in total")
    
    # Filter books with missing authors
    books_without_authors = [
        book for book in items
        if not book.get("author") or book.get("author", "").strip() == ""
    ]
    
    print(f"📝 {len(books_without_authors)} books need author information")
    print()
    
    if not books_without_authors:
        print("✅ All books already have authors!")
        return
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    updated_count = 0
    failed_count = 0
    failed_books = []  # Track books that failed for summary
    
    for i, book in enumerate(books_without_authors, 1):
        book_id = book.get("id")
        book_name = book.get("name", book_id)
        
        print(f"[{i}/{len(books_without_authors)}] {book_name}")
        
        # Try Google Books API first
        author = get_book_metadata_google(book_name)
        
        # If Google fails, try Open Library
        if not author:
            print(f"  → Trying Open Library API...")
            author = get_book_metadata_openlibrary(book_name)
        
        if author:
            if dry_run:
                print(f"  → Would update author to: {author}")
                updated_count += 1
            else:
                try:
                    # Update DynamoDB
                    books_table.update_item(
                        Key={"id": book_id},
                        UpdateExpression="SET author = :author",
                        ExpressionAttributeValues={":author": author},
                    )
                    print(f"  ✅ Updated author in DynamoDB")
                    updated_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to update DynamoDB: {e}")
                    failed_count += 1
        else:
            print(f"  ⚠️  Could not find author information")
            failed_count += 1
            failed_books.append(book_name)
        
        print()
        
        # Rate limiting - be nice to the APIs
        time.sleep(1)
    
    # Summary
    print("=" * 60)
    print("📊 Summary:")
    print(f"  Total books processed: {len(books_without_authors)}")
    print(f"  ✅ Successfully updated: {updated_count}")
    print(f"  ❌ Failed or not found: {failed_count}")
    
    if failed_books:
        print()
        print("📋 Books that could not be found:")
        for book in failed_books:
            print(f"  • {book}")
        print()
        print("💡 Tip: Multi-volume works (e.g., 'Volume 1 of 3') may need")
        print("   manual updates. Try searching without the volume number.")
    
    if dry_run:
        print()
        print("💡 Run without --dry-run to apply changes")


def main():
    parser = argparse.ArgumentParser(
        description="Populate missing author names in DynamoDB Books table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="AWS profile name to use",
    )
    
    args = parser.parse_args()
    
    try:
        populate_authors(dry_run=args.dry_run, profile=args.profile)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

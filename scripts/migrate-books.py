#!/usr/bin/env python3
"""
Migration script to populate DynamoDB with existing books from S3
Run this after deploying the DynamoDB table but before the frontend goes live

Environment Variables (optional):
    AWS_PROFILE: AWS profile name (default: 'default')
    AWS_REGION: AWS region (default: 'us-east-2')
    S3_BUCKET: S3 bucket name (default: 'YOUR_BUCKET')
    BOOKS_PREFIX: S3 prefix for books (default: 'books/')
    DYNAMODB_TABLE: DynamoDB table name (default: 'Books')

Example usage:
    # Use default profile and values
    python3 migrate-books.py
    
    # Use custom profile
    AWS_PROFILE=my-profile python3 migrate-books.py
    
    # Override all settings
    AWS_PROFILE=prod AWS_REGION=us-west-2 S3_BUCKET=my-books python3 migrate-books.py
"""

import boto3
import os
from datetime import datetime
from urllib.parse import unquote

# Configuration - Update these values or set environment variables
PROFILE = os.environ.get('AWS_PROFILE', 'default')
REGION = os.environ.get('AWS_REGION', 'us-east-2')
BUCKET = os.environ.get('S3_BUCKET', 'YOUR_BUCKET')
PREFIX = os.environ.get('BOOKS_PREFIX', 'books/')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'Books')

def main():
    # Initialize AWS clients
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    s3 = session.client('s3')
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)
    
    print(f"🔍 Scanning S3 bucket: s3://{BUCKET}/{PREFIX}")
    print(f"📊 Target DynamoDB table: {TABLE_NAME}")
    print(f"🌍 Using AWS Profile: {PROFILE}")
    print(f"🌎 Using AWS Region: {REGION}")
    print()
    
    # List all books in S3
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)
    
    books_found = 0
    books_migrated = 0
    books_skipped = 0
    
    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            
            # Skip non-zip files and the folder itself
            if key == PREFIX or not key.endswith('.zip'):
                continue
            
            books_found += 1
            
            # Extract filename
            filename = key.split('/')[-1]
            book_id = filename.replace('.zip', '')
            
            # Check if already exists in DynamoDB
            try:
                response = table.get_item(Key={'id': book_id})
                if 'Item' in response:
                    print(f"⏭️  Skipping (already exists): {filename}")
                    books_skipped += 1
                    continue
            except Exception as e:
                print(f"❌ Error checking {filename}: {e}")
                continue
            
            # Create friendly name
            friendly_name = filename.replace('.zip', '').replace('_', ' ').replace('-', ' ')
            
            # Build item
            item = {
                'id': book_id,
                's3_url': f"s3://{BUCKET}/{key}",
                'name': friendly_name,
                'created': obj['LastModified'].isoformat(),
                'read': False,
                'size': obj['Size']
            }
            
            # Try to extract author from filename if it contains " - "
            if ' - ' in friendly_name:
                parts = friendly_name.split(' - ', 1)
                item['author'] = parts[0].strip()
                item['name'] = parts[1].strip()
            
            # Write to DynamoDB
            try:
                table.put_item(Item=item)
                print(f"✅ Migrated: {filename}")
                if 'author' in item:
                    print(f"   📚 {item['author']} - {item['name']}")
                else:
                    print(f"   📚 {item['name']}")
                books_migrated += 1
            except Exception as e:
                print(f"❌ Failed to migrate {filename}: {e}")
    
    print()
    print("=" * 60)
    print(f"📊 Migration Summary:")
    print(f"   Books found in S3: {books_found}")
    print(f"   Books migrated: {books_migrated}")
    print(f"   Books skipped (already in DB): {books_skipped}")
    print("=" * 60)
    
    if books_migrated > 0:
        print()
        print("✅ Migration completed successfully!")
        print("   You can now use the frontend to view and download books.")
    elif books_skipped == books_found:
        print()
        print("ℹ️  All books already in DynamoDB. No migration needed.")
    else:
        print()
        print("⚠️  Some books could not be migrated. Check errors above.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise

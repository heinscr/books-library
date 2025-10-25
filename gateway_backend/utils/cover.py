"""
Cover image utilities for Books API

Provides functions for fetching and managing book cover images.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def fetch_cover_url(title: str, author: str | None = None) -> str | None:
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
    url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}&maxResults=1"

    try:
        with urllib.request.urlopen(url, timeout=3) as response:
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
        logger.warning(f"Failed to fetch cover for '{title}': {str(e)}")
        return None

    return None


def update_cover_on_author_change(
    current_author: str,
    new_author: str,
    title: str,
    metadata_fields: dict
) -> None:
    """
    Update cover URL in metadata fields if author is changing.

    Args:
        current_author: Current author value
        new_author: New author value
        title: Book title
        metadata_fields: Dictionary to update with coverImageUrl (modified in place)
    """
    # Only fetch new cover if author is actually changing
    if new_author and new_author != current_author:
        logger.info(f"Author changing from '{current_author}' to '{new_author}' - fetching new cover")

        cover_url = fetch_cover_url(title, new_author)
        if cover_url:
            metadata_fields["coverImageUrl"] = cover_url
            logger.info(f"Found new cover for '{title}' with author '{new_author}': {cover_url[:60]}...")
        else:
            # Remove cover if not found
            metadata_fields["coverImageUrl"] = None
            logger.info(f"No cover found for '{title}' with author '{new_author}' - removing existing cover")

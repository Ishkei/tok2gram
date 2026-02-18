"""TikTok module - re-exports from canonical modules for backward compatibility.

This module provides backward compatibility by re-exporting the public
API from the canonical modules:
- src.tiktok_api: contains Post model, fetch_posts, sort_posts_chronologically
- src.downloader: contains download functions

This allows existing code that used:
    from tiktok.fetcher import Post, fetch_posts
    from tiktok.downloader import download_video

To still work with the updated module structure.
"""

from src.tiktok_api import Post, fetch_posts, sort_posts_chronologically
from src.downloader import download_post, download_video, download_slideshow

__all__ = [
    'Post',
    'fetch_posts',
    'sort_posts_chronologically',
    'download_post',
    'download_video',
    'download_slideshow',
]

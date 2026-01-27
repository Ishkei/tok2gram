import yt_dlp
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("tok2gram.tiktok")

@dataclass
class Post:
    post_id: str
    creator: str
    kind: str  # 'video' or 'slideshow'
    url: str
    caption: str
    created_at: Optional[int]  # unix epoch

def fetch_posts(username: str, depth: int = 10, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> List[Post]:
    """
    Fetch latest posts for a TikTok user using yt-dlp metadata extraction.
    """
    url = f"https://www.tiktok.com/@{username}"
    
    ydl_opts = {
        'extract_flat': True,
        'playlist_items': f"1:{depth}",
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    actual_cookie = cookie_content
    if not actual_cookie and cookie_path and os.path.exists(cookie_path):
        with open(cookie_path, 'r') as f:
            actual_cookie = f.read().strip()

    if actual_cookie:
        ydl_opts['http_headers']['Cookie'] = actual_cookie

    posts = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info or 'entries' not in info:
                logger.warning(f"No posts found for creator: {username}")
                return []
            
            for entry in info['entries']:
                if not entry:
                    continue
                    
                caption = entry.get('description') or entry.get('title') or ""
                
                # Prioritize video over slideshow for mixed media
                # yt-dlp flat-extract often marks slideshows as 'playlist' in _type or type
                kind = 'video'
                if entry.get('_type') == 'playlist' or entry.get('type') == 'slideshow':
                    # Only mark as slideshow if it's NOT explicitly marked as a video elsewhere
                    if entry.get('_type') != 'video':
                        kind = 'slideshow'
                
                post = Post(
                    post_id=entry.get('id'),
                    creator=username,
                    kind=kind,
                    url=entry.get('url') or entry.get('webpage_url'),
                    caption=caption,
                    created_at=entry.get('timestamp')
                )
                posts.append(post)
                
    except Exception as e:
        logger.error(f"Failed to fetch posts for {username}: {e}")
        
    return posts

def sort_posts_chronologically(posts: List[Post]) -> List[Post]:
    """
    Sort posts by created_at ascending (oldest first).
    Posts with None created_at are placed at the end.
    """
    return sorted(posts, key=lambda p: p.created_at if p.created_at is not None else float('inf'))
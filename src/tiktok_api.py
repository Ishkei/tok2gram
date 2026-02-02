import yt_dlp
import time
import random
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Any

logger = logging.getLogger("tok2gram.tiktok")

def _probe_kind(url: str, ydl_base_opts: dict, cookie_manager=None, cookie_path: Optional[str] = None) -> str:
    """
    Probe a TikTok post URL to determine if it's a slideshow or video.
    Uses yt-dlp to extract metadata and check for slideshow indicators.
    Includes retry logic with exponential backoff for rate limits and cookie rotation.
    """
    max_attempts = 3
    current_cookie_path = cookie_path
    
    for attempt in range(max_attempts):
        probe_opts = dict(ydl_base_opts)
        probe_opts.pop("extract_flat", None)
        probe_opts.pop("playlist_items", None)
        probe_opts["quiet"] = True
        probe_opts["no_warnings"] = True
        
        # Use cookiefile option for Netscape format cookies
        if current_cookie_path and os.path.exists(current_cookie_path):
            probe_opts['cookiefile'] = current_cookie_path
        
        try:
            with yt_dlp.YoutubeDL(probe_opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=False)

            # If formats exist and contain any video stream, it's definitely a video.
            # This helps correctly classify posts that were redirected from /photo/ to /video/.
            fmts = info.get("formats") or []
            if any((f.get("vcodec") != "none") for f in fmts if isinstance(f, dict)):
                return "video"

            # Strong signal for slideshow: yt-dlp identifies it as a playlist or has entries.
            entries = info.get("entries")
            if info.get("_type") == "playlist" or entries:
                return "slideshow"

            # If formats exist but all are audio-only, it's very likely a slideshow.
            if fmts and all((f.get("vcodec") == "none") for f in fmts if isinstance(f, dict)):
                return "slideshow"

            # If the URL explicitly contains /photo/, trust it as a fallback.
            if "/photo/" in url:
                return "slideshow"

        except Exception as e:
            error_str = str(e)
            logger.warning(f"Probe failed for {url} (attempt {attempt + 1}/{max_attempts}): {e}")
            
            # Handle rate limiting with exponential backoff
            if "HTTP Error 429" in error_str and attempt < max_attempts - 1:
                wait_time = 2 ** attempt * 5  # 5, 10, 20 seconds
                logger.warning(f"Rate limited, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            
            # Handle "No video formats found" with cookie rotation
            elif "No video formats found" in error_str and cookie_manager and attempt < max_attempts - 1:
                logger.warning(f"No formats found, rotating cookies...")
                new_cookie_path = cookie_manager.rotate()
                if new_cookie_path and new_cookie_path != current_cookie_path:
                    current_cookie_path = new_cookie_path
                    continue
                else:
                    logger.warning("No more cookies to rotate, falling back to URL-based detection")
            
            # On failure, fall back to URL-based guess.
            if "/photo/" in url:
                return "slideshow"
            # If probe fails for a /video/ URL (e.g., "No video formats found"), consider it a slideshow fallback
            if "/video/" in url:
                logger.warning(f"Video probe failed for {url}; treating as slideshow fallback")
                return "slideshow"
            
            # If we've exhausted retries or it's not a retryable error, re-raise
            if attempt == max_attempts - 1:
                raise

    return "video"

@dataclass
class Post:
    post_id: str
    creator: str
    kind: str  # 'video' or 'slideshow'
    url: str
    caption: Optional[str]
    created_at: Optional[int]  # unix epoch

def fetch_posts(username: str, depth: int = 10, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None, user_id: Optional[str] = None) -> List[Post]:
    """
    Fetch latest posts for a TikTok user using yt-dlp metadata extraction.
    
    Args:
        username: The TikTok username
        depth: Number of posts to fetch
        cookie_path: Path to cookie file
        cookie_content: Cookie content string
        user_id: Optional TikTok user ID (numeric). If provided, will be used instead of username
                 for fetching posts, which helps with accounts that have privacy settings
                 preventing username-based lookups.
    """
    actual_cookie_path = cookie_path
    
    # If user_id is provided, use tiktokuser: prefix format
    if user_id:
        url = f"tiktokuser:{user_id}"
    # If username is already in tiktokuser: format or is numeric, use it directly
    elif username.startswith("tiktokuser:") or username.isdigit():
        url = username if username.startswith("tiktokuser:") else f"tiktokuser:{username}"
    else:
        url = f"https://www.tiktok.com/@{username}"
    
    ydl_opts: dict[str, Any] = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    if depth and depth > 0:
        ydl_opts['playlist_items'] = f"1:{depth}"
    
    # Preferred: use cookiefile (Netscape format) when available
    if actual_cookie_path and os.path.exists(actual_cookie_path):
        ydl_opts['cookiefile'] = actual_cookie_path
    # Fallback when necessary
    elif cookie_content:
        ydl_opts.setdefault('http_headers', {})
        ydl_opts['http_headers']['Cookie'] = cookie_content

    posts = []
    
    try:
        # Retry extraction with exponential backoff when facing HTTP 429 rate limits.
        max_attempts = 6
        info = None
        for attempt in range(max_attempts):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                    info = ydl.extract_info(url, download=False)
                break
            except Exception as inner:
                msg = str(inner)
                # yt-dlp surfaces HTTP 429 errors in the exception string. If we hit a 429,
                # back off for an increasing amount of time and retry.
                if "HTTP Error 429" in msg and attempt < max_attempts - 1:
                    sleep_s = min(300, (2 ** attempt) * 5) + random.uniform(0, 3)
                    logger.warning(
                        f"429 from TikTok while fetching posts for {username}. "
                        f"Backing off {sleep_s:.1f}s (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(sleep_s)
                    continue
                # Handle IP blocking errors - raise immediately to trigger creator skip
                if "IP address is blocked" in msg or "HTTP Error 403" in msg or "403" in msg:
                    logger.error(f"IP blocked while fetching posts for {username}: {msg}")
                    raise
                # For non-429 errors or after exhausting retries, re-raise.
                raise

        if not info or 'entries' not in info:
            logger.warning(f"No posts found for creator: {username}")
            return []

        entries = info.get('entries') or []
        if not isinstance(entries, list):
            entries = []
        for entry in entries:
            if not entry:
                continue

            caption = entry.get('description') or entry.get('title') or ""
            # Use either 'url' or 'webpage_url' from yt-dlp; if missing, default to empty string.
            entry_url: str = entry.get('url') or entry.get('webpage_url') or ""

            # Initial guess: if the URL already contains /photo/, mark as slideshow.
            kind = 'slideshow' if '/photo/' in entry_url else 'video'

            # Probe the URL to determine if it's truly a slideshow or video.
            if entry_url:
                kind = _probe_kind(entry_url, ydl_opts, cookie_manager=None, cookie_path=actual_cookie_path)

            # When yt-dlp labels a post as slideshow but the URL is still using /video/, rewrite
            # the URL to point at the /photo/ endpoint so downstream downloaders can fetch images.
            if kind == 'slideshow':
                post_id = entry.get('id')
                if post_id:
                    if '/photo/' not in entry_url:
                        if '/video/' in entry_url:
                            entry_url = entry_url.replace('/video/', '/photo/')
                        else:
                            entry_url = f"https://www.tiktok.com/@{username}/photo/{post_id}"

            post = Post(
                post_id=entry.get('id'),
                creator=username,
                kind=kind,
                url=entry_url,
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

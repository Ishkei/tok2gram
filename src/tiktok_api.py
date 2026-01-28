import yt_dlp
import time
import random
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("tok2gram.tiktok")

def _probe_kind(url: str, ydl_base_opts: dict) -> str:
    """
    Probe a TikTok post URL to determine if it's a slideshow or video.
    Uses yt-dlp to extract metadata and check for slideshow indicators.
    """
    probe_opts = dict(ydl_base_opts)
    probe_opts.pop("extract_flat", None)
    probe_opts.pop("playlist_items", None)
    probe_opts["quiet"] = True
    probe_opts["no_warnings"] = True

    try:
        with yt_dlp.YoutubeDL(probe_opts) as ydl:  # type: ignore
            info = ydl.extract_info(url, download=False)

        # Strong signal: playlist / entries => slideshow-like
        entries = info.get("entries")
        if info.get("_type") == "playlist" and entries:
            return "slideshow"

        # Another strong signal: TikTok photo posts often expose MANY thumbnails/images
        thumbs = info.get("thumbnails") or []
        if isinstance(thumbs, list) and len(thumbs) >= 2:
            return "slideshow"

        # If formats exist but all are audio-only, it's very likely a slideshow
        fmts = info.get("formats") or []
        if fmts and all((f.get("vcodec") == "none") for f in fmts if isinstance(f, dict)):
            return "slideshow"

    except Exception as e:
        logger.debug(f"Probe failed for {url}: {e}")

    return "video"

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
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    if depth and depth > 0:
        ydl_opts['playlist_items'] = f"1:{depth}"
    
    actual_cookie = cookie_content
    if not actual_cookie and cookie_path and os.path.exists(cookie_path):
        with open(cookie_path, 'r') as f:
            actual_cookie = f.read().strip()

    if actual_cookie:
        ydl_opts['http_headers']['Cookie'] = actual_cookie

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
                # For non-429 errors or after exhausting retries, re-raise.
                raise

        if not info or 'entries' not in info:
            logger.warning(f"No posts found for creator: {username}")
            return []

        entries = info['entries']  # type: ignore
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
                kind = _probe_kind(entry_url, ydl_opts)

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

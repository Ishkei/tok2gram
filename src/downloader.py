import yt_dlp
import logging
import os
import requests
from .tiktok_api import Post
from typing import Optional, List, Dict, Any, cast

logger = logging.getLogger("tok2gram.downloader")


class YoutubeDLLogger:
    """Custom logger for yt-dlp to filter out deprecated cookie warnings."""
    def debug(self, msg):
        pass  # Suppress debug messages
    
    def warning(self, msg):
        # Filter out the deprecated cookie warning
        if 'Deprecated Feature' not in msg:
            logger.warning(msg)
    
    def error(self, msg):
        logger.error(msg)

def download_post(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[List[str]]:
    """
    Dispatch download based on post kind.
    Returns a list of file paths.
    """
    logger.debug(f"DEBUG: download_post called for post {post.post_id}, kind={post.kind}, url={post.url}")
    if post.kind == 'video':
        # Attempt to download the video. If this fails (e.g., due to a misclassified
        # slideshow or missing video formats), fall back to downloading a slideshow.
        path = download_video(post, base_download_path, cookie_path, cookie_content)
        if path:
            return [path]
        # Video download failed; attempt to treat as a slideshow.
        logger.warning(
            f"Video download failed for {post.post_id}; attempting slideshow fallback"
        )
        return download_slideshow(post, base_download_path, cookie_path, cookie_content)
    elif post.kind == 'slideshow':
        # Attempt to download images for the slideshow. If this fails, fall back
        # to downloading a video by reconstructing the /video/ URL.
        files = download_slideshow(post, base_download_path, cookie_path, cookie_content)
        if files:
            return files
        logger.warning(
            f"Slideshow download failed for {post.post_id}; attempting video fallback"
        )
        fallback_url = post.url.replace('/photo/', '/video/')
        vid_path = download_video(
            post,
            base_download_path,
            cookie_path=cookie_path,
            cookie_content=cookie_content,
            url_override=fallback_url,
        )
        return [vid_path] if vid_path else None
    else:
        logger.error(f"Unknown post kind: {post.kind}")
        return None

def download_video(
    post: Post,
    base_download_path: str,
    cookie_path: Optional[str] = None,
    cookie_content: Optional[str] = None,
    url_override: Optional[str] = None,
) -> Optional[str]:
    """
    Download a TikTok video post using yt-dlp.
    Returns the path to the downloaded file.
    """
    # Create structured directory: downloads/{creator}/
    creator_path = os.path.join(base_download_path, post.creator)
    os.makedirs(creator_path, exist_ok=True)
    
    # Filename pattern: {post_id}.mp4
    output_template = os.path.join(creator_path, f"{post.post_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bv*+ba/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'logger': YoutubeDLLogger(),
        'concurrent_fragment_downloads': 2,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    actual_cookie = cookie_content
    if not actual_cookie and cookie_path and os.path.exists(cookie_path):
        with open(cookie_path, 'r') as f:
            actual_cookie = f.read().strip()

    if actual_cookie:
        ydl_opts['http_headers']['Cookie'] = actual_cookie

    try:
        # Cast ydl_opts to ``Dict[str, Any]`` to satisfy static type checkers.
        ydl_params = cast(Dict[str, Any], ydl_opts)
        with yt_dlp.YoutubeDL(ydl_params) as ydl:  # type: ignore[arg-type]
            # Allow overriding the URL to support fallback scenarios (e.g. when a
            # post was misclassified as a slideshow and we need to try the /video/
            # endpoint).
            target_url = url_override if url_override else post.url
            info = ydl.extract_info(target_url, download=True)
            # Find the actual filename
            filename = ydl.prepare_filename(info)
            # If it was merged, the extension might have changed to mp4
            if not os.path.exists(filename):
                # Try with mp4 extension
                base, _ = os.path.splitext(filename)
                filename = f"{base}.mp4"
                
            if os.path.exists(filename):
                logger.info(f"Successfully downloaded video: {filename}")
                return filename
            else:
                logger.error(f"Download finished but file not found: {filename}")
                return None
                
    except Exception as e:
        logger.error(f"Failed to download video {post.post_id}: {e}")
        return None

def download_slideshow(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[List[str]]:
    """
    Download a TikTok slideshow (multiple images).
    """
    creator_path = os.path.join(base_download_path, post.creator, post.post_id)
    os.makedirs(creator_path, exist_ok=True)
    
    # Convert /photo/ URL to /video/ URL for yt-dlp compatibility
    target_url = post.url
    if '/photo/' in post.url:
        target_url = post.url.replace('/photo/', '/video/')
        logger.debug(f"Converted slideshow URL from {post.url} to {target_url}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'logger': YoutubeDLLogger(),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

    actual_cookie = cookie_content
    if not actual_cookie and cookie_path and os.path.exists(cookie_path):
        with open(cookie_path, 'r') as f:
            actual_cookie = f.read().strip()

    if actual_cookie:
        ydl_opts['http_headers']['Cookie'] = actual_cookie

    try:
        with yt_dlp.YoutubeDL(cast(Dict[str, Any], ydl_opts)) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(target_url, download=False)

            image_urls: List[str] = []
            # Cast the info object to a plain Dict so static type checkers don't complain
            # about accessing arbitrary keys on a TypedDict.
            info_dict: Dict[str, Any] = cast(Dict[str, Any], info) if isinstance(info, dict) else {}
            # TikTok slideshows images are often in 'entries' or 'formats'
            entries = info_dict.get('entries')
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and entry.get('url'):
                        image_urls.append(entry['url'])
            else:
                formats = info_dict.get('formats')
                if isinstance(formats, list):
                    # Some versions might put images in formats
                    for f in formats:
                        if not isinstance(f, dict):
                            continue
                        # Look for formats that might be images: no video codec or
                        # explicitly marked as image or with image‑like extension.
                        note = (f.get('format_note') or '').lower()
                        if f.get('url') and (
                            f.get('vcodec') == 'none'
                            or 'image' in note
                            or (f.get('ext') or '').lower() in ("jpg", "jpeg", "png", "webp")
                        ):
                            image_urls.append(f['url'])

            if not image_urls:
                logger.error(f"No images found in slideshow {post.post_id}")
                return None

            downloaded_files: List[str] = []
            session = requests.Session()
            session.headers.update(ydl_opts['http_headers'])

            for i, url in enumerate(image_urls):
                # TikTok URLs often have many params, let's keep it simple
                ext = "jpg"

                filename = os.path.join(creator_path, f"{i+1}.{ext}")

                resp = session.get(url, timeout=10)
                resp.raise_for_status()

                # Check actual content type if possible
                content_type = resp.headers.get('Content-Type', '')
                if 'image/png' in content_type:
                    ext = "png"
                elif 'image/webp' in content_type:
                    ext = "webp"

                if ext != "jpg":
                    filename = os.path.join(creator_path, f"{i+1}.{ext}")

                with open(filename, 'wb') as f:
                    f.write(resp.content)

                downloaded_files.append(filename)
                logger.info(f"Downloaded slideshow image {i+1}/{len(image_urls)}: {filename}")

            return downloaded_files

    except Exception as e:
        logger.error(f"Failed to download slideshow {post.post_id}: {e}")
        return None
import yt_dlp
import logging
import os
import requests
from .fetcher import Post
from typing import Optional, List

logger = logging.getLogger("tok2gram.downloader")

def download_post(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[List[str]]:
    """
    Dispatch download based on post kind.
    Returns a list of file paths.
    """
    if post.kind == 'video':
        path = download_video(post, base_download_path, cookie_path, cookie_content)
        return [path] if path else None
    elif post.kind == 'slideshow':
        return download_slideshow(post, base_download_path, cookie_path, cookie_content)
    else:
        logger.error(f"Unknown post kind: {post.kind}")
        return None

def download_video(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[str]:
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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post.url, download=True)
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

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post.url, download=False)
            
            image_urls = []
            # TikTok slideshows images are often in 'entries' or 'formats'
            if 'entries' in info:
                for entry in info['entries']:
                    if entry.get('url'):
                        image_urls.append(entry['url'])
            elif 'formats' in info:
                # Some versions might put images in formats
                for f in info['formats']:
                    # Look for formats that might be images
                    if f.get('url') and (f.get('vcodec') == 'none' or 'image' in f.get('format_note', '').lower()):
                        image_urls.append(f['url'])
            
            if not image_urls:
                logger.error(f"No images found in slideshow {post.post_id}")
                return None

            downloaded_files = []
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
                if 'image/png' in content_type: ext = "png"
                elif 'image/webp' in content_type: ext = "webp"
                
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
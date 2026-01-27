import yt_dlp
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import requests

from .tiktok_api import Post
from typing import Optional, List

logger = logging.getLogger("tok2gram.downloader")


def _transcode_to_telegram_mp4(input_path: str) -> str:
    """Ensure Telegram Desktop can preview the video.

    Telegram Desktop is picky about container/codec combinations. TikTok downloads
    can end up as:
    - audio-only files (e.g. .m4a)
    - MP4 with unsupported video codec (e.g. AV1/H.265)
    - MP4 missing faststart (moov atom at end), causing bad preview/streaming

    This function forces a widely-supported baseline:
    - container: MP4
    - video: H.264 (libx264) + yuv420p
    - audio: AAC
    - faststart: +faststart
    """

    src = Path(input_path)

    # If ffmpeg isn't installed, keep the original file.
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        logger.warning("ffmpeg not found; skipping Telegram-compatibility transcode")
        return input_path

    # Keep output alongside input.
    out_path = src.with_suffix(".mp4")
    if out_path.resolve() == src.resolve():
        # avoid clobbering in-place; write to temp then replace
        out_path = src.with_name(f"{src.stem}.telegram.mp4")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", dir=str(src.parent)) as tmp:
        tmp_path = Path(tmp.name)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(tmp_path),
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            logger.warning(
                "ffmpeg transcode failed; uploading original file instead. ffmpeg output: %s",
                (proc.stdout or "").strip()[-4000:],
            )
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return input_path

        # Replace/rename output atomically
        try:
            tmp_path.replace(out_path)
        except Exception:
            # fallback: keep temp output
            out_path = tmp_path

        logger.info("Transcoded for Telegram Desktop preview: %s -> %s", src, out_path)
        return str(out_path)
    finally:
        # Cleanup temp if it still exists and wasn't moved
        try:
            if tmp_path.exists() and tmp_path != out_path:
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

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
    
    # Prefer MP4 downloads (helps Telegram compatibility) and avoid formats that
    # frequently produce audio-only outputs.
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 2,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        # Put the moov atom up front when possible (better streaming/preview)
        'postprocessor_args': {
            'ffmpeg': ['-movflags', '+faststart'],
        },
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
                # Enforce Telegram Desktop-friendly MP4 (H.264/AAC + faststart)
                return _transcode_to_telegram_mp4(filename)
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

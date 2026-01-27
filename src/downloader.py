import yt_dlp
import logging
import os
import re
import json
import subprocess
import tempfile
from pathlib import Path

import requests

from .tiktok_api import Post
from typing import Optional, List, Dict, Any

logger = logging.getLogger("tok2gram.downloader")


def _extract_json_script(html_text: str, script_id: str) -> Optional[dict]:
    """Extract embedded JSON from a <script id="..."> tag."""
    try:
        m = re.search(
            rf'<script[^>]+id="{re.escape(script_id)}"[^>]*>(?P<json>.*?)</script>',
            html_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not m:
            return None
        payload = (m.group('json') or '').strip()
        if not payload:
            return None
        return json.loads(payload)
    except Exception:
        return None


def _pick_first_http_url(value: Any) -> Optional[str]:
    """Best-effort helper to pick an http(s) URL from nested structures."""
    if isinstance(value, str):
        return value if value.startswith('http') else None
    if isinstance(value, list):
        for v in value:
            u = _pick_first_http_url(v)
            if u:
                return u
        return None
    if isinstance(value, dict):
        # Common TikTok url list containers
        for k in ("url", "urlList", "url_list", "UrlList", "playUrl", "play_url", "downloadAddr", "playAddr"):
            if k in value:
                u = _pick_first_http_url(value.get(k))
                if u:
                    return u
        for v in value.values():
            u = _pick_first_http_url(v)
            if u:
                return u
        return None
    return None


def _extract_slideshow_urls_from_html(post: Post, session: requests.Session, url: str) -> Dict[str, Any]:
    """Fallback extractor for TikTok photo posts by parsing webpage embedded JSON."""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html_text = resp.text or ""

    sigi = _extract_json_script(html_text, "SIGI_STATE")
    universal = _extract_json_script(html_text, "__UNIVERSAL_DATA_FOR_REHYDRATION__")

    item: Optional[dict] = None
    if isinstance(sigi, dict) and isinstance(sigi.get("ItemModule"), dict):
        item_module = sigi["ItemModule"]
        item = item_module.get(post.post_id) or next(iter(item_module.values()), None)
    
    # Some TikTok pages use the universal rehydration JSON
    if item is None and isinstance(universal, dict):
        # Best-effort: locate an itemStruct-like dict anywhere within
        stack = [universal]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if isinstance(cur.get("itemStruct"), dict):
                    item = cur.get("itemStruct")
                    break
                for v in cur.values():
                    stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)

    image_urls: List[str] = []
    audio_url: Optional[str] = None
    if isinstance(item, dict):
        image_post = item.get("imagePost") or item.get("image_post") or {}
        images = image_post.get("images") or item.get("images") or []
        if isinstance(images, list):
            for img in images:
                u = None
                if isinstance(img, dict):
                    # Prefer imageURL/urlList structure when present
                    u = _pick_first_http_url(img.get("imageURL") or img.get("imageUrl") or img.get("urlList") or img)
                else:
                    u = _pick_first_http_url(img)
                if u and u not in image_urls:
                    image_urls.append(u)

        music = item.get("music") or {}
        audio_url = _pick_first_http_url(music.get("playUrl") or music.get("play_url") or music)

    return {"image_urls": image_urls, "audio_url": audio_url}


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

def download_post(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Dispatch download based on post kind.
    Returns a dict with downloaded media paths.
    """
    if post.kind == 'video':
        path = download_video(post, base_download_path, cookie_path, cookie_content)
        return {"video": path} if path else None
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

def _is_gallery_dl_available() -> bool:
    """Check if gallery-dl is available on the system."""
    try:
        subprocess.run(
            ["gallery-dl", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False


def _download_slideshow_gallery_dl(post: Post, output_path: str) -> Optional[Dict[str, Any]]:
    """
    Download TikTok slideshow images using gallery-dl.
    Returns dict with 'images' list and optional 'audio' path.
    """
    os.makedirs(output_path, exist_ok=True)

    command = [
        "gallery-dl",
        "--directory", output_path,
        "--filename", "{num:>02}.{extension}",
        post.url,
    ]

    logger.info(f"Running gallery-dl for slideshow {post.post_id}: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        logger.debug(f"gallery-dl stdout: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"gallery-dl failed for {post.post_id}: {e.stderr}")
        return None

    # Collect downloaded image files
    downloaded_files: List[str] = []
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    
    if os.path.exists(output_path):
        for filename in sorted(os.listdir(output_path)):
            filepath = os.path.join(output_path, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in image_extensions:
                    downloaded_files.append(filepath)
                    logger.info(f"Found downloaded image: {filepath}")

    if not downloaded_files:
        logger.error(f"gallery-dl completed but no images found in {output_path}")
        return None

    # gallery-dl doesn't download audio separately for TikTok slideshows
    # Audio would need to be extracted via yt-dlp if needed
    return {"images": downloaded_files, "audio": None}


def _download_slideshow_fallback(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fallback slideshow download using yt-dlp metadata extraction and direct HTTP requests.
    Used when gallery-dl is not available or fails.
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
        info = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # NOTE: TikTok photo URLs (`/photo/<id>`) may be unsupported by yt-dlp.
                info = ydl.extract_info(post.url, download=False)
        except Exception as e:
            logger.warning(
                "yt-dlp metadata extraction failed for slideshow %s; falling back to HTML parsing. Error: %s",
                post.post_id,
                e,
            )

        image_urls: List[str] = []
        audio_url: Optional[str] = None

        # Primary extractor: yt-dlp info dict (when available)
        if isinstance(info, dict):
            # TikTok slideshows images are often in 'entries' or 'formats'
            if isinstance(info.get('entries'), list):
                for entry in info['entries']:
                    if isinstance(entry, dict) and entry.get('url'):
                        image_urls.append(entry['url'])
            elif isinstance(info.get('formats'), list):
                for f in info['formats']:
                    if not isinstance(f, dict):
                        continue
                    note = (f.get('format_note') or '').lower()
                    if f.get('url') and (f.get('vcodec') == 'none' or 'image' in note or (f.get('ext') or '').lower() in ("jpg", "jpeg", "png", "webp")):
                        image_urls.append(f['url'])

        session = requests.Session()
        session.headers.update(ydl_opts['http_headers'])

        # Fallback extractor: parse webpage HTML JSON for `/photo/` posts
        if not image_urls:
            logger.info(
                "No slideshow images found via yt-dlp for %s; attempting webpage JSON extraction",
                post.post_id,
            )
            extracted = _extract_slideshow_urls_from_html(post, session, post.url)
            image_urls = extracted.get('image_urls') or []
            audio_url = extracted.get('audio_url')

        if not image_urls:
            logger.error(f"No images found in slideshow {post.post_id}")
            return None

        downloaded_files: List[str] = []
        for i, url in enumerate(image_urls):
            ext = "jpg"
            filename = os.path.join(creator_path, f"{i+1}.{ext}")
            resp = session.get(url, timeout=15)
            resp.raise_for_status()

            content_type = (resp.headers.get('Content-Type', '') or '').lower()
            if 'image/png' in content_type:
                ext = "png"
            elif 'image/webp' in content_type:
                ext = "webp"
            elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = "jpg"

            if ext != "jpg":
                filename = os.path.join(creator_path, f"{i+1}.{ext}")

            with open(filename, 'wb') as f:
                f.write(resp.content)

            downloaded_files.append(filename)
            logger.info(f"Downloaded slideshow image {i+1}/{len(image_urls)}: {filename}")

        audio_path: Optional[str] = None
        if audio_url:
            try:
                logger.info("Downloading slideshow audio for %s", post.post_id)
                aresp = session.get(audio_url, timeout=20)
                aresp.raise_for_status()
                act = (aresp.headers.get('Content-Type', '') or '').lower()
                aext = "m4a"
                if 'audio/mpeg' in act:
                    aext = "mp3"
                elif 'audio/mp4' in act or 'audio/x-m4a' in act:
                    aext = "m4a"
                audio_path = os.path.join(creator_path, f"audio.{aext}")
                with open(audio_path, 'wb') as f:
                    f.write(aresp.content)
            except Exception as e:
                logger.warning("Failed to download slideshow audio for %s: %s", post.post_id, e)

        return {"images": downloaded_files, "audio": audio_path}

    except Exception as e:
        logger.error(f"Failed to download slideshow {post.post_id}: {e}")
        return None


def download_slideshow(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Download a TikTok slideshow (multiple images).
    
    Uses gallery-dl as the primary method for photo posts (more reliable for TikTok images).
    Falls back to yt-dlp/HTML parsing if gallery-dl is unavailable or fails.
    """
    creator_path = os.path.join(base_download_path, post.creator, post.post_id)
    
    # Try gallery-dl first (preferred for TikTok photo posts)
    if _is_gallery_dl_available():
        logger.info(f"Using gallery-dl for slideshow {post.post_id}")
        result = _download_slideshow_gallery_dl(post, creator_path)
        if result and result.get("images"):
            return result
        logger.warning(f"gallery-dl failed for {post.post_id}, falling back to yt-dlp/HTML method")
    else:
        logger.info(f"gallery-dl not available, using fallback method for slideshow {post.post_id}")
    
    # Fallback to yt-dlp/HTML parsing method
    return _download_slideshow_fallback(post, base_download_path, cookie_path, cookie_content)

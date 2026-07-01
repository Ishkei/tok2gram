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
from typing import Optional, List, Dict, Any, cast

logger = logging.getLogger("tok2gram.downloader")


class PostInaccessibleError(Exception):
    """Raised when a post is deleted, private, or region-restricted"""
    pass


class PostRetryableError(Exception):
    """Raised when a post download fails but may succeed on retry"""
    pass


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


def _extract_json_from_pattern(html_text: str, pattern: str) -> Optional[dict]:
    """Extract JSON from HTML using a regex pattern."""
    try:
        m = re.search(pattern, html_text, flags=re.DOTALL)
        if not m:
            return None
        payload = m.group(1).strip()
        if not payload:
            return None
        return json.loads(payload)
    except Exception:
        return None


def _extract_slideshow_urls_from_html(post: Post, session: requests.Session, url: str) -> Dict[str, Any]:
    """Fallback extractor for TikTok photo posts by parsing webpage embedded JSON."""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html_text = resp.text or ""
    
    # Check for login wall or error states
    if "Log in to TikTok" in html_text or "login" in html_text.lower()[:5000]:
        logger.warning(f"Post {post.post_id} may require login or is inaccessible")
    
    # Check for generic landing page (no post data)
    if post.post_id not in html_text:
        logger.warning(f"Post ID {post.post_id} not found in HTML - post may be deleted or private")
        return {"image_urls": [], "audio_url": None, "inaccessible": True}

    sigi = _extract_json_script(html_text, "SIGI_STATE")
    universal = _extract_json_script(html_text, "__UNIVERSAL_DATA_FOR_REHYDRATION__")
    
    # Also check for newer data structures
    ssr_hydrated = _extract_json_from_pattern(
        html_text, 
        r'<script[^>]*>window\._SSR_HYDRATED_DATA\s*=\s*({.+?})</script>'
    )
    init_props = _extract_json_from_pattern(
        html_text,
        r'<script[^>]*>window\.__INIT_PROPS__\s*=\s*({.+?})</script>'
    )
    webapp_data = _extract_json_from_pattern(
        html_text,
        r'<script[^>]*>window\._SSR_HYDRATED_DATA\s*=\s*({.+?})</script>'
    )

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
                # Check for webapp.video-detail structure
                if isinstance(cur.get("video-detail"), dict):
                    item = cur.get("video-detail")
                    break
                for v in cur.values():
                    stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
    
    # Check SSR hydrated data
    if item is None and isinstance(ssr_hydrated, dict):
        # Look for video detail or item info
        stack = [ssr_hydrated]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if isinstance(cur.get("itemInfo"), dict):
                    item = cur.get("itemInfo")
                    break
                if isinstance(cur.get("itemStruct"), dict):
                    item = cur.get("itemStruct")
                    break
                for v in cur.values():
                    stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
    
    # Check __INIT_PROPS__
    if item is None and isinstance(init_props, dict):
        stack = [init_props]
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
        return os.path.abspath(input_path)

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
        "ultrafast",
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
            return os.path.abspath(input_path)

        # Replace/rename output atomically
        try:
            tmp_path.replace(out_path)
        except Exception:
            # fallback: keep temp output
            out_path = tmp_path

        logger.info("Transcoded for Telegram Desktop preview: %s -> %s", src, out_path)
        return os.path.abspath(str(out_path))
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
    Raises PostInaccessibleError if the post is deleted, private, or region-restricted.
    """
    if post.kind == 'video':
        path = download_video(post, base_download_path, cookie_path, cookie_content)
        # If the video download failed (e.g. no formats found), attempt to treat the
        # post as a slideshow as a fallback. Some TikTok slideshows can be misclassified
        # as videos during the probe. Only fallback when no video file was returned.
        if path:
            return {"video": path}
        else:
            logger.warning(
                f"Video download failed for {post.post_id}; attempting slideshow fallback"
            )
            # Update the kind to slideshow so the caller can handle upload appropriately.
            post.kind = 'slideshow'
            # Fall back to slideshow downloader. Note: download_slideshow will not check kind.
            result = download_slideshow(post, base_download_path, cookie_path, cookie_content)
            return result
    elif post.kind == 'slideshow':
        # Attempt to download images for a slideshow. Some TikTok posts are
        # misclassified as slideshows because they expose multiple thumbnails or
        # audio‑only formats but still contain a playable video. If the image
        # download fails, fall back to the video downloader using a reconstructed
        # /video/ URL.
        try:
            result = download_slideshow(post, base_download_path, cookie_path, cookie_content)
            if result:
                if 'video' in result and 'images' not in result:
                    logger.info(f"Slideshow downloader returned a video for {post.post_id}; updating kind to video")
                    post.kind = 'video'
                    # Ensure the video is in a Telegram-friendly format
                    result['video'] = _transcode_to_telegram_mp4(result['video'])
                return result
        except PostInaccessibleError:
            # Post is inaccessible - don't retry, let caller handle
            raise
        except Exception as e:
            logger.warning(f"Slideshow download failed for {post.post_id}: {e}")
        
        # Slideshow extraction failed; attempt to treat as a video. Reconstruct
        # the video URL by replacing /photo/ with /video/ if present. If not
        # present, simply reuse the existing post URL. A None return from
        # download_video will propagate through, signalling that no media could
        # be retrieved.
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
        if vid_path:
            # Update the kind to video so the caller can handle upload appropriately.
            post.kind = 'video'
            return {"video": vid_path}
        return None
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
    
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    elif cookie_content:
        ydl_opts.setdefault('http_headers', {})
        ydl_opts['http_headers']['Cookie'] = cookie_content

    try:
        # Cast ydl_opts to ``Dict[str, Any]`` to satisfy static type checkers.
        ydl_params = cast(Dict[str, Any], ydl_opts)
        with yt_dlp.YoutubeDL(ydl_params) as ydl:  # type: ignore[arg-type]
            # Allow overriding the URL to support fallback scenarios (e.g. when a post
            # was misclassified as a slideshow and we need to try the /video/ endpoint).
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
                # Enforce Telegram Desktop-friendly MP4 (H.264/AAC + faststart)
                out_path = _transcode_to_telegram_mp4(filename)
                return out_path
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


def _download_slideshow_gallery_dl(post: Post, output_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Download TikTok slideshow images using gallery-dl.
    Returns dict with 'images' list and optional 'audio' path.
    Raises PostInaccessibleError if the post is deleted, private, or region-restricted.
    """
    os.makedirs(output_path, exist_ok=True)

    command = [
        "gallery-dl",
        "--directory", output_path,
        "--filename", "{num:>02}.{extension}",
    ]

    # Use Netscape format cookie file with -C option if available
    if cookie_path and os.path.exists(cookie_path):
        command.extend(['-C', cookie_path])
    elif cookie_content:
        # Fallback: use http-headers with cookie content
        command.extend(["-o", f"http-headers=Cookie: {cookie_content}"])
    
    # Always set User-Agent for better reliability
    command.extend(["-a", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"])

    command.append(post.url)

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
        stderr = e.stderr or ""
        stdout = e.stdout or ""
        
        # Check for "No results" - indicates deleted/private/region-restricted post
        if "No results" in stderr or "No results" in stdout:
            logger.warning(f"Post {post.post_id} appears to be deleted, private, or region-restricted (gallery-dl: No results)")
            raise PostInaccessibleError(f"Post {post.post_id} is inaccessible: No results from gallery-dl")
        
        # Check for 403 Forbidden
        if "403" in stderr or "Forbidden" in stderr:
            logger.warning(f"Post {post.post_id} returned 403 Forbidden")
            raise PostInaccessibleError(f"Post {post.post_id} is inaccessible: 403 Forbidden")
        
        logger.error(f"gallery-dl failed for {post.post_id}: {stderr}")
        raise PostRetryableError(f"gallery-dl failed for {post.post_id}: {stderr}")
    
    # Check output for "No results" even on successful exit
    if result.stdout and "No results" in result.stdout:
        logger.warning(f"Post {post.post_id} appears to be deleted, private, or region-restricted (gallery-dl: No results)")
        raise PostInaccessibleError(f"Post {post.post_id} is inaccessible: No results from gallery-dl")

    # Collect downloaded files
    image_files: List[str] = []
    video_files: List[str] = []
    audio_files: List[str] = []
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    video_extensions = {'.mp4', '.mkv', '.webm', '.mov'}
    audio_extensions = {'.mp3', '.m4a', '.wav', '.ogg'}

    if os.path.exists(output_path):
        for filename in sorted(os.listdir(output_path)):
            filepath = os.path.join(output_path, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                abs_path = os.path.abspath(filepath)
                if ext in image_extensions:
                    image_files.append(abs_path)
                    logger.info(f"Found downloaded image: {abs_path}")
                elif ext in video_extensions:
                    video_files.append(abs_path)
                    logger.info(f"Found downloaded video: {abs_path}")
                elif ext in audio_extensions:
                    audio_files.append(abs_path)
                    logger.info(f"Found downloaded audio: {abs_path}")

    # If gallery-dl downloaded a video for what we thought was a slideshow,
    # return it as a video.
    if video_files and not image_files:
        logger.info(f"gallery-dl downloaded a video instead of images for {post.post_id}")
        return {"video": video_files[0]}

    if not image_files:
        logger.error(f"gallery-dl completed but no images or video found in {output_path}")
        return None

    # Pick the first audio file if any
    audio_path = audio_files[0] if audio_files else None
    
    return {"images": image_files, "audio": audio_path}


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

    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    elif cookie_content:
        ydl_opts.setdefault('http_headers', {})
        ydl_opts['http_headers']['Cookie'] = cookie_content

    try:
        info = None
        try:
            # Cast ydl_opts to ``Dict[str, Any]`` to satisfy type checkers when passing
            # into ``yt_dlp.YoutubeDL``.
            ydl_params = cast(Dict[str, Any], ydl_opts)
            with yt_dlp.YoutubeDL(ydl_params) as ydl:  # type: ignore[arg-type]
                # Convert /photo/ URL to /video/ for yt-dlp compatibility
                # yt-dlp doesn't support /photo/ URLs directly, needs /video/ URL
                video_url = post.url.replace('/photo/', '/video/')
                logger.info(f"Using converted URL for yt-dlp: {video_url}")
                info = ydl.extract_info(video_url, download=False)
        except Exception as e:
            error_str = str(e)
            logger.warning(
                "yt-dlp metadata extraction failed for slideshow %s; falling back to HTML parsing. Error: %s",
                post.post_id,
                e,
            )
            # Check for inaccessible post errors
            if "No results" in error_str or "403" in error_str or "Forbidden" in error_str:
                raise PostInaccessibleError(f"Post {post.post_id} is inaccessible: {e}")

        image_urls: List[str] = []
        audio_url: Optional[str] = None

        # Primary extractor: yt-dlp info dict (when available)
        if isinstance(info, dict):
            # Cast the info object to a plain Dict so static type checkers don't
            # complain about accessing arbitrary keys on a TypedDict.
            info_dict: Dict[str, Any] = cast(Dict[str, Any], info)
            # TikTok slideshows images are often in 'entries' or 'formats'
            entries = info_dict.get('entries')
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and entry.get('url'):
                        image_urls.append(entry['url'])
            else:
                formats = info_dict.get('formats')
                if isinstance(formats, list):
                    for f in formats:
                        if not isinstance(f, dict):
                            continue
                        note = (f.get('format_note') or '').lower()
                        # Accept image-like formats or audio‑less video formats as images
                        if f.get('url') and (
                            f.get('vcodec') == 'none'
                            or 'image' in note
                            or (f.get('ext') or '').lower() in ("jpg", "jpeg", "png", "webp")
                        ):
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
            
            # Check if post is inaccessible based on HTML parsing
            if extracted.get('inaccessible'):
                raise PostInaccessibleError(f"Post {post.post_id} is inaccessible: HTML parsing failed")

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

            # Use absolute path for reliability
            abs_path = os.path.abspath(filename)
            downloaded_files.append(abs_path)
            logger.info(f"Downloaded slideshow image {i+1}/{len(image_urls)}: {abs_path}")

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

    except PostInaccessibleError:
        raise
    except Exception as e:
        error_str = str(e)
        # Check for permanent failure indicators
        if "403" in error_str or "Forbidden" in error_str:
            raise PostInaccessibleError(f"Post {post.post_id} is inaccessible: {e}")
        logger.error(f"Failed to download slideshow {post.post_id}: {e}")
        raise PostRetryableError(f"Failed to download slideshow {post.post_id}: {e}")


def download_slideshow(post: Post, base_download_path: str, cookie_path: Optional[str] = None, cookie_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Download a TikTok slideshow (multiple images).
    
    Uses gallery-dl as the primary method for photo posts (more reliable for TikTok images).
    Falls back to yt-dlp/HTML parsing if gallery-dl is unavailable or fails.
    
    Raises PostInaccessibleError if the post is deleted, private, or region-restricted.
    """
    creator_path = os.path.join(base_download_path, post.creator, post.post_id)
    
    # Try gallery-dl first (preferred for TikTok photo posts)
    if _is_gallery_dl_available():
        logger.info(f"Using gallery-dl for slideshow {post.post_id}")
        try:
            result = _download_slideshow_gallery_dl(post, creator_path, cookie_path=cookie_path, cookie_content=cookie_content)
            if result and (result.get("images") or result.get("video")):
                return result
            logger.warning(f"gallery-dl failed for {post.post_id}, falling back to yt-dlp/HTML method")
        except PostInaccessibleError:
            # Re-raise inaccessible errors immediately - don't retry
            raise
        except Exception as e:
            logger.warning(f"gallery-dl failed for {post.post_id}: {e}, falling back to yt-dlp/HTML method")
    else:
        logger.info(f"gallery-dl not available, using fallback method for slideshow {post.post_id}")
    
    # Fallback to yt-dlp/HTML parsing method
    return _download_slideshow_fallback(post, base_download_path, cookie_path, cookie_content)

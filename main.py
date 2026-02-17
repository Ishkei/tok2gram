import logging
import sys
import asyncio
import time
import random
import os
import json
import signal
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from src.config_loader import load_config, load_creators
from src.tiktok_api import fetch_posts, sort_posts_chronologically, Post
from src.downloader import download_post, PostInaccessibleError
from src.core.state import StateStore
from src.telegram_uploader import TelegramUploader
from src.cookie_manager import CookieManager

# Global shutdown event for graceful shutdown
_shutdown_event: Optional[asyncio.Event] = None


def _signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if _shutdown_event:
        _shutdown_event.set()


def _setup_signal_handlers():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: _signal_handler(s, None))
        except NotImplementedError:
            # Not supported on this platform, fallback to signal.signal
            signal.signal(sig, _signal_handler)


def get_retry_delay(attempt: int, is_ip_blocked: bool = False) -> float:
    """Calculate retry delay with exponential backoff."""
    base_delay = 5.0
    if is_ip_blocked:
        # Longer delays for IP-blocked scenarios
        return min(300, base_delay * (2 ** attempt))  # Max 5 minutes
    else:
        return min(60, base_delay * (2 ** attempt))  # Max 60 seconds

# Bot metadata (hardcoded for startup banner)
BOT_NAME = "Tok2Gram"
BOT_VERSION = "1.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/run.log")
    ]
)
logger = logging.getLogger("tok2gram")

async def upload_worker(queue: asyncio.Queue, uploader: TelegramUploader, state: StateStore, chat_id: str, stats: dict):
    while True:
        try:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break
            
            post, media = item
            try:
                logger.debug(f"DEBUG: media type = {type(media)}, value = {media}")
                message_id = None
                if post.kind == 'video' and 'video' in media:
                    message_id = await uploader.upload_video(post, media['video'], chat_id=chat_id)
                elif post.kind == 'slideshow' and 'images' in media:
                    message_id = await uploader.upload_slideshow(post, media['images'], chat_id=chat_id)
                
                if message_id:
                    state.mark_as_uploaded(post.post_id, chat_id, message_id)
                    stats['uploaded'] += 1
                    
                    # Randomized delay between uploads to avoid Telegram flood limits
                    delay = random.uniform(5, 10)
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to process upload for post {post.post_id}: {e}")
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")

async def resume_incomplete_uploads(username: str, state: StateStore, uploader: TelegramUploader, queue: asyncio.Queue, chat_id: str) -> int:
    """
    Check for and resume incomplete uploads for a creator.
    Returns count of posts queued for upload.
    """
    incomplete = state.get_incomplete_uploads(creator=username)
    if not incomplete:
        return 0
    
    logger.info(f"Found {len(incomplete)} incomplete upload(s) for {username}, resuming...")
    resumed_count = 0
    
    for post_id, creator, kind, source_url, downloaded_files_json in incomplete:
        try:
            # Parse downloaded files
            files_dict = json.loads(downloaded_files_json) if downloaded_files_json else None
            if not files_dict:
                logger.warning(f"No file paths recorded for {post_id}, skipping")
                continue
            
            # Verify files still exist
            files_exist = True
            if 'video' in files_dict:
                if not os.path.exists(files_dict['video']):
                    logger.warning(f"Video file missing for {post_id}: {files_dict['video']}")
                    files_exist = False
            elif 'images' in files_dict:
                for img_path in files_dict.get('images', []):
                    if not os.path.exists(img_path):
                        logger.warning(f"Image file missing for {post_id}: {img_path}")
                        files_exist = False
                        break
            
            if not files_exist:
                logger.warning(f"Skipping {post_id} - downloaded files no longer exist")
                continue
            
            # Reconstruct Post object
            post = Post(
                post_id=post_id,
                creator=creator,
                kind=kind,
                url=source_url,
                caption=None,  # Caption not needed for resume
                created_at=None
            )
            
            # Queue for upload
            await queue.put((post, files_dict))
            resumed_count += 1
            logger.info(f"Queued incomplete upload: {post_id} ({kind})")
            
        except Exception as e:
            logger.error(f"Failed to resume upload for {post_id}: {e}")
    
    return resumed_count

async def process_creator(creator_config: dict, settings: dict, state: StateStore, uploader: TelegramUploader, cookie_manager: CookieManager, shutdown_event: asyncio.Event):
    username = creator_config['username']
    user_id = creator_config.get('user_id')
    chat_id = creator_config.get('chat_id') or settings.get('telegram_chat_id')
    fetch_depth = settings.get('fetch_depth', 10)

    if not chat_id:
        logger.error(f"No chat_id specified for creator {username}")
        return

    # Log which identifier we're using
    if user_id:
        logger.info(f"Processing creator: {username} (using user_id: {user_id})")
    else:
        logger.info(f"Processing creator: {username}")
    
    cookie_content = cookie_manager.get_cookie_content()
    cookie_path = cookie_manager.get_current_cookie_path()
    
    loop = asyncio.get_running_loop()
    
    try:
        # Run fetch_posts in executor as it is blocking
        posts = await loop.run_in_executor(None, lambda: fetch_posts(username, depth=fetch_depth, cookie_path=cookie_path, cookie_content=cookie_content, user_id=user_id))
        
        if not posts and cookie_manager.cookie_files:
            logger.warning(f"No posts found for {username}, attempting cookie rotation...")
            cookie_manager.rotate()
            cookie_content = cookie_manager.get_cookie_content()
            cookie_path = cookie_manager.get_current_cookie_path()
            posts = await loop.run_in_executor(None, lambda: fetch_posts(username, depth=fetch_depth, cookie_path=cookie_path, cookie_content=cookie_content, user_id=user_id))
    except Exception as e:
        logger.error(f"Failed to fetch posts for {username}: {e}")
        return

    sorted_posts = sort_posts_chronologically(posts)
    
    stats = {'uploaded': 0}
    ip_blocked_detected = False
    
    # Initialize Queue and Worker for pipelined processing
    queue = asyncio.Queue()
    worker_task = asyncio.create_task(upload_worker(queue, uploader, state, chat_id, stats))
    
    try:
        # First, resume any incomplete uploads
        resumed = await resume_incomplete_uploads(username, state, uploader, queue, chat_id)
        if resumed > 0:
            logger.info(f"Resumed {resumed} incomplete upload(s) for {username}")
        
        for post in sorted_posts:
            # Check shutdown signal
            if shutdown_event.is_set():
                logger.info(f"Shutdown signal received, stopping processing {username}")
                break
            
            if state.is_processed(post.post_id):
                continue
            
            logger.info(f"New post found: {post.post_id} ({post.kind})")
            
            # Download (Non-blocking)
            try:
                # Refresh cookie path in case it changed
                current_cookie_path = cookie_manager.get_current_cookie_path()
                
                # Run download in executor
                media = await loop.run_in_executor(None, lambda: download_post(post, "downloads", cookie_path=current_cookie_path, cookie_content=cookie_content))
                
                if not media:
                    logger.error(f"Failed to download post {post.post_id}")
                    continue
                
                # Record that post was downloaded
                state.record_download(post.post_id, post.creator, post.kind, post.url, post.created_at)
                # Record downloaded files to database for resumption
                state.record_download_files(post.post_id, media)
                    
                # Queue for upload (this will not block unless queue is full, which is default infinite)
                await queue.put((post, media))
                
            except PostInaccessibleError as e:
                logger.warning(f"Post {post.post_id} is inaccessible, skipping: {e}")
                continue
            except Exception as e:
                error_str = str(e)
                if "IP address is blocked" in error_str or "HTTP Error 403" in error_str or "403" in error_str:
                    logger.error(f"IP blocked for post {post.post_id}, skipping creator {username}")
                    # Mark creator for longer cooldown
                    state.mark_ip_blocked(username)
                    ip_blocked_detected = True
                    break  # Stop processing this creator
                else:
                    logger.error(f"Failed to download post {post.post_id}: {e}")
                    continue
        
        # Wait for all uploads to complete
        await queue.join()
        
    finally:
        # Stop worker
        await queue.put(None)
        await worker_task
    
    if ip_blocked_detected:
        logger.warning(f"Creator {username} marked as IP-blocked. Will retry after cooldown period.")
    
    logger.info(f"Finished processing {username}. {stats['uploaded']} new posts uploaded.")

async def main():
    global _shutdown_event
    
    # Startup banner (print only when running as a program, not on import)
    print(f"{BOT_NAME} v{BOT_VERSION}")
    logger.info("Starting Tok2gram...")
    
    # Initialize shutdown event
    _shutdown_event = asyncio.Event()
    
    # Setup signal handlers
    _setup_signal_handlers()
    
    try:
        config = load_config("config.yaml")
        creators = load_creators("creators.yaml")
        settings = config.get('settings', {})
        
        logger.info(f"Loaded config and {len(creators)} creators.")
        
        state = StateStore("data/state.db")
        uploader = TelegramUploader(
            token=config['telegram']['bot_token'],
            chat_id=settings.get('telegram_chat_id')
        )
        
        cookie_manager = CookieManager("data/cookies")
        
        for creator in creators:
            # Check shutdown signal before processing each creator
            if _shutdown_event.is_set():
                logger.info("Shutdown signal received, stopping processing...")
                break
                
            username = creator['username']
            
            # Skip creators that are currently IP-blocked
            if state.is_ip_blocked(username):
                logger.info(f"Skipping {username} - IP blocked (cooldown)")
                continue
            
            await process_creator(creator, settings, state, uploader, cookie_manager, _shutdown_event)
            
            # Check shutdown signal before delay
            if _shutdown_event.is_set():
                logger.info("Shutdown signal received, stopping...")
                break
            
            # Delay between creators to avoid TikTok blocks
            # Use longer delay if the previous creator was IP-blocked
            if state.is_ip_blocked(username):
                delay = get_retry_delay(1, is_ip_blocked=True)
                logger.info(f"IP block detected for {username}, waiting {delay:.1f}s before next creator...")
            else:
                min_delay = settings.get('delay_between_creators_seconds_min', 30)
                max_delay = settings.get('delay_between_creators_seconds_max', 60)
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"Waiting {delay:.1f}s before next creator...")
            
            # Wait with shutdown check
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass  # Timeout means delay completed normally
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)
    finally:
        logger.info("StateStore connections closed via context managers.")

if __name__ == "__main__":
    # Register handlers using signal.signal() for non-asyncio fallback
    def fallback_signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if _shutdown_event:
            _shutdown_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, fallback_signal_handler)
        except (OSError, ValueError):
            pass  # Signal not supported on this platform
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
        if _shutdown_event:
            _shutdown_event.set()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

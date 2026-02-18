import logging
import sys
import asyncio
import time
import random
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from core.config_loader import load_config, load_creators
from tiktok_api import fetch_posts, sort_posts_chronologically
from downloader import download_post
from core.state import StateStore
from telegram_bot.uploader import TelegramUploader
from core.cookie_manager import CookieManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("../data/logs/run.log")
    ]
)
logger = logging.getLogger("tok2gram")

_shutdown_event: asyncio.Event | None = None


def _signal_handler(signame: str):
    logger.warning(f"Received {signame}; initiating graceful shutdown...")
    if _shutdown_event is not None:
        _shutdown_event.set()


def _setup_signal_handlers(loop: asyncio.AbstractEventLoop):
    import signal as _signal
    for sig in (_signal.SIGINT, _signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler, sig.name)
        except NotImplementedError:
            # On non-POSIX, signal handlers may not be available
            pass

async def process_creator(creator_config: dict, settings: dict, state: StateStore, uploader: TelegramUploader, cookie_manager: CookieManager, shutdown_event: asyncio.Event):
    username = creator_config['username']
    chat_id = creator_config.get('telegram_chat_id') or settings.get('telegram_chat_id')
    fetch_depth = settings.get('fetch_depth', 10)

    if not chat_id:
        logger.error(f"No chat_id specified for creator {username}")
        return

    logger.info(f"Processing creator: {username}")
    
    cookie_content = cookie_manager.get_cookie_content()
    posts = fetch_posts(username, depth=fetch_depth, cookie_content=cookie_content)
    
    if not posts and cookie_manager.cookie_files:
        logger.warning(f"No posts found for {username}, attempting cookie rotation...")
        cookie_manager.rotate()
        cookie_content = cookie_manager.get_cookie_content()
        posts = fetch_posts(username, depth=fetch_depth, cookie_content=cookie_content)

    sorted_posts = sort_posts_chronologically(posts)
    
    new_posts_count = 0
    for post in sorted_posts:
        if shutdown_event.is_set():
            logger.info("Shutdown requested; stopping new work for creator loop")
            break
        if state.is_processed(post.post_id):
            continue
        
        logger.info(f"New post found: {post.post_id} ({post.kind})")
        
        # Download
        media = download_post(post, "../data/downloads", cookie_content=cookie_content)
        if not media:
            logger.error(f"Failed to download post {post.post_id}")
            continue
            
        logger.info(f"Downloaded post {post.post_id}, determined kind={post.kind}, media keys={list(media.keys())}")
        state.record_download(post.post_id, post.creator, post.kind, post.url, post.created_at)
        
        # Upload
        try:
            message_id = None
            if post.kind == 'video' and 'video' in media:
                message_id = await uploader.upload_video(post, media['video'])
            elif post.kind == 'slideshow' and 'images' in media:
                message_id = await uploader.upload_slideshow(post, media['images'])
            else:
                logger.error(f"Media format mismatch for {post.post_id}: kind={post.kind}, keys={list(media.keys())}")
            
            if message_id:
                state.mark_as_uploaded(post.post_id, chat_id, message_id)
                new_posts_count += 1
                
                # Randomized delay between uploads to avoid Telegram flood limits
                delay = random.uniform(5, 10)
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                
        except Exception as e:
            logger.error(f"Failed to process upload for post {post.post_id}: {e}")

    logger.info(f"Finished processing {username}. {new_posts_count} new posts uploaded.")

async def main():
    logger.info("Starting Tok2gram...")
    
    try:
        config = load_config("../config/config.yaml")
        creators = load_creators("../config/creators.yaml")
        settings = config.get('settings', {})
        
        logger.info(f"Loaded config and {len(creators)} creators.")
        
        state = StateStore("../state.db")
        uploader = TelegramUploader(
            token=config['telegram']['bot_token'],
            chat_id=settings.get('telegram_chat_id')
        )
        
        cookie_manager = CookieManager("../data/cookies")
        
        global _shutdown_event
        _shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        _setup_signal_handlers(loop)
        
        for creator in creators:
            if _shutdown_event.is_set():
                logger.info("Shutdown requested; breaking before next creator")
                break
            await process_creator(creator, settings, state, uploader, cookie_manager, _shutdown_event)
            
            # Delay between creators to avoid TikTok blocks, but respond to shutdown
            min_delay = settings.get('delay_between_creators_seconds_min', 30)
            max_delay = settings.get('delay_between_creators_seconds_max', 60)
            delay = random.uniform(min_delay, max_delay)
            logger.info(f"Waiting {delay:.1f}s before next creator...")
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received; exiting gracefully.")
        sys.exit(0)
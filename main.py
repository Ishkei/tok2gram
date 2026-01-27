import logging
import sys
import asyncio
import time
import random
from src.config_loader import load_config, load_creators
from src.tiktok_api import fetch_posts, sort_posts_chronologically
from src.downloader import download_post
from src.state import StateStore
from src.telegram_uploader import TelegramUploader
from src.cookie_manager import CookieManager

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

async def process_creator(creator_config: dict, settings: dict, state: StateStore, uploader: TelegramUploader, cookie_manager: CookieManager):
    username = creator_config['username']
    chat_id = creator_config.get('chat_id') or settings.get('telegram_chat_id')
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
        if state.is_processed(post.post_id):
            continue
        
        logger.info(f"New post found: {post.post_id} ({post.kind})")
        
        # Download
        media = download_post(post, "downloads", cookie_content=cookie_content)
        if not media:
            logger.error(f"Failed to download post {post.post_id}")
            continue
            
        state.record_download(post.post_id, post.creator, post.kind, post.url, post.created_at)
        
        # Upload
        try:
            message_id = None
            if post.kind == 'video':
                message_id = await uploader.upload_video(post, media["video"], chat_id=chat_id)
            elif post.kind == 'slideshow':
                image_paths = media.get("images") or []
                audio_path = media.get("audio")
                if image_paths:
                    message_id = await uploader.upload_slideshow(post, image_paths, chat_id=chat_id)
                if audio_path:
                    # Telegram doesn't allow mixing audio + album in a single message.
                    # Upload audio after the album.
                    await uploader.upload_audio(post, audio_path, chat_id=chat_id)
            
            if message_id:
                state.mark_as_uploaded(post.post_id, chat_id, message_id)
                new_posts_count += 1
                
                # Randomized delay between uploads to avoid Telegram flood limits
                delay = random.uniform(5, 10)
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Failed to process upload for post {post.post_id}: {e}")

    logger.info(f"Finished processing {username}. {new_posts_count} new posts uploaded.")

async def main():
    # Startup banner (print only when running as a program, not on import)
    print(f"{BOT_NAME} v{BOT_VERSION}")
    logger.info("Starting Tok2gram...")
    
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
        
        cookie_manager = CookieManager("cookies")
        
        for creator in creators:
            await process_creator(creator, settings, state, uploader, cookie_manager)
            
            # Delay between creators to avoid TikTok blocks
            min_delay = settings.get('delay_between_creators_seconds_min', 30)
            max_delay = settings.get('delay_between_creators_seconds_max', 60)
            delay = random.uniform(min_delay, max_delay)
            logger.info(f"Waiting {delay:.1f}s before next creator...")
            await asyncio.sleep(delay)
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

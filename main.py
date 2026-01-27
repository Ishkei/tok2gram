import logging
import sys
import asyncio
import time
import random
from config_loader import load_config, load_creators
from tiktok import fetch_posts, sort_posts_chronologically
from downloader import download_post
from state import StateStore
from telegram_uploader import TelegramUploader

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

async def process_creator(creator_config: dict, settings: dict, state: StateStore, uploader: TelegramUploader):
    username = creator_config['username']
    chat_id = creator_config.get('telegram_chat_id') or settings.get('telegram_chat_id')
    fetch_depth = settings.get('fetch_depth', 10)
    cookie_path = settings.get('cookie_path')

    if not chat_id:
        logger.error(f"No chat_id specified for creator {username}")
        return

    logger.info(f"Processing creator: {username}")
    
    posts = fetch_posts(username, depth=fetch_depth, cookie_path=cookie_path)
    sorted_posts = sort_posts_chronologically(posts)
    
    new_posts_count = 0
    for post in sorted_posts:
        if state.is_processed(post.post_id):
            continue
        
        logger.info(f"New post found: {post.post_id} ({post.kind})")
        
        # Download
        file_paths = download_post(post, "downloads", cookie_path)
        if not file_paths:
            logger.error(f"Failed to download post {post.post_id}")
            continue
            
        state.record_download(post.post_id, post.creator, post.kind, post.url, post.created_at)
        
        # Upload
        try:
            message_id = None
            if post.kind == 'video':
                message_id = await uploader.upload_video(post, file_paths[0])
            elif post.kind == 'slideshow':
                message_id = await uploader.upload_slideshow(post, file_paths)
            
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
    logger.info("Starting Tok2gram...")
    
    try:
        config = load_config("config.yaml")
        creators = load_creators("creators.yaml")
        settings = config.get('settings', {})
        
        logger.info(f"Loaded config and {len(creators)} creators.")
        
        state = StateStore("state.db")
        uploader = TelegramUploader(
            token=settings['telegram_bot_token'],
            chat_id=settings.get('telegram_chat_id')
        )
        
        for creator in creators:
            await process_creator(creator, settings, state, uploader)
            
            # Delay between creators to avoid TikTok blocks
            delay = random.uniform(30, 60)
            logger.info(f"Waiting {delay:.1f}s before next creator...")
            await asyncio.sleep(delay)
            
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

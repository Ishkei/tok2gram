import os
import asyncio
import re
import logging
import sys
from typing import List, Dict
from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram.constants import ParseMode

# Add project root to sys.path to import from src
sys.path.append("/home/soto/tok2gram")
from src.telegram_uploader import TelegramUploader

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sd_upload")

def load_env_manual():
    env_path = "/home/soto/tok2gram/.env"
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        os.environ[parts[0]] = parts[1]

load_env_manual()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = "-1003605752690"  # From creators.yaml
SOURCE_DIR = "/mnt/chromeos/removable/SD Card/649ff37f91fb9abfcc814718b20c0dd3~tplv-tiktokx-cropcenter;100;100"
STATE_FILE = "/home/soto/tok2gram/logs/uploaded_files.txt"

# Regex to identify base names (e.g., 2025-12-18_@username_ID)
BASE_NAME_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}_@[a-zA-Z0-9_.]+_\d+)')

def get_uploaded_files():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def mark_as_uploaded(file_path):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'a') as f:
        f.write(file_path + "\n")

async def upload_batch(bot, uploader, batch):
    media = []
    opened_files = []
    audio_files = []
    
    try:
        for path in batch:
            ext = os.path.splitext(path)[1].lower()
            final_path = path
            
            # Use compression for large videos
            if ext in ['.mp4', '.mov', '.mkv'] and os.path.getsize(path) > 50 * 1024 * 1024:
                logger.info(f"Compressing large video: {path}")
                final_path = await asyncio.get_event_loop().run_in_executor(None, uploader._compress_video, path)
            
            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                f = open(final_path, 'rb')
                opened_files.append(f)
                media.append(InputMediaPhoto(media=f))
            elif ext in ['.mp4', '.mov', '.mkv']:
                f = open(final_path, 'rb')
                opened_files.append(f)
                media.append(InputMediaVideo(media=f))
            elif ext in ['.mp3', '.m4a', '.opus', '.wav']:
                audio_files.append(final_path)
        
        if len(media) > 1:
            await bot.send_media_group(chat_id=CHAT_ID, media=media)
        elif len(media) == 1:
            f = opened_files[0]
            ext = os.path.splitext(batch[0])[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                await bot.send_photo(chat_id=CHAT_ID, photo=f)
            else:
                await bot.send_video(chat_id=CHAT_ID, video=f)
        
        for ap in audio_files:
            with open(ap, 'rb') as f:
                await bot.send_audio(chat_id=CHAT_ID, audio=f)
                
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return False
    finally:
        for f in opened_files:
            f.close()
    return True

async def upload_files():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env")
        return

    bot = Bot(token=TOKEN)
    uploader = TelegramUploader(TOKEN, CHAT_ID)
    uploaded = get_uploaded_files()
    
    # 1. Collect and group files
    files = sorted(os.listdir(SOURCE_DIR))
    groups: Dict[str, List[str]] = {}
    ungrouped: List[str] = []

    for f in files:
        path = os.path.join(SOURCE_DIR, f)
        if path in uploaded:
            continue
            
        match = BASE_NAME_PATTERN.match(f)
        if match:
            base_name = match.group(1)
            groups.setdefault(base_name, []).append(path)
        elif "~tplv-" in f:
            base_name = f.split("~")[0]
            groups.setdefault(base_name, []).append(path)
        else:
            ungrouped.append(path)

    # 2. Upload groups
    for base_name, paths in groups.items():
        logger.info(f"Processing group: {base_name} ({len(paths)} files)")
        for i in range(0, len(paths), 10):
            batch = paths[i:i+10]
            if await upload_batch(bot, uploader, batch):
                for p in batch:
                    mark_as_uploaded(p)
            await asyncio.sleep(2)

    # 3. Upload ungrouped
    for path in ungrouped:
        logger.info(f"Processing ungrouped: {os.path.basename(path)}")
        if await upload_batch(bot, uploader, [path]):
            mark_as_uploaded(path)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(upload_files())

import logging
import asyncio
from typing import List, Optional
from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram.constants import ParseMode
from tiktok import Post
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("tok2gram.telegram")

class TelegramUploader:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    def _format_caption(self, post: Post) -> str:
        caption = post.caption or ""
        return f"{caption}\n\n— @{post.creator}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_video(self, post: Post, video_path: str) -> Optional[int]:
        """
        Upload a single video to Telegram.
        Returns the message_id if successful.
        """
        caption = self._format_caption(post)
        logger.info(f"Uploading video for post {post.post_id} to {self.chat_id}")
        
        try:
            with open(video_path, 'rb') as video:
                message = await self.bot.send_video(
                    chat_id=self.chat_id,
                    video=video,
                    caption=caption,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60,
                    pool_timeout=60
                )
                logger.info(f"Successfully uploaded video: {message.message_id}")
                return message.message_id
        except Exception as e:
            logger.error(f"Failed to upload video {post.post_id}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_slideshow(self, post: Post, image_paths: List[str]) -> Optional[int]:
        """
        Upload multiple images as a media group.
        Returns the first message_id if successful.
        """
        if not image_paths:
            return None

        caption = self._format_caption(post)
        logger.info(f"Uploading slideshow for post {post.post_id} to {self.chat_id} ({len(image_paths)} images)")

        media = []
        for i, path in enumerate(image_paths):
            if i == 0:
                media.append(InputMediaPhoto(media=open(path, 'rb'), caption=caption))
            else:
                media.append(InputMediaPhoto(media=open(path, 'rb')))

        try:
            messages = await self.bot.send_media_group(
                chat_id=self.chat_id,
                media=media,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
                pool_timeout=60
            )
            # Close file handles
            for m in media:
                if hasattr(m.media, 'close'):
                    m.media.close()

            logger.info(f"Successfully uploaded slideshow: {[m.message_id for m in messages]}")
            return messages[0].message_id
        except Exception as e:
            # Ensure file handles are closed even on error
            for m in media:
                if hasattr(m.media, 'close'):
                    m.media.close()
            logger.error(f"Failed to upload slideshow {post.post_id}: {e}")
            raise

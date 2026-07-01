import logging
import asyncio
from typing import List, Optional, Any
from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram.constants import ParseMode
try:
    from src.tiktok_api import Post
except ImportError:
    # Fallback for test imports
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tiktok_api import Post
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("tok2gram.telegram")

class TelegramUploader:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    def _format_caption(self, post: Post) -> str:
        caption = post.caption or ""
        attribution = f"\n\n— @{post.creator}"
        max_length = 1024
        
        # If total length exceeds limit, truncate the caption part
        if len(caption) + len(attribution) > max_length:
            truncated_len = max_length - len(attribution) - 3  # -3 for "..."
            caption = caption[:truncated_len] + "..."
            
        return f"{caption}{attribution}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_video(self, post: Post, video_path: str, chat_id: Optional[str] = None, message_thread_id: Optional[int] = None) -> Optional[int]:
        """
        Upload a single video to Telegram.
        Returns the message_id if successful.
        """
        target_chat = chat_id or self.chat_id
        caption = self._format_caption(post)
        logger.info(f"Uploading video for post {post.post_id} to {target_chat} (thread: {message_thread_id})")
        
        try:
            with open(video_path, 'rb') as video:
                message = await self.bot.send_video(
                    chat_id=target_chat,
                    video=video,
                    caption=caption,
                    message_thread_id=message_thread_id,
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
    async def upload_slideshow(self, post: Post, image_paths: List[str], chat_id: Optional[str] = None, message_thread_id: Optional[int] = None) -> Optional[int]:
        """
        Upload multiple images as a media group.
        Returns the first message_id if successful.
        """
        if not image_paths:
            return None

        target_chat = chat_id or self.chat_id
        caption = self._format_caption(post)
        logger.info(f"Uploading slideshow for post {post.post_id} to {target_chat} (thread: {message_thread_id}) ({len(image_paths)} images)")

        media: List[InputMediaPhoto] = []
        open_files: List[Any] = []

        try:
            for i, path in enumerate(image_paths):
                try:
                    f = open(path, "rb")
                except Exception as e:
                    logger.error(f"Failed to open image file {path}: {e}")
                    for of in open_files:
                        try:
                            of.close()
                        except Exception:
                            pass
                    raise

                open_files.append(f)
                if i == 0:
                    media.append(InputMediaPhoto(media=f, caption=caption))
                else:
                    media.append(InputMediaPhoto(media=f))

            messages = await self.bot.send_media_group(
                chat_id=target_chat,
                media=media,
                message_thread_id=message_thread_id,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
                pool_timeout=60
            )

            logger.info(f"Successfully uploaded slideshow: {[m.message_id for m in messages]}")
            return messages[0].message_id
        finally:
            for f in open_files:
                try:
                    f.close()
                except Exception as e:
                    logger.warning(f"Error closing slideshow image file: {e}")
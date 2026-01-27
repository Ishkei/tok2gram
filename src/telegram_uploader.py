import logging
import asyncio
import subprocess
from typing import List, Optional
from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from .tiktok_api import Post
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("tok2gram.telegram")


def _has_video_stream(path: str) -> bool:
    """Return True if ffprobe detects at least one video stream."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return proc.returncode == 0 and bool((proc.stdout or "").strip())
    except Exception:
        # If ffprobe isn't available for some reason, assume it's a video.
        return True

class TelegramUploader:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    def _format_caption(self, post: Post) -> str:
        caption = post.caption or ""
        return f"{caption}\n\n— @{post.creator}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_video(self, post: Post, video_path: str, chat_id: Optional[str] = None, message_thread_id: Optional[int] = None) -> Optional[int]:
        """
        Upload a single video to Telegram.
        Returns the message_id if successful.
        """
        target_chat = chat_id or self.chat_id
        caption = self._format_caption(post)
        logger.info(f"Uploading video for post {post.post_id} to {target_chat} (thread: {message_thread_id})")

        # Some downloads can be audio-only (e.g. .m4a). If we try to send those as
        # a video, Telegram Desktop can show "Video.Unsupported.Desktop".
        # In that case, fall back to sending as audio so it plays everywhere.
        if not _has_video_stream(video_path):
            logger.warning(
                "File has no video stream; sending as audio instead: %s",
                video_path,
            )
            try:
                with open(video_path, 'rb') as audio:
                    message = await self.bot.send_audio(
                        chat_id=target_chat,
                        audio=audio,
                        caption=caption,
                        message_thread_id=message_thread_id,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60,
                        pool_timeout=60,
                    )
                    logger.info(f"Successfully uploaded audio: {message.message_id}")
                    return message.message_id
            except Exception as e:
                logger.error(f"Failed to upload audio {post.post_id}: {e}")
                raise
        
        try:
            with open(video_path, 'rb') as video:
                message = await self.bot.send_video(
                    chat_id=target_chat,
                    video=video,
                    caption=caption,
                    message_thread_id=message_thread_id,
                    supports_streaming=True,
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
    async def upload_audio(self, post: Post, audio_path: str, chat_id: Optional[str] = None, message_thread_id: Optional[int] = None) -> Optional[int]:
        """Upload a single audio file to Telegram."""
        target_chat = chat_id or self.chat_id
        caption = self._format_caption(post)
        logger.info(f"Uploading audio for post {post.post_id} to {target_chat} (thread: {message_thread_id})")

        try:
            with open(audio_path, 'rb') as audio:
                message = await self.bot.send_audio(
                    chat_id=target_chat,
                    audio=audio,
                    caption=caption,
                    message_thread_id=message_thread_id,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60,
                    pool_timeout=60,
                )
                logger.info(f"Successfully uploaded audio: {message.message_id}")
                return message.message_id
        except Exception as e:
            logger.error(f"Failed to upload audio {post.post_id}: {e}")
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

        media = []
        for i, path in enumerate(image_paths):
            if i == 0:
                media.append(InputMediaPhoto(media=open(path, 'rb'), caption=caption))
            else:
                media.append(InputMediaPhoto(media=open(path, 'rb')))

        try:
            messages = await self.bot.send_media_group(
                chat_id=target_chat,
                media=media,
                message_thread_id=message_thread_id,
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

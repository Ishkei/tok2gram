import logging
import asyncio
import subprocess
import os
from typing import List, Optional, Any
from telegram import Bot, InputMediaPhoto, InputFile
from telegram.constants import ParseMode
from .tiktok_api import Post
from tenacity import retry, stop_after_attempt, wait_exponential

MAX_ALBUM = 10  # Telegram's hard limit for media groups
CHUNK_DELAY = 1.5  # Delay between chunks to reduce flood risk (seconds)

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
        attribution = f"\n\n— @{post.creator}"
        max_length = 1024
        
        # If total length exceeds limit, truncate the caption part
        if len(caption) + len(attribution) > max_length:
            truncated_len = max_length - len(attribution) - 3  # -3 for "..."
            caption = caption[:truncated_len] + "..."
            
        return f"{caption}{attribution}"

    def _get_dynamic_timeouts(self, file_path: str):
        """
        Calculate dynamic timeouts based on file size.
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            Tuple of (read_timeout, write_timeout, connect_timeout, pool_timeout)
        """
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Estimate upload time at 5 Mbps (typical connection)
        # Time = size / speed, then add buffer
        estimated_time_seconds = (file_size * 8) / (5 * 1024 * 1024)  # 5 Mbps = 5,242,880 bps
        
        if file_size_mb < 20:
            # Small files: keep default timeouts
            read_timeout = 60
            write_timeout = 60
        elif file_size_mb < 50:
            # Medium files (20-50MB): moderate increase
            write_timeout = max(120, int(estimated_time_seconds * 1.5) + 60)
            read_timeout = max(60, int(estimated_time_seconds * 0.5) + 30)
        else:
            # Large files (>50MB): significant increase
            write_timeout = max(180, int(estimated_time_seconds * 1.5) + 120)
            read_timeout = max(90, int(estimated_time_seconds * 0.5) + 60)
        
        connect_timeout = max(30, int(estimated_time_seconds * 0.2) + 10)
        pool_timeout = max(60, int(estimated_time_seconds * 0.3) + 30)
        
        logger.info(
            f"File size: {file_size_mb:.2f}MB, "
            f"estimated upload time: ~{estimated_time_seconds:.0f}s, "
            f"timeouts: read={read_timeout}s, write={write_timeout}s, connect={connect_timeout}s, pool={pool_timeout}s"
        )
        
        return read_timeout, write_timeout, connect_timeout, pool_timeout

    def _get_duration(self, file_path: str) -> Optional[float]:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get duration for {file_path}: {e}")
        return None

    def _compress_video(self, input_path: str, target_size_mb: float = 49.0) -> str:
        """
        Compress video to target size using 2-pass encoding.
        Returns path to compressed video (or original if compression fails/unnecessary).
        """
        try:
            duration = self._get_duration(input_path)
            if not duration:
                logger.warning("Could not determine duration, skipping compression")
                return input_path

            # Calculate target bitrate
            # target_size_bits = target_size_mb * 8 * 1024 * 1024
            # target_bitrate = target_size_bits / duration
            # Use a slightly lower bitrate to be safe (audio is separate)
            audio_bitrate_k = 128
            target_total_bitrate_k = (target_size_mb * 8 * 1024) / duration
            target_video_bitrate_k = max(100, target_total_bitrate_k - audio_bitrate_k)

            logger.info(f"Compressing {input_path} to < {target_size_mb}MB (duration: {duration}s, target video bitrate: {target_video_bitrate_k:.0f}k)")

            # Create temp output path
            directory = os.path.dirname(input_path) or "."
            filename = os.path.basename(input_path)
            base, ext = os.path.splitext(filename)
            output_path = os.path.join(directory, f"{base}_compressed{ext}")

            # 2-pass encoding for better quality at specific size
            # Pass 1
            pass1_cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", "libx264", "-b:v", f"{target_video_bitrate_k}k", "-pass", "1",
                "-f", "mp4", "/dev/null"
            ]
            subprocess.run(pass1_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=directory)

            # Pass 2
            pass2_cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", "libx264", "-b:v", f"{target_video_bitrate_k}k", "-pass", "2",
                "-c:a", "aac", "-b:a", f"{audio_bitrate_k}k",
                "-movflags", "+faststart",
                output_path
            ]
            subprocess.run(pass2_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=directory)

            # Cleanup pass log files
            for f in os.listdir(directory):
                if f.startswith("ffmpeg2pass"):
                    try:
                        os.remove(os.path.join(directory, f))
                    except:
                        pass
            
            if os.path.exists(output_path):
                new_size = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"Compression complete: {new_size:.2f}MB")
                return output_path
            
            return input_path

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return input_path

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_video(self, post: Post, video_path: str, chat_id: Optional[str] = None, message_thread_id: Optional[int] = None) -> Optional[int]:
        """
        Upload a single video to Telegram.
        Returns the message_id if successful.
        """
        target_chat = chat_id or self.chat_id
        caption = self._format_caption(post)
        
        # Check file size (50MB limit for standard bots)
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)
        
        final_video_path = video_path
        
        if file_size_mb >= 50:
            if os.getenv("TELEGRAM_LOCAL_API"):
                logger.info(f"File size {file_size_mb:.2f}MB > 50MB, but TELEGRAM_LOCAL_API is set. Proceeding.")
            else:
                logger.warning(f"File size {file_size_mb:.2f}MB > 50MB and standard API in use. Compressing...")
                final_video_path = self._compress_video(video_path)
                # Recalculate size for logging/timeouts
                file_size = os.path.getsize(final_video_path)
                file_size_mb = file_size / (1024 * 1024)

        # Get dynamic timeouts based on file size
        read_timeout, write_timeout, connect_timeout, pool_timeout = self._get_dynamic_timeouts(final_video_path)
        
        logger.info(f"Uploading video for post {post.post_id} to {target_chat} (thread: {message_thread_id})")

        # Some downloads can be audio-only (e.g. .m4a). If we try to send those as
        # a video, Telegram Desktop can show "Video.Unsupported.Desktop".
        # In that case, fall back to sending as audio so it plays everywhere.
        if not _has_video_stream(final_video_path):
            logger.warning(
                "File has no video stream; sending as audio instead: %s",
                final_video_path,
            )
            try:
                with open(final_video_path, 'rb') as audio:
                    message = await Bot.send_audio(
                        self.bot,
                        chat_id=target_chat,
                        audio=audio,
                        caption=caption,
                        message_thread_id=message_thread_id,
                        read_timeout=read_timeout,
                        write_timeout=write_timeout,
                        connect_timeout=connect_timeout,
                        pool_timeout=pool_timeout,
                    )
                    logger.info(f"Successfully uploaded audio: {message.message_id}")
                    return message.message_id
            except Exception as e:
                logger.error(f"Failed to upload audio {post.post_id}: {e}")
                raise
        
        try:
            with open(final_video_path, 'rb') as video:
                # Prepare send_video kwargs
                send_kwargs = {
                    'chat_id': target_chat,
                    'video': video,
                    'caption': caption,
                    'message_thread_id': message_thread_id,
                    'supports_streaming': True,
                    'read_timeout': read_timeout,
                    'write_timeout': write_timeout,
                    'connect_timeout': connect_timeout,
                    'pool_timeout': pool_timeout,
                }
                
                message = await Bot.send_video(
                    self.bot,
                    **send_kwargs
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
        
        # Get dynamic timeouts based on file size
        read_timeout, write_timeout, connect_timeout, pool_timeout = self._get_dynamic_timeouts(audio_path)
        
        logger.info(f"Uploading audio for post {post.post_id} to {target_chat} (thread: {message_thread_id})")

        try:
            with open(audio_path, 'rb') as audio:
                # Prepare send_audio kwargs
                send_kwargs = {
                    'chat_id': target_chat,
                    'audio': audio,
                    'caption': caption,
                    'message_thread_id': message_thread_id,
                    'read_timeout': read_timeout,
                    'write_timeout': write_timeout,
                    'connect_timeout': connect_timeout,
                    'pool_timeout': pool_timeout,
                }
                
                message = await Bot.send_audio(
                    self.bot,
                    **send_kwargs
                )
                logger.info(f"Successfully uploaded audio: {message.message_id}")
                return message.message_id
        except Exception as e:
            logger.error(f"Failed to upload audio {post.post_id}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_slideshow(self, post: Post, image_paths: List[str], chat_id: Optional[str] = None, message_thread_id: Optional[int] = None) -> Optional[int]:
        """
        Upload multiple images as a media group, chunked into batches of MAX_ALBUM (10) images.
        Returns the first message_id from the first chunk if successful.
        """
        if not image_paths:
            return None

        target_chat = chat_id or self.chat_id
        caption = self._format_caption(post)
        total_images = len(image_paths)
        
        logger.info(f"Uploading slideshow for post {post.post_id} to {target_chat} (thread: {message_thread_id}) ({total_images} images)")
        
        # Calculate number of chunks needed
        num_chunks = (total_images + MAX_ALBUM - 1) // MAX_ALBUM
        logger.info(f"Splitting slideshow into {num_chunks} chunk(s) (max {MAX_ALBUM} images per chunk)")
        
        first_message_id = None
        
        for chunk_idx in range(num_chunks):
            start_idx = chunk_idx * MAX_ALBUM
            end_idx = min(start_idx + MAX_ALBUM, total_images)
            chunk_paths = image_paths[start_idx:end_idx]

            logger.info(
                f"Uploading chunk {chunk_idx + 1}/{num_chunks} with {len(chunk_paths)} images"
            )

            # If there is only one image in this chunk, Telegram API does not support
            # sending a media group with a single item. In that case, send it as a
            # regular photo message instead. Only the first chunk should contain
            # a caption.
            if len(chunk_paths) == 1:
                single_path = chunk_paths[0]
                try:
                    with open(single_path, "rb") as photo_file:
                        # Only attach caption on the very first message of the first chunk
                        photo_caption = caption if chunk_idx == 0 else None
                        message = await Bot.send_photo(
                            self.bot,
                            chat_id=target_chat,
                            photo=photo_file,
                            caption=photo_caption,
                            message_thread_id=message_thread_id,
                            read_timeout=60,
                            write_timeout=60,
                            connect_timeout=60,
                            pool_timeout=60,
                        )
                        logger.info(
                            f"Successfully uploaded photo for chunk {chunk_idx + 1}/{num_chunks}: message_id={message.message_id}"
                        )
                        # Record the first message_id
                        if chunk_idx == 0:
                            first_message_id = message.message_id
                except Exception as e:
                    logger.error(
                        f"Failed to upload photo for chunk {chunk_idx + 1}/{num_chunks} for post {post.post_id}: {e}"
                    )
                    raise
                # Continue to next chunk without using album logic
                continue

            # Otherwise, build an album (media group) for this chunk.
            media: List[InputMediaPhoto] = []
            # Maintain strong references to opened file objects for the duration of the
            # upload. Use typing.Any rather than the built‑in ``any`` function when
            # declaring the list type to satisfy static type checkers like Pylance.
            open_files: List[Any] = []
            for i, path in enumerate(chunk_paths):
                f = open(path, "rb")
                open_files.append(f)  # Keep reference to prevent GC until after sending
                # For albums, pass file-like objects directly to InputMediaPhoto rather than wrapping
                # them in InputFile, as wrapping can cause 'media not found' errors in some library versions.
                if chunk_idx == 0 and i == 0:
                    media.append(InputMediaPhoto(media=f, caption=caption))
                else:
                    media.append(InputMediaPhoto(media=f))

            try:
                messages = await Bot.send_media_group(
                    self.bot,
                    chat_id=target_chat,
                    media=media,
                    message_thread_id=message_thread_id,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60,
                    pool_timeout=60,
                )

                chunk_message_ids = [m.message_id for m in messages]
                logger.info(
                    f"Successfully uploaded chunk {chunk_idx + 1}/{num_chunks}: message_ids={chunk_message_ids}"
                )

                # Store the first message_id from the first chunk
                if chunk_idx == 0 and messages:
                    first_message_id = messages[0].message_id

            except Exception as e:
                logger.error(
                    f"Failed to upload chunk {chunk_idx + 1}/{num_chunks} for post {post.post_id}: {e}"
                )
                raise
            finally:
                # Close all file handles after upload completes
                for f in open_files:
                    f.close()
            
            # Add delay between chunks to reduce flood risk (except after the last chunk)
            if chunk_idx < num_chunks - 1:
                logger.debug(f"Waiting {CHUNK_DELAY}s before next chunk...")
                await asyncio.sleep(CHUNK_DELAY)
        
        logger.info(f"Successfully uploaded all {num_chunks} chunk(s) for post {post.post_id}, first message_id={first_message_id}")
        return first_message_id

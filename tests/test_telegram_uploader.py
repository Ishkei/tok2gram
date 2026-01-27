import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram_uploader import TelegramUploader
from tiktok import Post

@pytest.mark.asyncio
@patch('telegram_uploader.Bot')
async def test_upload_video_success(mock_bot):
    uploader = TelegramUploader("token", "chat_id")
    post = Post("vid1", "creator1", "video", "https://tiktok.com/vid1", "caption", 1600000000)
    
    # Mock bot.send_video
    mock_bot_instance = mock_bot.return_value
    mock_message = MagicMock()
    mock_message.message_id = 123
    mock_bot_instance.send_video = AsyncMock(return_value=mock_message)
    
    with patch('builtins.open', MagicMock()):
        message_id = await uploader.upload_video(post, "dummy_path.mp4")
    
    assert message_id == 123
    mock_bot_instance.send_video.assert_called_once()

@pytest.mark.asyncio
@patch('telegram_uploader.Bot')
async def test_upload_slideshow_success(mock_bot):
    uploader = TelegramUploader("token", "chat_id")
    post = Post("slide1", "creator1", "slideshow", "https://tiktok.com/slide1", "caption", 1600000000)
    
    # Mock bot.send_media_group
    mock_bot_instance = mock_bot.return_value
    mock_message = MagicMock()
    mock_message.message_id = 456
    mock_bot_instance.send_media_group = AsyncMock(return_value=[mock_message])
    
    with patch('builtins.open', MagicMock()):
        message_id = await uploader.upload_slideshow(post, ["img1.jpg", "img2.jpg"])
    
    assert message_id == 456
    mock_bot_instance.send_media_group.assert_called_once()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import sys
import os

# Set up path for imports
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, 'src')
sys.path.insert(0, src_dir)

from telegram_bot.uploader import TelegramUploader
from src.tiktok_api import Post

@pytest.fixture
def uploader():
    return TelegramUploader("token", "chat_id")

@pytest.fixture
def mock_post():
    return Post("vid1", "creator1", "video", "https://tiktok.com/vid1", "caption", 1600000000)

@pytest.mark.asyncio
@patch('telegram_bot.uploader.Bot')
@patch('os.path.getsize')
@patch('os.getenv')
async def test_upload_large_file_compressed(mock_getenv, mock_getsize, mock_bot, uploader, mock_post):
    # Setup
    large_size = 60 * 1024 * 1024  # 60MB
    small_size = 40 * 1024 * 1024  # 40MB
    
    def getsize_side_effect(path):
        if "compressed" in str(path):
            return small_size
        return large_size
        
    mock_getsize.side_effect = getsize_side_effect
    mock_getenv.return_value = None  # Standard API
    
    # Mock compression related methods
    uploader._get_duration = MagicMock(return_value=60.0)
    
    # Mock subprocess.run for compression
    with patch('subprocess.run') as mock_run, \
         patch('os.path.exists', return_value=True), \
         patch('os.remove'), \
         patch('builtins.open', MagicMock()):
        
        # Configure mock_run to handle multiple calls
        # 1. ffprobe duration (mocked by _get_duration override, but just in case)
        # 2. ffmpeg pass 1
        # 3. ffmpeg pass 2
        # 4. ffprobe video stream check
        
        # We can set side_effect to return different mocks or values
        def run_side_effect(*args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            # If it's a verify video stream check (ffprobe)
            if args and "stream=codec_name" in args[0]:
                 m.stdout = "h264"
            return m
            
        mock_run.side_effect = run_side_effect
        
        # Execute
        await uploader.upload_video(mock_post, "large_video.mp4")
        
        # Verify compression was called
        # Check that we called ffmpeg twice (2-pass)
        assert mock_run.call_count >= 2
        
        # Filter for ffmpeg calls
        ffmpeg_calls = [c for c in mock_run.call_args_list if c[0] and "ffmpeg" in c[0][0]]
        assert len(ffmpeg_calls) >= 2
        
        # Check passes
        assert "-pass" in ffmpeg_calls[0][0][0]
        assert "1" in ffmpeg_calls[0][0][0]
        assert "-pass" in ffmpeg_calls[1][0][0]
        assert "2" in ffmpeg_calls[1][0][0]

@pytest.mark.asyncio
@patch('telegram_bot.uploader.Bot')
@patch('os.path.getsize')
@patch('os.getenv')
async def test_upload_large_file_local_api(mock_getenv, mock_getsize, mock_bot, uploader, mock_post):
    # Setup
    large_size = 60 * 1024 * 1024  # 60MB
    mock_getsize.return_value = large_size
    mock_getenv.return_value = "1"  # Local API enabled
    
    # Execute
    with patch('subprocess.run') as mock_run, \
         patch('builtins.open', MagicMock()):
        
        await uploader.upload_video(mock_post, "large_video.mp4")
        
        # Verify NO compression was attempted
        mock_run.assert_not_called()

@pytest.mark.asyncio
@patch('telegram_bot.uploader.Bot')
@patch('os.path.getsize')
async def test_upload_small_file_no_compression(mock_getsize, mock_bot, uploader, mock_post):
    # Setup
    small_size = 20 * 1024 * 1024  # 20MB
    mock_getsize.return_value = small_size
    
    # Execute
    with patch('subprocess.run') as mock_run, \
         patch('builtins.open', MagicMock()):
        
        await uploader.upload_video(mock_post, "small_video.mp4")
        
        # Verify NO compression
        mock_run.assert_not_called()

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.downloader import download_video, download_slideshow
from src.tiktok_api import Post


@patch('src.downloader.yt_dlp.YoutubeDL')
def test_download_video_success(mock_ytdl, tmp_path):
    post = Post("vid1", "creator1", "video", "https://tiktok.com/vid1", "caption", 1600000000)
    download_path = tmp_path / "downloads"
    download_path.mkdir()
    
    # Mock successful download
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    # Mock prepare_filename to return an existing file
    mock_instance.prepare_filename.return_value = str(download_path / "vid1.mp4")
    
    # Create dummy file
    with open(download_path / "vid1.mp4", "w") as f:
        f.write("dummy content")
    
    result_path = download_video(post, str(download_path))
    
    # Check yt-dlp was called with correct options
    args, kwargs = mock_ytdl.call_args
    opts = args[0]
    assert opts['format'] == 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    assert opts['merge_output_format'] == 'mp4'
    assert opts['concurrent_fragment_downloads'] in [1, 2]
    
    assert result_path is not None
    assert os.path.exists(result_path)


@patch('src.downloader.yt_dlp.YoutubeDL')
def test_download_slideshow_success(mock_ytdl, tmp_path):
    post = Post("slide1", "creator1", "slideshow", "https://tiktok.com/slide1", "caption", 1600000000)
    download_path = tmp_path / "downloads"
    download_path.mkdir()
    
    # Mock slideshow metadata
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {
        'entries': [
            {'url': 'img1_url', 'id': 'img1', 'ext': 'jpg'},
            {'url': 'img2_url', 'id': 'img2', 'ext': 'jpg'}
        ]
    }
    
    # In the real implementation we'll need to mock the file creation if we check existence
    with patch('src.downloader.requests.Session') as mock_session:
        mock_resp = MagicMock()
        mock_resp.content = b"fake image content"
        mock_resp.headers = {'Content-Type': 'image/jpeg'}
        mock_session.return_value.get.return_value = mock_resp
        
        result_paths = download_slideshow(post, str(download_path))
    
    assert result_paths is not None
    # Check if we got images or video
    assert 'images' in result_paths or 'video' in result_paths

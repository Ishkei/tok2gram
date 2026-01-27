import pytest
from unittest.mock import patch, MagicMock
from downloader import download_video, download_slideshow
from tiktok import Post

@patch('downloader.yt_dlp.YoutubeDL')
def test_download_video_success(mock_ytdl, tmp_path):
    post = Post("vid1", "creator1", "video", "https://tiktok.com/vid1", "caption", 1600000000)
    download_path = tmp_path / "downloads"
    download_path.mkdir()
    
    # Mock successful download
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    
    result_path = download_video(post, str(download_path))
    
    # Check yt-dlp was called with correct options
    args, kwargs = mock_ytdl.call_args
    opts = args[0]
    assert opts['format'] == 'bv*+ba/best'
    assert opts['merge_output_format'] == 'mp4'
    assert opts['concurrent_fragment_downloads'] in [1, 2]
    
    assert result_path is not None

@patch('downloader.yt_dlp.YoutubeDL')
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
    with patch('downloader.requests.Session') as mock_session:
        mock_resp = MagicMock()
        mock_resp.content = b"fake image content"
        mock_resp.headers = {'Content-Type': 'image/jpeg'}
        mock_session.return_value.get.return_value = mock_resp
        
        result_paths = download_slideshow(post, str(download_path))
    
    assert len(result_paths) == 2
    assert "1.jpg" in result_paths[0]

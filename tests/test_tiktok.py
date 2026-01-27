import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.tiktok.fetcher import fetch_posts, Post, sort_posts_chronologically

def test_post_model():
    post = Post(
        post_id="123",
        creator="user",
        kind="video",
        url="https://tiktok.com/123",
        caption="test caption",
        created_at=1674768503
    )
    assert post.post_id == "123"
    assert post.kind == "video"

@patch('src.tiktok.fetcher.yt_dlp.YoutubeDL')
def test_fetch_posts_success(mock_ytdl):
    # Mock yt-dlp response
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {
        'entries': [
            {
                'id': 'post1',
                'webpage_url': 'url1',
                'description': 'caption1',
                'timestamp': 1600000000,
                'uploader': 'creator1',
                '_type': 'video' # simplified
            }
        ]
    }
    
    posts = fetch_posts("creator1", depth=10)
    assert len(posts) == 1
    assert posts[0].post_id == 'post1'
    assert posts[0].creator == 'creator1'

@patch('src.tiktok.fetcher.yt_dlp.YoutubeDL')
def test_fetch_posts_slideshow_detection(mock_ytdl):
    # Mock yt-dlp response for slideshow
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {
        'entries': [
            {
                'id': 'slide1',
                'webpage_url': 'url1',
                'description': 'caption1',
                'timestamp': 1600000000,
                '_type': 'playlist' # yt-dlp flat-extract often marks slideshows as playlist
            },
            {
                'id': 'slide2',
                'webpage_url': 'url2',
                'description': 'caption2',
                'timestamp': 1600000500,
                'type': 'slideshow' # some versions might use 'type'
            }
        ]
    }
    
    posts = fetch_posts("creator1", depth=10)
    assert len(posts) == 2
    assert posts[0].kind == 'slideshow'
    assert posts[1].kind == 'slideshow'

@patch('src.tiktok.fetcher.yt_dlp.YoutubeDL')
def test_fetch_posts_mixed_media_prioritization(mock_ytdl):
    # Mock mixed media (video metadata + playlist type)
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {
        'entries': [
            {
                'id': 'mixed1',
                'webpage_url': 'url1',
                '_type': 'video', 
                'type': 'slideshow' # Contradictory, should favor video
            }
        ]
    }
    
    posts = fetch_posts("creator1", depth=10)
    assert len(posts) == 1
    assert posts[0].kind == 'video'

def test_sort_posts_chronologically():
    p1 = Post("1", "c1", "v", "u1", "cap1", 1000)
    p2 = Post("2", "c1", "v", "u2", "cap2", 500)
    p3 = Post("3", "c1", "v", "u3", "cap3", None)
    
    sorted_posts = sort_posts_chronologically([p1, p2, p3])
    
    assert sorted_posts[0].post_id == "2" # 500
    assert sorted_posts[1].post_id == "1" # 1000
    assert sorted_posts[2].post_id == "3" # None (last)

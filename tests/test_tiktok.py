import pytest
from unittest.mock import patch, MagicMock
from tiktok import fetch_posts, Post, sort_posts_chronologically

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

@patch('tiktok.yt_dlp.YoutubeDL')
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

def test_sort_posts_chronologically():
    p1 = Post("1", "c1", "v", "u1", "cap1", 1000)
    p2 = Post("2", "c1", "v", "u2", "cap2", 500)
    p3 = Post("3", "c1", "v", "u3", "cap3", None)
    
    sorted_posts = sort_posts_chronologically([p1, p2, p3])
    
    assert sorted_posts[0].post_id == "2" # 500
    assert sorted_posts[1].post_id == "1" # 1000
    assert sorted_posts[2].post_id == "3" # None (last)

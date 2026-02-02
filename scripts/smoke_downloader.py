import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.downloader import download_video
from src.tiktok_api import Post

logging.basicConfig(level=logging.INFO)

def smoke_test():
    # Use a real TikTok URL for testing
    post = Post(
        post_id="7580769030701681942", # Just an example ID
        creator="adrynalynbeats",
        kind="video",
        url="https://www.tiktok.com/@adrynalynbeats/video/7580769030701681942?is",
        caption="test download",
        created_at=None
    )
    
    download_dir = "downloads_test"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    print(f"Testing download_video for {post.url}...")
    path = download_video(post, download_dir, cookie_path="data/cookies/sid_tt_1.txt")
    
    if path and os.path.exists(path):
        print(f"Successfully downloaded to: {path}")
        print(f"File size: {os.path.getsize(path)} bytes")
    else:
        print("Download failed.")

if __name__ == "__main__":
    smoke_test()

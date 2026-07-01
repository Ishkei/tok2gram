import logging
import os
import sys
import asyncio

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.downloader import download_post
from src.tiktok_api import Post

logging.basicConfig(level=logging.INFO)

async def smoke_test():
    # Use a real TikTok URL for testing
    post = Post(
        post_id="7600025807024606494", 
        creator="edstarginfiniteet",
        kind="slideshow",
        url="https://www.tiktok.com/@rebelsoulrudegyal/photo/7600025807024606494",
        caption="test slideshow download with images",
        created_at=None
    )
    
    download_dir = "downloads_test"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    print(f"Testing download_post for {post.url}...")
    # download_post in src/downloader.py returns a dict
    media = download_post(post, download_dir, cookie_path="cookies/sid_tt_1.txt")
    
    if media:
        print(f"Successfully downloaded: {media}")
        if 'video' in media:
            path = media['video']
            if os.path.exists(path):
                print(f"Video file exists at: {path}")
                print(f"File size: {os.path.getsize(path)} bytes")
        if 'images' in media:
            print(f"Images: {len(media['images'])} files")
            for img in media['images']:
                if os.path.exists(img):
                    print(f"  Image file exists at: {img}")
    else:
        print("Download failed.")

if __name__ == "__main__":
    asyncio.run(smoke_test())

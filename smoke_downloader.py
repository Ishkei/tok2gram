import logging
import os
from downloader import download_video
from tiktok import Post

logging.basicConfig(level=logging.INFO)

def smoke_test():
    # Use a real TikTok URL for testing
    post = Post(
        post_id="7462618991475756321", # Just an example ID
        creator="khaby.lame",
        kind="video",
        url="https://www.tiktok.com/@khaby.lame/video/7462618991475756321",
        caption="test download",
        created_at=None
    )
    
    download_dir = "downloads_test"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    print(f"Testing download_video for {post.url}...")
    path = download_video(post, download_dir, cookie_path="cookies/sid_tt_1.txt")
    
    if path and os.path.exists(path):
        print(f"Successfully downloaded to: {path}")
        print(f"File size: {os.path.getsize(path)} bytes")
    else:
        print("Download failed.")

if __name__ == "__main__":
    smoke_test()

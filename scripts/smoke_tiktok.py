import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tiktok.fetcher import fetch_posts

logging.basicConfig(level=logging.INFO)

def smoke_test():
    # Use one of the creators from the list
    username = "adrynalynbeats" # Use a famous one for testing if yours are small/private
    print(f"Testing fetch_posts for {username}...")
    posts = fetch_posts(username, depth=5, cookie_path="data/cookies/sid_tt_1.txt")
    
    print(f"Found {len(posts)} posts.")
    for p in posts:
        print(f"- [{p.kind}] {p.post_id}: {p.caption[:50]}... ({p.url})")

if __name__ == "__main__":
    smoke_test()
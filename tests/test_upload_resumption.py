#!/usr/bin/env python3
"""
Test script to verify upload resumption functionality.
This script simulates downloads and incomplete uploads to test the resumption system.
"""
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.state import StateStore
from src.tiktok_api import Post

def test_upload_resumption():
    """Test the upload resumption system."""
    print("Testing Upload Resumption System")
    print("=" * 50)
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_state.db")
    
    try:
        # Initialize state store
        state = StateStore(db_path)
        print("✓ Database initialized")
        
        # Create a test post
        post_id = "7234567890123456789"
        creator = "test_creator"
        
        # Record download
        state.record_download(
            post_id=post_id,
            creator=creator,
            kind="video",
            url="https://www.tiktok.com/@test/video/7234567890123456789",
            created_at=1234567890
        )
        print(f"✓ Recorded download for post {post_id}")
        
        # Record downloaded files
        test_files = {"video": "/tmp/test_video.mp4"}
        state.record_download_files(post_id, test_files)
        print(f"✓ Recorded file paths: {test_files}")
        
        # Query incomplete uploads
        incomplete = state.get_incomplete_uploads(creator=creator)
        print(f"✓ Found {len(incomplete)} incomplete upload(s)")
        
        if len(incomplete) == 1:
            retrieved_post = incomplete[0]
            print(f"  - Post ID: {retrieved_post[0]}")
            print(f"  - Creator: {retrieved_post[1]}")
            print(f"  - Kind: {retrieved_post[2]}")
            print(f"  - Files: {retrieved_post[4]}")
            print("✓ Successfully retrieved incomplete upload data")
        else:
            print("✗ Expected 1 incomplete upload, got", len(incomplete))
            return False
        
        # Test get_downloaded_files
        files = state.get_downloaded_files(post_id)
        if files == test_files:
            print("✓ get_downloaded_files() works correctly")
        else:
            print(f"✗ Expected {test_files}, got {files}")
            return False
        
        # Simulate successful upload
        state.mark_as_uploaded(post_id, "-1001234567890", 12345)
        print("✓ Marked post as uploaded")
        
        # Verify no more incomplete uploads
        incomplete_after = state.get_incomplete_uploads(creator=creator)
        if len(incomplete_after) == 0:
            print("✓ No incomplete uploads after marking as uploaded")
        else:
            print(f"✗ Expected 0 incomplete uploads, got {len(incomplete_after)}")
            return False
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print("\n✓ Cleaned up test database")
        except:
            pass

if __name__ == "__main__":
    success = test_upload_resumption()
    sys.exit(0 if success else 1)

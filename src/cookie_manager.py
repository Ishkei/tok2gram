import os
import glob
import logging
import random
from typing import List, Optional

logger = logging.getLogger("tok2gram.cookies")

class CookieManager:
    def __init__(self, cookies_dir: str):
        self.cookies_dir = cookies_dir
        self.cookie_files = []
        self.current_index = 0
        self.refresh()

    def refresh(self):
        """Find all .txt files in the cookies directory."""
        self.cookie_files = sorted(glob.glob(os.path.join(self.cookies_dir, "*.txt")))
        if not self.cookie_files:
            logger.warning(f"No cookie files found in {self.cookies_dir}")
        else:
            # Set permissions to 600 for security as per story 5.1
            for f in self.cookie_files:
                try:
                    os.chmod(f, 0o600)
                except Exception as e:
                    logger.debug(f"Could not set permissions for {f}: {e}")
            logger.info(f"Loaded {len(self.cookie_files)} cookie files from {self.cookies_dir}")

    def get_current_cookie_path(self) -> Optional[str]:
        if not self.cookie_files:
            return None
        return self.cookie_files[self.current_index]

    def get_cookie_content(self) -> Optional[str]:
        path = self.get_current_cookie_path()
        if not path:
            return None
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read cookie file {path}: {e}")
            return None

    def rotate(self) -> Optional[str]:
        """Switch to the next available cookie and return the new cookie path."""
        if not self.cookie_files:
            return None
        self.current_index = (self.current_index + 1) % len(self.cookie_files)
        new_path = self.get_current_cookie_path()
        logger.info(f"Rotated to cookie file: {new_path}")
        return new_path

    def handle_failure(self):
        """Called when a request fails due to potential blocking."""
        self.rotate()

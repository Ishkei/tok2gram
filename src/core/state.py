import sqlite3
import logging
import os
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger("tok2gram.state")

class StateStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # In-memory tracking for IP-blocked creators (not persisted to DB)
        self.ip_blocked_creators: Dict[str, datetime] = {}
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS posts (
                        post_id     TEXT PRIMARY KEY,
                        creator     TEXT NOT NULL,
                        kind        TEXT NOT NULL,
                        source_url  TEXT NOT NULL,
                        created_at  INTEGER,
                        downloaded_at INTEGER,
                        uploaded_at INTEGER,
                        telegram_chat_id TEXT,
                        telegram_message_id TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_creator_uploaded ON posts(creator, uploaded_at)")
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def mark_ip_blocked(self, username: str):
        """Mark a creator as IP-blocked with timestamp."""
        self.ip_blocked_creators[username] = datetime.now()
        logger.warning(f"Creator {username} marked as IP-blocked (cooldown: 1 hour)")

    def is_ip_blocked(self, username: str) -> bool:
        """Check if creator is currently IP-blocked (cooldown period)."""
        if username not in self.ip_blocked_creators:
            return False
        blocked_time = self.ip_blocked_creators[username]
        # 1 hour cooldown for IP-blocked creators
        cooldown = timedelta(hours=1)
        is_blocked = datetime.now() - blocked_time < cooldown
        if not is_blocked:
            # Clear expired block
            del self.ip_blocked_creators[username]
            logger.info(f"IP block for {username} has expired")
        return is_blocked

    def clear_ip_block(self, username: str):
        """Clear IP block status for a creator."""
        if username in self.ip_blocked_creators:
            del self.ip_blocked_creators[username]
            logger.info(f"IP block cleared for {username}")

    def is_processed(self, post_id: str) -> bool:
        """
        Check if a post has been successfully uploaded.
        Returns True if post_id exists and uploaded_at is not null.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT uploaded_at FROM posts WHERE post_id = ?", 
                    (post_id,)
                )
                row = cursor.fetchone()
                return row is not None and row[0] is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking processed status for {post_id}: {e}")
            return False

    def record_download(self, post_id: str, creator: str, kind: str, url: str, created_at: Optional[int]):
        """Record that a post has been downloaded (but not yet uploaded)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO posts (post_id, creator, kind, source_url, created_at, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(post_id) DO UPDATE SET
                        downloaded_at = excluded.downloaded_at
                """, (post_id, creator, kind, url, created_at, int(time.time())))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error recording download for {post_id}: {e}")

    def mark_as_uploaded(self, post_id: str, chat_id: str, message_id: int):
        """Mark a post as successfully uploaded to Telegram."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE posts SET 
                        uploaded_at = ?,
                        telegram_chat_id = ?,
                        telegram_message_id = ?
                    WHERE post_id = ?
                """, (int(time.time()), str(chat_id), str(message_id), post_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error marking post {post_id} as uploaded: {e}")
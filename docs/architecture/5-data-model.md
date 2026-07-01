# 5. Data Model

## 5.1 SQLite schema (minimal)
```sql
CREATE TABLE IF NOT EXISTS posts (
  post_id     TEXT PRIMARY KEY,
  creator     TEXT NOT NULL,
  kind        TEXT NOT NULL,         -- 'video' | 'slideshow'
  source_url  TEXT NOT NULL,
  created_at  INTEGER,               -- unix epoch (nullable)
  downloaded_at INTEGER,             -- unix epoch (nullable)
  uploaded_at INTEGER,               -- unix epoch (nullable)
  telegram_chat_id TEXT,             -- stored for audit (nullable)
  telegram_message_id TEXT           -- stored for audit (nullable)
);
```

Indexes (optional):
```sql
CREATE INDEX IF NOT EXISTS idx_posts_creator_uploaded ON posts(creator, uploaded_at);
```

## 5.2 Config files
### `config.yaml`
- `fetch_depth: 10`
- `download_workers: 3`
- `yt_concurrent_fragments: 2`
- `retry_uploads: 1`
- delay jitter ranges

### `creators.yaml`
Per creator routing:
- `username`
- `chat_id`
- optional `topic_id`

---

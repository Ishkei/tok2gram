# 4. Runtime Components

## 4.1 `main.py` (Orchestrator)
Responsibilities:
- Load configuration
- Iterate creators sequentially
- Fetch newest posts
- For each unseen post: download → upload → commit state
- Exit cleanly

## 4.2 Intake (`tiktok.py`)
Responsibilities:
- Get latest post list (depth = 10) per creator
- Normalize to a common internal `Post` model:
  - `post_id`
  - `creator`
  - `kind` (`video` or `slideshow`)
  - `url`
  - `caption`
  - `created_at` (if available)

Implementation approach:
- Prefer **yt-dlp metadata extraction** to avoid fragile HTML parsing.

## 4.3 Downloader (`downloader.py`)
Responsibilities:
- Download post media into structured folders
- Enforce best-quality formats:
  - format: `bv*+ba/best`
  - merge: mp4
- Limit fragmentation and concurrency for stability
- Support cookie rotation and retry

Parallelism:
- Use `ThreadPoolExecutor(max_workers=2..3)` for downloads only.

## 4.4 Telegram Uploader (`telegram_uploader.py`)
Responsibilities:
- Upload files sequentially
- Route to chat + optional topic (`message_thread_id`)
- Apply caption template:
  - `{original_caption}\n\n— @{creator}`
- For slideshows: `sendMediaGroup`, caption on the **first item only**
- Retry upload **once** on transient failures

## 4.5 State Store (`state.py`)
Responsibilities:
- SQLite open/close and schema management
- Fast lookup: `is_processed(post_id)`
- Transactional write: `mark_uploaded(post_id, ...)` **only after** successful Telegram upload

---

# TikTok → Telegram Local Monitor & Reposter  
## Architecture Document

**Author (Architect):** Winston 🏗️  
**Target environment:** ChromeOS (rammus) + Crostini Debian 12 (Bookworm)  
**Execution model:** Short-lived, stateless runs (manual or cron). No systemd/daemons required.

---

## Tech Stack Specification

### 1. Runtime & Language
- Python 3.11
- ChromeOS Crostini (Debian 12 – Bookworm)
- Chosen for stability, performance, and library support

### 2. Core Dependencies
- **yt-dlp** — TikTok media downloading
- **python-telegram-bot v20.x** — Telegram Bot API
- **SQLite (stdlib)** — persistent state storage

### 3. Concurrency Model
- Hybrid model
- Sequential creator processing
- `ThreadPoolExecutor` with **2–3 workers** for downloads
- Telegram uploads are **strictly sequential**

### 4. Supporting Libraries
- **PyYAML** — configuration parsing
- **tenacity** — retry and backoff logic
- **logging (stdlib)** — application logging

### 5. Project Structure
- `main.py` entrypoint
- Downloader wrapper
- Telegram uploader module
- SQLite state handler
- Configuration files
- Cookies, downloads, and logs directories

### 6. yt-dlp Configuration
- Best available video + audio: `bv*+ba/best`
- Merge to MP4 without re-encoding
- Limited fragment concurrency for VM stability

### 7. Telegram Upload Strategy
- `sendVideo` for videos (streaming enabled)
- `sendMediaGroup` for slideshows
- Caption applied to **first image only**
- Optional topic routing via `message_thread_id`

### 8. Explicit Exclusions
- No Selenium or browser automation
- No Docker or systemd
- No cloud services
- No HTML scraping
- No async-heavy frameworks

### 9. Stability Rationale
Minimal dependencies, conservative parallelism, and stateless execution ensure resilience against
ChromeOS sleep, reboots, and TikTok platform changes.

---

## 1. Architecture Goals

### Functional goals
- Monitor **one or many TikTok creators**
- Detect **new uploads only**
- Download **videos** and **photo/slideshow** posts
- Upload to **Telegram channel/group** (optionally specific topics)
- Avoid duplicates across runs/reboots/sleep

### Non-functional goals
- **Restart-safe**: state survives reboots and container pauses
- **Best available quality**: no unnecessary recompression
- **Operational simplicity**: minimal dependencies; easy to debug locally
- **Resilient to TikTok anti-bot** measures via cookie support and backoff

---

## 2. System Context

### External systems
- **TikTok**: content source (rate-limited; may require cookie authentication)
- **Telegram Bot API**: content destination

### Local systems
- **Crostini filesystem**: stores state DB and downloaded media
- **Scheduler** (optional): cron if available; otherwise manual runs

---

## 3. High-Level Architecture

```
┌────────────────────────────┐
│   creators.yaml / config    │
└───────────────┬────────────┘
                │
┌───────────────▼────────────┐
│   Monitor / Intake Layer    │
│   - fetch latest 10 posts   │
│   - sort oldest→newest      │
└───────────────┬────────────┘
                │ post IDs
┌───────────────▼────────────┐
│   State Layer (SQLite)      │
│   - dedupe by post_id       │
│   - mark after upload       │
└───────────────┬────────────┘
                │ unseen posts
┌───────────────▼────────────┐
│   Download Layer (yt-dlp)   │
│   - best quality            │
│   - slideshow support       │
│   - 2–3 parallel downloads  │
└───────────────┬────────────┘
                │ local files
┌───────────────▼────────────┐
│ Telegram Upload Layer       │
│ - sendVideo                 │
│ - sendMediaGroup            │
│ - sequential uploads        │
└────────────────────────────┘
```

---

## 4. Runtime Components

### 4.1 `main.py` (Orchestrator)
Responsibilities:
- Load configuration
- Iterate creators sequentially
- Fetch newest posts
- For each unseen post: download → upload → commit state
- Exit cleanly

### 4.2 Intake (`tiktok.py`)
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

### 4.3 Downloader (`downloader.py`)
Responsibilities:
- Download post media into structured folders
- Enforce best-quality formats:
  - format: `bv*+ba/best`
  - merge: mp4
- Limit fragmentation and concurrency for stability
- Support cookie rotation and retry

Parallelism:
- Use `ThreadPoolExecutor(max_workers=2..3)` for downloads only.

### 4.4 Telegram Uploader (`telegram_uploader.py`)
Responsibilities:
- Upload files sequentially
- Route to chat + optional topic (`message_thread_id`)
- Apply caption template:
  - `{original_caption}\n\n— @{creator}`
- For slideshows: `sendMediaGroup`, caption on the **first item only**
- Retry upload **once** on transient failures

### 4.5 State Store (`state.py`)
Responsibilities:
- SQLite open/close and schema management
- Fast lookup: `is_processed(post_id)`
- Transactional write: `mark_uploaded(post_id, ...)` **only after** successful Telegram upload

---

## 5. Data Model

### 5.1 SQLite schema (minimal)
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

### 5.2 Config files
#### `config.yaml`
- `fetch_depth: 10`
- `download_workers: 3`
- `yt_concurrent_fragments: 2`
- `retry_uploads: 1`
- delay jitter ranges

#### `creators.yaml`
Per creator routing:
- `username`
- `chat_id`
- optional `topic_id`

---

## 6. Sequence Flows

### 6.1 Normal run (per creator)
1. Load config and creators
2. Fetch latest 10 posts
3. Sort oldest→newest
4. For each post:
   - If already in SQLite → skip
   - Else download media (parallel pool)
5. Upload each completed download sequentially
6. After successful upload → mark in SQLite (`uploaded_at`)

### 6.2 Failure handling
**TikTok fetch fails**
- Rotate cookie
- Backoff (skip creator this run)
- Do not write state

**Download fails**
- Retry download once (optional)
- Do not upload; do not mark state

**Telegram upload fails**
- Retry once
- If still fails: do not mark state (post will retry next run)

---

## 7. Quality Strategy

### Videos
- Use best available streams with yt-dlp:
  - `-f "bv*+ba/best"`
  - `--merge-output-format mp4`
- Avoid ffmpeg recompression unless absolutely necessary.

### Slideshows
- Download original images where possible.
- Upload as album (`sendMediaGroup`) to preserve ordering.

---

## 8. Security & Compliance

- Store Telegram bot token in **environment variable** or `.env` not committed to git
- Store TikTok cookies in `cookies/` and restrict permissions (`chmod 600`)
- Respect platform terms and applicable laws; avoid aggressive polling and scraping.

---

## 9. Deployment (Local-only)

### Recommended filesystem layout
```
~/tiktok-monitor/
  .venv/
  main.py
  config.yaml
  creators.yaml
  state.db
  cookies/
  downloads/
  logs/
```

### Execution options
- Manual:
  - `source .venv/bin/activate && python main.py`
- Cron (if available):
  - every 15 minutes, append logs to `logs/run.log`
  - safe across sleep because state + fetch_depth ensure catch-up

---

## 10. Observability

- Use stdlib `logging`
- Log:
  - per creator: fetch success/failure
  - number of unseen posts
  - download results per post
  - Telegram upload success/failure
  - state commits

---

## 11. Architecture Decisions (Why this design)

- **SQLite** over JSON: crash-safe, atomic, scalable enough
- **Stateless runs**: correct for ChromeOS sleep/pause semantics
- **Sequential uploads**: avoids Telegram flood limits and simplifies retries
- **Parallel downloads only**: balances speed and stability

---

## 12. Open Extensions (Future-safe)
- Proxy support
- Multiple cookie pool with health scoring
- Per-creator poll intervals
- Optional media cleanup policy (age-based deletion)
- Add “dry-run” mode (no downloads/uploads; intake only)

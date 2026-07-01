# Tech Stack Specification

## 1. Runtime & Language
- Python 3.11
- ChromeOS Crostini (Debian 12 – Bookworm)
- Chosen for stability, performance, and library support

## 2. Core Dependencies
- **yt-dlp** — TikTok media downloading
- **python-telegram-bot v20.x** — Telegram Bot API
- **SQLite (stdlib)** — persistent state storage

## 3. Concurrency Model
- Hybrid model
- Sequential creator processing
- `ThreadPoolExecutor` with **2–3 workers** for downloads
- Telegram uploads are **strictly sequential**

## 4. Supporting Libraries
- **PyYAML** — configuration parsing
- **tenacity** — retry and backoff logic
- **logging (stdlib)** — application logging

## 5. Project Structure
- `main.py` entrypoint
- Downloader wrapper
- Telegram uploader module
- SQLite state handler
- Configuration files
- Cookies, downloads, and logs directories

## 6. yt-dlp Configuration
- Best available video + audio: `bv*+ba/best`
- Merge to MP4 without re-encoding
- Limited fragment concurrency for VM stability

## 7. Telegram Upload Strategy
- `sendVideo` for videos (streaming enabled)
- `sendMediaGroup` for slideshows
- Caption applied to **first image only**
- Optional topic routing via `message_thread_id`

## 8. Explicit Exclusions
- No Selenium or browser automation
- No Docker or systemd
- No cloud services
- No HTML scraping
- No async-heavy frameworks

## 9. Stability Rationale
Minimal dependencies, conservative parallelism, and stateless execution ensure resilience against
ChromeOS sleep, reboots, and TikTok platform changes.

---

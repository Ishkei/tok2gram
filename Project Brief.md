# TikTok → Telegram Local Monitor & Reposter  
## Project Brief

## 1. Objective
Build a **local-only**, **restart-safe** system that monitors specified TikTok creators and reposts new
content to Telegram channels or topics with best available quality, avoiding duplicates and surviving
ChromeOS sleep and reboots.

## 2. Operating Environment
- Host OS: ChromeOS (rammus)
- Linux VM: Crostini (Debian 12 – Bookworm)
- Execution model: short-lived, stateless script runs
- No always-on services, systemd, or Docker

## 3. High-Level Architecture
ChromeOS → Crostini Debian VM containing:
- Python virtualenv
- `main.py` entrypoint
- yt-dlp
- SQLite `state.db`
- `creators.yaml`, `config.yaml`
- `cookies/`, `downloads/`, `logs/`

## 4. Core Workflow
1. Load configuration and creators
2. Fetch latest **10 posts per creator**
3. Sort posts **oldest → newest**
4. Download unseen posts
5. Upload to Telegram
6. Mark posts as processed
7. Exit cleanly

## 5. Content Handling Rules
- **Videos:** Best quality, uploaded with caption + attribution
- **Slideshows:** Uploaded as Telegram media groups, caption on first image only
- **Mixed media:** Treated as video-first

## 6. Edge Case Rules
- Pinned videos: upload once
- Deleted & reposted content: treated as new
- Duplicate detection: post ID only
- Failed uploads: retry once, not marked processed unless successful
- Music metadata ignored

## 7. Parallelism & Performance
- Parallel downloads: **2–3**
- yt-dlp fragments: **1–2**
- Creators processed sequentially
- Telegram uploads sequential
- No recompression or recoding

## 8. Quality Guarantees
- Video: best available video + audio, merged to MP4 without re-encoding
- Photos: original quality
- Telegram bot must be admin to avoid auto-compression

## 9. State Management
- SQLite `state.db` stores processed post IDs
- Posts marked processed only after successful download and upload

## 10. Anti-Block Strategy
- TikTok cookies (`sid_tt`)
- Cookie rotation on failure
- Conservative polling and random delays
- Residential IP behavior

## 11. Configuration Files
- `creators.yaml`: creator usernames and Telegram routing
- `config.yaml`: parallelism limits, retry counts, delays

## 12. Non-Goals
- Real-time streaming
- Web UI
- Cloud hosting
- Content hashing
- Audio-only extraction
- Analytics dashboards

## 13. Success Criteria
- No duplicate uploads
- No missed content across restarts
- Preserved quality
- Clean recovery from sleep/reboot
- Reliable operation on ChromeOS Crostini

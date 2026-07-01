# TikTok → Telegram Local Monitor & Reposter  
## Step-by-step Build Checklist (ChromeOS Crostini / Debian 12)

> Goal: Build a local-only, restart-safe system that monitors one/many TikTok creators, downloads new posts (videos + slideshows), and reposts them to Telegram (channel/group + optional topics).  
> Execution model: short-lived runs (manual or cron). State is stored in SQLite to prevent duplicates.

---

## 0) Pre-flight (10 minutes)

### 0.1 Confirm your environment
- [x] You’re in the Linux container (Crostini) terminal
- [x] `python3 --version` shows **3.11+** (3.11 recommended)
- [x] You have enough disk space for downloads

### 0.2 Create a working folder
- [x] Create a project directory:
  - [x] `mkdir -p ~/tiktok-monitor && cd ~/tiktok-monitor`

---

## 1) Telegram Setup (15 minutes)

### 1.1 Create a bot token
- [x] Open Telegram and chat with **@BotFather**
- [x] Run `/newbot`
- [x] Save the **BOT_TOKEN** somewhere safe

### 1.2 Prepare your target (channel/group)
- [x] Create a Telegram **channel** or **group** (supergroup recommended)
- [x] Add your bot as an **administrator**
- [x] Confirm the bot can post messages in that chat

### 1.3 Get your `chat_id` (and optional `message_thread_id`)
- [x] Add your bot to the chat
- [x] Send a test message in the target chat
- [x] Use a small helper script later (Phase 4) to print:
  - [x] `chat_id`
  - [x] `message_thread_id` (only if using topics)

✅ Validation: You have `BOT_TOKEN` + a target chat where the bot is admin.

---

## 2) TikTok Cookie Setup (10 minutes)

TikTok frequently rate-limits unauthenticated scraping. Cookies help.

### 2.1 Extract `sid_tt` cookie (Chrome)
- [x] Login to TikTok in Chrome
- [x] Open DevTools → **Network**
- [x] Refresh TikTok
- [x] Click any request → **Headers** → **Cookie**
- [x] Copy the cookie value that starts with `sid_tt=...;`

### 2.2 Store cookie locally
- [x] Create cookies directory:
  - [x] `mkdir -p cookies`
- [x] Save cookie to file (example):
  - [x] `printf '%s\n' 'sid_tt=PASTE_VALUE_HERE;' > cookies/sid_tt_1.txt`

Optional (recommended later):
- [x] Add a second cookie file for rotation (`cookies/sid_tt_2.txt`)

✅ Validation: `cookies/sid_tt_1.txt` exists and contains a valid `sid_tt=...;` line.

---

## 3) Project Scaffold (20–30 minutes)

### 3.1 Create Python virtual environment
- [x] Install venv tools (if needed):
  - [x] `sudo apt update && sudo apt install -y python3-venv python3-pip`
- [x] Create venv:
  - [x] `python3 -m venv .venv`
- [x] Activate venv:
  - [x] `source .venv/bin/activate`

### 3.2 Install dependencies
- [x] Create `requirements.txt` with:
  - [x] `yt-dlp`
  - [x] `python-telegram-bot==20.*`
  - [x] `PyYAML`
  - [x] `tenacity`
- [x] Install:
  - [x] `pip install -U pip`
  - [x] `pip install -r requirements.txt`

### 3.3 Create folders
- [x] `mkdir -p downloads logs`

### 3.4 Create configuration files
- [x] Create `config.yaml` (suggested defaults):
  - [x] `fetch_depth: 10`
  - [x] `download_workers: 3`
  - [x] `yt_concurrent_fragments: 2`
  - [x] `retry_uploads: 1`
  - [x] `delay_between_creators_seconds_min: 10`
  - [x] `delay_between_creators_seconds_max: 30`
- [x] Create `creators.yaml` with structure:
  - [x] list of creators with Telegram routing:
    - [x] `username`
    - [x] `chat_id`
    - [x] optional `topic_id`

✅ Validation: venv activates; `pip show yt-dlp` works; config files exist.

---

## 4) Phase Validation: Telegram Connectivity (15–30 minutes)

### 4.1 Run a Telegram smoke test
- [x] Write a tiny script to send a text message using `BOT_TOKEN` to your `chat_id`
- [x] Confirm it arrives in the correct chat/topic

### 4.2 Permissions validation
- [x] If posting to a channel, confirm bot is **admin**
- [x] If using topics, confirm `message_thread_id` works (post goes to the right topic)

✅ Validation: Bot can successfully post to your chosen destination.

---

## 5) Phase Validation: TikTok Intake (30–60 minutes)

### 5.1 Verify yt-dlp can read a TikTok URL
- [x] Test on a single known TikTok URL (no automation yet)
- [x] Confirm you can extract metadata and download

### 5.2 Implement “fetch latest 10 posts per creator”
- [x] For each creator:
  - [x] Fetch latest posts (depth = 10)
  - [x] Extract post IDs
  - [x] Print IDs (no downloads yet)

### 5.3 Add SQLite state
- [x] Create `state.db`
- [x] Create `posts` table:
  - [x] `post_id` PRIMARY KEY
  - [x] `creator`
  - [x] `created_at`
  - [x] `uploaded_at`
- [x] On each run:
  - [x] Filter out already-seen IDs

✅ Validation: Running twice prints the same IDs but reports “already seen” correctly.

---

## 6) Phase Validation: Download Layer (45–90 minutes)

### 6.1 Best-quality video download rules (locked)
- [x] Use format: `bv*+ba/best`
- [x] Merge to MP4 without re-encode
- [x] Set fragment concurrency (1–2)

### 6.2 Parallel downloads (locked)
- [x] Use a thread pool with **2–3** workers
- [x] Keep creators sequential

### 6.3 Slideshow handling (locked)
- [x] Detect slideshow posts
- [x] Download all images
- [x] Keep order stable

✅ Validation: For a creator with a slideshow, all images download in correct order.

---

## 7) Phase Validation: Telegram Upload Layer (60–90 minutes)

### 7.1 Upload rules (locked)
- [x] Uploads are **sequential**
- [x] Videos via `sendVideo`
- [x] Slideshows via `sendMediaGroup`
- [x] Caption only on first image in media group

### 7.2 Caption template (locked)
- [x] `{original_caption}`
- [x] blank line
- [x] `— @{creator}`

### 7.3 Failure behavior (locked)
- [x] Retry upload once
- [x] If still fails: do **not** mark processed

✅ Validation: A successful upload results in a DB entry with `uploaded_at`.

---

## 8) End-to-End (30–45 minutes)

### 8.1 First full run (one creator)
- [x] Run the script for one creator
- [x] Confirm:
  - [x] downloads happen
  - [x] Telegram uploads happen
  - [x] DB marks processed only after upload

### 8.2 Second run (dedupe)
- [x] Run again immediately
- [x] Confirm: **no duplicate uploads**

✅ Validation: End-to-end works for one creator with zero duplicates.

---

## 9) Local Scheduling (Optional)

### 9.1 Cron (if available)
- [x] Check cron availability:
  - [x] `which cron || which crond`
- [x] If present, add a crontab entry:
  - [x] `*/15 * * * * /home/YOURUSER/tiktok-monitor/.venv/bin/python /home/YOURUSER/tiktok-monitor/main.py >> /home/YOURUSER/tiktok-monitor/logs/run.log 2>&1`

> ChromeOS sleep will pause cron runs. That’s OK: the next run catches up because we fetch the latest 10 posts and dedupe via SQLite.

✅ Validation: Log file updates on schedule when the container is awake.

---

## 10) Operational Checklist (Ongoing)

- [x] Rotate cookies if TikTok blocks you (add `sid_tt_2.txt`)
- [x] Keep polling conservative (15–30 min per creator)
- [x] Monitor `logs/run.log` for errors
- [x] Verify disk space periodically (downloads grow quickly)
- [x] If Telegram rejects large files: confirm bot admin and channel limits

---

## Definition of Done

- [x] New posts are reposted exactly once
- [x] Videos are best available quality (no re-encode)
- [x] Slideshows post correctly as albums
- [x] System survives sleep/reboot (rerun catches up)
- [x] All behavior matches the accepted defaults

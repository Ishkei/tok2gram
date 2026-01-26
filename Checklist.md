# TikTok → Telegram Local Monitor & Reposter  
## Step-by-step Build Checklist (ChromeOS Crostini / Debian 12)

> Goal: Build a local-only, restart-safe system that monitors one/many TikTok creators, downloads new posts (videos + slideshows), and reposts them to Telegram (channel/group + optional topics).  
> Execution model: short-lived runs (manual or cron). State is stored in SQLite to prevent duplicates.

---

## 0) Pre-flight (10 minutes)

### 0.1 Confirm your environment
- [ ] You’re in the Linux container (Crostini) terminal
- [ ] `python3 --version` shows **3.11+** (3.11 recommended)
- [ ] You have enough disk space for downloads

### 0.2 Create a working folder
- [ ] Create a project directory:
  - [ ] `mkdir -p ~/tiktok-monitor && cd ~/tiktok-monitor`

---

## 1) Telegram Setup (15 minutes)

### 1.1 Create a bot token
- [ ] Open Telegram and chat with **@BotFather**
- [ ] Run `/newbot`
- [ ] Save the **BOT_TOKEN** somewhere safe

### 1.2 Prepare your target (channel/group)
- [ ] Create a Telegram **channel** or **group** (supergroup recommended)
- [ ] Add your bot as an **administrator**
- [ ] Confirm the bot can post messages in that chat

### 1.3 Get your `chat_id` (and optional `message_thread_id`)
- [ ] Add your bot to the chat
- [ ] Send a test message in the target chat
- [ ] Use a small helper script later (Phase 4) to print:
  - [ ] `chat_id`
  - [ ] `message_thread_id` (only if using topics)

✅ Validation: You have `BOT_TOKEN` + a target chat where the bot is admin.

---

## 2) TikTok Cookie Setup (10 minutes)

TikTok frequently rate-limits unauthenticated scraping. Cookies help.

### 2.1 Extract `sid_tt` cookie (Chrome)
- [ ] Login to TikTok in Chrome
- [ ] Open DevTools → **Network**
- [ ] Refresh TikTok
- [ ] Click any request → **Headers** → **Cookie**
- [ ] Copy the cookie value that starts with `sid_tt=...;`

### 2.2 Store cookie locally
- [ ] Create cookies directory:
  - [ ] `mkdir -p cookies`
- [ ] Save cookie to file (example):
  - [ ] `printf '%s\n' 'sid_tt=PASTE_VALUE_HERE;' > cookies/sid_tt_1.txt`

Optional (recommended later):
- [ ] Add a second cookie file for rotation (`cookies/sid_tt_2.txt`)

✅ Validation: `cookies/sid_tt_1.txt` exists and contains a valid `sid_tt=...;` line.

---

## 3) Project Scaffold (20–30 minutes)

### 3.1 Create Python virtual environment
- [ ] Install venv tools (if needed):
  - [ ] `sudo apt update && sudo apt install -y python3-venv python3-pip`
- [ ] Create venv:
  - [ ] `python3 -m venv .venv`
- [ ] Activate venv:
  - [ ] `source .venv/bin/activate`

### 3.2 Install dependencies
- [ ] Create `requirements.txt` with:
  - [ ] `yt-dlp`
  - [ ] `python-telegram-bot==20.*`
  - [ ] `PyYAML`
  - [ ] `tenacity`
- [ ] Install:
  - [ ] `pip install -U pip`
  - [ ] `pip install -r requirements.txt`

### 3.3 Create folders
- [ ] `mkdir -p downloads logs`

### 3.4 Create configuration files
- [ ] Create `config.yaml` (suggested defaults):
  - [ ] `fetch_depth: 10`
  - [ ] `download_workers: 3`
  - [ ] `yt_concurrent_fragments: 2`
  - [ ] `retry_uploads: 1`
  - [ ] `delay_between_creators_seconds_min: 10`
  - [ ] `delay_between_creators_seconds_max: 30`
- [ ] Create `creators.yaml` with structure:
  - [ ] list of creators with Telegram routing:
    - [ ] `username`
    - [ ] `chat_id`
    - [ ] optional `topic_id`

✅ Validation: venv activates; `pip show yt-dlp` works; config files exist.

---

## 4) Phase Validation: Telegram Connectivity (15–30 minutes)

### 4.1 Run a Telegram smoke test
- [ ] Write a tiny script to send a text message using `BOT_TOKEN` to your `chat_id`
- [ ] Confirm it arrives in the correct chat/topic

### 4.2 Permissions validation
- [ ] If posting to a channel, confirm bot is **admin**
- [ ] If using topics, confirm `message_thread_id` works (post goes to the right topic)

✅ Validation: Bot can successfully post to your chosen destination.

---

## 5) Phase Validation: TikTok Intake (30–60 minutes)

### 5.1 Verify yt-dlp can read a TikTok URL
- [ ] Test on a single known TikTok URL (no automation yet)
- [ ] Confirm you can extract metadata and download

### 5.2 Implement “fetch latest 10 posts per creator”
- [ ] For each creator:
  - [ ] Fetch latest posts (depth = 10)
  - [ ] Extract post IDs
  - [ ] Print IDs (no downloads yet)

### 5.3 Add SQLite state
- [ ] Create `state.db`
- [ ] Create `posts` table:
  - [ ] `post_id` PRIMARY KEY
  - [ ] `creator`
  - [ ] `created_at`
  - [ ] `uploaded_at`
- [ ] On each run:
  - [ ] Filter out already-seen IDs

✅ Validation: Running twice prints the same IDs but reports “already seen” correctly.

---

## 6) Phase Validation: Download Layer (45–90 minutes)

### 6.1 Best-quality video download rules (locked)
- [ ] Use format: `bv*+ba/best`
- [ ] Merge to MP4 without re-encode
- [ ] Set fragment concurrency (1–2)

### 6.2 Parallel downloads (locked)
- [ ] Use a thread pool with **2–3** workers
- [ ] Keep creators sequential

### 6.3 Slideshow handling (locked)
- [ ] Detect slideshow posts
- [ ] Download all images
- [ ] Keep order stable

✅ Validation: For a creator with a slideshow, all images download in correct order.

---

## 7) Phase Validation: Telegram Upload Layer (60–90 minutes)

### 7.1 Upload rules (locked)
- [ ] Uploads are **sequential**
- [ ] Videos via `sendVideo`
- [ ] Slideshows via `sendMediaGroup`
- [ ] Caption only on first image in media group

### 7.2 Caption template (locked)
- [ ] `{original_caption}`
- [ ] blank line
- [ ] `— @{creator}`

### 7.3 Failure behavior (locked)
- [ ] Retry upload once
- [ ] If still fails: do **not** mark processed

✅ Validation: A successful upload results in a DB entry with `uploaded_at`.

---

## 8) End-to-End (30–45 minutes)

### 8.1 First full run (one creator)
- [ ] Run the script for one creator
- [ ] Confirm:
  - [ ] downloads happen
  - [ ] Telegram uploads happen
  - [ ] DB marks processed only after upload

### 8.2 Second run (dedupe)
- [ ] Run again immediately
- [ ] Confirm: **no duplicate uploads**

✅ Validation: End-to-end works for one creator with zero duplicates.

---

## 9) Local Scheduling (Optional)

### 9.1 Cron (if available)
- [ ] Check cron availability:
  - [ ] `which cron || which crond`
- [ ] If present, add a crontab entry:
  - [ ] `*/15 * * * * /home/YOURUSER/tiktok-monitor/.venv/bin/python /home/YOURUSER/tiktok-monitor/main.py >> /home/YOURUSER/tiktok-monitor/logs/run.log 2>&1`

> ChromeOS sleep will pause cron runs. That’s OK: the next run catches up because we fetch the latest 10 posts and dedupe via SQLite.

✅ Validation: Log file updates on schedule when the container is awake.

---

## 10) Operational Checklist (Ongoing)

- [ ] Rotate cookies if TikTok blocks you (add `sid_tt_2.txt`)
- [ ] Keep polling conservative (15–30 min per creator)
- [ ] Monitor `logs/run.log` for errors
- [ ] Verify disk space periodically (downloads grow quickly)
- [ ] If Telegram rejects large files: confirm bot admin and channel limits

---

## Definition of Done

- [ ] New posts are reposted exactly once
- [ ] Videos are best available quality (no re-encode)
- [ ] Slideshows post correctly as albums
- [ ] System survives sleep/reboot (rerun catches up)
- [ ] All behavior matches the accepted defaults

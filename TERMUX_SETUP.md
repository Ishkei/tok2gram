# Tok2Gram Termux Android Setup Guide

## Overview

This guide explains how to set up and run Tok2Gram on Android using Termux.

## Prerequisites

- Android device (7.0 or higher recommended)

- At least 500MB free storage

- Stable internet connection

## Step 1: Install Termux

1. **Download Termux from F-Droid** (recommended):

- Visit [https://f-droid.org/packages/com.termux](https://f-droid.org/packages/com.termux)

- Download the latest APK

- Install it (enable "Unknown sources" in Android settings if needed)

 

> ⚠️ Avoid the Play Store version - it's outdated and no longer maintained

2. **Alternative: Download from GitHub**:

- Visit [https://github.com/termux/termux-app/releases](https://github.com/termux/termux-app/releases)

- Download the latest `termux-app_*_debug.apk` or `termux-app_*_release.apk`

- Install the APK

## Step 2: Update Termux

Open Termux and run:

```bash
pkg update && pkg upgrade -y
pkg install coreutils curl wget git openssl-tool
```

## Step 3: Install System Dependencies

Tok2Gram requires these system packages for yt-dlp, gallery-dl, and other dependencies:

```bash
pkg install -y python ffmpeg wget curl git libffi openssl clang ca-certificates
```

## Step 4: Install Python and Create Virtual Environment

```bash
# Verify Python version (should be 3.11+)
python --version

# Upgrade pip
pip install --upgrade pip

# Create virtual environment in your project directory
python -m venv ~/tok2gram/venv
```

## Step 5: Transfer Tok2Gram Files

### Option A: Git Clone (Recommended)

```bash
cd ~

git clone https://github.com/yourusername/tok2gram.git

cd tok2gram
```

### Option B: From Local Device

1. Upload files to cloud storage (Google Drive, Dropbox)

2. Download in Termux:

```bash
cd ~

termux-setup-storage

cp ~/storage/shared/path/to/tok2gram.zip .

unzip tok2gram.zip
```

### Option C: Using ADB

```bash
adb push tok2gram /data/data/com.termux/files/home/tok2gram
```

## Step 6: Install Python Dependencies

```bash
cd ~/tok2gram

source venv/bin/activate

pip install --upgrade pip

# Install all dependencies
pip install yt-dlp python-telegram-bot==20.* PyYAML tenacity requests pytest-asyncio gallery-dl
```

## Step 7: Configure Storage Access

```bash
termux-setup-storage
```

This creates symlinks in `~/storage/`:

- `~/storage/downloads/` - Downloads folder

- `~/storage/shared/` - Internal storage

## Step 8: Configure Tok2Gram

1. **Copy configuration template**:

```bash
cp config.yaml config.yaml.example

cp creators.yaml creators.yaml.example
```

2. **Edit configuration**:

```bash
nano config.yaml
```

Set your Telegram bot token:

```yaml
bot_token: "YOUR_ACTUAL_BOT_TOKEN"
```

3. **Edit creators**:

```bash
nano creators.yaml
```

Add your TikTok creators and Telegram channels.

4. **Set up cookies** (optional but recommended):

- Create `data/cookies/` directory

- Place TikTok session cookies (sid_tt files) there

## Step 9: Test the Program

```bash
cd ~/tok2gram

source venv/bin/activate

python main.py
```

The program should start monitoring TikTok creators. Use `Ctrl+C` to stop.

## Step 10: Run in Background

### Option A: Using nohup + termux-wake-lock

```bash
termux-wake-lock

nohup python ~/tok2gram/main.py > output.log 2>&1 &
```

### Option B: Using tmux (Recommended)

```bash
# Install tmux
pkg install tmux

# Create new session

tmux new-session -s tok2gram

# Inside tmux, run:

termux-wake-lock && python main.py

# Detach from tmux: Ctrl+B, then D

# Reattach: tmux attach-session -t tok2gram
```

### Option C: Using termux-services

```bash
pkg install termux-services

sv-enable cron # or other service manager
```

## Step 11: Auto-Start on Boot

Create a startup script:

```bash
mkdir -p ~/.termux/boot

nano ~/.termux/boot/tok2gram.sh
```

Add to `~/.termux/boot/tok2gram.sh`:

```bash
#!/bin/bash

termux-wake-lock

cd ~/tok2gram

source venv/bin/activate

python main.py
```

Make it executable:

```bash
chmod +x ~/.termux/boot/tok2gram.sh
```

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| pip build errors | `pkg install clang python-dev` |
| ffmpeg missing for video processing | `pkg install ffmpeg` |
| SSL certificate errors | `pkg install ca-certificates && pip install --certificates` |
| Process killed by Android | Use `termux-wake-lock` + F-Droid Termux |
| Storage permission denied | Run `termux-setup-storage` again |
| Cannot download TikTok videos | Ensure cookies are set in `data/cookies/` |
| Telegram API errors | Verify bot token in config.yaml |

## Quick Setup Script

Save this as `setup-termux.sh` and run it:

```bash
#!/bin/bash

set -e

echo "Installing Termux packages..."

pkg update -y && pkg upgrade -y

pkg install -y python ffmpeg wget curl git libffi openssl clang ca-certificates

echo "Creating virtual environment..."

python -m venv ~/tok2gram/venv

source ~/tok2gram/venv/bin/activate

pip install --upgrade pip

echo "Installing Python dependencies..."

pip install yt-dlp python-telegram-bot==20.* PyYAML tenacity requests pytest-asyncio gallery-dl

echo "Setting up storage access..."

termux-setup-storage

echo "Setup complete!"

echo "Next steps:"

echo "1. Clone or transfer Tok2Gram files to ~/tok2gram"

echo "2. Configure config.yaml and creators.yaml"

echo "3. Run: cd ~/tok2gram && source venv/bin/activate && python main.py"
```

## Performance Tips

1. **Use tmux** - Keeps session alive when you close Termux

2. **termux-wake-lock** - Prevents Android from killing the process

3. **Adjust config.yaml** - Set appropriate check intervals to reduce battery usage

4. **Monitor logs** - Check `output.log` for errors

5. **Schedule restarts** - Use cron to restart periodically

## File Structure on Android

```
/data/data/com.termux/files/home/

├── tok2gram/

│ ├── venv/ # Virtual environment

│ ├── main.py # Entry point

│ ├── config.yaml # Configuration

│ ├── creators.yaml # Creator list

│ ├── data/

│ │ ├── cookies/ # TikTok cookies

│ │ ├── downloads/ # Downloaded media

│ │ └── state.db # SQLite state database

│ └── ...

└── storage/

├── downloads/ # Android downloads

└── shared/ # Internal storage
```

## Security Notes

1. **Never commit config.yaml** with real tokens to git

2. **Use environment variables** for sensitive data:

```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
```

3. **Keep Termux updated** to get security patches

4. **Review permissions** before installing additional packages

## Support

- Termux Wiki: [https://wiki.termux.com](https://wiki.termux.com)

- Termux GitHub: [https://github.com/termux/termux-app](https://github.com/termux/termux-app)

- Tok2Gram Issues: Report bugs on the project repository

---

**Note**: This guide assumes you have basic familiarity with command-line interfaces. If you encounter issues, check the Termux wiki or community forums for additional help.
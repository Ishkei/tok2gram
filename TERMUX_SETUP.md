# Tok2Gram Termux Android Setup Guide for Beginners

## What is This Guide?

Hello! This guide will help you set up **Tok2Gram** on your Android phone using an app called **Termux**. Tok2Gram is a tool that automatically monitors TikTok creators and reposts their videos to Telegram channels.

Don't worry if you're new to this - we'll explain everything step by step, like you're learning it for the first time. We'll use simple words and tell you exactly what to do.

## What You Need Before Starting

Before we begin, make sure you have:

- **An Android phone** (version 7.0 or newer is best)
- **At least 500MB of free space** on your phone
- **A good internet connection** (Wi-Fi is recommended)

If you don't have these, you might run into problems later.

## Quick Start (For Experienced Users)

If you're comfortable with commands, you can use this quick setup script. Otherwise, skip to the detailed steps below.

**Save this as `setup-termux.sh` and run it:**

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
pip install yt-dlp python-telegram-bot==20.* PyYAML tenacity requests pytest-asyncio gallery-dl rich

echo "Setting up storage access..."
termux-setup-storage

echo "Creating required directories..."
mkdir -p ~/tok2gram/data/{cookies,downloads,logs}

echo "Setup complete!"
echo "Next steps:"
echo "1. Get Tok2Gram files to ~/tok2gram"
echo "2. Copy creators-template.yaml to creators.yaml"
echo "3. Edit config.yaml and creators.yaml with your settings"
echo "4. Run: cd ~/tok2gram && source venv/bin/activate && python main.py"
```

## Step 1: Install Termux

Termux is like a mini computer on your phone. It lets you run commands just like on a computer.

### Option 1: Download from F-Droid (Easiest)

1. **What is F-Droid?** It's a free app store for Android, like Google Play but for open-source apps.

2. **Install F-Droid first:**
   - Go to [https://f-droid.org](https://f-droid.org) on your phone's browser
   - Download and install the F-Droid app

3. **Get Termux:**
   - Open F-Droid
   - Search for "Termux"
   - Tap "Install"

4. **Allow unknown apps if asked:**
   - Go to your phone's Settings > Security
   - Turn on "Unknown sources" or "Install unknown apps"
   - Allow F-Droid to install apps

> **Important:** Don't use the Termux from Google Play Store - it's old and doesn't work well!

### Option 2: Download Directly from GitHub

If F-Droid doesn't work:

1. Go to [https://github.com/termux/termux-app/releases](https://github.com/termux/termux-app/releases) on your phone

2. Download the latest file that ends with `.apk` (like `termux-app_118_debug.apk`)

3. Open the downloaded file to install it

4. Allow installation from unknown sources if prompted

## Step 2: First Time Setup in Termux

1. **Open Termux** - it looks like a black screen with white text

2. **Update everything:**
   ```bash
   pkg update && pkg upgrade -y
   ```
   *What this does:* Updates Termux to the latest version and installs basic tools.

3. **Install essential tools:**
   ```bash
   pkg install coreutils curl wget git openssl-tool
   ```
   *What this does:* Adds tools we need for downloading and managing files.

## Step 3: Install Required Software

Tok2Gram needs special programs to download videos and talk to Telegram.

```bash
pkg install -y python ffmpeg wget curl git libffi openssl clang ca-certificates
```

*What this does:*
- **python**: Programming language for Tok2Gram
- **ffmpeg**: Tool for video processing
- **Others**: Helper tools for security and downloading

## Step 4: Set Up Python Environment

Python is the language Tok2Gram is written in. We need to set it up properly.

```bash
# Check if Python works
python --version

# Update the tool that installs Python packages
pip install --upgrade pip

# Create a special folder for Tok2Gram's Python setup
python -m venv ~/tok2gram/venv
```

*What this does:* Creates a "virtual environment" so Tok2Gram's Python stuff doesn't mix with other apps.

## Step 5: Get the Tok2Gram Files

You need to get the Tok2Gram program files onto your phone.

### Easiest Way: Download from GitHub

```bash
# Go to your home folder
cd ~

# Download Tok2Gram (replace 'yourusername' with the actual GitHub username)
git clone https://github.com/yourusername/tok2gram.git

# Go into the Tok2Gram folder
cd tok2gram
```

*What this does:* Downloads all the Tok2Gram files from the internet.

### Alternative: Copy from Your Computer

1. **On your computer:** Zip the tok2gram folder

2. **Upload the zip file** to Google Drive or Dropbox

3. **On your phone in Termux:**
   ```bash
   # Set up file access
   termux-setup-storage

   # Copy the file (change the path to where you put it)
   cp ~/storage/shared/Download/tok2gram.zip .

   # Unzip it
   unzip tok2gram.zip
   ```

## Step 6: Install Tok2Gram's Python Packages

Now we install all the special libraries Tok2Gram needs.

```bash
# Go to Tok2Gram folder
cd ~/tok2gram

# Activate our Python environment
source venv/bin/activate

# Update installer
pip install --upgrade pip

# Install all needed packages
pip install yt-dlp python-telegram-bot==20.* PyYAML tenacity requests pytest-asyncio gallery-dl rich
```

*What these packages do:*
- **yt-dlp**: Downloads videos from TikTok
- **python-telegram-bot**: Sends messages to Telegram
- **PyYAML**: Reads configuration files
- **Others**: Help with errors, downloads, and testing

## Step 7: Set Up File Access

Allow Termux to access your phone's files.

```bash
termux-setup-storage
```

*What this does:* Creates shortcuts to your phone's storage so Tok2Gram can save downloaded videos.

You'll see folders like:
- `~/storage/downloads/` - Your phone's Downloads folder
- `~/storage/shared/` - Your phone's main storage

## Step 8: Create Required Directories

Tok2Gram needs some folders to store data, logs, and cookies.

```bash
# Create the necessary directories
mkdir -p data/{cookies,downloads,logs}
```

*What this creates:*
- `data/cookies/` - For TikTok session cookies
- `data/downloads/` - For temporarily downloaded videos
- `data/logs/` - For application log files

## Step 9: Configure Tok2Gram

Set up your personal settings for TikTok and Telegram.

### 1. Set up the configuration files

The config.yaml file should already exist. For creators, copy the template:

```bash
# Copy the creators template (config.yaml already exists)
cp creators-template.yaml creators.yaml
```

### 2. Set up your Telegram bot

You need a Telegram bot token. Here's how to get one:

1. Open Telegram and search for "@BotFather"
2. Type `/newbot` and follow the instructions
3. Copy the token (it looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

Edit the config file:

```bash
nano config.yaml
```

Find the telegram section and update the bot_token:

```yaml
telegram:
  bot_token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

*How to use nano:* Type your changes, then press Ctrl+X, then Y, then Enter to save.

### 3. Add your TikTok creators and Telegram channels

```bash
nano creators.yaml
```

Add something like:

```yaml
creators:
  - username: "tiktok_creator_username"
    chat_id: "-1001234567890"
```

### 4. Set up TikTok cookies (Optional but helps)

Cookies help Tok2Gram access private or restricted TikTok content.

1. Create the cookies folder:
   ```bash
   mkdir -p data/cookies
   ```

2. Get cookies from your browser (search online for "export TikTok cookies")

3. Save them as `sid_tt.txt` in the `data/cookies/` folder

## Step 10: Test That Everything Works

Let's make sure Tok2Gram runs without errors.

```bash
# Go to Tok2Gram folder
cd ~/tok2gram

# Activate Python environment
source venv/bin/activate

# Run Tok2Gram
python main.py
```

*What should happen:* Tok2Gram starts and shows messages about checking for new videos. Press Ctrl+C to stop it.

If you see errors, check the troubleshooting section below.

## Step 11: Run Tok2Gram in the Background

You don't want to keep Termux open all the time. Here's how to run it hidden.

### Best Way: Use tmux (Recommended)

tmux keeps programs running even when you close Termux.

```bash
# Install tmux
pkg install tmux

# Start a new tmux session called "tok2gram"
tmux new-session -s tok2gram

# Inside tmux, run these commands:
termux-wake-lock
python main.py

# To leave tmux running: Press Ctrl+B, then D

# To come back later: tmux attach-session -t tok2gram
```

### Simpler Way: nohup

```bash
# Prevent Android from stopping the app
termux-wake-lock

# Run in background and save output to a file
nohup python ~/tok2gram/main.py > output.log 2>&1 &
```

## Step 12: Make It Start Automatically

Want Tok2Gram to start when your phone turns on?

```bash
# Create the startup folder
mkdir -p ~/.termux/boot

# Create the startup script
nano ~/.termux/boot/tok2gram.sh
```

Put this in the file:

```bash
#!/bin/bash

# Prevent Android from killing the process
termux-wake-lock

# Go to Tok2Gram folder
cd ~/tok2gram

# Activate Python
source venv/bin/activate

# Start Tok2Gram
python main.py
```

Make it executable:

```bash
chmod +x ~/.termux/boot/tok2gram.sh
```

Now Tok2Gram will start when Termux starts!

## Common Problems and How to Fix Them

### "Command not found" errors
**Problem:** When you type a command, it says "command not found"

**Solutions:**
- Make sure you're typing it exactly right (copy-paste if possible)
- Try running `pkg install coreutils` first
- Restart Termux

### Python or pip doesn't work
**Problem:** `python --version` or `pip` gives errors

**Solutions:**
- Run `pkg install python` again
- Make sure you're in the right folder
- Try `python3` instead of `python`

### Can't download videos
**Problem:** Tok2Gram can't get TikTok videos

**Solutions:**
- Check your internet connection
- Add TikTok cookies (see Step 8.4)
- Make sure the TikTok username is correct
- Run `pkg install ffmpeg` again

### Telegram errors
**Problem:** "Invalid bot token" or can't send messages

**Solutions:**
- Double-check your bot token in config.yaml
- Make sure the bot is added as admin to your Telegram channel
- Test the bot token manually first

### App gets killed by Android
**Problem:** Tok2Gram stops running randomly

**Solutions:**
- Always use `termux-wake-lock` when running
- Use tmux to keep it running
- Close other apps to free up memory
- Use the F-Droid version of Termux

### Storage permission denied
**Problem:** Can't access files

**Solutions:**
- Run `termux-setup-storage` again
- Grant storage permissions to Termux in Android settings
- Restart your phone

### Build/compilation errors
**Problem:** Installing packages fails with build errors

**Solutions:**
- Run `pkg install clang python-dev` first
- Update Termux: `pkg update && pkg upgrade`
- Try installing one package at a time

### SSL/certificate errors
**Problem:** Connection errors when downloading

**Solutions:**
- Run `pkg install ca-certificates`
- Try `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org [package]`

## Tips for Better Performance

1. **Use tmux** - It keeps your session alive even if you close Termux

2. **Use termux-wake-lock** - Prevents Android from stopping Tok2Gram to save battery

3. **Check your config** - Adjust how often it checks for new videos to save battery

4. **Monitor logs** - Check `output.log` for errors and what's happening

5. **Restart regularly** - Set up a cron job to restart Tok2Gram every few hours

## How Files Are Organized on Your Phone

After setup, your files will look like this:

```
/data/data/com.termux/files/home/  (Termux's home folder)

├── tok2gram/                     (Main Tok2Gram folder)
│   ├── venv/                     (Python environment)
│   ├── main.py                   (The main program)
│   ├── config.yaml               (Your settings)
│   ├── creators.yaml             (TikTok creators list)
│   ├── data/                     (Data storage)
│   │   ├── cookies/              (TikTok login cookies)
│   │   ├── downloads/            (Downloaded videos)
│   │   ├── logs/                 (Application log files)
│   │   └── state.db              (Remembers what was posted)
│   └── ...
│
└── storage/                      (Shortcuts to phone storage)
    ├── downloads/                (Phone's Downloads folder)
    └── shared/                   (Phone's main storage)
```

## Security Tips

1. **Don't share your config files** - They contain your bot token

2. **Use environment variables** for secrets:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_secret_token_here"
   ```

3. **Keep Termux updated** - Run `pkg update` regularly for security fixes

4. **Be careful with permissions** - Only install packages you trust

## Words You Might Not Know (Glossary)

- **APK**: Android app file (like .exe for Windows)
- **F-Droid**: Alternative app store for free/open-source apps
- **Git/GitHub**: System for sharing and downloading code
- **Virtual Environment**: Isolated Python setup for one project
- **Bot Token**: Secret code that lets programs control Telegram bots
- **Cookies**: Small files that remember login info for websites
- **tmux**: Tool that lets programs run in the background
- **nohup**: Command that prevents programs from stopping when you close the terminal

## Need Help?

If you get stuck:

- **Termux Wiki**: [https://wiki.termux.com](https://wiki.termux.com) - Official help
- **Termux GitHub**: [https://github.com/termux/termux-app](https://github.com/termux/termux-app) - Report bugs
- **Tok2Gram Issues**: Check the project repository for known problems

Remember: Take it slow, double-check your typing, and don't be afraid to ask for help. You've got this! 🚀
# Tok2gram - TikTok to Telegram Reposter

A robust, production-ready TikTok content monitoring and reposting system that automatically detects new posts from specified creators and forwards them to Telegram channels with anti-bot protection.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration Guides](#configuration-guides)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Features

### Core Functionality
- **🎥 Video & Slideshow Support**: Automatically downloads videos and slideshows with best quality preservation
- **🔄 Duplicate Prevention**: SQLite-based state management prevents reposting the same content
- **🛡️ Anti-Bot Protection**: Rotating cookie system with randomized delays to avoid detection
- **📱 Smart Media Handling**: Videos uploaded as MP4, slideshows as media groups with proper captions
- **⚡ Resumable Operation**: Crash-safe with persistent state across restarts

### Advanced Features  
- **🍪 Cookie Management**: Automatic cookie rotation when requests fail
- **⏰ Smart Polling**: Configurable delays with jitter to avoid rate limits
- **📊 Comprehensive Logging**: Detailed logs for monitoring and debugging
- **🔧 Flexible Configuration**: YAML-based configuration for easy management
- **🧪 Test Coverage**: 16 unit tests ensuring reliability

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd tok2gram
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Configure**:
   ```bash
   cp config/creators-template.yaml config/creators.yaml
   # Edit config/config.yaml and config/creators.yaml
   ```

3. **Add cookies** (see [Cookie Setup Guide](#how-to-set-cookies)):
   ```bash
   # Place TikTok cookies in data/cookies/ as .txt files
   ```

4. **Run**:
   ```bash
   cd src && python main.py
   ```

## Installation

### Prerequisites
- Python 3.11+ 
- Git
- TikTok account (for cookies)
- Telegram Bot Token

### Step-by-Step Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd tok2gram
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate.ps1  # Windows PowerShell
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create required directories**:
   ```bash
   mkdir -p data/{cookies,downloads,logs}
   ```

## Configuration

### Main Configuration (`config/config.yaml`)

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"

settings:
  fetch_depth: 10  # Number of latest posts to check
  download_workers: 3  # Concurrent downloads
  yt_concurrent_fragments: 2  # yt-dlp concurrency
  retry_uploads: 1  # Upload retry attempts
  delay_between_creators_seconds_min: 10  # Min delay between creators
  delay_between_creators_seconds_max: 30  # Max delay between creators
```

### Creators Configuration (`config/creators.yaml`)

```yaml
creators:
  - username: "creator_username"
    chat_id: "-1001234567890"  # Telegram chat/channel ID
  - username: "another_creator"
    chat_id: "-1009876543210"
```

## Usage

### Running the Application

**Basic run**:
```bash
cd src
python main.py
```

**Run with custom config**:
```bash
cd src
python main.py --config ../config/custom-config.yaml
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_tiktok.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Smoke Testing

Test individual components:

```bash
# Test TikTok fetching
python scripts/smoke_tiktok.py

# Test video downloading
python scripts/smoke_downloader.py
```

## Project Structure

```
tok2gram/
├── src/                     # Source code
│   ├── core/               # Core utilities
│   │   ├── config_loader.py    # Configuration loading
│   │   ├── state.py            # SQLite state management
│   │   └── cookie_manager.py   # Cookie rotation system
│   ├── tiktok/             # TikTok integration
│   │   ├── fetcher.py         # Post fetching logic
│   │   └── downloader.py      # Video/slideshow downloading
│   ├── telegram/           # Telegram integration
│   │   └── uploader.py        # Upload to Telegram
│   └── main.py             # Application entry point
├── config/                 # Configuration files
│   ├── config.yaml           # Main configuration
│   ├── creators.yaml         # Creator list
│   └── creators-template.yaml # Template for creators
├── data/                   # Runtime data
│   ├── cookies/             # TikTok cookie files (.txt)
│   ├── downloads/           # Downloaded content
│   └── logs/                # Application logs
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── docs/                   # Project documentation
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Configuration Guides

### How to Set Cookies

1. **Login to TikTok** in your browser
2. **Extract sid_tt cookie**:
   - Press F12 → Application/Storage → Cookies → https://www.tiktok.com
   - Find `sid_tt` cookie, copy its value
3. **Create cookie file**:
   ```bash
   echo "sid_tt=YOUR_COOKIE_VALUE_HERE" > data/cookies/sid_tt_1.txt
   ```
4. **Add multiple cookies** (optional):
   ```bash
   echo "sid_tt=ANOTHER_COOKIE" > data/cookies/sid_tt_2.txt
   ```

### How to Get Telegram Chat ID

1. **Create your bot** via @BotFather
2. **Add bot to target channel/group** as admin
3. **Send a message** to the channel/group
4. **Get chat ID** via API:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
   ```
5. **Find chat ID** in response (usually negative for groups/channels)

### How to Enable Upload to Telegram

1. **Get Bot Token**:
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Save the token

2. **Configure Bot**:
   - Add bot to your channel/group as admin
   - Get chat ID (see guide above)
   - Update `config/config.yaml` with bot token
   - Update `config/creators.yaml` with chat IDs

3. **Test Upload**:
   ```bash
   cd src
   python -c "
   import asyncio
   from telegram.uploader import TelegramUploader
   async def test():
       uploader = TelegramUploader('YOUR_TOKEN', 'YOUR_CHAT_ID')
       print('Upload test successful!')
   asyncio.run(test())
   "
   ```

## Development

### Running in Development

1. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Install development dependencies**:
   ```bash
   pip install pytest pytest-asyncio pytest-cov
   ```

3. **Run tests during development**:
   ```bash
   python -m pytest tests/ -v --tb=short
   ```

### Code Organization

- **`src/core/`**: Core business logic, configuration, and state management
- **`src/tiktok/`**: TikTok-specific functionality (fetching, downloading)
- **`src/telegram/`**: Telegram-specific functionality (uploading)
- **`tests/`**: Comprehensive test suite with mocks
- **`scripts/`**: Utility scripts for testing and development

### Adding New Features

1. **Create branch**: `git checkout -b feature/your-feature`
2. **Write tests first**: Add tests in `tests/`
3. **Implement feature**: Add code in appropriate `src/` module
4. **Run tests**: `python -m pytest tests/ -v`
5. **Update docs**: Update this README if needed
6. **Submit PR**: Create pull request with description

## Troubleshooting

### Common Issues

**No posts found for creator**:
- Check if cookies are valid (cookies in `data/cookies/`)
- Verify creator username is correct
- Try different cookie rotation

**Upload failed**:
- Verify bot token in `config/config.yaml`
- Check if bot is admin in target chat
- Confirm chat ID is correct (negative for groups/channels)

**Download failed**:
- Check internet connection
- Verify yt-dlp is up to date: `pip install --upgrade yt-dlp`
- Try with different cookies

**Permission denied**:
- Ensure proper file permissions: `chmod 600 data/cookies/*.txt`
- Check write permissions for `data/` directories

### Logs and Debugging

- **Main logs**: `data/logs/run.log`
- **Increase verbosity**: Set `logging.DEBUG` in `src/main.py`
- **Test individual components**: Use scripts in `scripts/` directory

### Getting Help

1. **Check logs**: Review `data/logs/run.log` for errors
2. **Run smoke tests**: Use `scripts/smoke_*.py` to test components
3. **Check configuration**: Verify YAML syntax and required fields
4. **Review documentation**: See `docs/` directory for detailed guides

## Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Add tests**: Ensure new code has test coverage
4. **Run test suite**: `python -m pytest tests/ -v`
5. **Update documentation**: Update README and docs as needed
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push branch**: `git push origin feature/amazing-feature`  
8. **Create Pull Request**: Submit PR with clear description

---

**Built with**: Python 3.11+, yt-dlp, python-telegram-bot, SQLite

**License**: MIT - see `LICENSE` file for details
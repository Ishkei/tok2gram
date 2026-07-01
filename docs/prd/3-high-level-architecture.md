# 3. High-Level Architecture
ChromeOS → Crostini Debian VM containing:
- Python virtualenv
- `main.py` entrypoint
- yt-dlp
- SQLite `state.db`
- `creators.yaml`, `config.yaml`
- `cookies/`, `downloads/`, `logs/`

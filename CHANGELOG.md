# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Upload Resumption System**: Automatically tracks downloads and resumes incomplete uploads after interruptions
  - Downloads are recorded with file paths in the SQLite database
  - On startup, checks for posts that were downloaded but not uploaded
  - Verifies files still exist before resuming upload
  - Handles missing/corrupted files gracefully with warnings
  - Saves bandwidth by avoiding re-downloads after crashes

### Changed
- Database schema updated to include `downloaded_files` column (automatic migration on first run)
- `StateStore` class now includes methods for tracking and querying incomplete uploads:
  - `record_download_files()` - Record file paths after download
  - `get_downloaded_files()` - Retrieve stored file paths
  - `get_incomplete_uploads()` - Query posts ready for resumption

### Technical Details
- Modified `state.py` to add new database column with automatic migration
- Updated `main.py` to record downloads and check for resumption on startup
- Resumption happens per-creator before processing new posts
- No breaking changes - existing databases are automatically migrated

## [1.0.0] - Initial Release

### Features
- TikTok video and slideshow downloading
- Automatic upload to Telegram channels
- Cookie rotation for anti-bot protection
- SQLite-based state management
- Duplicate prevention
- Comprehensive logging

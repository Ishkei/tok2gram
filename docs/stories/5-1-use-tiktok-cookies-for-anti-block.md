# Story 5.1: Use TikTok Cookies for Anti-Block

Status: done

## Story

As an anti-block system,
I want to use TikTok cookies for requests,
so that access is not blocked by TikTok.

## Acceptance Criteria

1. Given TikTok cookies are available
2. When making requests to TikTok
3. Then include cookies in requests
4. And store cookies securely in cookies/ directory
5. And set permissions to 600

## Tasks / Subtasks

- [x] Load cookies from cookies/ directory (AC: 1,4,5)
  - [x] Read cookie files
  - [x] Set secure permissions (chmod 600)
- [x] Include cookies in yt-dlp requests (AC: 2,3)
  - [x] Configure yt-dlp with cookie jar
  - [x] Use cookies for all TikTok fetches

## Dev Notes

- Cookies stored in cookies/ directory
- Permissions: chmod 600 for security
- Use yt-dlp --cookies option or cookie jar
- Rotate cookies on failure (next story)
- Part of anti-bot protection

### Project Structure Notes

- cookies/ directory in project root
- Aligns with FR13
- Part of Epic 5: Anti-Bot Protection

### References

- [Source: docs/epics.md#Epic 5: Anti-Bot Protection]
- [Source: docs/architecture.md#8 Security Compliance]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Cookie files permissions set to 600 via `os.chmod` in `CookieManager`.
- Cookies passed to `yt-dlp` via custom `http_headers` for flexibility.

### Completion Notes List

- Implemented `CookieManager` in `cookie_manager.py`.
- Integrated cookie loading into `main.py` and `tiktok.py`.
- Verified secure permissions are applied on initialization.

### File List

- cookie_manager.py
- main.py
- tiktok.py
- tests/test_cookies.py
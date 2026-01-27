# Story 1.2: Fetch Latest Posts from TikTok

Status: done

## Story

As a content monitor,
I want to fetch the latest 10 posts per creator,
so that new content can be identified.

## Acceptance Criteria

1. Given a valid creator username
2. When fetching posts using yt-dlp metadata extraction
3. Then retrieve up to 10 latest posts
4. And normalize each to Post model with post_id, creator, kind, url, caption, created_at

## Tasks / Subtasks

- [x] Implement yt-dlp metadata extraction for TikTok profile (AC: 1,2,3)
  - [x] Configure yt-dlp to fetch JSON metadata only
  - [x] Limit to latest 10 posts
- [x] Parse metadata and extract post information (AC: 3,4)
  - [x] Extract post_id, creator, kind, url, caption, created_at
  - [x] Handle missing timestamps gracefully
- [x] Create Post model instances (AC: 4)

## Dev Notes

- Use yt-dlp --dump-json to get metadata without downloading
- Prefer metadata extraction over HTML parsing for reliability
- Post model: post_id (str), creator (str), kind ('video' or 'slideshow'), url (str), caption (str), created_at (datetime or None)
- Handle rate limiting and anti-bot measures

### Project Structure Notes

- Implement in tiktok.py module
- Aligns with intake layer in architecture
- No conflicts detected

### References

- [Source: docs/architecture.md#4.2 Intake]
- [Source: docs/prd.md#4 Core Workflow]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- yt-dlp Netscape cookie requirement bypassed by using `http_headers` with raw cookie value.
- Flat extraction used for performance.

### Completion Notes List

- Implemented `Post` dataclass in `tiktok.py`.
- Implemented `fetch_posts` using `yt-dlp`.
- Verified with unit tests and a live smoke test against `khaby.lame`.
- Successfully handled raw `sid_tt` cookie via custom headers.

### File List

- tiktok.py
- tests/test_tiktok.py
- smoke_tiktok.py

# Story 2.3: Download Slideshow Content

Status: done

## Story

As a downloader,
I want to download slideshow images in original quality,
so that photo content is available for upload.

## Acceptance Criteria

1. Given an unseen slideshow post
2. When downloading images
3. Then download all images in the slideshow
4. And preserve original quality
5. And save to structured download folders

## Tasks / Subtasks

- [x] Implement slideshow download logic (AC: 1,2,3,4,5)
  - [x] Extract all image URLs from slideshow post
  - [x] Download each image preserving original quality
  - [x] Save images to structured download folders
  - [x] Maintain image order for upload

## Dev Notes

- Slideshow posts contain multiple images
- Download all images in the slideshow
- Preserve original quality (no compression)
- Use yt-dlp or direct download for images
- Save to downloads/{creator}/{post_id}/ folder structure
- Part of parallel download process

### Project Structure Notes

- Downloads to downloads/creator/post_id/ with numbered images
- Aligns with NFR7: Photos: original quality
- Part of Epic 2: Content Download

### References

- [Source: docs/epics.md#Story 2.3: Download Slideshow Content]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Slideshow detection implemented by checking `_type` and `entries` in `yt-dlp` metadata.
- Images downloaded sequentially within the post to maintain order.

### Completion Notes List

- Implemented `download_slideshow` in `downloader.py`.
- Integrated `requests` for direct image downloading where appropriate.
- Verified directory creation and file numbering.

### File List

- downloader.py
- tests/test_downloader.py

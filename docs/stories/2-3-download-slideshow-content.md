# Story 2.3: Download Slideshow Content

Status: ready-for-dev

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

- [ ] Implement slideshow download logic (AC: 1,2,3,4,5)
  - [ ] Extract all image URLs from slideshow post
  - [ ] Download each image preserving original quality
  - [ ] Save images to structured download folders
  - [ ] Maintain image order for upload

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
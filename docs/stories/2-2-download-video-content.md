# Story 2.2: Download Video Content

Status: done

## Story

As a downloader,
I want to download video posts with best available quality,
so that content is preserved without recompression.

## Acceptance Criteria

1. Given an unseen video post
2. When downloading using yt-dlp
3. Then use format "bv*+ba/best"
4. And merge output to MP4 without re-encoding
5. And limit concurrent fragments to 1-2

## Tasks / Subtasks

- [x] Implement video download logic (AC: 1,2,3,4,5)
  - [x] Configure yt-dlp with best video+audio format
  - [x] Set merge output to MP4 without re-encoding
  - [x] Limit concurrent fragments to 1-2
  - [x] Handle download to structured folders

## Dev Notes

- Use yt-dlp for downloading video content
- Format selection: "bv*+ba/best" for best video and audio merged
- Output format: MP4 without re-encoding to preserve quality
- Concurrent fragments: 2 (as per code implementation)
- Downloads structured under downloads/{creator}/

### Project Structure Notes

- Downloads go to structured folders under downloads/
- Aligns with NFR5: No recompression or recoding
- Part of Epic 2: Content Download

### References

- [Source: docs/epics.md#Story 2.2: Download Video Content]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- yt-dlp configured with `bv*+ba/best` and `merge_output_format: mp4`.
- Concurrent fragments set to 2.
- IP blocking encountered in smoke test, but logic verified via unit tests mocking yt-dlp.

### Completion Notes List

- Implemented `download_video` in `downloader.py`.
- Verified options and structure with unit tests.

### File List

- downloader.py
- tests/test_downloader.py
- smoke_downloader.py

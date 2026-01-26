# Story 2.2: Download Video Content

Status: ready-for-dev

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

- [ ] Implement video download logic (AC: 1,2,3,4,5)
  - [ ] Configure yt-dlp with best video+audio format
  - [ ] Set merge output to MP4 without re-encoding
  - [ ] Limit concurrent fragments to 1-2
  - [ ] Handle download to structured folders

## Dev Notes

- Use yt-dlp for downloading video content
- Format selection: "bv*+ba/best" for best video and audio merged
- Output format: MP4 without re-encoding to preserve quality
- Concurrent fragments: 1-2 to balance speed and resource usage
- Downloads should be part of the parallel download process using ThreadPoolExecutor

### Project Structure Notes

- Downloads go to structured folders under downloads/
- Aligns with NFR5: No recompression or recoding
- Part of Epic 2: Content Download

### References

- [Source: docs/epics.md#Story 2.2: Download Video Content]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used
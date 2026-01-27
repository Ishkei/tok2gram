# Story 2.4: Handle Download Edge Cases

Status: done

## Story

As a robust downloader,
I want to handle pinned posts, reposts, and mixed media correctly,
so that all content types are processed appropriately.

## Acceptance Criteria

1. Given a pinned post
2. When processing for download
3. Then download once regardless of pin status
4. Given deleted and reposted content
5. When processing
6. Then treat as new post based on current post_id
7. Given mixed media post
8. When processing
9. Then prioritize video download over photos

## Tasks / Subtasks

- [x] Handle pinned posts (AC: 1,3)
  - [x] Detect pinned status
  - [x] Download once regardless of pin
- [x] Handle reposts (AC: 4,6)
  - [x] Treat deleted/reposted as new based on post_id
- [x] Handle mixed media (AC: 7,9)
  - [x] Prioritize video over photos in mixed posts

## Dev Notes

- Pinned posts: download only once, not repeatedly
- Reposts: treat as new if post_id is new
- Mixed media: video takes precedence over images
- Use post metadata to determine type and handle accordingly
- Ensure no duplicates by checking post_id

### Project Structure Notes

- No additional structure changes needed
- Aligns with FR8, FR9, FR7
- Part of Epic 2: Content Download

### References

- [Source: docs/epics.md#Story 2.4: Handle Download Edge Cases]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Primary key uniqueness in SQLite handles pinned posts (won't re-process if ID exists).
- Mixed media detected and handled by prioritizing `video` kind in `tiktok.py`.

### Completion Notes List

- Implemented `kind` detection logic in `tiktok.py`.
- Verified that `is_processed` correctly blocks already-seen pinned posts.
- Smoke tests confirmed video priority for mixed content.

### File List

- tiktok.py
- state.py
- downloader.py
- tests/test_tiktok.py
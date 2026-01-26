# Story 2.1: Check for Processed Posts

Status: ready-for-dev

## Story

As a content processor,
I want to check if a post has been processed before,
so that duplicates are avoided across runs.

## Acceptance Criteria

1. Given a post_id and SQLite state.db exists
2. When querying the posts table
3. Then return true if post_id exists with uploaded_at set
4. And return false if post_id does not exist or uploaded_at is null

## Tasks / Subtasks

- [ ] Implement is_processed(post_id) function (AC: 1,2,3,4)
  - [ ] Connect to SQLite state.db
  - [ ] Query posts table for post_id
  - [ ] Check if uploaded_at is not null
- [ ] Handle database connection errors gracefully (AC: 1)

## Dev Notes

- Only posts with successful upload are marked processed
- uploaded_at is set only after Telegram upload succeeds
- Fast lookup required for performance

### Project Structure Notes

- Implement in state.py module
- Aligns with state layer in architecture
- SQLite schema as defined in architecture

### References

- [Source: docs/architecture.md#4.5 State Store]
- [Source: docs/architecture.md#5.1 SQLite schema]

## Dev Agent Record

### Agent Model Used

Grok Code Fast 1

### Debug Log References

### Completion Notes List

### File List
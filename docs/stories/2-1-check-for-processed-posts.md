# Story 2.1: Check for Processed Posts

Status: done

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

- [x] Implement is_processed(post_id) function (AC: 1,2,3,4)
  - [x] Connect to SQLite state.db
  - [x] Query posts table for post_id
  - [x] Check if uploaded_at is not null
- [x] Handle database connection errors gracefully (AC: 1)

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

Amelia (Dev Agent) - Zencoder

### Debug Log References

- SQLite schema implemented as per architecture.
- is_processed logic verified with unit tests.

### Completion Notes List

- Created `state.py` with `StateStore` class.
- Implemented automatic schema initialization.
- Implemented `is_processed` with correct null handling for `uploaded_at`.

### File List

- state.py
- tests/test_state.py

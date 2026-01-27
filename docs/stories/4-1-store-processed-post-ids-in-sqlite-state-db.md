# Story 4.1: Store Processed Post IDs in SQLite State DB

Status: done

## Story

As a state manager,
I want to store processed post IDs in SQLite state.db,
so that duplicates are avoided across restarts.

## Acceptance Criteria

1. Given a post has been processed
2. When storing state
3. Then create/update SQLite posts table with post details
4. And include post_id, creator, kind, source_url, created_at, downloaded_at, uploaded_at, telegram_chat_id, telegram_message_id
5. And ensure reliable recovery from reboots

## Tasks / Subtasks

- [x] Create SQLite schema for state.db (AC: 3,4)
  - [x] Define posts table with required columns
  - [x] Set up database connection
- [x] Implement state storage logic (AC: 1,2,3,4,5)
  - [x] Insert/update post records
  - [x] Mark downloaded_at and uploaded_at appropriately
  - [x] Store Telegram IDs after upload

## Dev Notes

- SQLite database: state.db in project root
- Table: posts with columns as specified
- Use sqlite3 library
- Store after successful download and upload
- Query for duplicates by post_id

### Project Structure Notes

- state.db in project root
- Aligns with FR17, NFR10
- Part of Epic 4: State Persistence

### References

- [Source: docs/epics.md#Epic 4: State Persistence]
- [Source: docs/architecture.md#5 Data Model]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Verified primary key constraint on `post_id` prevents duplicates.
- Added `record_download` and `mark_as_uploaded` methods for granular state tracking.

### Completion Notes List

- Implemented `StateStore` in `state.py` using `sqlite3`.
- Ensured thread-safe access (though currently sequential).
- Verified data types for timestamps and IDs.

### File List

- state.py
- tests/test_state.py

# Story 4.1: Store Processed Post IDs in SQLite State DB

Status: ready-for-dev

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

- [ ] Create SQLite schema for state.db (AC: 3,4)
  - [ ] Define posts table with required columns
  - [ ] Set up database connection
- [ ] Implement state storage logic (AC: 1,2,3,4,5)
  - [ ] Insert/update post records
  - [ ] Mark downloaded_at and uploaded_at appropriately
  - [ ] Store Telegram IDs after upload

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
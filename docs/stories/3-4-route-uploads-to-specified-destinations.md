# Story 3.4: Route Uploads to Specified Destinations

Status: done

## Story

As a channel manager,
I want uploads routed to correct chats and topics,
so that content reaches the intended audience.

## Acceptance Criteria

1. Given creator config with chat_id and optional topic_id
2. When uploading content
3. Then send to the specified chat_id
4. And include message_thread_id if topic is configured
5. And store telegram_chat_id and telegram_message_id in state

## Tasks / Subtasks

- [x] Implement routing logic (AC: 1,2,3,4,5)
  - [x] Read chat_id from creator config
  - [x] Include message_thread_id for topics
  - [x] Send to correct destination
  - [x] Store chat_id and message_id in SQLite state

## Dev Notes

- Use creators.yaml for chat_id and optional topic_id
- message_thread_id for Telegram topics
- Store in posts table: telegram_chat_id, telegram_message_id
- Applies to all upload types

### Project Structure Notes

- No additional structure changes
- Uses existing config files
- Part of Epic 3: Telegram Upload

### References

- [Source: docs/epics.md#Story 3.4: Route Uploads to Specified Destinations]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Added `message_thread_id` support to both `upload_video` and `upload_slideshow`.
- Updated `StateStore.mark_as_uploaded` to persist chat and message IDs.

### Completion Notes List

- Integrated routing logic in `main.py` by passing `telegram_chat_id` and `message_thread_id` to uploader methods.
- Verified state persistence of Telegram identifiers in `state.py`.

### File List

- main.py
- telegram_uploader.py
- state.py
- tests/test_telegram_uploader.py

# Story 3.4: Route Uploads to Specified Destinations

Status: ready-for-dev

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

- [ ] Implement routing logic (AC: 1,2,3,4,5)
  - [ ] Read chat_id from creator config
  - [ ] Include message_thread_id for topics
  - [ ] Send to correct destination
  - [ ] Store chat_id and message_id in SQLite state

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
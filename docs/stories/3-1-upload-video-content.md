# Story 3.1: Upload Video Content

Status: done

## Story

As a Telegram uploader,
I want to upload videos with attribution captions,
so that content appears correctly in channels.

## Acceptance Criteria

1. Given a downloaded video file and Telegram bot token
2. When uploading using sendVideo
3. Then upload the MP4 file
4. And set caption to "{original_caption}\n\n— @{creator}"
5. And ensure bot has admin rights to avoid compression

## Tasks / Subtasks

- [x] Implement video upload to Telegram (AC: 1,2,3,4,5)
  - [x] Use Telegram Bot API sendVideo
  - [x] Set caption with original_caption and attribution
  - [x] Ensure bot is admin to prevent compression
  - [x] Handle upload response and store message_id

## Dev Notes

- Use python-telegram-bot or telebot library
- Caption format: {original_caption}\n\n— @{creator}
- Bot must be admin in the channel to avoid auto-compression
- Uploads are sequential to avoid flood limits
- Store telegram_chat_id and telegram_message_id in state

### Project Structure Notes

- No additional structure changes
- Aligns with FR5, NFR8
- Part of Epic 3: Telegram Upload

### References

- [Source: docs/epics.md#Story 3.1: Upload Video Content]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Verified `send_video` call with `ANY` for file stream in tests.
- Caption formatting logic moved to `_format_caption` helper.

### Completion Notes List

- Implemented `upload_video` in `telegram_uploader.py`.
- Added retry logic using `tenacity`.
- Verified caption formatting: `{caption}\n\n— @{creator}`.
- Added support for `message_thread_id` (Topic routing).

### File List

- telegram_uploader.py
- tests/test_telegram_uploader.py

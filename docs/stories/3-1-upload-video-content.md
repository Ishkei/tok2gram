# Story 3.1: Upload Video Content

Status: ready-for-dev

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

- [ ] Implement video upload to Telegram (AC: 1,2,3,4,5)
  - [ ] Use Telegram Bot API sendVideo
  - [ ] Set caption with original_caption and attribution
  - [ ] Ensure bot is admin to prevent compression
  - [ ] Handle upload response and store message_id

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
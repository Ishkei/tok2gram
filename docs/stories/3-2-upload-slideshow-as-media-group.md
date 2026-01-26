# Story 3.2: Upload Slideshow as Media Group

Status: ready-for-dev

## Story

As a Telegram uploader,
I want to upload slideshows as media groups with proper captions,
so that images appear as albums.

## Acceptance Criteria

1. Given downloaded slideshow images
2. When uploading using sendMediaGroup
3. Then include all images in the group
4. And set caption on the first media item only
5. And preserve image order

## Tasks / Subtasks

- [ ] Implement slideshow upload as media group (AC: 1,2,3,4,5)
  - [ ] Use Telegram Bot API sendMediaGroup
  - [ ] Include all images in the group
  - [ ] Set caption only on first item
  - [ ] Preserve order of images
  - [ ] Store message_id for the group

## Dev Notes

- Use sendMediaGroup for multiple photos
- Caption only on the first photo in the group
- Maintain the order of images as downloaded
- Sequential uploads to avoid flood limits
- Store telegram_message_id in state

### Project Structure Notes

- No additional structure changes
- Aligns with FR6
- Part of Epic 3: Telegram Upload

### References

- [Source: docs/epics.md#Story 3.2: Upload Slideshow as Media Group]
- [Source: docs/architecture.md#4 Runtime Components]

## Dev Agent Record

### Agent Model Used
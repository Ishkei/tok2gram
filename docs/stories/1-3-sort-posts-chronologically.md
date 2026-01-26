# Story 1.3: Sort Posts Chronologically

Status: ready-for-dev

## Story

As a content processor,
I want posts sorted from oldest to newest,
so that content is processed in the correct order.

## Acceptance Criteria

1. Given a list of posts with created_at timestamps
2. When sorting the posts
3. Then posts are ordered by created_at ascending (oldest first)
4. And posts without timestamps are handled appropriately

## Tasks / Subtasks

- [ ] Implement sorting logic for Post list (AC: 1,2,3)
  - [ ] Sort by created_at ascending
  - [ ] Use stable sort to preserve relative order
- [ ] Handle posts with None created_at (AC: 4)
  - [ ] Place None timestamps at the end (newest)
  - [ ] Log warning for missing timestamps

## Dev Notes

- Sorting happens after fetching posts in main workflow
- Use Python's sorted() with key=lambda p: p.created_at or datetime.max
- Ensures chronological processing for consistent behavior

### Project Structure Notes

- Implement in main.py or dedicated sorting function
- Aligns with core workflow step 3
- No conflicts detected

### References

- [Source: docs/prd.md#4 Core Workflow]

## Dev Agent Record

### Agent Model Used

Grok Code Fast 1

### Debug Log References

### Completion Notes List

### File List
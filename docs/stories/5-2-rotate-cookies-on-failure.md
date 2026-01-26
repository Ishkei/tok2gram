# Story 5.2: Rotate Cookies on Failure

Status: ready-for-dev

## Story

As an anti-block system,
I want to rotate cookies on failure,
so that blocked cookies don't prevent access.

## Acceptance Criteria

1. Given a fetch request fails due to blocking
2. When handling the failure
3. Then switch to the next available cookie
4. And retry the request with the new cookie
5. And log the rotation for monitoring

## Tasks / Subtasks

- [ ] Detect fetch failures (AC: 1,2)
  - [ ] Identify blocking-related errors
- [ ] Implement cookie rotation (AC: 3,4)
  - [ ] Cycle through available cookies
  - [ ] Update yt-dlp configuration
- [ ] Log rotation events (AC: 5)
  - [ ] Record cookie switches in logs

## Dev Notes

- Rotate to next cookie on failure
- Cycle through all available cookies
- Part of anti-bot protection
- Follows 5-1 cookie loading

### Project Structure Notes

- Uses cookies/ directory
- Aligns with FR14
- Part of Epic 5: Anti-Bot Protection

### References

- [Source: docs/epics.md#Epic 5: Anti-Bot Protection]

## Dev Agent Record

### Agent Model Used
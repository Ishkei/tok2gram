# Story 5.3: Implement Conservative Polling and Random Delays

Status: ready-for-dev

## Story

As an anti-block system,
I want to implement conservative polling and random delays,
so that requests appear human-like and avoid detection.

## Acceptance Criteria

1. Given polling configuration
2. When fetching posts from creators
3. Then add random delays between requests
4. And limit polling frequency
5. And configure delay ranges in config.yaml

## Tasks / Subtasks

- [ ] Add random delays between fetches (AC: 3,4)
  - [ ] Implement jitter ranges
  - [ ] Use random delays
- [ ] Configure polling parameters (AC: 1,5)
  - [ ] Load from config.yaml
  - [ ] Set conservative defaults
- [ ] Apply delays in fetch loop (AC: 2)
  - [ ] Delay between creator fetches

## Dev Notes

- Conservative polling: not too frequent
- Random delays to mimic human behavior
- Configurable delay ranges
- Part of anti-bot protection

### Project Structure Notes

- Config in config.yaml
- Aligns with FR15
- Part of Epic 5: Anti-Bot Protection

### References

- [Source: docs/epics.md#Epic 5: Anti-Bot Protection]

## Dev Agent Record

### Agent Model Used
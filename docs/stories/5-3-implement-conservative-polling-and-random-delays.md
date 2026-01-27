# Story 5.3: Implement Conservative Polling and Random Delays

Status: done

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

- [x] Add random delays between fetches (AC: 3,4)
  - [x] Implement jitter ranges
  - [x] Use random delays
- [x] Configure polling parameters (AC: 1,5)
  - [x] Load from config.yaml
  - [x] Set conservative defaults
- [x] Apply delays in fetch loop (AC: 2)
  - [x] Delay between creator fetches

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

Amelia (Dev Agent) - Zencoder

### Debug Log References

- Added randomized `asyncio.sleep` between creator fetches.
- Added randomized `asyncio.sleep` between Telegram uploads to avoid flood limits.

### Completion Notes List

- Implemented jittered delays in `main.py` using `random.uniform`.
- Configuration-based delay ranges loaded from `config.yaml`.
- Verified delay logic with integration tests.

### File List

- main.py
- config_loader.py
- config.yaml
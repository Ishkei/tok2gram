# Story 1.1: Load Configuration and Creators

Status: done

## Story

As a system administrator,
I want to load configuration files (creators.yaml, config.yaml),
so that the system knows which creators to monitor and operational parameters.

## Acceptance Criteria

1. Given valid config.yaml and creators.yaml files exist
2. When the application starts
3. Then all configuration parameters are loaded (fetch_depth, download_workers, etc.)
4. And creators list with usernames, chat_ids, and optional topic_ids is available

## Tasks / Subtasks

- [x] Load config.yaml file (AC: 1,3)
  - [x] Parse YAML structure
  - [x] Validate required parameters
- [x] Load creators.yaml file (AC: 1,4)
  - [x] Parse YAML structure
  - [x] Validate creator entries
- [x] Make configurations available to application (AC: 2,3,4)

## Dev Notes

- Configuration loading happens at application startup in main.py
- config.yaml contains operational parameters like fetch_depth, download_workers, yt_concurrent_fragments, retry_uploads
- creators.yaml contains per-creator routing with username, chat_id, optional topic_id
- Use PyYAML library for parsing
- Handle file not found and parsing errors gracefully

### Project Structure Notes

- Files located in project root: config.yaml, creators.yaml
- Aligns with architecture requiring local configuration files
- No conflicts detected

### References

- [Source: docs/architecture.md#5.2 Config files]
- [Source: docs/prd.md#3 High-Level Architecture]

## Dev Agent Record

### Agent Model Used

Amelia (Dev Agent) - Zencoder

### Debug Log References

- PYTHONPATH issues resolved by exporting current dir.
- config_loader.py created to separate logic.

### Completion Notes List

- Implemented `config_loader.py` with `load_config` and `load_creators`.
- Integrated loading into `main.py`.
- Verified with unit tests in `tests/test_config.py`.
- Smoke test on real files passed.

### File List

- config_loader.py
- main.py
- tests/test_config.py

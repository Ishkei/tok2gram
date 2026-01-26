# 1. Architecture Goals

## Functional goals
- Monitor **one or many TikTok creators**
- Detect **new uploads only**
- Download **videos** and **photo/slideshow** posts
- Upload to **Telegram channel/group** (optionally specific topics)
- Avoid duplicates across runs/reboots/sleep

## Non-functional goals
- **Restart-safe**: state survives reboots and container pauses
- **Best available quality**: no unnecessary recompression
- **Operational simplicity**: minimal dependencies; easy to debug locally
- **Resilient to TikTok anti-bot** measures via cookie support and backoff

---

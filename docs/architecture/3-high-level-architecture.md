# 3. High-Level Architecture

```
┌────────────────────────────┐
│   creators.yaml / config    │
└───────────────┬────────────┘
                │
┌───────────────▼────────────┐
│   Monitor / Intake Layer    │
│   - fetch latest 10 posts   │
│   - sort oldest→newest      │
└───────────────┬────────────┘
                │ post IDs
┌───────────────▼────────────┐
│   State Layer (SQLite)      │
│   - dedupe by post_id       │
│   - mark after upload       │
└───────────────┬────────────┘
                │ unseen posts
┌───────────────▼────────────┐
│   Download Layer (yt-dlp)   │
│   - best quality            │
│   - slideshow support       │
│   - 2–3 parallel downloads  │
└───────────────┬────────────┘
                │ local files
┌───────────────▼────────────┐
│ Telegram Upload Layer       │
│ - sendVideo                 │
│ - sendMediaGroup            │
│ - sequential uploads        │
└────────────────────────────┘
```

---

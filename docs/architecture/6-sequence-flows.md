# 6. Sequence Flows

## 6.1 Normal run (per creator)
1. Load config and creators
2. Fetch latest 10 posts
3. Sort oldest→newest
4. For each post:
   - If already in SQLite → skip
   - Else download media (parallel pool)
5. Upload each completed download sequentially
6. After successful upload → mark in SQLite (`uploaded_at`)

## 6.2 Failure handling
**TikTok fetch fails**
- Rotate cookie
- Backoff (skip creator this run)
- Do not write state

**Download fails**
- Retry download once (optional)
- Do not upload; do not mark state

**Telegram upload fails**
- Retry once
- If still fails: do not mark state (post will retry next run)

---

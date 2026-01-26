# 9. Deployment (Local-only)

## Recommended filesystem layout
```
~/tiktok-monitor/
  .venv/
  main.py
  config.yaml
  creators.yaml
  state.db
  cookies/
  downloads/
  logs/
```

## Execution options
- Manual:
  - `source .venv/bin/activate && python main.py`
- Cron (if available):
  - every 15 minutes, append logs to `logs/run.log`
  - safe across sleep because state + fetch_depth ensure catch-up

---

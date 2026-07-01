# 11. Architecture Decisions (Why this design)

- **SQLite** over JSON: crash-safe, atomic, scalable enough
- **Stateless runs**: correct for ChromeOS sleep/pause semantics
- **Sequential uploads**: avoids Telegram flood limits and simplifies retries
- **Parallel downloads only**: balances speed and stability

---

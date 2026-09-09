# `gamma_metrics` tail measurements — 2026-09-09

Appended by `gamma_metrics_tail_probe.py`. One block per run.
All counts are `count=exact`. Read-only.

---

## Run at 2026-09-09T00:03:34.474962+00:00

- `min(ts)` = `2026-06-10T10:55:05.214937+00:00`
- `max(ts)` = `2026-09-08T09:50:06.404415+00:00`
- total rows (`count=exact`) = **9,807**
- oldest row age at run time = **91 days**

First 10 calendar days from `min(ts)`:

| date | rows |
|---|---:|
| 2026-06-10 | 1 |
| 2026-06-11 | 1 |
| 2026-06-12 | 32 |
| 2026-06-13 | 0 |
| 2026-06-14 | 0 |
| 2026-06-15 | 72 |
| 2026-06-16 | 85 |
| 2026-06-17 | 89 |
| 2026-06-18 | 166 |
| 2026-06-19 | 166 |

Queries:
```
GET /gamma_metrics?select=ts&order=ts.asc|desc&limit=1
GET /gamma_metrics?select=*&limit=0                      Prefer: count=exact
GET /gamma_metrics?select=*&limit=0&ts=gte.<d>&ts=lt.<d+1>  Prefer: count=exact
```


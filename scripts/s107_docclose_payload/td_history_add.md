
### TD-PIN2-NEW-13 (S3 priority) — the root `.gitignore` drops research records of type `.txt`, `.csv` and `.log` repo-wide

| Field | Value |
|---|---|
| **Priority** | **S3.** `git add` silently leaves out records of those types: 1,255 of 3,528 files in the pin lane's first records commit. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 18) |
| **Component** | Root `.gitignore` (lines 33, 43, 44 at `7eb3ba5`) |
| **Measured** | The pin lane worked around it under `docs/research/pin_proof/` with a negation file; futures OI needed a force-add for C1. |
| **Fix** | One negation block in the root file, after those rules: `!docs/research/**/*.txt`, `!docs/research/**/*.csv`, `!docs/research/**/*.log`. The repo-wide rule stays, because the production tree writes logs and data files at many paths. Decision and its limits: `docs/registers/intake/I002.md` §2. The check in `apply_i002.py` can fail: a probe path under `docs/research/` must be not ignored and `logs/_probe.log` must be ignored. |
| **Status** | **CLOSED at filing** — the block landed in `99044ff` (2026-11-23, merged `ae1914d`). |

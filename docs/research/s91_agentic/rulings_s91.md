# Operator rulings — Session 91 / AM-2

Single source for S91 rulings. Other documents point here and do not restate them —
a ruling transcribed into a second place is a ruling that can drift out of agreement
with itself.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S91-A** | 2026-10-07 ~11:50 IST | Fixture-suite run window and memory ceiling | **No fixture-suite run between 08:30 and 15:40 IST**, and **every such run under an explicit `ulimit -v`**. The window covers pre-open through the close, so the suite cannot contend with the live capture chain for memory on a trading day; the ceiling makes a memory regression **fail** rather than kill the box. | **TD-S91-NEW-7.** `dmesg -T`: 08:51:24 IST `Killed process 403065 (python3) anon-rss:911788kB` — directly attributed, the suite printed `403065 Killed  python3 tests/replay/test_replay_seeded.py` itself — and 08:58:11 IST `Killed process 403716 anon-rss:955396kB`, **not attributed**. ~0.87 / ~0.91 GB on a box reading 1910 MB total, 638 MB free. **Session Manager became unreachable** during the pre-open window of a live trading morning. |
| **S91-B** | 2026-10-07 ~11:50 IST | Session concurrency and where a session may be rooted | **One Claude Code session at a time per tree**, and **never root a session in `~/meridian-engine`** — root in `~/meridian-cc` and let the engine tree pull. | **TD-S91-NEW-11.** Two sessions overlapped 08:19–08:53 IST 2026-10-07 on the same tree and **both were rooted in `~/meridian-engine`**, including the session that filed the item. A file was rewritten between one session's read and its write, caught **only** by a changed-since-read refusal; a concurrent edit elsewhere in the same file would not have been caught that way. The only thing keeping writes out of the production tree was **absolute paths** — a discipline, not a guardrail — and one slip did occur (a scratch `.sql` written to `/tmp`), harmless only because `/tmp` is not the engine tree. `~/meridian-engine` is PRIMARY and receives code by `git pull` only (**CLAUDE.md Rule 1**), so a session rooted there can edit production outside the Change Protocol with no preflight hash comparison. |

## Consequences recorded at ruling time

- **Codified as `CLAUDE.md` rules 23 (S91-A) and 24 (S91-B).** 22 was the highest existing
  rule number, measured before choosing: 0–20 are the numbered non-negotiable list, and
  21 and 22 live in a later section in `**Rule N —**` block form. 23 and 24 were added to
  the **numbered list**, because the rulings are non-negotiable rules and that is the
  section that holds them.
- **S91-A takes effect immediately.** The post-fix run owed by TD-S91-NEW-7 therefore runs
  **after 15:40 IST** under `( ulimit -v 700000; … )`, with its exits pre-registered in
  `scratch/s91/r16_result.txt`. The OOM fix itself is applied and **still unverified**.
- **S91-B takes effect at the next session start**, not retroactively: the session that
  received this ruling is itself rooted in `~/meridian-engine` and cannot re-root in place.
  It has held every write inside `~/meridian-cc` by absolute path. The operator restarts
  Claude Code rooted in `~/meridian-cc` after this task — that restart is the ruling's
  first compliance point, and nothing in this session should be read as demonstrating it.
- **Not ruled here:** the Deployment Topology §S71.1 time correction is a doc fix carried
  alongside these rulings (TD-S91-NEW-3, *Stale doc found alongside* row), not a ruling.

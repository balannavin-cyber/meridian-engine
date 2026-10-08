# Operator rulings — Session 91 / AM-2

Single source for S91 rulings. Other documents point here and do not restate them —
a ruling transcribed into a second place is a ruling that can drift out of agreement
with itself.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S91-A** | 2026-10-07 ~11:50 IST | Fixture-suite run window and memory ceiling | **No fixture-suite run between 08:30 and 15:40 IST**, and **every such run under an explicit `ulimit -v`**. The window covers pre-open through the close, so the suite cannot contend with the live capture chain for memory on a trading day; the ceiling makes a memory regression **fail** rather than kill the box. | **TD-S91-NEW-7.** `dmesg -T`: 08:51:24 IST `Killed process 403065 (python3) anon-rss:911788kB` — directly attributed, the suite printed `403065 Killed  python3 tests/replay/test_replay_seeded.py` itself — and 08:58:11 IST `Killed process 403716 anon-rss:955396kB`, **not attributed**. ~0.87 / ~0.91 GB on a box reading 1910 MB total, 638 MB free. **Session Manager became unreachable** during the pre-open window of a live trading morning. |
| **S91-B** | 2026-10-07 ~11:50 IST | Session concurrency and where a session may be rooted | **One Claude Code session at a time per tree**, and **never root a session in `~/meridian-engine`** — root in `~/meridian-cc` and let the engine tree pull. | **TD-S91-NEW-11.** Two sessions overlapped 08:19–08:53 IST 2026-10-07 on the same tree and **both were rooted in `~/meridian-engine`**, including the session that filed the item. A file was rewritten between one session's read and its write, caught **only** by a changed-since-read refusal; a concurrent edit elsewhere in the same file would not have been caught that way. The only thing keeping writes out of the production tree was **absolute paths** — a discipline, not a guardrail — and one slip did occur (a scratch `.sql` written to `/tmp`), harmless only because `/tmp` is not the engine tree. `~/meridian-engine` is PRIMARY and receives code by `git pull` only (**CLAUDE.md Rule 1**), so a session rooted there can edit production outside the Change Protocol with no preflight hash comparison. |
| **S91-C** | 2026-10-07 ~18:40 IST | Monitor alert dedupe interval | **The same condition re-notifies at most once per 30 minutes.** The brief's original *"in-session failure for 60 simulated minutes → 1 send"* was **withdrawn by the operator as wrong** once the arithmetic was put on the table: at a 30-minute re-notify, 60 minutes of continuous failure sends at minute 0 and minute 30, which is **2**. The test asserts **1 across 29 minutes and 2 across 60**, both derived from `DEDUPE_MIN` rather than transcribed. | The assistant declined to write the assertion to match the brief, on the grounds that adjusting an expected number until it passes replaces the belief with the observation (the §D.40.1 / S83 discipline). The operator ruled the spec clause wrong rather than the implementation. |
| **S91-D** | 2026-10-07 ~19:20 IST | Monitor flapping — one key AND a hold-down | **Implement both:** merge `orchestrator_not_firing` and `orchestrator_failed` into **one** condition key, **and** require **10 consecutive clear ticks** before RECOVERED. Ten is **two orchestrator cycles**, because a single **successful** cycle sits in the 5-minute look-back for up to 5 ticks, so a 5-tick hold-down is satisfiable by one good cycle between two failing ones. (A *missed* cycle is not the hazard — it reads `NOT_FIRING`, which is unhealthy, not clear.) | Gating alone left **148 sends** on the real 2026-10-07 day: **119 adjacent-minute condition changes** in band, so the 30-minute re-notify engaged **zero** times and every change cost an alert plus a RECOVERED. The operator rejected the assistant's estimate that one key alone would reach ≈14 and required a replay: **one key alone measures 93**, because merging keys cannot absorb `FAILED → OK → FAILED`. With both, **14**. |
| **S91-E** | 2026-10-07 ~19:35 IST | An unreadable probe is UNKNOWN, not healthy | **A probe failure (`QueryFailed` or any exception) must not count as a clear tick.** `check_orchestrator_failures` signals a third state, and that minute skips **both** the send and the hold-down progress. | Raised by the assistant mid-implementation: an empty condition set from a *successful* read means healthy, but from a *failed* read means no information, and collapsing the two would let **10 consecutive query failures accrue a full hold-down and emit a RECOVERED for a condition nobody observed clearing**. The operator ruled it in and required the test cell: active alert + 12 probe-failure ticks → **0 RECOVERED**, with the same 12 ticks as real OK readings → **1 RECOVERED** as the control. |

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
- **S91-C/D/E are implementation rulings on `monitor_orchestrator_health.py`, shipped in
  `6a5c0e2`** — not `CLAUDE.md` rules. They govern one file and are cited from
  **TD-S91-NEW-12**, which carries the measured before/after (**835 → 14 sends**).
- **The 30-minute figure and the 10-tick figure are different kinds of number.** 30 is a
  notification-policy choice (S91-C). 10 is **derived from the probe's own geometry** and
  the derivation is written beside the constant in the source, per the settled rule that a
  gate's threshold comes from the quantity's scale before measuring.
- **Two estimates were corrected by replay in the course of these rulings**, both recorded
  in **§D.47**: the "60 min → 1 send" spec clause (S91-C) and the assistant's "≈14 sends
  for one key alone" (**measured 93**, a 6.6× error, D.47.3). The second is the one that
  mattered — ≈14 is what the *combined* fix delivers, so accepting the estimate would have
  made a weaker fix look like it hit its target.
- **Not ruled here:** `SKIPPED_NO_INPUT` → exit 0 (**TD-S91-NEW-15**) is **requested and
  owed**, not ruled. Twelve orchestrator cycles are marked failed every trading day by
  construction until it is.

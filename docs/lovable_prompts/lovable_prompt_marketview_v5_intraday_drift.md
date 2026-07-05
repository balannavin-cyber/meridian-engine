# Marketview v5 — Home intraday-drift banner — Lovable prompt

**Paste into the same `meridian-connect` Lovable project.** One addition to **Home — Ambient**. Uses
values already on the page — no new tables, no new queries, read-only.

## The gap this closes

Home already shows the **OPEN SHIFT** line (open-vs-settled, computed once at ~09:25 by the reconciler).
But the ambient verdict is a once-nightly compute, so a regime flip that happens **intraday, after the
open** is caught by neither clock. Today's live case: the Key-Parameters **REGIME** tile reads
`POSITIVE_γ` (live) while the Ambient Verdict's gamma lens (**NET GEX REGIME**) reads `NEGATIVE_γ`
(settled) — a genuine intraday long-γ flip that the page shows as two unconnected tiles instead of a
signal.

## What to add

An **INTRADAY DRIFT** banner in the Ambient Verdict block, directly beneath the OPEN SHIFT line. It
compares two values you're already rendering:
- **live regime** = the mapped regime from the latest `gamma_metrics` cycle (the same value the
  Key-Parameters "REGIME" tile shows — `POSITIVE_γ` / `NEGATIVE_γ` / `MIXED`).
- **settled regime** = `market_environment_snapshots.net_gex_regime` (the four-lens Gamma cell).

Logic:
- **live === settled** → render nothing (the settled read still holds intraday; keep Home quiet).
- **live !== settled** → amber banner:
  **`⚠ INTRADAY DRIFT — dealers flipped to {live} since the open; the settled verdict ({settled}) is stale until tonight's recompile.`**

Style it like the OPEN SHIFT banner (same amber treatment) but with its own `INTRADAY DRIFT` label so
the two are distinguishable — OPEN SHIFT is the morning's open-vs-settled read, INTRADAY DRIFT is the
continuous live-vs-settled read that updates every 60s poll. Together they mean the settled headline is
never silently wrong: if the open moved it, the SHIFT line says so; if the tape moved it after the open,
the DRIFT banner says so.

Only the gamma regime is compared (it's the one lens with a clean live counterpart every cycle); do not
attempt live-vs-settled on breadth/participant — those have no per-minute live value on this page.

## Constraint

Read-only, existing values, existing 60s poll. This is a comparison + conditional banner, nothing else.

Deploy unchanged: `cd ~/meridian-connect && git pull && npm install && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx`.

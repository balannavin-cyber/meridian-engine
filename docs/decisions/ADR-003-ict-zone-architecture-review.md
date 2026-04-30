# ADR-003 — ICT Zone Detection Architecture Review (PROPOSED)

**Status:** PROPOSED 2026-04-30 (Session 14, end-of-day operator observation)
**Decision driver:** Operator observation that ICT zones drawn by `build_ict_htf_zones.py` are not reflecting actual price-pivot behavior reliably this week, despite working "last week". Specific symptom: zones either (a) sit far from where intraday price respects/rejects, or (b) old zones remain ACTIVE despite price clearly invalidating them, or (c) fresh structural pivots intraday don't get captured as new zones.

## Context

The ICT zone detection layer is foundational. ENH-76 / ENH-77 / ENH-78 / ENH-46-D / dashboard / Pine all read from `ict_htf_zones` and trust the zones' boundaries + status. If the zone layer is misaligned, every signal downstream is operating on bad context.

This concern is NOT new — it has surfaced over multiple sessions in different forms:
- TD-030 (CLOSED Session 11 ext) — `recheck_breached_zones()` not running, zones never marked BREACHED
- TD-031 (CLOSED Session 11 ext) — D BEAR_OB underactive (filter timing bug)
- TD-040 (CLOSED Session 13) — recheck order overwrote BREACHED → ACTIVE every rebuild
- TD-042 (CLOSED Session 13) — Pine bar_index negative on old zones (rendering, not detection)
- TD-047 (Session 14) — `ict_zones` vs `ict_htf_zones` two-table architecture confusion

The pattern is: each session finds a different specific bug in the zone layer, fixes it, but the operator's underlying confidence in zone correctness has not stabilized. Today's observation suggests the cumulative fixes have not addressed something more fundamental.

## Hypotheses (not yet tested)

1. **Detection thresholds tuned to wrong regime.** Current OB threshold (0.40% NIFTY, 0.30% SENSEX from Exp 29 v2 Session 10) may be calibrated for a normal-vol environment. Current week is high-vol (today -1.5% NIFTY). Threshold may admit too many noisy candidates or miss real structural pivots.
2. **5m basis is too noisy for HTF zones.** ADR-002 settled "5m for ICT", but H/D/W zones may need source bars at the same TF as the zone (D zones from D bars, not 5m bars rolled up).
3. **Breach detection is necessary but not sufficient.** Marking a zone BREACHED is a binary outcome — but zones can also EXPIRE / become STALE without being broken (e.g. price moves away, the zone becomes structurally irrelevant). No "stale" status currently exists.
4. **Zone validity windows (`valid_from` / `valid_to`) may be too long.** Default 30-day weekly zone window may persist zones past their useful life. Today's spot is reading against zones from 04-06 to 05-08 — three weeks of lookback, possibly too long for the current move structure.
5. **Order block detection logic may be wrong.** Standard ICT OB definition is "the last opposite-direction candle before a strong directional move". MERDIAN's `detect_order_blocks()` implementation may not match this definition exactly. Worth code review against ICT canon.
6. **PDH/PDL coverage may be misaligned.** Daily PDH/PDL is defined by yesterday's high/low — but yesterday vs which session? Cash session 09:15-15:30? Or 24h day? Or NSE/BSE close timestamp?
7. **The whole concept may not work in current regime.** ICT works best in mean-reverting environments. Trending environments (today, this week) may simply not respect HTF structures at the same rate. The edge may be regime-conditional.

## Decision required

NOT this session. NOT this week. This needs a structured diagnostic before any redesign work.

**Proposed work plan:**

| Phase | Session | Output |
|---|---|---|
| **Phase 1 — Diagnostic** | Session 15 (or 16 if ENH-79 takes priority) | Pull last 10 trading days. For each day: query `ict_htf_zones` ACTIVE zones at session open; identify intraday pivots in `hist_spot_bars_5m`; compute "respect rate" — % of pivots that occurred within X points of an active zone boundary. Per-symbol, per-pattern-type. Publish numeric truth. |
| **Phase 2 — Targeted redesign** | Sessions 16-17+ | Only after Phase 1 identifies WHICH layer is broken (W vs D vs H, OB vs FVG vs PDH-PDL, threshold vs validity window vs definition). Targeted, not from-scratch. |
| **Phase 3 — Rebuild + validation** | Sessions 17-18+ | Implement, deploy with shadow window, compare old-vs-new respect rates, cut over only on >X% improvement. |

## DO NOT

- Do NOT touch `build_ict_htf_zones.py` reactively in Session 15 based on intuition. Diagnosis first.
- Do NOT propose a full rewrite without numeric evidence of which layer is broken.
- Do NOT block ENH-79 build on this — ENH-79's PWL weekly sweep is a different signal layer (price levels, not zones).
- Do NOT re-litigate TD-030/031/040/042/047 closures. Those were real fixes, just incomplete.

## Status

- **PROPOSED** (Session 14)
- Operator concern logged. Diagnostic deferred to Session 15+.
- File this as `docs/decisions/ADR-003-ict-zone-architecture-review.md` when committing tomorrow.

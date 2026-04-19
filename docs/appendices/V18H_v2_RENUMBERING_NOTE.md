# V18H_v2 Renumbering + Migration Errata

**Issued:** 2026-04-19
**Applies to:** MERDIAN_AppendixV18H_v2.docx
**Affected session:** 2026-04-17 / 2026-04-18 (Research Sessions 4-5)

## Summary

V18H_v2 introduced ENH items as ENH-43..47 and OI items as OI-11..15.
Two problems:

1. **ENH collision** -- ENH-43..47 were already taken by COMPLETE items in
   `MERDIAN_Enhancement_Register_v7.md`.

2. **OI register violation** -- `MERDIAN_OpenItems_Register_v7.md` was
   permanently closed on 2026-04-15 with the directive that "new
   operational issues will be tracked in the Enhancement Register or
   session appendices". V18H_v2's OI-11..15 should never have been
   created as a new OI series.

Reconciliation: ENH renumbered to next-free integers; OI items folded
into the matching ENH entries (or promoted to their own ENH when
standalone). No new OI-* series created.

V18H_v2.docx is NOT modified -- session records are immutable.

## ENH Renumbering

| V18H_v2 label | Canonical ID | Title |
|---|---|---|
| ENH-43 | **ENH-53** | Remove breadth regime as hard gate |
| ENH-44 | **ENH-55** | Momentum opposition hard block |
| ENH-45 | **ENH-56** | Premium sweep detector (monitor) |
| ENH-46 | **ENH-57** | MTF OHLCV infrastructure (COMPLETE) |
| ENH-47 | **ENH-58** | hist_pattern_signals table (COMPLETE) |

ENH-54 (HTF Sweep Reversal) in v7 is unrelated to any V18H_v2 item. The
renumbering skips ENH-54 to preserve it.

## OI Migration

V18H_v2 OI-11..15 are NOT renumbered to `RESEARCH-OI-*` or any other OI
prefix. The OpenItems Register was permanently closed 2026-04-15. All
content migrates to the Enhancement Register.

| V18H_v2 label | Destination | How it merges |
|---|---|---|
| OI-11 | **ENH-53** Build field | "`build_trade_signal_local.py`: remove breadth_regime from hard gate..." -- becomes ENH-53's build instructions |
| OI-12 | **ENH-55** Build field | "`build_trade_signal_local.py`: if abs(ret_session) > 0.0005 and opposes..." -- becomes ENH-55's build instructions |
| OI-13 | **ENH-59** (new) | Promoted to full ENH: "Patch script syntax validation rule" |
| OI-14 | (no persistent ID) | Shadow gate sessions 9+10 verify -- one-off session task, tracked only in `session_log.md` |
| OI-15 | **ENH-56** Monitoring field | "Log live PE/CE sweeps <1%..." -- becomes ENH-56's monitoring instructions |

## JSON Migration

The following keys were deleted from `docs/registers/merdian_reference.json`
`open_items` on 2026-04-19 as part of this reconciliation:

- `ENH-43`, `ENH-44`, `ENH-45`, `ENH-46`, `ENH-47` -- renumbered, migrated
  to Enhancement Register v8 section
- `ENH-35`, `ENH-37`, `ENH-38`, `ENH-42` -- stale duplicates of register
  entries (already COMPLETE / DEFERRED in register)
- `RESEARCH-OI-07`, `-08`, `-09`, `-10` -- stale open state (all closed
  2026-04-13 per Enhancement Register v7 COMPLETE flags on ENH-38/40/44)
- `RESEARCH-OI-11..15` -- migrated to Enhancement Register v8 section

Retained in JSON:

- `C-N` (critical) -- per convention, critical fixes stay in lightweight JSON tracker
- `A-N`, `V18A-N`, `D-06`, `E-01/02/06`, `OI-01..06`, `OI-07-INFRA`,
  `HIST-02`, `SPO-01` -- closed historical audit trail

## Numbering Convention (adopted 2026-04-19)

See `MERDIAN_Documentation_Protocol_v2.md` Rule 5.

- **ENH IDs**: monotonic integers in Enhancement Register. Pick next-free
  when adding. IDs permanent -- REJECTED items keep their ID as
  rejection record.
- **OI IDs**: No new OI-* prefixes. OpenItems Register permanently closed
  2026-04-15. New operational items go to Enhancement Register (if
  persistent) or session appendix (if session-local).
- **C-N IDs**: Critical fixes continue in `merdian_reference.json`
  `open_items` as lightweight in-flight tracker. Monotonic integers.

## Authoritative Cross-Reference

- `docs/registers/merdian_reference.json` v6+ -- current operational state.
  `open_items` contains only C-N, legacy closed-historical, and
  non-ENH/OI prefixes.
- `MERDIAN_Enhancement_Register_v7.md` v8 appendix section -- ENH-53, 55,
  56, 57, 58, 59 definitions with migrated OI content.
- `MERDIAN_Documentation_Protocol_v2.md` Rule 5 -- numbering convention
  enforcement.
- This file -- mapping for readers of V18H_v2.docx.

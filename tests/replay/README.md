# Replay harness (S90 / AM-1)

Test MERIDIAN against recorded days, offline, at any hour — instead of waiting for a live session.

```bash
bash tests/run_offline.sh          # all offline checks; exit 0 = PASS (~35 s)
python3 tests/replay/replay_contracts.py            # score every golden day, print a summary
python3 tests/replay/replay_contracts.py --check    # compare with expected/, exit 1 on any difference
python3 tests/replay/replay_contracts.py --pin      # re-pin expected/ — only after reading why it changed
python3 tests/replay/test_replay_seeded.py          # inject defects into a golden day; each must be caught
```

| Piece | What it is |
|---|---|
| `fixture_client.py` | In-memory stand-in for `SupabaseClient` over `tests/golden/*/inputs/*.csv.gz`. Same `select`/count calls as live; read-only. |
| `replay_contracts.py` | Runs `check_contracts_shadow.evaluate()` — the exact function the `*/5` cron runs — at every 5-minute cycle 09:15–15:30 IST of each golden day. |
| `contracts.json` | The contracts as applied in S90 (seed + SENSEX strike-GEX widening). Refresh when live contracts change, then re-pin. |
| `expected/*.statuses.csv` | Pinned status per product per cycle. A code change that alters any of them fails `--check`. |
| `test_replay_seeded.py` | Frozen chain → STALE (+ lineage); dropped gamma cycles → MISSING; second expiry → DEGRADED; closed day → CLOSED; clean day → all OK. |

**Scope, stated:** only the relations frozen in the fixtures (chain, strike GEX, gamma, spot) for the fixture's own symbol. The fixtures hold the front expiry only, so the chain is scored against 1 expiry with no row band (`fixture_scope()`); every other check runs as in production. Calendar = the V18E rule engine (offline).

**Proven to catch a regression:** moving `SESSION_CLOSE` from 15:30 to 15:20 fails `--check` with 8 differences on 2026-10-01 SENSEX (S90, 2026-10-06).

**First finding from replay (2026-10-06):** `market_spot_snapshots` reads **MISSING at 15:20 and 15:25 on every golden day**. Spot capture stops at 15:14 by design (`capture_spot_1m_v2.py` `MARKET_CLOSE_GUARD`, the CAS window, ADR-022) while the contract assumes the session runs to 15:30 — so the live shadow runner raises a false MISSING every afternoon. The fix is in the contract (a per-product session end), not the capture. Pinned as-is until that is ruled.

**Next:** compute writers join as they gain `as_of` reads (roadmap R2.6): golden inputs in, their outputs diffed against the frozen `gamma_metrics` / `gex_strike_snapshots`. Tick-based writers (WCB, breadth) use the daily tick freeze (`scripts/freeze_market_ticks.sh`, `~/merdian_fixtures/ticks/`).

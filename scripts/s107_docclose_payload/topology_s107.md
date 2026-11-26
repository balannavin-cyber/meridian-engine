
## §S107 — Session 107 (2026-11-21 → 11-26): the tape writer's database login exists on the production box; a one-off backfill ran from a separate clone; the Board build depends on two settings; the box's memory is measured

Doc Protocol v5.1: hosts, schedules and credential paths only. Detail: `docs/research/s107/`;
`docs/registers/intake/I003.md`; `docs/registers/STREAMS.md`. Recorded at the S107 doc-close (2026-11-26).

**Production box, tape writer credential.** `/etc/tape-live/tape-w.env` (mode 600, owner `tapelive`, 169 bytes)
holds `TAPE_LIVE_W_DSN` for the pooler user `tape_w.<ref>`, created 2026-11-24 06:18 IST by `tape_w_password.py`,
which refuses a second run. The installed unit is still the 2a unit (file only, no database write, code
`56bf0558`); the 2b unit template is **not installed**. 2b code for the gate sits at
`/opt/tape-live/d1f9ba243a4c1882ea72f28d42ed93249887bec1`. The first live 2b day is earliest Mon 2026-11-30
(order-flow lane, `claude/ofl/MR_OFL9_close_inputs.md` §2).

**Production box, memory.** t3.small, **1,910 MB, no swap**, Python 3.10.12, clock UTC. On 2026-11-24 a stray
`claude --resume` held 460 MB; with it gone, used 238 MB and available 1,474 MB. The operator ruled no resize.
TD-PIN2-NEW-12.

**Production box, a second clone used for one job.** `~/v2-backfill` is a shallow clone of branch `pin/v2-check`
at `2574709`, made 2026-11-25 to run `backfill_gamma_v2_from_gss.py` with the engine `.env` sourced (never printed)
under `ulimit -v 700000`. It holds four logs (`dry_full.log`, `apply_full.log`, `apply_1125.log`,
`rerun_full.log`). It is not a deploy tree and nothing is scheduled from it; it can be deleted once the logs'
totals are in git (they are, in `docs/research/s107/engine_to_pin_LATEST.md`). The pin lane's trees on the box are
`~/meridian-cc` and the detached worktree `~/meridian-v2-check`.

**Marketview build settings.** Every Board build since 2026-11-03 must be made with
`VITE_SUPABASE_URL=https://marketview.meridianalpha.in` and `VITE_SUPABASE_ANON_KEY=proxy`. A build without them
produces a Board that reads nothing. The S107 guard and promote scripts set both and audit the built bundle
(TD-S107-NEW-1). Staging is a folder on the production box, served at `marketview.meridianalpha.in/staging/`
from `/var/www/marketview-staging`; live is `/var/www/marketview`. Live from 2026-11-25 about 18:08 IST: Board
`d7642c2`, bundle `index-CHOS8H-T.js`; the build it replaced is kept at `/var/www/marketview.bak-90cb618`.

**Retail box (from the retail lane, MR-S13).** `ubuntu@ip-172-31-30-166`, t4g.medium, 3,824 MB. Measured load
peaks under a 850 MB cap: Dhan contracts 756 MB, Kite 497 MB, Upstox 681.1 MB; the Upstox serving process idles at
104 MB RSS. Timers enabled: `gateway-load-dhan` 06:30 IST, `gateway-load-kite` 06:45, `broker-preopen-watch` 08:10,
`broker-feed-adopt` 06:15, `tape-runner` 08:50. Upstox socket and timers installed, not enabled.

**Gamma writer host.** The registers do not record the date the production gamma writer moved from the Windows
machine to the box, or which code version ran on which date. TD-S107-NEW-6.

**Windows machine.** `refresh_dhan_token.py` failed there on 2026-11-23 with a vendor message that the refresh
method changed (TD-S107-NEW-4). This machine generates nothing (§S76.A); the production mint is the box's 08:20 IST
cron. The open question of a second 09:05 schedule (CURRENT, carried) is not answered here.

**Observed, not changed.** PUBLIC grants on `cron`, `net` and `pg_stat_statements` objects in the engine database
(TD-S107-NEW-3). No cron line, unit or security group changed in S107.

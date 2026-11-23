<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/cc_prompt_pin_fix_stage0_code_read.md -->
# CC prompt: pin fix, Stage 0 (read-only code read)

Box: MERIDIAN engine EC2, SSM shell, user ssm-user, tmux session `0`, Claude Code in `~/meridian-cc`. Manual mode. Scope document: `claude/pin/pin_fix_scope_DRAFT_2026-11-21.md` (operator approved D1–D6 as recommended, 2026-11-21 16:53 IST). Stage 0 changes nothing.

Paste:

```
Pin fix, Stage 0: read-only code read. You write exactly one file and change nothing else.

Rules, all binding:
- No write to the database. No vendor call. No edit to any tracked file. No git write of any kind (no add, commit, stash, restore, clean, switch, checkout, pull, fetch, merge). Git reads only, always as git --no-optional-locks.
- Never cat, grep, head, source or otherwise read .env or any file whose name contains .env. Never print a token, key, password or connection string; if a line you would quote contains one, write REDACTED in its place.
- Database: catalog reads only (information_schema.columns, pg_indexes, pg_get_viewdef), through bin/roq.sh as merdian_ro, one statement per file, under ( ulimit -v 700000; ... ). One table read is allowed, item 8 below, and only if its plain EXPLAIN shows no Seq Scan; otherwise write UNMEASURED.
- Any python only as PYTHONDONTWRITEBYTECODE=1 python3 -B under ( ulimit -v 700000; ... ). The box has 1,910 MB of memory and no swap and hung today from memory exhaustion: run nothing heavy, import nothing that loads data, do not run analyze_v5.py.
- Read production source in ~/meridian-engine (read-only). Write only docs/research/pin_proof/fix/stage0_code_read.md under ~/meridian-cc (create the folder). First line of that file: <!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/stage0_code_read.md -->
- Every statement carries file and line numbers. Quote at most the few lines that carry each rule. Anything you cannot find is written NOT FOUND with where you looked. Do not infer, do not propose a design, do not write code.

Items:
0. State: for ~/meridian-engine and ~/meridian-cc print the current branch and HEAD sha (git --no-optional-locks -C <tree> rev-parse --abbrev-ref HEAD and rev-parse HEAD), and for ~/meridian-cc whether branch e1-e3-e10 exists and whether it is merged into main (git --no-optional-locks branch -a --merged main, filtered to e1). Print date in IST.
1. option_chain_snapshots: every column with type (information_schema), its indexes (pg_indexes), and from ingest_option_chain_local.py which code line writes each of: last traded price, open interest, strike, option type, expiry date, run id, spot, the timestamp. Say which column holds the price a solver would use and whether a bid/ask or mid is stored.
2. compute_gamma_metrics_local.py: how one run is selected (run id, front expiry), where spot comes from, how time to expiry is computed and in what unit, and the exact lines that build gex_cr and the gamma_call / gamma_put columns of gex_strike_snapshots.
3. write_gex_cycle_history_local.py: how it obtains rank 1 and the runner-up, every column it writes to gex_cycle_history, and what triggers it.
4. Views: for v_gex_strike_rank, v_pin_board and v_gex_concentration give the sql/ file that defines each, the live definition length from pg_get_viewdef, and the columns each exposes. List every other view or script in the repo that reads v_gex_strike_rank (grep the tree, excluding .env files).
5. Board: whether the Marketview frontend source is on this box. If it is not, write NOT ON THIS BOX. If the repo holds an API or read layer the Board calls for the Pin tab, name the file and the objects it reads.
6. Schedule: from crontab -l and systemd timers, print only the lines that run ingest_option_chain_local.py, compute_gamma_metrics_local.py and write_gex_cycle_history_local.py (REDACT anything secret), their order and spacing, and the wrapper script if any.
7. Study code: in docs/research/pin_proof/lookback_v5/analyze_v5.py list, by reading the source only, the functions a per-run job would need (solvers, compute_run, pick, tie-break), each with its line range, its imports, and whether it touches the filesystem or load_runs. State the exact inputs compute_run takes and what it returns.
8. Retention: the earliest row date in option_chain_snapshots. Read pg_indexes first, choose an ORDER BY ... LIMIT 1 on an indexed column, run plain EXPLAIN, and run the query only if there is no Seq Scan.

At the end print to the screen, in your reply text inside one code block, under 60 lines: item 0 in full; for items 1 to 8 the two or three facts that matter most, each with file:line; every NOT FOUND and UNMEASURED; the sha256 of stage0_code_read.md; and confirmation that no tracked file changed (git --no-optional-locks status --porcelain, lines other than untracked files under docs/research/pin_proof/ counted by status code). Then stop.
```

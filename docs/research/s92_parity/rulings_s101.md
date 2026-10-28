# Operator rulings — S101 (2026-10-25 → 10-28)

Single source for S101 rulings. Evidence and findings: `S101_close_inputs.md` (→ `docs/research/s101/` at the doc-close).

| # | When (IST) | Ruling |
|---|---|---|
| **S101-A** | 10-25 21:31 | **Core split — YES.** Package the composed gamma cycle as `merdian_compute.gamma.compute_gamma_core` the same night, same branch, separate commit (C2). |
| **S101-B** | 10-25 21:31 | **Deploy timing as recommended.** Part C reads first on unchanged writers; deploy from 16:30 IST Monday 10-26 (S90-J window), fast-forward, read-only recompute check, written rollback `git revert --no-edit 7b91d1a..4a1d8e1`. Deployed 10-26 17:08. |
| **S101-C** | 10-25 21:31 | **Board-core gaps:** package ATM IV (C3) and the pin path (C4); update the contract (C5); one commit per item, branch only, nothing merged until the deploy. |
| **S101-D** | 10-25 21:31 | **File the S101 findings as TDs at the close** (list: `S101_close_inputs.md` §5). Stop with an evidence table. |
| **S101-E** | 10-26 10:10 | **O1:** the live `v_gex_strike_pin_zone` matches no file in `sql/` — file a TD, commit the live definition to `sql/` (C6), correct contract §8; the sibling `v_gex_strike_accel_zone` likewise (C7). Live views are identified by full `pg_get_viewdef` md5 against a file that reproduces it. |
| **S101-F** | 10-26 17:23 | **Close TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2** on the Part C (a) evidence. The one non-zero runner exit (10-26 14:00, ENH-133 writer `57014` timeout) is a different class — **file as a new TD**. |
| **S101-G** | 10-27 10:27 | Schedule the 10-27 close-time board reads and R19; keep the Chrome board tab open. |
| **S101-H** | 10-28 09:58 | **EOS.** Close S101; the Doc Protocol v5 doc-close and the carried reads run at S102 open. |

**Open for the operator's ruling (raised in S101, not ruled):** Health OVERALL token threshold (30 min); the NIFTY board
after the expiry-day close (roll to the next leg or label the expired-leg state); Context IV skew blank on a 0-DTE front
leg; WCB publishing from pre-open ticks; carry of `held_for_cycles` across an expiry roll when the leader strike is the
same on both contracts. Details: `S101_close_inputs.md` §5.

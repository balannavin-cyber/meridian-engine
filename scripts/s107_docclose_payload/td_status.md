### S107 status changes to existing entries (doc-close run for Session 107; Doc Protocol v5.1 Rule 3: one paragraph, no body edits)

Rulings `docs/research/s107/rulings_s107.md`; intakes `docs/registers/intake/I002.md` (register bodies written in this
close) and `docs/registers/intake/I003.md` (MR-OFL9, MR-S13, MR-PIN3). Ledger: `TDs_NEW=31` — Board-pin
TD-PIN2-NEW-1…13 and TD-PIN3-NEW-1…3, order-flow TD-OFL9-NEW-1…8, engine TD-S107-NEW-1…7 · `TDs_CLOSED=1`:
**TD-PIN2-NEW-13 closed at filing** (the root `.gitignore` negation block landed in `99044ff`, 2026-11-23), its block
written straight to the end of `tech_debt_history.md`'s entries by the S104 / S105 precedent. **TD-PIN1-NEW-1** (a blank
vendor gamma leg treated as zero, S1) keeps its OPEN status and its body; two things are recorded against it here.
First, its framing is corrected by AR §D.61.1: the vendor's gamma field is never missing, "0.0" is present, and the
defect is lopsided call and put gammas at one strike. Second, the fix chosen is not an in-place change: the operator
ruled versioned isolation on 2026-11-25 (ADR-033), so V1 keeps the per-leg rule and V2 (`merdian_compute/gamma_v2.py`,
`gex_strike_v2`, `gex_run_v2`) carries one gamma per strike beside it. The V2 tables hold the full stored history
(19,050 runs, 2026-05-25 → 2026-11-25); the live V2 writer is **not** switched on, so the entry stays OPEN until the
operator's decision after the pin lane's old-against-new comparison. **TD-S101-NEW-6** gains a second and a third
occurrence (TD-OFL9-NEW-3; the `/apply_*.py` rule in S107) and is not edited. **TD-S81-NEW-3**: the `tape_w` login is
proved (2026-11-24, `PASS tape_w login ok`), so the "login owed" half of its 2026-11-21 Update row is met; the row is
left as written. **TD-PIN1-NEW-4**: the registration of `v_gex_pin_gross` records the server version beside both md5s
(plain and pretty), which is the second option of that entry's proper fix, applied to one view. Nothing else changed
status. **Tracker rows:** §2.2 unchanged; the tracker's version moves in this close (v2.23).


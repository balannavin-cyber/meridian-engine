# docs/research/s106 — engine lane, 2026-11-05 → 2026-11-21 (archived from project knowledge)

Engine session **S106** (Doc Protocol v5.1, ruled 2026-11-21) covers the engine-lane work done in chat under the name "S105" after the S105 git close (`eba1193`, 2026-11-05), plus 2026-11-18 → 11-21. None of it was in git before this commit.

**Provenance.** Each file is a byte copy of the project-knowledge doc of the same name (`claude/<name>`; parity files `claude/parity_eval/<name>`) as read on 2026-11-21, with one change: the reference product's name is replaced by "the parity target" (v5.1 Rule 15(d); S104 precedent). Two files were renamed for the same reason:

| Git name | Project-knowledge name |
|---|---|
| `docs/research/s106/engine_note_parity_target_observed_2026-11-12.md` | `claude/engine_note_<vendor>_observed_2026-11-12.md` |
| `docs/research/parity_eval/05_parity_target_updates_2026-11-15_synthesis.md` | `claude/parity_eval/05_<vendor>_updates_2026-11-15_synthesis.md` |

References inside the files to `MERDIAN_Parity_Target_Spec.md` anticipate the rename of the git spec file in the S106 doc-close (Phase 2).

**State notes (not edits to the records):**
- `rulings_s105_tape_w.md` says "NOT APPLIED". Read on 2026-11-21: `pg_policies` returns the 10 `tape_w` policies and `merdian_ro` carries `default_transaction_read_only=on`, so the grants and R-2 are applied. The password step, V2/V3/V5 and the login proof are still owed. Recorded in `docs/registers/intake/I001.md` A5/A6.
- `cc_prompt_engine_one_login_e1_e3_e10.md` and `engine_e1_e3_e10_plan_review_2026-11-20.md` were written from the retail lane's chat for the engine lane; the build landed as `e4ef1b8`.

Also in this commit: `docs/registers/STREAMS.md` (v0.2) and `docs/operational/MERDIAN_Documentation_Protocol_v5.1.md` (in force 2026-11-21). `SHA256SUMS` at the archive root covers every file.

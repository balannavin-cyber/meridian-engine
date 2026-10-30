# Rulings — Session 102 (2026-10-28 → 2026-10-30)

Single source for S102 rulings. Operator words quoted where the record holds them.

| # | When (IST) | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S102-A** | 10-30 morning | Γ size on the board vs the parity target ("L Cr" should be thousands) | **Option 1 first: display-only rescale** (×0.01 to ₹ Cr per 1 % move) — "1". | Verified: stored γ·OI·S²/1e7 is per 100 % move; the target's figure is per 1 % (× √(τ/5 d)) — S97 F1. |
| **S102-B** | 10-30 morning | Stored unit | "1 first, record ADR to be implemented after studying pan meridian impact and a change roadmap causing least impact, testing every bit before pushing to board." → **ADR-032**: D1 display via `_1pct` wrapper views (RULED); D2 stored unit, D3 history, D4 COMMENTs (PROPOSED, gated on §5 impact study + §6 roadmap); D5 √τ out of scope (R26). | `docs/decisions/ADR-032-gex-stored-unit.md`; inventory `docs/research/s102/gex_unit_inventory_S102.md` v2. |
| **S102-C** | 10-30 08:43 | D1 board wording and scope | "I agree. Proceed" — **A: D1 with the W wording table approved**; caveats name √τ ("Not normalised for time to expiry (the parity target scales by √(τ/5 d)) …"); B (adopt R26 √τ) not taken. | Cost comparison A vs B given before the ruling. |
| **S102-D** | 10-30 09:43 | Legacy pages (Positioning, Max Pain, Context, Structure strip) | **Rescale** (not retire), second Lovable round — "this" on the Rescale option. | S100-N precedent (aligned, not retired). |
| **S102-E** | 10-30 10:20 | In-app manual Γ figures before promote | "So lets go" on options A / B / C — **taken as A** (text restated ÷100 with "(then shown as …)", ≈ where the board had rounded; screenshots unchanged and labelled as old scale). B (new screenshots) owed. | Recorded as taken, not as an explicit "A". |
| **S102-F** | 10-30 11:05 | Session | **EOS**: "We will need to EOS document and carry forward to the next session." Doc-close runs at S103 open from `docs/research/s102/S102_close_inputs.md`. | Precedent S101-H. |

**Rulings owed (carried):** see `docs/research/s102/S102_close_inputs.md` §4.

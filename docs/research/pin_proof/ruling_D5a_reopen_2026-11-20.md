# Ruling: D-5a re-opened for the pin look-back only (2026-11-20)

**Ruled by:** the operator, Fri 2026-11-20 07:23 IST ("re-open"), confirmed 07:29 IST ("Record a re-open of the pressure-style pin").
**Stream:** engine (Board pin). **Recorded by:** the advisor, same session.
**Status:** RULING. It authorises a test. It authorises nothing in production.

## 1. What is re-opened

D-5a (S89, 2026-10-03; Enhancement Register ENH-125) declined the ranked-pressure leg on evidence and recorded "Do NOT re-propose a proximity-weighted-gamma pressure key".

That instruction is lifted **for one purpose only**: a pressure-style pin may be entered as a candidate definition in the pin look-back (pre-registration v2 of `claude/pin/`, not yet written).

## 2. Why

- D-5a asked whether two stand-in formulas could **copy the parity target's ranking**. It used 12 NIFTY runs and scored top-5 rank agreement (mean ρ about 0).
- The look-back asks a different question: whether a pressure-style pin **predicts where price is drawn and settles**, against other definitions and against baselines, on the full chain history.
- D-5a's finding stands for the question it tested. It was never evidence on the outcome question.

## 3. Terms (proposed by the advisor in the question the operator answered)

1. At most **two** pressure variants.
2. The distance-decay shape and width of each are **fixed in writing in the pre-registration before any outcome query**. No tuning after.
3. Each variant must beat **both** the at-the-money baseline and its own mirror baseline, not only the netted pin.
4. The holdout period is read **once**.
5. **Nothing is authorised for the Board.** A win earns a separate proposal and a separate ruling.

## 4. What does not change

- D-5a's decline of the ranked-pressure leg **as a Board item** stands.
- ADR-025 D3's recorded deviation for L12 (pin ranked on |gamma|, not the reference's pressure key) stands.
- S96-I (D-4, four-case direction classification, declined) is not touched.
- The parity target's own formula is still undisclosed. A variant in the look-back is MERIDIAN's own construction, not a copy.

## 5. Order of work agreed in the same session

The operator ruled that the gamma-input question comes before the pin look-back:

1. Origin of the blank gamma legs (vendor, ingest, or writer/compute). Read-only.
2. Whether the own-solved history (`hist_option_greeks_1m`) is clean enough to carry the look-back. Read-only.
3. Pin look-back (pre-registration v2), on the inputs steps 1 and 2 support.
4. Production gamma fix, scoped from steps 1 and 2.

Steps 1 and 2: `claude/pin/cc_prompt_gamma_inputs_check.md`.

## 6. Owed at doc close

- Enhancement Register, ENH-125 block: add a dated line pointing here.
- `docs/research/s89_rulings/pressure_leg_decline_S89.md`: add a dated pointer here (do not edit the finding).
- Session rulings file for this session: carry this ruling under its session id.

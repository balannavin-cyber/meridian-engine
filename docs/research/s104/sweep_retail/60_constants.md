# 60 — thresholds and tolerances (numeric literals compared with or scaled against a Γ value)

| file:line | literal | compared with / scaled against | Γ-scale-sensitive? |
| --- | --- | --- | --- |
| migrations …1300:160 (+engine copy s83:286) | `1e7` | divides γ·oi·S² | defines scale A; only the sign of the sum is used downstream |
| …1000:94 | `tau` (0.30 / 0.25 in L4) × peak_gex_cr | `gex_cr >= tau*peak` | no (ratio) |
| …0700:63, …0800:45,85 | `0` | `gex_cr <> 0`, `> 0`, `< 0` | no (sign) |
| …1300:66-69 | `5e-5` | `abs(s.gamma)` per-option γ | no (γ not Γ); listed to prove it is not Γ |
| …0600:44-45 (walls) | 1.5 (wall.band), 120 (iv floor) | σ multiple, IV | no |
| O2: pin_state.nopin_conc_floor 0.04, locked_ratio_max 0.50, stable_held_for 6, locked_held_for 12 | | concentration share, ratio, cycle counts | no (shares) |
| compute/tests/l3.py:11,24 | `TOL = 1e-9`, `max(1.0, |want|)` | relative-with-floor tolerance on net_gex and others | **mildly**: a floor of 1.0 means values below 1 are compared absolutely; at scale B net_gex ~ 100x smaller, so more cycles fall under the floor (tolerance becomes looser relative to the value). Not a failure, a changed meaning |
| board read-sentence.ts:27 | `grossGex > 0`, `.toFixed(2)` | ratio | no |
| board read-sentence.ts:45,49 | `localGex === 0`, `> 0` | sign | no |
| board loader.ts:76-87 | none (sums, nearest strike) | | no |
| board view-model.ts:38 | max 2 fraction digits | displayed Γ | **yes** (resolution) |
| packages/worker/src/dev-cycle.ts:111,131 | `(r.gamma ?? 0) > 0`, gammas === 0 | per-option γ | no |
| normalize.ts:40 | `gamma !== 0` | per-option γ | no |
| tests 41/43 | 1.5, 111111, 222222, 0.1+0.2 | fingerprints / float round trip | no |

Claim "no non-zero numeric literal is compared with a Γ identifier in TS": pattern `(Gex|gex_cr|net_gex|strikeGamma)[^;]*[<>]=? *-?[0-9]|[<>]=? *-?[0-9][^;]*(Gex|gex_cr|net_gex)` over board/src and worker/src non-test .ts (14 files): matched only comparisons with 0 (read-sentence.ts:27,49). Control: the pattern matched those two known lines. Python side (compute/tests, scripts) and SQL were read, not pattern-claimed.

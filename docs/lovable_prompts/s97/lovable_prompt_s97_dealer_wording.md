# Lovable prompt — S97 "dealer" wording on the ∂Δ/∂t and ∂Δ/∂σ surfaces (TD-S96-NEW-1)

> Paste everything below the line into Lovable. Base: `meridian-connect` `804d684` (live).
> Ruling: **S97-A** (TD-S96-NEW-1: drop "dealer", add the P2 tag; scope widened by the operator's second yes to the
> two drawers' WHAT IT IS lines and the COMPUTED sign note). Wording approved by the operator 2026-10-12, ~10:10 IST,
> strings C1, C2, D1–D3 as below.
> **Wording-only round: no data read is added, edited or removed.** Guard (layout-only form, S92 README):
> `bash ~/mv_lovable_guard.sh 804d684` — no view named, so `src/lib/board.ts` is outside the allowlist and any change
> to a data read fails the build. The guard checks the **net** diff since `804d684`, so any stray Lovable commit on
> top of `804d684` must be reverted before this round.
> ACL fingerprint: nothing in the database changes in this round, so pre- and after-round must equal the current
> baseline on all nine rows (`relations 350 ccc3895d…`, `anon_public_privs 256 f19b614e…`, `anon_writable_objs 0`,
> `public_functions 40 5d8cd7f8…`, `rls_policies 28 d16e21d6…`, …) — **unless the P3b apply has run first**, in which
> case the post-P3b re-baseline is the reference.
> Out of scope, unchanged by ruling: the Hedge-per-1 % tile and its drawer ("What dealers must trade …", "dealers
> would buy …"), the Net Γ drawer, the ∂Γ/∂t and ∂Γ/∂σ entries, and every DEX string.

---

**Change five existing strings on the Flows tab and nothing else. You do NOT own these words — copy them exactly.**

**Change ONLY** the file(s) that hold these strings (expected: `src/components/board/PinFlowsBody.tsx` and/or
`src/components/board/LadderPanel.tsx`). Do not touch any other file, dependency, config, env, SQL or Supabase setting.
Do not add, edit or remove any data read (no `supabase.` line may change). Do not change layout, styling, numbers,
formatting functions, or any other string. Never use the words "vanna" or "charm". Copy every quoted string EXACTLY,
including `·`, `—`, `Δ`, `σ`, `(`, `)` and `;`.

## 1. Captions under the ladder (the paragraph shown when a Δ layer is selected)

Only the fixed words change. Every interpolated value, the `bars per strike.` text and the gap sentence that follows
it stay exactly as they are.

**C1 — ∂Δ/∂t layer.** Today it reads, with the numbers interpolated:
`Dealer delta-notional drifts {net} per calendar day (gross {gross}); bars per strike.`
Make it:
`Delta-notional drifts {net} per calendar day (gross {gross}); dealer side regime-dependent (P2); bars per strike.`

**C2 — ∂Δ/∂σ layer.** Today:
`A +1 IV point moves dealer delta-notional {net} (gross {gross}); bars per strike.`
Make it:
`A +1 IV point moves delta-notional {net} (gross {gross}); dealer side regime-dependent (P2); bars per strike.`

## 2. Explanation drawer entries (`DETAIL`)

**D1 — ∂Δ/∂t entry, `what`.** Replace
`How dealer delta-notional changes as one calendar day passes with spot and IV unchanged.`
with
`How delta-notional changes as one calendar day passes with spot and IV unchanged.`

**D2 — ∂Δ/∂σ entry, `what`.** Replace
`How dealer delta-notional changes for a +1 implied-vol point, spot and time fixed.`
with
`How delta-notional changes for a +1 implied-vol point, spot and time fixed.`

**D3 — ∂Δ/∂t and ∂Δ/∂σ entries, `computed`, only where the text occurs.** Replace the substring
`PE legs negated (dealer long calls, short puts)`
with
`PE legs negated (S89 sign convention; dealer side regime-dependent, P2)`
In those two entries only. If the substring also occurs in the ∂Γ/∂t, ∂Γ/∂σ, Net Γ or any other entry, leave it
there unchanged and list where you saw it in your reply.

## Reply with

The file(s) changed and each string you replaced (old → new). Confirm: no `supabase.` line was added, edited or
removed; no other string, file, style or behaviour changed; where else (if anywhere) the D3 substring or the word
"dealer" occurs on the Flows tab. If any string above does not exist exactly as quoted, change nothing and say which.

---

## Staging read (Claude, operator's Chrome, after the guard PASS)

1. Both symbols, Flows tab: select the ∂Δ/∂t and then the ∂Δ/∂σ layer and read the caption — C1 / C2 exactly, with
   the gap sentence still appended after `bars per strike.`
2. Open both Δ drawers: D1 / D2 exactly; D3 exactly where it occurred.
3. Numbers unchanged: the two Δ tiles' book, pre-open and flow against the L4 statement of the live read pack, taken
   on the same `ts` (`docs/research/s96_priority/p7/live_read_pack_2026-10-12.md`, L4).
4. Unchanged by scope: the Hedge-per-1 % caption still reads "… dealers would buy …"; the DEX drawer still carries
   "dealer side regime-dependent (P2)" once.
5. Promote only from the checked commit, in a refusing subshell, with a backup of `804d684`
   (`/var/www/marketview.bak-804d684`), as the S96 rounds.

---

## Round record

**Wording** approved by the operator 2026-10-12 ~10:10 IST (S97-A; drawers included by a second yes). **Base `804d684`
→ staging `c0aad8d`** (commits `97fc8a2` "Changes", `c0aad8d` "Updated Board caption strings").

**Lovable.** A first reply answered the S96 gap-sentence follow-up instead of this prompt ("Fixed — the gap sentence now
appends …", `Board.tsx`); a re-paste reported C1/C2 in `Board.tsx` and D1–D3 in `LadderPanel.tsx` already applied and no
`supabase.` line touched. Neither reply was taken as evidence; the guard and the staging read were.

**Fingerprint** 10:15 IST, all nine rows equal to the S96 baseline: `relations 350 ccc3895d…`, `anon_public_privs 256
f19b614e…`, `anon_writable_objs 0`, `public_functions 40 5d8cd7f8…`, `rls_policies 28 d16e21d6…`, `default_privileges 27
9db86164…`, `schemas 10 2a889318…`, `public_triggers 0`, `anon_role 1 c506ff14…`.

**Guard** `mv_lovable_guard.sh 804d684` (layout-only): PASS — two paths, both M (`LadderPanel.tsx`, `Board.tsx`); no new
data reads, no credentials, no vanna/charm; build clean; **net 2 files, 4 insertions, 4 deletions** (so the stray
gap-sentence edit contributes nothing net).

**Staging read** (Claude, operator's Chrome, `/staging/board`, chain 10:15): C1 exact on SENSEX and NIFTY, C2 exact on
SENSEX; D1, D2 exact; D3 exact in the ∂Δ/∂t COMPUTED and absent from ∂Δ/∂σ's, which never carried the substring; the
gap sentence once per caption, no duplicate; Hedge-per-1 % caption and drawer unchanged ("dealers would sell …", "What
dealers must trade …"). Numbers against L4 in one statement through roq on the same run (NIFTY ts 10:15:08, SENSEX
10:15:07): NIFTY ∂Δ/∂t −41,016 / −24,728 / −16,288, ∂Δ/∂σ +5,356 / +3,082 / +2,274, gap 45,370; SENSEX −3,406 / −2,080 /
−1,326, +1,197 / +734 / +463, gap 1,67,720 — all equal to the columns rounded. **Staging PASS.**

**Promotion (2026-10-12 17:26 IST):** promoted together with the help round as `04fcd05`, live bundle
`index-BrWRk1OP.js`, backup `/var/www/marketview.bak-804d684`; live read PASS (ruling S97-A). Help round record:
`claude/lovable_prompt_s97_help_route.md` (project knowledge; written by the parallel manual session).

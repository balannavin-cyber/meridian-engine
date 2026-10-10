# Lovable prompt — S94 wording pass (text only)

> Paste everything below the line into Lovable. Base: `meridian-connect` `417e966`.
> Rulings: S94-D (levels evidence note), the P2 (S94) sign result, and TD-S92-NEW-1 ("contracts" → "quantity").

---

**This is a text-only change. Change ONLY the user-visible string literals listed below.** Do not
change any identifier, variable or prop name (for example `dampenTotal`, `amplifyTotal`,
`strongestAmplifyStrike`, `maxGammaStrike` all stay exactly as they are). Do not change colours,
CSS variables, layout, components, imports, data fetching, queries, Supabase, SQL, env,
package or config files. Do not add dependencies. If a listed string is not found exactly,
**leave that file unchanged and say so in your reply.** Do not search for near-matches.
Code comments may be left as they are.

Why: positive and negative γ on this board are a **positioning sign** (call γ +, put γ −). The labels
"dampening/amplifying" describe **dealer** gamma, which needs dealers to be net long calls and short
puts. NSE participant OI does not support that as a standing assumption (P2, S94). So the labels
must state the sign, not a dealer behaviour.

## 1. `src/lib/read.ts` line 29

`"a dampening"` → `"a net +γ"` and `"an amplifying"` → `"a net −γ"`

## 2. `src/components/NarrativeModal.tsx`

- line 26: `"Short-gamma regime, amplified moves"` → `"Net −γ regime (positioning sign)"`
- line 91: replace the sentence
  `Net dealer γ of {fmt(state.netDealerGamma, " Cr")} indicates {((state.netDealerGamma ?? 0) > 0) ? "dampening flows" : "amplifying flows"}.`
  with
  `Net positioning γ of {fmt(state.netDealerGamma, " Cr")} ({((state.netDealerGamma ?? 0) > 0) ? "net +γ" : "net −γ"}; calls +, puts −). Not a dealer reading (P2, S94).`
  The expression `state.netDealerGamma` itself is unchanged.
- line 96, and the matching other branch of the same conditional: replace **both** branch strings so that
  neither describes dealer behaviour. The negative branch, currently
  `"Short-γ dealers chase price, amplifying directional moves."`, becomes `"Net −γ positioning."`
  The positive branch becomes `"Net +γ positioning."`

## 3. `src/components/board/LadderPanel.tsx`

- line 27 (`g_net`):
  - `what`: `"Signed sum of dealer gamma — same value as the strip's Net Γ."` →
    `"Signed sum of positioning gamma (calls +, puts −) — same value as the strip's Net Γ."`
  - `how`: `"Cool = dampening (dealers hedge against moves); warm = amplifying. The white dots on the ladder are its running sum from the top strike down."` →
    `"Cool = net +γ; warm = net −γ. Reading these as dealer dampening/amplifying assumes dealers are net long calls and short puts; NSE participant OI does not support that as a standing assumption (P2, S94). The white dots on the ladder are its running sum from the top strike down."`
- line 30 (`g_spark`) `how`: `"Shape of the day: drifting toward zero means the dampening is wearing off."` →
  `"Shape of the day: drifting toward zero means the net +γ is shrinking."`
- line 33 (`oi_callwall`): `scale: "raw contracts"` → `scale: "raw quantity"`; and append to `caveat`:
  `" Levels: P1 — the day's high/low did not land closer to the walls than to random strikes at the same σ (n = 85)."`
- line 34 (`oi_putwall`): the same two changes as line 33.
- line 35 (`oi_total`): `unit: "contracts"` → `unit: "quantity"`; `caveat: "Do not compare contract counts across products without context."` →
  `caveat: "OI is quantity at the current lot size, not contracts. Do not compare across products without context."`
- line 38 (`p_pin`): `how` — replace `"Cool = dampening, warm = amplifying."` with `"Cool = net +γ, warm = net −γ."`;
  append to `caveat`: `" Levels: P1 — the day's high/low did not land closer to the pin than to random strikes at the same σ (n = 85)."`
- line 260: `"← amplifying · dampening →"` → `"← net −γ · net +γ →"`
- line 282: `l="dampening strike"` → `l="net +γ strike"`; `l="amplifying strike"` → `l="net −γ strike"`
- line 285: `l="amplifying γ"` → `l="net −γ"`; `l="dampening γ"` → `l="net +γ"`

## 4. `src/pages/Board.tsx` line 266

`net >= 0 ? "dampening" : "amplifying"` → `net >= 0 ? "net +γ" : "net −γ"`

## 5. `src/marketview/ui.tsx` line 78

`desc: "short dealer γ · trend-amplifying"` → `desc: "net −γ (positioning sign)"`.
If the sibling `LONG_GAMMA` entry's `desc` mentions dealers, change it to `"net +γ (positioning sign)"`.
Otherwise leave it.

## 6. `src/marketview/sections.tsx`

- lines 78–79: `` `Σdmp ${fmtNum(s.dampenTotal)}k · Σamp ${fmtNum(s.amplifyTotal)}` `` →
  `` `Σ+γ ${fmtNum(s.dampenTotal)}k · Σ−γ ${fmtNum(s.amplifyTotal)}` ``
- line 108: `dampening (long γ) vs amplifying (short γ)` → `net +γ vs net −γ (positioning sign: calls +, puts −)`
- lines 111 and 150: `label="Σ dampen"` → `label="Σ net +γ"`
- lines 112 and 151: `label="Σ amplify"` → `label="Σ net −γ"`
- line 113: `label="strongest dampen"` → `label="largest +γ strike"`
- line 114: `label="strongest amplify"` → `label="largest −γ strike"`
- line 138: `positive = dampening flows · negative = amplifying flows` → `positive = net +γ · negative = net −γ (positioning sign)`

## 7. `src/pages/Lab3D.tsx`

- line 251: `(cool dampening · warm amplifying)` → `(cool net +γ · warm net −γ)`
- line 327: `l="dampening · long γ"` → `l="net +γ"`; `l="amplifying"` → `l="net −γ"`

## Reply with

The list of files you changed, and for each one the count of string replacements made. Name any
listed string you could not find exactly. Expected: exactly 7 files —
`src/lib/read.ts`, `src/components/NarrativeModal.tsx`, `src/components/board/LadderPanel.tsx`,
`src/pages/Board.tsx`, `src/marketview/ui.tsx`, `src/marketview/sections.tsx`, `src/pages/Lab3D.tsx`.
`SplitBar.tsx` holds only a code comment and may be left.

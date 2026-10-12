# S92 Lovable safeguard kit

How Marketview parity presentation was changed through Lovable in Session 92 without trusting
Lovable's track record (S39: anon granted ALL through Lovable's Supabase connection; `.env` committed
to the public repo, TD-S39-NEW-3; S40: guessed column names). Recorded in ADR-025 Amendment C, C7.

| file | what it is | when |
|---|---|---|
| `acl_fingerprint.sql` | **Read-only.** Counts + md5 of relation ACLs/RLS flags, anon privileges in `public`, `public` functions (ACL, SECURITY DEFINER), RLS policies, default privileges, schema ACLs, triggers, the anon role. | Supabase SQL editor, **before** pasting a prompt and **after** Lovable pushes. Any change in a count or md5 means the database was touched. |
| `mv_lovable_guard.sh` (v2) | Box script. Checks Lovable's **net** diff since a base commit; only if every check passes does it fast-forward `~/meridian-connect`, run `tsc`, build `/staging/` (pipefail) and rsync it. **Never pushes, never touches live.** | `bash ~/mv_lovable_guard.sh <BASE>` (layout-only) or `bash ~/mv_lovable_guard.sh <BASE> <view>` (one named data read allowed, in `src/lib/board.ts`). |
| `lovable_prompt_pin_flows_design_pass.md` | Pin + Flows presentation pass (L7/L8/L12 surfaces). | Base `e3fc3d3` → live `5563bb7`. |
| `lovable_prompt_followups.md` | The three follow-up messages sent in that chat. | — |
| `baseline_pin_flows_2026-10-09.json` | 32 exact strings captured from live before the pass; staging was read against them. | Data frozen until 09:15 IST. |
| `l13_measure.sql` | M1 anon EXPLAIN · M2 per-symbol summary · M3 top-5 \|Δ\| per side. **Run each block on its own** — the editor shows only the last statement's result. | Before the L13 prompt. |
| `lovable_prompt_l13_rotation.md` | L13 bind of `v_oi_rotation_since_open` (S92-G), SENSEX withheld (S92-H). | Base `5563bb7` → live `1deeb87`. |
| `lovable_prompt_lab3d_optional.md` | Optional 3D view at `/board/3d` reading `v_gex_strike_terrain` (S92-J). | Base `1deeb87` → live `417e966`. |
| `mv_lovable_guard_lab3d.sh` | **One-time** guard for S92-J: allows exactly `three`, `@react-three/fiber`, `@react-three/drei`, `@types/three`, the lazy `/board/3d` route, `Lab3D.tsx`, `terrain.ts`; one read of `v_gex_strike_terrain`; no raw-table reads; **fails if three.js lands in the entry chunk**. | `bash ~/mv_lovable_guard_lab3d.sh <BASE>` |

**Guard checks (any one fails the build):** a path outside the allowlist (`src/pages/Board.tsx`,
`src/components/board/**`, `roadmap.md`, plus `src/lib/board.ts` only when a view is named); a
forbidden path (`.env*`, lockfiles, `package.json`, build/ts/lint config, `index.html`, other
`src/lib/**`, `supabase/**`, `*.sql`); an added data read other than exactly one
`supabase.from("<view>")`; an added credential pattern (case-sensitive — v1 was case-insensitive and
a lockfile checksum `…tEYjHy8O…` matched the JWT prefix); the words *vanna*/*charm* in any case.

**S92 record.** ACL fingerprint identical at 05:07, 06:53 and 07:25 IST (`relations 343
fa642324…`, `anon_public_privs 249 63c4a8e7…`, `anon_writable_objs 0`). The guard stopped one build
(`78fb26e`, an operator 3D experiment — TD-S92-NEW-2). Lovable cannot set commit messages; commits
are identified by SHA.

**S92-J record.** ACL fingerprint identical before and after the round (`relations 344 d985125a…`,
`anon_public_privs 250 436d93b7…`, `anon_writable_objs 0`). Guard `1deeb87` → `b6ffec1`, then
`417e966` (legend + phone-width labels): PASS both, three.js absent from the entry chunk. One stop on
the way — the box has no bun and `package-lock.json` was untracked, so `npm ci --silent` failed
silently (TD-S92-NEW-6). Promoted from the checked commit with no pull; previous live kept at
`/var/www/marketview.bak-1deeb87`.

**Always:** verify `/staging/` in a browser against figures measured from SQL before promoting; a
browser check also caught what the guard cannot (CSS `uppercase` turning ∂Δ/∂t into ∂Δ/∂T).

**S95 record.** ACL fingerprint identical before and after each round: the 11:19 IST baseline for
the DEX rounds, and the 13:18 snapshot (`relations 346 06c07d80…`, `anon_public_privs 252
7f41638b…`, `anon_writable_objs 0`, taken after `v_dex_repriced_zero` was created) for the S\*
rounds. It predates `v_oi_since_preopen`, so re-baseline before the next round. DEX book: `d1912d2` → `392256a`;
S\* tile `103f663` / `1c5a047`; sub-line fix `719e85c` / `858cb46`. Guard PASS on each; promoted
from the checked commit with a backup each time. Prompts and record: `docs/lovable_prompts/s95/`.

**Two lessons, both found on `/staging/` in a browser, neither visible to `tsc` or the guard:**
- **Read the component that places items before adding items.** Round 1 declared three DEX items
  that `FlowsBody` never placed, so nothing rendered.
- **A level tile names the spot it is measured from** when the header's spot comes from a
  different clock. The S\* tile said "above spot" against the chain spot while the header showed
  the γ run's spot, so on NIFTY the tile and the header disagreed on the side.

**S96 record.** Three rounds, prompts and round records in `docs/lovable_prompts/s96/`: DEX flow bricks
`858cb46` → `62f5c55`, the badge `62f5c55` → `c81b700`, the Δ-pair bricks `c81b700` → `804d684`. Guard PASS on each
(one named read per round; an extended read must be rewritten as ONE line with `.select(`, because the guard counts
added lines containing `supabase.from("<view>")`). Fingerprint identical before and after every round. **Baseline
(06:15 / 06:30 IST 2026-10-12):** `relations 350 ccc3895d…`, `anon_public_privs 256 f19b614e…`, `anon_writable_objs 0`,
`public_functions 40 5d8cd7f8…`, `rls_policies 28 d16e21d6…`, `default_privileges 27 9db86164…`, `schemas 10 2a889318…`,
`public_triggers 0`, `anon_role 1 c506ff14…`. **Re-baseline after the P3b apply** (a table, a sequence, a function and a
policy). Lovable predicted "no flow before 09:15" before the open three rounds running; each time the views carried the
previous SESSION run (§D.50.12). A rollback command is printed only inside a block that refuses to run without an
explicit argument.

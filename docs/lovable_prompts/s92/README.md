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
| `lovable_prompt_lab3d_optional.md` | Optional 3D view at `/board/3d` reading `v_gex_strike_terrain` (S92-J). | After the view passes Section 4 live. |
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

**Always:** verify `/staging/` in a browser against figures measured from SQL before promoting; a
browser check also caught what the guard cannot (CSS `uppercase` turning ∂Δ/∂t into ∂Δ/∂T).

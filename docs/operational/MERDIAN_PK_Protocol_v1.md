# MERIDIAN Project Knowledge Protocol v1.1

<!-- pk: lane=engine; git=meridian-engine:docs/operational/MERDIAN_PK_Protocol_v1.md -->

| Field | Value |
|---|---|
| Status | **IN FORCE.** Ruled by the operator 2026-11-21 ~16:43 IST ("accepted as recommended", D1–D5), engine session S106. It is the detailed form of Doc Protocol v5.1 Rule 15: Rule 15 stays in force, and this document says how to carry it out. P7 replaces the 90 % prune line in Rule 15(c), and P3.4 replaces the copy-time substitution in Rule 15(d) for new files. It takes effect for each lane at that lane's next close (v5.1 Rule 13(e)). **v1.1** (P9–P13) ruled 2026-11-21 ~18:05 IST (D6–D9). |
| Git home | `meridian-engine` `docs/operational/MERDIAN_PK_Protocol_v1.md` |
| Applies to | Every lane (engine, OFL, retail, FOI, PIN, parity), every box (Local, production, retail), every repo (`meridian-engine`, `meridian-tape-staging`, `retail-platform`, `retail-gateway`). There is **one** project knowledge (PK), "Meridian 0404". |
| Companions | `MERDIAN_Documentation_Protocol_v5.1.md` (Rules 12–17), `STREAMS.md` (lanes, git homes) |

## Why (what went wrong, 2026-11-21)

The S106 close found PK at 1,895,965 of 2,000,000 (94.8 %) and could not safely prune it:

1. **PK-only files.** 30 files existed only in PK: 12 OFL prompts, 15 retail prompts and 3 engine sweep reports. None could be deleted without losing it.
2. **No owner, no git home.** Nothing in a PK file said which lane owned it or where its git copy lived. Checking needed one round trip per lane and per repo, and matched by file name only.
3. **Duplicates at the same path.** Uploading through the project UI adds a second file instead of replacing the first, which left two `ADR-025-parity-acceptance-criterion.md`. A delete by path cannot tell the two apart.
4. **Accumulation.** Rulings went back to S87, superseded protocol drafts were still there, and executed CC prompts were never removed.
5. **Name drift.** Git copies carried a substituted reference-product name (v5.1 Rule 15(d)). PK copies kept the original, so PK and git were no longer byte-equal and their names differed.
6. **Stray locations.** Lane files sat at the PK root (`rulings_s87.md`, `rulings_s91.md`, `rulings_s93.md`) instead of in a folder.

## The rule, in one line

**PK holds only the working set. Every PK file has one owner lane and one git home, both readable from the file itself. A file leaves PK at its owner's close once its git copy is pushed.**

---

## P1 — What PK may hold (three tiers)

| Tier | What | Where in PK | Owner | Refreshed |
|---|---|---|---|---|
| **A. Canon** | Engine registers and the CLAUDE.md set: `tech_debt_LATEST`, `MERDIAN_Enhancement_Register_LATEST`, `merdian_reference_LATEST.json`, `CLAUDE.md`, `CLAUDE_history.md`, System Map, Topology, Data Inventory, Assumption Register, Decision Index, the roadmap, and the CLAUDE.md split files (`registers.md`, `ops-shell.md` and the rest, per ADR-028) | PK root | engine | **Replaced** at every engine close from git (the `pk_extract` output plus the upload list). Never edited in PK. |
| **B. Reference** | ADRs, CASEs, runbooks, Governance, Testing Protocol, Guardrails, the Doc and PK protocols, `STREAMS.md`, `CURRENT.md`, `session_log.md` | PK root, or `claude/` for `STREAMS`, `CURRENT`, `session_log`, protocols and intake | engine | Only when the git file changes. |
| **C. Lane working set** | Per lane: the current session prompt, the latest close inputs, rulings for the current and previous session, live pre-registrations and designs, results the open session still reads, and CC/Lovable prompts **not yet run or still running** | `claude/<lane>/` | that lane | At each of that lane's closes (P4). |

**Nothing else.** Anything outside these three tiers is a prune candidate at the next close of the lane that owns it.

**Never in PK, under any tier:**
- Secrets, `.env` content, tokens, passwords, connection strings.
- Raw dumps: query output, logs, CSV or JSON data over **40 KB**. Those go to git or stay on the box; PK gets a summary that points to them.
- A file over **60 KB**, unless it is Tier A.
- The reference product's name, in a file name or in its content (P3).

## P2 — Ownership and git home, readable from the file

### P2.1 — Lane folders and their git mirrors (single table; also the source for `STREAMS.md` §1)

| Lane | PK folder | Git mirror (repo : directory) | Branch that counts |
|---|---|---|---|
| Engine | `claude/` (root files) and `claude/intake/` | `meridian-engine` : `docs/research/s<N>/`; intake goes to `docs/registers/intake/` | `main` |
| Order flow | `claude/ofl/` (moved at OFL's own close; v5.1 Rule 16) | `meridian-engine` : `docs/research/tape/` | `main` (records). Code follows its own gate on `tape/live-l2`. |
| Retail | `claude/retail/` | `retail-platform` : `docs/research/retail/` (DECIDE D1) | `main` |
| Futures OI | `claude/futoi/` | `meridian-engine` : `docs/research/futoi/` | `main` |
| Board pin | `claude/pin/` | `meridian-engine` : `docs/research/pin_proof/` | `main` |
| Parity (reference) | `claude/parity_eval/` | `meridian-engine` : `docs/research/parity_eval/` | `main` |

**Mirror rule:** the git path is the mirror directory plus the same relative path and the **same file name** as in PK. A PK subfolder such as `claude/retail/runbooks/` becomes the same subdirectory in git. No renames and no edits between the two copies: they are byte-equal.

### P2.2 — Header line on every new Tier C file

Every new Tier C file starts with one line:

```
<!-- pk: lane=<engine|ofl|retail|futoi|pin|parity>; git=<repo>:<path> -->
```

The header never changes, so it stays byte-equal in PK and git. It lets anyone looking at PK alone see who owns a file and where to check for its git copy. In JSON files, put it as a `"_pk"` key. In code files (`.py`, `.ts`, `.sql`), put it in a comment. For files that existed before this protocol, the folder in P2.1 decides ownership.

### P2.3 — What counts as "in git"

A file is in git when it exists at its mirror path on the **origin** of the branch listed in P2.1, after a `git fetch`. None of these count:
- a local commit that hasn't been pushed;
- a worktree;
- an unmerged feature branch;
- the box's working tree;
- a file with the same name at a different path.

The check matches on the **path**, not only the name.

## P3 — Writing to PK

1. **Write only into your own folder.** A lane never writes to, replaces or deletes another lane's folder or Tier A/B. If another lane needs a change, it asks the owner, either through `STREAMS.md` §3 or with a note pasted into the owner's chat.
2. **Replace in place.** To update a file, write it to the **same path** (`project_write`). Don't create `_v2` or `_final` copies of a working document. Versioned names are only for documents that are **frozen** by design (pre-registrations `_FROZEN`, studies `_v4`/`_v5`). Only the live version stays in PK. Older frozen versions go once they are in git.
3. **UI upload over an existing path means delete first.** The project UI adds a second copy instead of replacing. Before uploading a file whose path already exists in PK, delete the PK copy from a chat (`project_delete`), then upload. After the upload, run `project_info` and check that the path appears once.
4. **No reference-product name.** Write "the parity target" in PK documents from the start, so the PK and git copies stay byte-equal. This replaces the copy-time substitution in v5.1 Rule 15(d) for every new file.
5. **Names:** ISO dates (`YYYY-MM-DD`). Use fixed prefixes per v5.1 Rule 16: `MR_<SERIES><n>_session_prompt.md`, `MR_<SERIES><n>_close_inputs.md`, `rulings_<series><n>.md`, `cc_prompt_<topic>.md`, `lovable_prompt_<topic>.md`, `<topic>_prereg_*`, `<topic>_result_*`, `<topic>_record_*`. Lowercase lane folders.
6. **Prompts are single-use.** Once a CC or Lovable prompt has run, its outcome lives in that lane's result, record or close inputs. The prompt goes to git at the lane's close and leaves PK at the same close (P4 step 3). It never sits in PK across a close.

## P4 — Lane close: the PK steps (added to the v5.1 Rule 3 lane checklist)

Run these in order, in the lane's chat, at every lane close.

```
☐ 1. List:   project_info → every path under claude/<lane>/ (and any path whose header names this lane).
☐ 2. Sort each file into KEEP (P1 Tier C, still needed next session) or GO (everything else: superseded, executed prompts, prior-session rulings older than "previous", results nothing reads now).
☐ 3. Commit: copy every file created or changed this session (KEEP and GO) byte for byte to its mirror path (P2.1); commit by explicit path; push. Record the sha.
☐ 4. Check:  one command, labelled box + shell, run in the mirror repo after `git fetch`:
             git ls-files --error-unmatch <mirror path 1> <mirror path 2> ...   (on the counting branch)
             Every GO path must be printed. A path that is not printed stays in PK and goes on the carry-over list with its reason.
☐ 5. Delete: project_delete every GO path that step 4 confirmed. Never delete a path step 4 did not print.
☐ 6. Verify: project_info → no GO path remains; no path appears twice; record knowledge_size.
☐ 7. Record the "PK delta" section in the close inputs (template below).
```

The lane's close is not done until step 7 is written. If the operator stops the close partway, the close inputs say which step was reached.

## P5 — Lane session open: two checks

```
☐ project_info: your folder holds only your Tier C set; nothing of yours sits at the PK root; no duplicate paths.
☐ Read STREAMS.md §3 for any PK request addressed to your lane.
```

## P6 — Engine close: the PK steps (added to the v5.1 Rule 3 engine checklist, after the register steps)

```
☐ 1. Collect every lane's "PK delta" since the last engine close (part of the Rule 13 intake read). Carry-overs go into I<nnn>.md as items to verify.
☐ 2. Tier A refresh: for each Tier A file, project_delete the PK copy, then write or upload the new one (P3.3). Never upload over an existing path.
☐ 3. Tier B: replace only the files whose git copy changed this session.
☐ 4. Engine Tier C: P4 steps 1–7 for claude/ root and claude/intake/.
☐ 5. Whole-PK audit from project_info:
      (a) no duplicate paths;
      (b) no file at the PK root outside Tier A/B;
      (c) every claude/<lane>/ folder matches its lane's last PK delta;
      (d) knowledge_size against the budget (P7).
     Any finding goes in STREAMS.md §3 as a request to its owner lane. The engine never deletes a lane's file itself.
☐ 6. Record knowledge_size and the audit result in CURRENT.md and in the engine close inputs.
```

## P7 — Budget

| Measure | Value | Action |
|---|---|---|
| Cap | 2,000,000 (project `max_knowledge_size`) | — |
| **Target after every engine close** | ≤ **1,600,000 (80 %)** | Headroom for one full Tier A refresh plus a week of lane work. |
| **Prune line** | > **1,700,000 (85 %)** at any lane close | That lane runs P4 before adding anything new. |
| **Hard stop** | > **1,800,000 (90 %)** | No lane adds a file until the engine runs the P6 audit and owners prune. This replaces the 90 % prune line in v5.1 Rule 15(c), which proved too late: on 2026-11-21 the close found PK at 94.8 % with no PK-only file safe to delete. |

Each lane records `knowledge_size` at its close (P4 step 6), so the trend is visible before it becomes a problem.

## P8 — Boxes, repos, trees

- PK is reached only from chats, never from a box. Boxes reach git only. Every PK↔git move is therefore two steps, done by the lane: the chat gives the content, then a box commits it, or a box commits it and the operator uploads it. Name the box and shell for every command (Local PowerShell, production `ssm-user@ip-172-31-35-90` bash, retail `ubuntu@ip-172-31-30-166` bash).
- A lane commits only in its own git home (P2.1) and its own tree. One CC session per tree. The engine never commits into a lane's working tree (v5.1 Rule 13(e)). Lanes whose mirror is in `meridian-engine` commit the records on their own branch or worktree and merge to `main` at their close. Otherwise they hand the files to the next engine close through intake.
- Production-box rules still apply: no box analysis 08:30–15:40 IST Mon–Fri. `git ls-files` and `git fetch` count as light checks, but confirm the box time first.

## P9 — Opening a new lane (v1.1)

A lane exists only once its row is in `STREAMS.md` §1 and in the P2.1 table. No lane writes to PK before that.

```
☐ 1. The operator names the lane and its purpose.
☐ 2. The engine writes the row in STREAMS.md §1 the same day (v5.1 Rule 13(d)):
       lane key (lowercase, one word), series code MR-<X>, ID prefix TD-<X><n>-NEW-k,
       PK folder claude/<key>/, git mirror <repo>:<dir>, counting branch,
       boxes and trees it works in, engine-owned objects it touches (§2).
     If the mirror is a new repo, add the repo to P8. No repo yet → the mirror is
     meridian-engine:docs/research/<key>/ until one exists.
☐ 3. The operator approves the row. That approval opens the lane.
☐ 4. The lane's first session prompt carries the standing PK block (P10).
```

Work that started before the row was approved moves into `claude/<key>/` at once. Its first close runs P4 like any other close.

**A study inside a lane is not a lane.** It lives in a subfolder of its parent, `claude/<lane>/<study>/`, with the same subdirectory in the parent's git mirror. It becomes its own lane only by P9. Example: the greeks study (v5.1 ruling 4) sits in the engine lane.

## P10 — Every session prompt carries the PK block (v1.1)

Each lane passes its rules forward through its next session prompt. So every session prompt, in every lane, now and in future, includes this block under its standing rules. The closing session copies it forward unchanged:

```
PK (binding, claude/MERDIAN_PK_Protocol_v1.md): lane=<key>; PK folder claude/<key>/;
git mirror <repo>:<dir> on <branch>. Write only in your folder; new files carry the
P2.2 header; executed prompts leave PK at the close; no reference-product name.
At close: P4 steps 1–7 and the "PK delta" section. Open: P5.
```

The engine checks this at intake (P6 step 1). A lane's close inputs that come without the block in the next session prompt become a request in STREAMS §3.

## P11 — Chats that belong to no lane (v1.1)

Any chat in this project that writes to PK must belong to a lane, and it writes only into that lane's folder. Ad hoc questions, one-off analysis and quick checks write nothing to PK unless the result is durable. If it is durable, the chat puts it in the folder of the lane it serves. If no lane fits, it goes into the engine's `claude/` root, and the next engine close handles it under P4.

A paste that belongs to another lane (a CC prompt, a close input) is not acted on. Send it back to its own chat.

## P12 — Dormant and retired lanes (v1.1)

| State | When | PK holds | STREAMS §1 |
|---|---|---|---|
| **Dormant** | No session for 30 days, or the operator parks the lane | Only the last close inputs and the next session prompt. Everything else goes through P4 at the lane's last close, or at the next engine close if the lane never closed. | status `dormant`, date |
| **Retired** | The operator ends the lane | Nothing. A final P4 runs, every file is in git, and the folder is deleted from PK. | status `retired`, final sha; the git home stays |

A dormant lane wakes by its next session prompt. Its row and prefix remain reserved, and the prefix of a retired lane is never reused.

## P13 — External systems (v1.1)

A system with its own Claude project and knowledge base is **not a lane** here, even when Meridian depends on it. Today that is **MALPHA**: its own box, its own repo, its own project. This PK holds only the facts at the point where it meets Meridian:
- Meridian takes the Kite token from the MALPHA box, and that token feeds market breadth and WCB.
- Those facts live in the engine registers: Topology, `STREAMS.md` §2 and §3, and the engine TDs and rulings (for example R8, TD-S106-NEW-3).

The external system's own documents stay in its own project. A lane's working document about such a point stays with that lane, under P4 (for example `claude/retail/malpha_cold_storage_brief_2026-11-17.md`). If the external system later moves its work into this project, it joins by P9.

---

## Template — "PK delta" section of a lane's close inputs

```
## N. PK delta (PK Protocol v1, P4)

knowledge_size at close: <n> / 2,000,000 (<pct> %)   Step reached: 7 of 7
Commit: <repo> <branch> <sha> (pushed; three-way sha if box + Local + origin)

| PK path | Action | Mirror path | In git (P4 step 4) | Note |
|---|---|---|---|---|
| claude/<lane>/<file> | ADDED / REPLACED / KEPT / DELETED / CARRIED | <repo>:<path> | yes / no | reason if CARRIED |

Carried (not in git, still in PK): <n>; each with its reason and the close that clears it.
Requests to other lanes (also in STREAMS.md §3): <none / list>
```

---

## Transition (one-off, from 2026-11-21)

| # | Item | Owner | Clears at |
|---|---|---|---|
| T1 | 15 retail prompts PK-only (`claude/retail/pk_prune_carryover_2026-11-21.md`): commit to the P2.1 retail mirror, then delete from PK | retail | MR-S13 close |
| T2 | 12 OFL prompts PK-only: commit to `docs/research/tape/`, then delete from PK; move OFL files to `claude/ofl/` (v5.1 Rule 16, STREAMS R6) | OFL | OFL9 close |
| T3 | 3 engine sweep reports PK-only (`claude/adr032_sweep_engine_90_report.md`, `adr032_sweep_engine_95_diff.md`, `adr032_sweep_retail_90_report.md`): commit to `docs/research/s104/`, then delete from PK | engine | next engine close |
| T4 | Remaining engine `claude/` root working files (S102–S105 era: `anon_*`, `gex_unit_inventory_S102`, `S103_close_inputs`, `S104_session_prompt`, `rulings_s104`, `muhurat_*`, `paper_trades_*`, `ref_2026-10-01_*`, `target_read_*`, `P4_charm_*` and others): run P4 against `meridian-engine`, keep only Tier C | engine | next engine close |
| T5 | FOI and PIN folders: first P4 run under this protocol | FOI, PIN | FOI3 close; PIN2 close (after the seal) |
| T6 | Headers (P2.2): new files from the ruling date on. Existing files are not retrofitted; the folder decides ownership. | all | standing |
| T7 | Commit this file to `docs/operational/MERDIAN_PK_Protocol_v1.md`; `STREAMS.md` §1 gains the P2.1 columns (PK folder, git mirror, counting branch); v5.1 Rule 15 gets a pointer line to this protocol; both lane checklists in v5.1 Rule 3 point to P4 and P6 | engine | next engine close |

## Rulings (2026-11-21, operator: "accepted as recommended")

| # | Question | Ruled |
|---|---|---|
| D1 | Retail mirror directory in `retail-platform` | `docs/research/retail/`. This mirrors `claude/retail/` exactly, and the retail lane's `docs/prompts/` suggestion becomes a subfolder only if PK has one. |
| D2 | Budget lines | 80 % target / 85 % prune / 90 % hard stop (P7) |
| D3 | Size limits | 40 KB raw dump, 60 KB any non-canon file (P1) |
| D4 | Executed prompts leave PK at the same close (P3.6) | Yes |
| D5 | Adopt as v1 and point v5.1 Rule 15 to it | Yes. It takes effect for each lane at that lane's next close; no lane is retrofitted mid-session (v5.1 Rule 13(e)). |

### v1.1 amendment (P9–P13): ruled 2026-11-21 ~18:05 IST

| # | Question | Ruled |
|---|---|---|
| D6 | Adopt P9–P12 (new lanes, the PK block in every session prompt, chats that belong to no lane, dormant and retired lanes) | Yes |
| D7 | MALPHA: a lane, or part of retail? | **Neither.** It is an external system with its own box, repo and project. P13 added: only the facts where it meets Meridian (the Kite token for breadth and WCB) live here, in the engine registers. |
| D8 | Engine-root files `claude/board_accuracy_*` and `claude/marketview_user_manual_v04_DRAFT.md` | **No move.** The Board is engine-owned and the accuracy list covers the whole Board (the pin is its first item), so all three stay engine Tier C files under `claude/`. PIN reads them. Each goes through the engine's P4 check at its next close and stays while the work is live. |
| D9 | Dormant threshold | 30 days without a session |

*MERIDIAN Project Knowledge Protocol v1.1 — v1 in force 2026-11-21; v1.1 (P9–P13) in force 2026-11-21 — S106.*

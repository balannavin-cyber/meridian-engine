# MERIDIAN Documentation Protocol v5.1

| Field | Value |
|---|---|
| Status | **IN FORCE.** Ruled by the operator 2026-11-21 ~09:52 IST ("as recommended"), engine session S106. Supersedes v5 (adopted S95-E, file `claude/MERDIAN_Documentation_Protocol_v5_DRAFT.md`, retired). v4 remains the base text for every rule not amended below. |
| Git home | `docs/operational/MERDIAN_Documentation_Protocol_v5.1.md` |
| Why | MERIDIAN runs five lanes (engine, order flow, retail, futures OI, Board pin) with separate session series. Between the S104 close (2026-11-04) and 2026-11-21 no lane fact reached the engine registers; two lanes held uncommitted results; facts about shared objects were recorded in places that disagreed (examples in `docs/registers/intake/I001.md` A5, D3, D6). v5's rule — each fact has one home, others point — held inside the engine lane and was never applied across lanes. |
| Companion | `docs/registers/STREAMS.md` (the hub register this protocol creates) |

## The rule, in one line (unchanged from v5, now across lanes)

**Each fact has one home. Facts about engine-owned objects live in the engine registers; lane work lives in the lane. Lanes point to the engine; they do not restate it.**

---

## Exhaustive changelog (v5 → v5.1)

### Added

| Item | Detail |
|---|---|
| **Rule 12 — Lanes and the hub** | A lane is a session series with its own folder. The engine lane is the hub: it owns the engine registers and every engine-owned object (schema, roles, grants, hosts, crons, tokens, Board/Marketview, `merdian_compute`). `STREAMS.md` lists lanes, homes, prefixes, touched objects and cross-lane dependencies. A lane never edits an engine register or applies a grant/DDL itself. |
| **Rule 13 — Engine intake** | (a) Every lane's close inputs carry an **"Engine intake"** section (template below), listing only changes to engine-owned facts. (b) At every engine doc-close the engine reads every lane's intake section written since the previous engine close, applies them in `doc-close` skill order, and writes `taken: <ID / file §>` against each row. (c) The intake record lives at `docs/registers/intake/I<nnn>.md`. (d) An engine-owned change that blocks another lane (a grant, a fix, a Board change) is also entered in `STREAMS.md` §3 the same day, not at the next close. (e) A lane that is mid-session is not retrofitted: its items enter at its own close; the engine never edits a lane's working tree or project folder. |
| **Rule 14 — ID prefixes by origin** | TD IDs carry their origin session: engine `TD-S<N>-NEW-k`; lanes `TD-OFL<n>-NEW-k`, `TD-FOI<n>-NEW-k`, `TD-PIN<n>-NEW-k`. The form cannot collide, so a lane writes its TD IDs in its close inputs and the operator's approval of those close inputs is the allocation (meets ADR-027 D7 without blocking filing). **One `tech_debt.md` per repo:** engine, OFL, FOI and PIN TDs go to `meridian-engine` `docs/registers/tech_debt.md`; retail keeps `TD-MR-n` in `tech_debt_retail.md` (retail-platform). ADR, ENH, AR §D and CASE IDs stay engine-minted at intake (lanes write `PROPOSED-ID`). |
| **Rule 15 — Git is the record; project knowledge is a cache** | (a) Every lane commits its research outputs and its close inputs, session prompt and rulings to its git home at its close (or names the gate that holds them, e.g. OFL's x5-before-commit for code). Nothing lives only in project knowledge after the lane's next close. (b) Project knowledge keeps, per lane: the current session prompt, the latest close inputs, live pre-registrations and designs, and the rulings files of the current and previous session. Older items are deleted from project knowledge once their git copy is confirmed (`git ls-files`), by the S104 prune precedent. (c) Budget: re-measure `knowledge_size` at every engine close; at 90 % of the cap, prune before adding. (d) Copies of project docs made into git carry the reference product's name replaced by "the parity target" (operator preference; S104 precedent for `target_read_Mar-Oct2026.md`). |
| **Rule 16 — Lane folder** | Each lane keeps everything under its own project folder (`claude/<lane>/`) with fixed names: `MR_<SERIES><n>_session_prompt.md`, `MR_<SERIES><n>_close_inputs.md`, `rulings_<series><n>.md`, `cc_prompt_*.md`, pre-registrations, records. The engine keeps `claude/` root and `claude/intake/`. A folder move happens at that lane's own close. |
| **Rule 17 — `merdian_reference.json` update form** | `change_log` has been frozen at S91 since S92; each session's state goes in a top-level `_s<N>_addendum` key. That is now the written rule: one `_s<N>_addendum` per engine session; `change_log` is not appended. |

### Modified

| Rule | v5 form | v5.1 form | Why |
|---|---|---|---|
| **Rule 3** (session end) | Engine checklist only; registers as pointer entries; PK re-upload of "changed pointer files and working docs" | **Engine close** adds, before the register steps: `☐ Intake: read every lane's "Engine intake" since the last engine close; apply; write taken-IDs; file I<nnn>.md`, and after them `☐ STREAMS.md: lane rows, dependencies, rollout`. **Lane close** checklist (new): `☐ close inputs with "Engine intake" section ☐ TDs under the lane prefix ☐ commit lane records to the git home (or name the gate) ☐ PK: replace prompt + close inputs; delete superseded per Rule 15(b)`. **Upload list** = every file modified this session under `docs/`, plus `CLAUDE.md` (the modified set, not an enumerated list). | Lanes had no close checklist that reached the engine. The enumerated upload list omitted ADRs, System Map, Topology, AR and Decision Index (TD-S79 entry). |
| **Rule 7** (`CURRENT.md`) | Engine session resume | Engine session resume **plus** one line per lane: series, open session, pointer to its latest close inputs. No lane content. | One place shows where every lane stands without copying it. |
| Session numbering | implicit | Engine session IDs are monotonic and name one git close each. Work done in chat under a session name after that session's git close is closed under the next engine session ID (precedent: 2026-11-05→11-21 work closed as S106). | The chat kept "S105" for ten days after `eba1193`. |

### Removed

Nothing.

### Preserved unchanged

v4 Rules 0, 1, 2, 4, 5, 6, 8, 9, 10, 11 and v5's pointer-entries principle. Full-file discipline (count==1 anchors, line/byte deltas, `json.loads`, EOL preserved), ADR-before-code, Decision Index mechanics, the operator declares session close.

### Rulings recorded with this version (2026-11-21)

1. Rule 14 lane-prefixed TDs: accepted.
2. Rule 15(b) rulings retention (current + previous session in PK once in git): accepted.
3. Rule 16 OFL folder move: at OFL's own close.
4. The greeks / forward question (FOI3 item 1 and PIN gamma-rate sensitivity) is one engine-lane study fed by both lanes.

---

## Template — "Engine intake" section of a lane's close inputs

```
## N. Engine intake (for the next engine doc-close; v5.1 Rule 13)

Only changes to engine-owned facts. Lane-local results stay above.
Labels: EVIDENCED / VERIFY (give the read) / DECIDE (operator choice needed).

| # | Fact (one line, with figure and unit) | Engine object | Target register | Proposed ID | Label | Evidence (file §, command output) |
|---|---|---|---|---|---|---|
| 1 | | | System Map / Topology / Data Inventory / TD / AR / ENH / ADR / CLAUDE.md / tracker | TD-<SERIES><n>-NEW-k or PROPOSED-ID | | |

Blocks another lane? (also enter in STREAMS.md §3 today): <yes: which / no>
Git: lane records committed at <sha> / held by <gate>
```

*MERIDIAN Documentation Protocol v5.1 — 2026-11-21 — S106. Exhaustive changelog per v4 Rule 1.*

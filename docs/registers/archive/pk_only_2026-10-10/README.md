# Project-knowledge-only docs, archived 2026-10-10 (S94)

These seven files existed only in Claude.ai project knowledge, under `claude/`, and had never
been committed. They are archived here byte-for-byte, so that they can be removed from project
knowledge (capacity, S94 step 0) without being lost. Git is now their only copy.

`MANIFEST.sha256` holds each file's sha256, computed from the project-knowledge content
before the transfer. Run `sha256sum -c MANIFEST.sha256` in this directory. Every line must read OK,
or the project-knowledge copies must not be deleted.

| File | Bytes | What it is |
|---|---:|---|
| `S93_session_prompt.md` | 5,000 | S93 starter prompt; superseded by the S94 prompt |
| `S91_AM2_starter.md` | 12,728 | AM-2 / S91 starter; superseded |
| `S90_agentic_build_starter.md` | 5,568 | S90 starter; superseded |
| `CC_prompt_1006_SENSEX_trade_replay.md` | 6,309 | One-off read-only CC prompt; its output went to the 08-Oct paper log |
| `tech_debt_S90_additions.md` | 10,238 | Extract of TD-S90-NEW-1…11; `tech_debt.md` is canonical |
| `s89_1001_ladder_replay_findings.md` | 4,909 | Contained in, and corrected by, `ref_2026-10-01_SENSEX_0DTE.md` |
| `ADR-031-DRAFT-spine-contracts-status-provenance-ledger.md` | 14,905 | ADR-031 as drafted for ruling A-8; superseded by the accepted ADR-031 |

Archive only. Nothing here is current guidance.

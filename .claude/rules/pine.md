---
paths:
  - "**/*.pine"
  - "generate_pine_overlay*.py"
---

# Pine v6 overlays

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is
unchanged; only its location moved.

5. **PDH/PDL canonical fetch idiom: `[high[1], low[1]] + lookahead=barmerge.lookahead_on`.** Combining `[1]` index with `lookahead_on` works correctly for both same-TF and cross-TF security calls. This is the canonical pattern; document for future Pine work.

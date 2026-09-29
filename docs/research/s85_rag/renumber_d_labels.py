"""Renumber ADR-027's own decision labels so D1-D7 are unique across the pair.

Mapping (ADR-027's OWN decisions only):  D3->D4  D4->D5  D5->D6  D6->D7
ADR-026 keeps D1, D2, D3.

Two hazards, both measured before writing rather than assumed:

 1. ADR-027 cites ADR-026's D3 (staleness floor) at two places and ADR-025 D1 /
    ADR-026 D1 elsewhere. Those are FOREIGN references and must NOT move. They
    are masked to @@KEEPn@@ before the mapping and restored after.
 2. ADR-026 cites ADR-027's D5 (operator diff gate) twice, in the section 8.2
    Lane B table. Those MUST move to D6. ADR-026 declares no D4/D5/D6/D7 of its
    own, so every D5 in it is a reference to ADR-027 -- asserted below.

The mapping runs through @@Dn@@ placeholders so D4->D5 cannot re-hit a label
D3->D4 has already produced. Per-label counts are printed before and after and
the totals are asserted.
"""
import re
import sys
from pathlib import Path

D = Path("/home/ssm-user/meridian-cc/docs/research/s85_rag")
A26 = Path("/home/ssm-user/meridian-cc/docs/decisions/ADR-026-docs-retrieval-index.md")
A27 = D / "ADR-027-DRAFT-doc-close-drafting-and-verification.md"

MAP = {"D3": "D4", "D4": "D5", "D5": "D6", "D6": "D7"}
FOREIGN = re.compile(r"(ADR-0\d\d)\s+D([1-9])\b")
LABEL = re.compile(r"\bD([1-9])\b")


def counts(text):
    out = {}
    for m in LABEL.finditer(text):
        k = "D" + m.group(1)
        out[k] = out.get(k, 0) + 1
    return out


def show(tag, c):
    print(f"  {tag:8} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))


def main():
    t26 = A26.read_text(encoding="utf-8")
    t27 = A27.read_text(encoding="utf-8")
    c26, c27 = counts(t26), counts(t27)

    print("BEFORE")
    show("ADR-026", c26)
    show("ADR-027", c27)

    # ---- guard: ADR-026 must declare no D4..D7 of its own -------------
    for bad in ("D4", "D6", "D7"):
        if bad in c26:
            sys.exit(f"STOP: ADR-026 unexpectedly contains {bad}; "
                     "the 'every D5 in ADR-026 is a reference' premise fails")
    if c26.get("D5", 0) != 2:
        sys.exit(f"STOP: ADR-026 has {c26.get('D5', 0)} D5 occurrences, "
                 "expected exactly 2 (both references to ADR-027's D5)")

    # ================= ADR-027: mask foreign, map, restore ============
    n_foreign = len(FOREIGN.findall(t27))
    masked = FOREIGN.sub(lambda m: f"{m.group(1)} @@KEEP{m.group(2)}@@", t27)
    if len(FOREIGN.findall(masked)) != 0:
        sys.exit("STOP: foreign masking incomplete in ADR-027")
    print(f"\nADR-027 foreign references masked: {n_foreign}")

    mapped = LABEL.sub(
        lambda m: "@@" + MAP["D" + m.group(1)] + "@@"
        if ("D" + m.group(1)) in MAP else m.group(0), masked)
    mapped = re.sub(r"@@(D[1-9])@@", r"\1", mapped)
    restored = re.sub(r"@@KEEP([1-9])@@", r"D\1", mapped)
    if "@@" in restored:
        sys.exit("STOP: placeholder residue left in ADR-027")

    # ================= ADR-026: the two ADR-027 D5 refs ==============
    t26_new, n26 = re.subn(r"\bD5\b", "D6", t26)
    if n26 != 2:
        sys.exit(f"STOP: ADR-026 D5->D6 replaced {n26}, expected 2")

    c26n, c27n = counts(t26_new), counts(restored)
    print("\nAFTER")
    show("ADR-026", c26n)
    show("ADR-027", c27n)

    # ---- assertions on the shape of the result ----------------------
    for k in ("D1", "D2", "D3"):
        if c26n.get(k, 0) != c26.get(k, 0):
            sys.exit(f"STOP: ADR-026 {k} count moved "
                     f"{c26.get(k, 0)} -> {c26n.get(k, 0)}")
    total_before = sum(c27.values())
    total_after = sum(c27n.values())
    if total_before != total_after:
        sys.exit(f"STOP: ADR-027 total D tokens {total_before} -> {total_after}")
    # ADR-027 must retain exactly the foreign D3/D1 refs and nothing else low
    if c27n.get("D3", 0) != 2:
        sys.exit(f"STOP: ADR-027 should keep exactly 2 D3 (ADR-026 refs), "
                 f"has {c27n.get('D3', 0)}")

    A26.write_text(t26_new, encoding="utf-8")
    A27.write_text(restored, encoding="utf-8")
    print("\nwritten. D1-D3 = ADR-026, D4-D7 = ADR-027, no label in both.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

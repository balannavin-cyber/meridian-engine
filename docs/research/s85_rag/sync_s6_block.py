"""Copy ADR-026 section 6's canonical block into ADR-027, byte-for-byte.

ADR-026 is the canonical text. This replaces ADR-027's block with ADR-026's
exact bytes rather than retyping them, so the 'inherited verbatim' claim is made
true by construction. Fail-loud: aborts unless exactly one START and one END
match are found in each file, and asserts byte-identity after the write.
"""
import hashlib
import sys

A = "/home/ssm-user/meridian-cc/docs/decisions/ADR-026-docs-retrieval-index.md"
B = ("/home/ssm-user/meridian-cc/docs/research/s85_rag/"
     "ADR-027-DRAFT-doc-close-drafting-and-verification.md")

START = "**The only mutable surface is rows in pre-existing `rag` tables.**"
END = "depend on it."


def bounds(raw, label):
    n = raw.count(START)
    if n != 1:
        sys.exit(f"ABORT: {label} has {n} START matches, expected 1")
    i = raw.find(START)
    j = raw.find(END, i)
    if j < 0:
        sys.exit(f"ABORT: {label} END not found after START")
    return i, j + len(END)


a_raw = open(A, encoding="utf-8").read()
b_raw = open(B, encoding="utf-8").read()

ai, aj = bounds(a_raw, "ADR-026")
bi, bj = bounds(b_raw, "ADR-027")

canonical = a_raw[ai:aj]
old = b_raw[bi:bj]

if canonical == old:
    print("Already identical -- nothing to do.")
    sys.exit(0)

new_b = b_raw[:bi] + canonical + b_raw[bj:]
expected_len = len(b_raw) - len(old) + len(canonical)
if len(new_b) != expected_len:
    sys.exit(f"ABORT: length assertion failed {len(new_b)} != {expected_len}")

with open(B, "w", encoding="utf-8") as fh:
    fh.write(new_b)

check = open(B, encoding="utf-8").read()
ci, cj = bounds(check, "ADR-027 (post-write)")
got = check[ci:cj]
if got != canonical:
    sys.exit("ABORT: post-write block does NOT match canonical")

print(f"ADR-027 block replaced: {len(old)} -> {len(canonical)} bytes")
print(f"file: {len(b_raw)} -> {len(check)} bytes (asserted {expected_len})")
print(f"canonical md5: {hashlib.md5(canonical.encode()).hexdigest()}")
print("post-write byte-identity: ASSERTED OK")

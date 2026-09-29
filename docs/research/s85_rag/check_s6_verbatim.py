"""Assert ADR-027 section 6's inherited block is BYTE-IDENTICAL to ADR-026 section 6.

The 'inherited verbatim' claim is a parity claim between two texts, so it is
established by comparison, never by a comment saying so. Extracts the block from
START to END inclusive in both files and compares bytes + md5.
"""
import hashlib
import sys

A = "/home/ssm-user/meridian-cc/docs/decisions/ADR-026-docs-retrieval-index.md"
B = ("/home/ssm-user/meridian-cc/docs/research/s85_rag/"
     "ADR-027-DRAFT-doc-close-drafting-and-verification.md")

START = "**The only mutable surface is rows in pre-existing `rag` tables.**"
END = "it declines to\ndepend on it."
END_ALT = "it declines to depend on it."


def block(path):
    raw = open(path, encoding="utf-8").read()
    i = raw.find(START)
    if i < 0:
        return None, "START not found"
    for end in (END, END_ALT):
        j = raw.find(end, i)
        if j >= 0:
            return raw[i:j + len(end)], None
    return None, "END not found"


a, ea = block(A)
b, eb = block(B)
if ea or eb:
    print(f"EXTRACTION FAILED  026={ea}  027={eb}")
    sys.exit(2)

ha = hashlib.md5(a.encode()).hexdigest()
hb = hashlib.md5(b.encode()).hexdigest()
print(f"ADR-026 block: {len(a):>5} bytes  md5={ha}")
print(f"ADR-027 block: {len(b):>5} bytes  md5={hb}")

if a == b:
    print("\nRESULT: IDENTICAL -- 'inherited verbatim' claim HOLDS")
    sys.exit(0)

print("\nRESULT: DIVERGENT -- 'inherited verbatim' claim IS FALSE")
la, lb = a.splitlines(), b.splitlines()
for n in range(max(len(la), len(lb))):
    x = la[n] if n < len(la) else "<absent>"
    y = lb[n] if n < len(lb) else "<absent>"
    if x != y:
        print(f"\nline {n+1} differs:\n  026: {x}\n  027: {y}")
sys.exit(1)

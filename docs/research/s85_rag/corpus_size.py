"""S85 measure-only: text-vs-binary split and chunk/token estimate for the corpus.

Token estimate uses a chars/token divisor, stated explicitly, because tiktoken
is not installed on this host. It is an ESTIMATE and labelled as such -- not a
measurement.
"""
import subprocess

REPO = "/home/ssm-user/meridian-cc"
CHARS_PER_TOKEN = 4.0          # stated assumption, not measured
CHUNK_TOKENS = 512
OVERLAP = 0.15


def git(args):
    return subprocess.run(["git", "-C", REPO] + args,
                          capture_output=True, check=True).stdout


names = [n for n in git(["ls-tree", "-r", "--name-only", "HEAD"]).decode().splitlines()
         if n.startswith("docs/") or n == "CLAUDE.md"]

text_b = bin_b = 0
text_n = bin_n = 0
big = []
line_heavy = []
for p in names:
    raw = git(["show", f"HEAD:{p}"])
    if b"\x00" in raw[:8192]:
        bin_b += len(raw)
        bin_n += 1
        continue
    text_b += len(raw)
    text_n += 1
    nl = len(raw.decode("utf-8", errors="replace").splitlines()) or 1
    big.append((len(raw), p))
    line_heavy.append((len(raw) / nl, len(raw), nl, p))

est_tokens = text_b / CHARS_PER_TOKEN
stride = CHUNK_TOKENS * (1 - OVERLAP)
est_chunks = est_tokens / stride

print(f"text files : {text_n:4d}   bytes {text_b:>9,}")
print(f"binary     : {bin_n:4d}   bytes {bin_b:>9,}  (.docx -- excluded from RAG)")
print(f"TOTAL      : {text_n+bin_n:4d}   bytes {text_b+bin_b:>9,}")
print()
print(f"ESTIMATE (assumption: {CHARS_PER_TOKEN} chars/token, NOT measured -- tiktoken absent)")
print(f"  est tokens            ~ {est_tokens:>12,.0f}")
print(f"  est chunks @ {CHUNK_TOKENS}tok/{int(OVERLAP*100)}% overlap ~ {est_chunks:>8,.0f}")
print(f"  384-dim float32 index ~ {est_chunks*384*4/1e6:>8.1f} MB")
print(f"  768-dim float32 index ~ {est_chunks*768*4/1e6:>8.1f} MB")
print()
print("TOP 12 text files by bytes (chunk-count drivers):")
for b, p in sorted(big, reverse=True)[:12]:
    print(f"  {b:>9,}  {p}")
print()
print("TOP 10 by BYTES-PER-LINE (paragraph-per-line: breaks line-based chunkers):")
for bpl, b, nl, p in sorted(line_heavy, reverse=True)[:10]:
    print(f"  {bpl:>8,.0f} B/line  ({b:>9,} B / {nl:>5,} lines)  {p}")

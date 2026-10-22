"""S97-I: telegram_utils.py fix. Run from the repo root (C:\\GammaEnginePython). Edits ONE file, two anchors.

1. Drop 'parse_mode': 'plain' -- Telegram answers 400 "unsupported parse_mode" (probe A, 2026-10-22 04:23 IST);
   the same request without it answers 200 (probe B).
2. On a non-200, print the HTTP status and Telegram's description before returning False (it was silent).
   Only resp is read, never the URL, so the bot token cannot reach a log.

Each anchor must occur exactly once; line endings are preserved; nothing is written unless both match.
"""
import hashlib

P = "telegram_utils.py"

raw = open(P, "rb").read()
crlf = b"\r\n" in raw
s = raw.decode("utf-8").replace("\r\n", "\n")

A_OLD = "        'text': text,\n        'parse_mode': 'plain'\n    }\n"
A_NEW = "        'text': text,\n    }\n"

B_OLD = ("        resp = requests.post(url, json=payload, timeout=5)\n"
         "        return resp.status_code == 200\n")
B_NEW = ("        resp = requests.post(url, json=payload, timeout=5)\n"
         "        if resp.status_code != 200:\n"
         "            try:\n"
         "                desc = resp.json().get('description', '')\n"
         "            except ValueError:\n"
         "                desc = resp.text[:200]\n"
         "            print(f\"[WARN] Telegram send rejected: HTTP {resp.status_code} {desc}\")\n"
         "            return False\n"
         "        return True\n")

for name, old in (("A parse_mode", A_OLD), ("B status", B_OLD)):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"STOPPED - anchor {name} found {n} times (need 1); file NOT changed")

before_lines = s.count("\n")
s = s.replace(A_OLD, A_NEW).replace(B_OLD, B_NEW)
if "parse_mode" in s:
    raise SystemExit("STOPPED - parse_mode still present after edit; file NOT changed")

out = (s.replace("\n", "\r\n") if crlf else s).encode("utf-8")
open(P, "wb").write(out)

print(f"eol={'CRLF' if crlf else 'LF'} lines {before_lines} -> {s.count(chr(10))} "
      f"(expected +6) sha256_12={hashlib.sha256(out).hexdigest()[:12]}")
print("APPLIED S97-I telegram_utils.py")

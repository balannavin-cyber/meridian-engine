---
paths:
  - "**/*.sh"
  - "bin/**"
---

# Shell and remote-host operations

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is
unchanged; only its location moved.

- **`find_dotenv()` fails in Python heredoc context — use file approach.** Session 22 hit this twice when running diagnostic Python via `python3 << 'EOF'` heredoc. `find_dotenv()` calls `frame.f_back` which doesn't exist in heredoc execution context, raising AssertionError. Fix: `cat > /tmp/script.py << EOF` then `python3 /tmp/script.py`, with explicit `load_dotenv("/path/.env")` in the script. Codified as: **for any AWS/SSH diagnostic Python that needs env vars, write a file via `cat >` then invoke. Avoid heredoc execution. Always pass explicit path to `load_dotenv()`.**
- **Multi-line nano paste into SSM beats base64 single-line paste for code transfer to MERDIAN AWS.** Single-line clipboard paste through SSM Session Manager truncates at ~4KB (per-line buffer limit observed empirically S35); base64-encoded 19KB Python file paste fragmented. Splitting into 4×5KB chunks still failed PowerShell-side because `C:\Temp\` did not exist; relocating to `C:\GammaEnginePython\` worked but each chunk paste-to-shell was still mangled by here-doc quote handling. Solution: `nano /home/ssm-user/<file>.py` on MERDIAN, Ctrl+A Ctrl+C on the source file open in Notepad locally, paste into nano (line-breaks chunk the input naturally so terminal buffer never hits its single-line limit), Ctrl+O Enter Ctrl+X. md5sum verification cross-environment confirmed byte-identical. Codified as: **for ad-hoc code transfer to a single SSM-only host, multi-line nano paste is the canonical method; here-docs and base64 streaming are anti-patterns. The terminal buffer is per-line, not per-paste, so line-broken content streams cleanly.**

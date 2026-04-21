# OI-20 - Disposition Note - 2026-04-22

**Status:** CLOSED - FIXED FORWARD. History not rewritten.

## Finding

Commits 3a22735 through d15c494 (Session 3+4, 9 commits) carry a
literal UTF-8 BOM (EF BB BF) embedded in the commit subject
immediately before "MERDIAN". Confirmed via `git log --format="%s"
| Format-Hex`. Not a display artifact.

## Root cause

PowerShell 5.1 default console encoding is cp850/cp1252
(WindowsCodePage=1252). When `git commit -m "..."` received a
message containing non-ASCII (em-dash), PS 5.1 emitted a
UTF-8-WITH-BOM byte sequence through the pipeline and git stored
the BOM prefix verbatim. `i18n.commitEncoding` was unset.

## Disposition

History NOT rewritten. Force-push cost across Local + MERDIAN AWS
+ MeridianAlpha consumer repos exceeds benefit for cosmetic BOMs.
Commit hashes remain valid as audit trail for Session 3+4 work.

## Fix forward applied

1. PowerShell `$PROFILE` created at
   `C:\Users\balan\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`.
   Forces `$OutputEncoding`, `Console.OutputEncoding`, and
   `Console.InputEncoding` to `UTF8Encoding::new($false)` -
   UTF-8 without BOM.
2. Git global config: `i18n.commitEncoding=utf-8`,
   `i18n.logOutputEncoding=utf-8`.
3. Verification commit (subsequently reset) confirmed:
   - No BOM (subject starts cleanly at byte `4F`, not `EF BB BF`).
   - Em-dash character substituted to `?` (0x3F) in stored bytes.

## Residual known limitation

PS 5.1 cannot pass non-ASCII characters through `-m "..."` args
cleanly even with the profile fix applied. `Console.OutputEncoding`
controls display; it does not control external-process argv
serialization on PS 5.1. Em-dashes, currency symbols, and other
non-ASCII get best-fit-substituted to `?`.

## Discipline going forward

- Commit subjects: ASCII only. Use `-`, `->`, `...`, not `--`, `->`, `...`.
- If non-ASCII required: `git commit -F message.txt` where
  `message.txt` is saved UTF-8.
- Full fix (non-blocking): upgrade to PowerShell 7 at a future
  date. Not required for production.

## Verification path

Future auditor can confirm with:

```powershell
git log --format="%H %s" -20 | Format-Hex | Select-String "EF BB BF"
```

Any match = a BOM-contaminated commit. After 2026-04-22 no new
matches should appear.

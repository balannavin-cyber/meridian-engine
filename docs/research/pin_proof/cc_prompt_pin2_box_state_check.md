# CC prompt: MR-PIN2 step 1, box state check (BLOCKED.txt section, SHA256SUMS)

Box: MERIDIAN engine EC2, SSM shell, user ssm-user. Plain shell, no tmux. Run after 15:40 IST on a trading day.
No database query. File reads only, plus one conditional append to `BLOCKED.txt`.

Start:

```
cd ~/meridian-cc && git pull --ff-only && claude
```

Paste:

```
Read-only state check of docs/research/pin_proof/gamma_inputs/ (MR-PIN2 step 1). Do not run any database query, do not use bin/roq.sh, do not call any vendor API, do not commit, do not edit any tracked file, do not rebuild SHA256SUMS. Run every command under ( ulimit -v 700000; ... ). If you run python, use python3 -B; never create __pycache__ or .pyc. Never cat, grep or source .env.

Folder: ~/meridian-cc/docs/research/pin_proof/gamma_inputs/

Step 1. From the repo root run: git ls-files docs/research/pin_proof/gamma_inputs/BLOCKED.txt and git status --porcelain --ignored -- docs/research/pin_proof/ . Report whether BLOCKED.txt is tracked by git (yes/no).
Step 2. In the folder run: grep -n "PART H AND ALIGNMENT RE-CHECK 2026-11-20" BLOCKED.txt . Report the line number(s), or "absent". If present, report the section's line count (from the heading to the next line starting with "PART " or end of file) and print its first 3 lines only. Do not change it.
Step 3. In the folder run: sha256sum -c SHA256SUMS . Report counts of OK, FAILED and missing, and name every FAILED or missing file. Then list every file under the folder, recursive, excluding SHA256SUMS itself, that is not named in SHA256SUMS: count and names.
Step 4. In the folder run: find . \( -name '*.pyc' -o -name __pycache__ \) . Report the count.
Step 5. Print sha256sum and byte size of: _partH_raw.txt, _partH_analysis.txt, _alignment_v2_recheck.txt, partB_code.md, partB_results.md. If one does not exist, say so by name.

Conditions:
A. If step 3 shows any file other than BLOCKED.txt as FAILED or missing, edit nothing. Say STOP-MANIFEST and name the files.
B. If step 1 shows BLOCKED.txt is tracked by git, edit nothing. Say STOP-TRACKED.
C. Only if step 2 says absent and neither A nor B applied: append to BLOCKED.txt exactly the lines between the marker lines BEGIN-BLOCK and END-BLOCK below (not the marker lines themselves), preceded by one blank line. Then re-run the step 2 grep and print the line number, and print sha256sum BLOCKED.txt. Make no other change to any file.
D. If step 2 found the heading, append nothing, even if its wording differs from the block below.

BEGIN-BLOCK
PART H AND ALIGNMENT RE-CHECK 2026-11-20
1. Coverage run: the 24 Part B sample symbol-days (NIFTY 12, SENSEX 12) x 3 IST minutes (10:00, 12:30, 15:00), one EXPLAIN-gated query per symbol-day, 5 s sleep. 24 OK, 0 FAIL, 0 STOP, 2.530-3.049 s per query, 1,219 raw lines. Precondition clause 4 (last log line = ALL 24 DONE) was waived by the operator: the marker went to task stdout, not _partH_run.log (loop script bug).
2. Coverage result: 72 of 72 sampled minutes have a fyers_futures_bars_1m bar at the exact true-UTC instant (IST minute minus 5 h 30 m, offset 0). Near-month contract every time; fut_dte 22 to 30. F missing 0; fut_dte < 3 (unstable) 0; ties 0; next contract used 0. Zero-volume futures bars: 10 of 36 SENSEX minutes (7 at 12:30, 2 at 15:00, 1 at 10:00); NIFTY 0 of 36.
3. Alignment re-check (NIFTY 2026-03-04, SENSEX 2026-03-02): ALIGNMENT INCONCLUSIVE, not void. SENSEX 2026-03-02 10:00: SENSEX26MARFUT close 80880.50 at both offset 0 and +60 s (flat print), so offset 0 is not singled out there; F is identical under either. The other five minutes are exact and unique at offset 0 to the nearest-expiry contract. NIFTY 2026-03-04: hist series 1, 2, 3 = MAR, APR, MAY one-to-one, 9 of 9; non-matches 101-267 points away.
4. Operator decision: the offset-0 rule stands. SENSEX 2026-03-02 10:00 is flagged as not independently confirmed. Any SENSEX sensitivity result carries the caveat that SENSEX alignment rests on the 2025-05-02 test plus two unambiguous minutes in this re-check.
5. Status: no Fyers price has been used in any sensitivity. The SELECT grant and policy ro_select_merdian on fyers_futures_bars_1m (operator action, 2026-11-20) are in place.
6. New files since the 49/49 seal: q09-q14, q13b, qF/qG/qH templates, analyze_partF.py, analyze_partG.py, analyze_partH.py, analyze_alignment.py, analyze_alignment_v2.py, the _q*, _part* and _alignment* outputs (including _partH_raw.txt, _partH_run.log, _partH_analysis.txt, _alignment_v2_recheck.txt), the explain plans, and this edit to BLOCKED.txt. SHA256SUMS not yet rebuilt.
END-BLOCK

At the end print to the screen only: step 1 result; step 2 result; step 3 counts and file names; step 4 count; step 5 hashes and sizes; which of A, B, C, D applied, and if C, the new heading line number and the new sha256 of BLOCKED.txt. Keep the screen print under 35 lines.
```

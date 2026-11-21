# Engine lane E1 + E3 + E10: CC plan review and rulings (Fri 2026-11-20 ~16:45 IST, MR-S13 retail lane)

Plan reported by the `e1` CC session in `~/meridian-cc` (HEAD = origin/main = `ba505cf`), against `claude/cc_prompt_engine_one_login_e1_e3_e10.md`. All plan reads are read-only; nothing was built. Labels: MEASURED = CC read on the engine box; OPERATOR-RUN = pasted by the operator.

## What the plan measured
- `~/.ssh`: `retail_drop_ed25519` (600) and `.pub` (Nov 16 04:25), `known_hosts` with an unhashed `16.4.29.153 ssh-ed25519` entry (the retail host) and github; `~/.ssh/config` NOT read (declined), so its contents are UNKNOWN. MEASURED.
- No second scheduler: no `dhan` match in `systemctl list-timers --all` or `/etc/systemd/system`; only `merdian-wsfeed-{start,stop,retry}.timer`; one Dhan login line in the crontab. MEASURED.
- `merdian_live_dashboard.py` is a Local/Windows tool; no process, cron line or unit on the engine box. Third call site: `run_token_refresh.bat:3` (Local, harmless now: Local has no PIN/seed after the 2026-11-20 `.env` edit, OPERATOR-RUN). MEASURED.
- Tests are standalone scripts aggregated by `tests/run_offline.sh`: **40 suite steps, 34 `tests/test_*.py` files** (baseline). 6 hand-rolled `tests/*_mutants.py` exist, so mutant rows are in scope. MEASURED.
- Anchors in `refresh_dhan_token.py` @ `ba505cf` (239 lines): guard in `main()` after `load_dotenv` (:134), before `_idempotency_skip` (:137); stamp write inside the script's own `request_dhan_token` right before `requests.post` (:60), covering both call sites; success insert at :197 after `write_token_status(True, ...)` :196; failure branches :165-175 and :176-186. MEASURED.
- Production `~/meridian-engine` is at `79efb0b`, 2 behind origin/main (`8fde9df`, `ba505cf`, both futoi docs). Deploy = the operator's `git pull --ff-only`. MEASURED.
- `.claude/settings.json:21` denies `Bash(*refresh_dhan_token*)`. Tests and the wrapper must not be invoked with that substring in the command line. MEASURED.

## Correction to the prompt's Basis item 3
`dhan_token_refresh_lib.request_with_retry` does not exist (zero hits). The script carries its own duplicate `request_dhan_token` (:59); the lib's is unused by it. "Two attempts at most" stands, by a different route.

## Rulings (answers to the plan's open points)
- **D5 (config).** The three values stay env-only with no defaults for the host: `MERIDIAN_RETAIL_DROP_KEY`, `MERIDIAN_RETAIL_DROP_KNOWN_HOSTS`, `MERIDIAN_RETAIL_DROP_HOST`. They reach the process through the engine `.env` (the script's `load_dotenv` at :134 loads them before the helper runs). They are non-secret paths and an address. **The operator adds the three lines to `~/meridian-engine/.env` at deploy; CC never edits `.env`.** Intended values: `/home/ssm-user/.ssh/retail_drop_ed25519`, `/home/ssm-user/.ssh/known_hosts`, `16.4.29.153`.
- **D6 (ssh).** The ssh call adds `-F /dev/null`, so the unread `~/.ssh/config` cannot change the user, host, proxy or key for this call. Keep `-i`, `IdentitiesOnly=yes`, `BatchMode=yes`, `ConnectTimeout=10`, `StrictHostKeyChecking=yes`, `UserKnownHostsFile`.
- **D7 (what counts as failed).** Plan open points 2 and 3: **any** exception on the login path other than the rate-limit case writes `dhan_login_status` = `failed <IST>` and then propagates unchanged. That includes `requests.Timeout` / `ConnectionError` (non-`RuntimeError`) and a `require_env` failure for `DHAN_CLIENT_ID` / `DHAN_PIN` / `DHAN_TOTP_SEED`: in each case no new key was handed over today. The guard refusal (exit 3) and `_idempotency_skip` (return 0, open point 4) write nothing, as CC proposed. Note for the cell: with the 300 s stamp written before every request, `_idempotency_skip` (90 s) is shadowed by the guard in normal use; keep it, assert it still works when the stamp is absent.
- **D8 (empty expires).** Open point 5: the writer's list of required keys is not visible to me. If `expiryTime` is empty, send `expires=unknown` (free printable text per the drop spec), never an empty value. T8 asserts every value in the file is non-empty. Only an empty token refuses to send.
- **D9 (tests and the deny rule).** Do not loosen the `refresh_dhan_token` deny rule for the build; it is the fence against an accidental live login. Tests import the module and stub the request; they run as `python3 tests/test_<name>.py`. Suite runs only after 15:40 IST and only as `( ulimit -v 700000; bash tests/run_offline.sh )`.
- **D10 (mutant rows).** At least one `*_mutants.py` row per rule: threshold 300 changed; stamp written after the request instead of before; helper exception escapes; token in argv; drop on rate-limit; `ok` written when the `dhan` drop failed; time offset not `+05:30`; `-F /dev/null` removed.
- **Baseline.** Record 40 steps / 34 test files before; state the new totals in the report.

## Owed (not blocking the build)
- Fingerprint match, public data only, operator on the engine box: `ssh-keygen -lf ~/.ssh/retail_drop_ed25519.pub` must print `SHA256:iocEQKKHcGRzdvB06+0Cqgd+yZw53jEi/8HSKXeXs4M`; `ssh-keygen -F 16.4.29.153 -f ~/.ssh/known_hosts -l` must print `SHA256:uJHw/p/dprgGtag29R1HV7x3PiY2QoI6cSt33PZgaqs` (both from `MR_S11_close_inputs.md`).
- Retail Elastic IP (`16.4.29.153`) and MALPHA's address (`16.192.223.197` on the drop's `from=`) still UNVERIFIED as Elastic.
- The first live proof is the first real `dhan` drop at a 08:20 IST run after deploy plus E9; a manual `dhan_login_status` test path already worked on 2026-11-16.

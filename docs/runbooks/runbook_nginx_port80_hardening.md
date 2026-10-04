# Runbook — nginx `:80` hardening on the Marketview host

| Field | Value |
|---|---|
| Created | 2026-10-04 (Session 89) |
| Applies to | `i-0878c118835386ec2` (eu-north-1) · `/etc/nginx/sites-available/marketview` |
| Tracked config | `deploy/nginx/marketview.conf` (live) · `deploy/nginx/marketview.PRE_PORT80_20261004_0400` (pre-change) |
| Status | **APPLIED 2026-10-04 ~04:00 UTC.** This runbook records what was done and how to undo it |
| Related | **TD-S89-NEW-4** (TCP 80 at the SG) · **TD-S89-NEW-5** (anon-grant audit) · `CASE-2026-09-22-anon-privilege-exposure` §10 |

---

## 1. What was wrong

`/etc/nginx/sites-available/marketview` had **two** server blocks listening on `:80`:

- a **`default_server`** with `server_name _` and **`root /var/www/marketview`**, and
- Certbot's own block with `server_name marketview.meridianalpha.in`, which already redirected.

nginx routes `:80` by `server_name`, so the canonical host matched Certbot's block and redirected —
and **everything else fell through to `default_server` and was served the application
unauthenticated.** Measured before the change:

| request on `:80` | result |
|---|---|
| `Host: marketview.meridianalpha.in` `GET /` | **301** — correct, and the control that scopes the fault |
| `Host: 13.63.27.85` `GET /assets/index-Bp8WxCgw.js` | **200 · `application/javascript` · 651,242 B** |
| `Host: nonsense.example` `GET /` | **200 · 878 B** (the real `index.html`) |

**`:443` was never exposed.** Its block carries `auth_request /oauth2/auth` at **server** level, so
every `location` inherits it — including the `\.(js|css)$` block. The same asset over TLS returns
the oauth2-proxy sign-in page, not the bundle.

## 2. The fix

`:80` became a **redirector with no docroot**. Removed: `root`, `index`, the SPA `try_files`
fallback, and the static-asset `location`. Added: an ACME location (inert today — see §4) and
`location / { return 301 https://marketview.meridianalpha.in$request_uri; }`. `/_health` was kept
as a fixed literal; it reads nothing from disk, and it is the only unauthenticated target
`scripts/smoke/smoke_probe_marketview_surfaces.py:213` has.

The `:443` block and Certbot's `:80` redirect block were **not touched** — verified byte-identical,
2,211 B, with a deliberately offset slice correctly failing so the comparison was a test.

## 3. Procedure — G1 to G7, as executed

```bash
# G1  Back up, and HASH-GATE before writing anything.
sudo cp -a /etc/nginx/sites-available/marketview \
           /etc/nginx/sites-available/marketview.PRE_PORT80_$(date +%Y%m%d_%H%M)
sha256sum /etc/nginx/sites-available/marketview      # expect b68e266c…  STOP if it differs

# G2  Write the new config, then confirm the diff is EXACTLY ONE hunk.
sudo cp deploy/nginx/marketview.conf /etc/nginx/sites-available/marketview
sudo diff -u <backup> /etc/nginx/sites-available/marketview | grep -c '^@@'   # expect 1

# G3  Validate BEFORE any reload. A failed -t leaves the RUNNING config live.
sudo nginx -t

# G4  Reload, NOT restart. Reload re-execs workers with no dropped listener.
sudo systemctl reload nginx && systemctl is-active nginx
systemctl show nginx -p MainPID -p ActiveEnterTimestamp   # MainPID must NOT change

# G5  Verify — see §5, every line has a different expected value than its pre-state.
# G6  sudo certbot renew --dry-run        # the renewal proof; MUST succeed
# G7  Rollback if G3–G6 fails — see §6.
```

**Measured on the real run:** hash gate PASS · one hunk · `nginx -t` successful · **MainPID 550
unchanged and `ActiveEnterTimestamp` still 2026-09-22**, which is the evidence it was a reload and
not a restart · all six G5 checks as expected · `certbot renew --dry-run` **succeeded**.

## 4. ACME — the renewal path, and why the location in the config is inert

`/etc/letsencrypt/renewal/marketview.meridianalpha.in.conf` reads **`authenticator = nginx`,
`installer = nginx`**, with **no `webroot_path` and no `webroot_map`**. The certbot **nginx plugin**
inserts its **own temporary server block**, validates, and reverts — it does not read the
`/.well-known/acme-challenge/` location in this config. **That location is therefore INERT today**
and is kept only so a later switch to `--webroot` cannot fail silently.

**This is stated because an un-annotated ACME block looks load-bearing** and would be preserved
forever by readers who assume it is doing work.

Renewal runs on `snap.certbot.renew.timer`. **Do not apply changes to this file inside that
window** — check `systemctl list-timers | grep certbot` first.

## 5. Verification — and why these checks can fail

**The three checks that look obvious are the ones that cannot fail.** Over TLS, `auth_request` is
at server level, so **every path returns 200 with the sign-in page** — the page, a real asset and
a **bogus** asset alike. A 200 through `marketview.meridianalpha.in` proves nothing about whether
the deploy is serving.

The sign-in page **embeds the requested path verbatim, exactly once**, so its size is
**`8484 + len(path)`** — measured 8,485 B at `/`, 8,486 at `/a`, 8,495 at `/aaaaaaaaaa`, 8,509 at
the 25-character asset paths. Equal size therefore follows from **equal path length** and says
nothing about equal content: the real and bogus asset responses are both 8,509 B and differ in
**exactly 8 bytes**, the embedded filename.

**Verify on the un-gated `:80` origin instead, and always run the bogus-path control:**

```bash
# must be 301 (was 200 / 651,242 B)
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -H 'Host: 13.63.27.85' \
     http://127.0.0.1/assets/index-Bp8WxCgw.js
# must be 301 (was 200 / 878 B)
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -H 'Host: nonsense.example' http://127.0.0.1/
# must STILL be 301 — the canonical path, unchanged
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: marketview.meridianalpha.in' http://127.0.0.1/
# must STILL be 200 / 8,485 — :443 untouched
curl -sk -o /dev/null -w '%{http_code} %{size_download}\n' https://127.0.0.1/
# redirect target preserves the path
curl -s -o /dev/null -w '%{redirect_url}\n' -H 'Host: 13.63.27.85' http://127.0.0.1/assets/index-Bp8WxCgw.js
curl -s http://127.0.0.1/_health
```

**After a redeploy, verify the bundle on `:80` with a bogus-path control:**

```bash
for p in /assets/<real>.js /assets/index-ZZZZZZZZ.js; do
  curl -sI "http://127.0.0.1$p" | head -1       # real: 200 application/javascript ; bogus: 404
done
```
The `location ~* \.(js|css)$` block uses `try_files $uri =404`, so it does **not** fall through to
the SPA handler — **which is what makes the 404 a real control.**

## 6. Rollback

```bash
sudo cp -a /etc/nginx/sites-available/marketview.PRE_PORT80_<stamp> \
           /etc/nginx/sites-available/marketview
sudo nginx -t && sudo systemctl reload nginx
sha256sum /etc/nginx/sites-available/marketview      # must read b68e266c…
```
Byte-exact and verified by hash, not by eye. The original has **no trailing newline**; `cp -a`
preserves that, so the hash matches.

## 7. The forensic finding — what this did NOT undo

Full record: `CASE-2026-09-22-anon-privilege-exposure` **§10**; disposition in **TD-S89-NEW-5**.

The bundle **was** served to parties other than the operator while the hole was open — 15 serves to
14 distinct IPs with no `Referer`, across DigitalOcean and Alibaba ranges, 2026-09-20 → 10-03. It
contains the Supabase URL and **anon** key (`service_role` ×0), so **nothing needs rotating** — but
where RLS is off the **GRANT alone is the boundary** (TD-S81-NEW-2), and that boundary has no watcher.

**Two things this change cannot do, stated so they are not assumed:**

1. **Caches.** Already-fetched assets carry `Cache-Control: public, immutable, max-age=2592000` —
   **30 days**. Closing a hole revokes nothing already served.
2. **The port.** TCP 80 remains open at the security group. **TD-S89-NEW-4** carries that decision,
   and any SG edit must be preceded by the **IMDSv2 attached-SG query** — a settled decision from
   S39, where hours were lost editing an orphan SG while Console naming and memory both said
   otherwise:
   ```bash
   TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
            -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
   curl -H "X-aws-ec2-metadata-token: $TOKEN" \
        http://169.254.169.254/latest/meta-data/security-groups
   ```

## 8. Reading the access log — what it can and cannot tell you

**The log cannot answer "which Host?"** The format is nginx default `combined`, which **omits the
`Host` header**, and `:80` and `:443` write to the **same file**. Response **size** is the only
available discriminator: a gated serve is the sign-in page (`8484 + len(path)`), an un-gated one is
the real asset.

If `Host` is ever needed, the log format must be changed **forward** — nothing retrospective can
recover it.

One caution from the S89 pass: a `< 2000 B` filter over `GET /` produced **2,757** apparent hits,
of which the real count was **4**. The rest were 46 responses of **`200 / 496 B`** that match
neither `index.html` (878 B) nor the sign-in page, **could not be reproduced, and remain
unidentified**. Do not assume a size bucket is what it looks like; reproduce it first.

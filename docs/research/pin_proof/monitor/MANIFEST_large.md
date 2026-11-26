# Monitor files over 40 KB, not committed

Files over 40 KB stay on the box in ~/meridian-cc/docs/research/pin_proof/monitor/; each is also listed in its folder's SHA256SUMS, which is committed.

Written 2026-11-26, MR-PIN4, for days 2026-11-25 and 2026-11-26. Threshold 40,960
bytes (40 KiB); the largest committed file is 38,957 bytes and the smallest excluded
is 1,614,404, so a 40,000-byte threshold would exclude the same four files.

| relative path | bytes | sha256 |
|---|---|---|
| `2026-11-25/NIFTY_T1_strikes.txt` | 1622990 | `2d085b8d9119a012503fd8126d8faf5a3c516a48760a6ada0b218836bd8df8ca` |
| `2026-11-25/SENSEX_T1_strikes.txt` | 2156281 | `705c07ab37c8fe10b68d34089b03a6981a7908eada076c1092d8c0711de4f2eb` |
| `2026-11-26/NIFTY_T1_strikes.txt` | 1614404 | `1855a52060622ccd1ef2f8d529ed95285cf83224a19f7367c1f9e32a25a7739b` |
| `2026-11-26/SENSEX_T1_strikes.txt` | 2226802 | `7b5c5473a3139b0671a027ff26e13e3d7444e894bdc16a79f864b37f4b4fe81e` |

Each of the four appears in its own day folder's `SHA256SUMS` (two entries per day
folder, verified `rc=0` on 2026-11-26), so the committed manifest fixes the content of
the uncommitted file.

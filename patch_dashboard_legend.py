"""
patch_dashboard_legend.py  --  Active-only legend filter
=========================================================
Patches merdian_signal_dashboard.py:
  1. Removes the global WIN_RATES legend table (full-width card)
  2. Adds a per-symbol active legend inside each signal card —
     shows ONLY rows matching the current ict_pattern for that symbol
  3. If no ICT pattern active, shows a single "No active pattern" row

Run:      python patch_dashboard_legend.py
Dry-run:  python patch_dashboard_legend.py --dry-run
"""

import os
import sys
import shutil

BASE   = r'C:\GammaEnginePython'
TARGET = os.path.join(BASE, 'merdian_signal_dashboard.py')
DRY    = '--dry-run' in sys.argv

# ── [A] Remove the global legend card from the HTML body ─────────────────────

LEGEND_CARD_OLD = """  <!-- Win rate legend -->
  <div class="legend-card full-width">
    <div class="legend-title">Win Rate Reference — Full Year Apr 2025–Mar 2026 · Experiments 2/5/8/10c/15/16</div>
    <table>
      <thead>
        <tr>
          <th>Pattern</th><th>Condition</th><th>WR</th><th>Tier</th><th>Note</th>
        </tr>
      </thead>
      <tbody>
        {legend_rows()}
      </tbody>
    </table>
  </div>"""

LEGEND_CARD_NEW = ""  # removed entirely

# ── [B] Replace legend_rows() function with active_legend_rows(pattern) ───────

LEGEND_FN_OLD = """    def legend_rows():
        rows = []
        for pattern, cond, wr, tier, note in WIN_RATES:
            tc = tier_color(tier)
            wr_cls = "wr-high" if wr >= 80 else "wr-mid" if wr >= 60 else "wr-skip" if wr < 30 else "wr-low"
            rows.append(f\"\"\"
            <tr class="{'skip-row' if tier=='SKIP' else ''}">
              <td class="pattern">{pattern}</td>
              <td class="cond">{cond}</td>
              <td class="wr-cell {wr_cls}">{wr:.0f}%</td>
              <td><span class="pill sm" style="border-color:{tc};color:{tc}">{tier}</span></td>
              <td class="note">{note}</td>
            </tr>\"\"\")
        return "\\n".join(rows)"""

LEGEND_FN_NEW = """    def active_legend_rows(pattern):
        \"\"\"Return legend rows for the active pattern only.\"\"\"
        if not pattern or pattern in ('NONE', 'NO DATA', 'ERROR'):
            return '<tr><td colspan="5" class="no-pattern">No active ICT pattern this cycle</td></tr>'
        matches = [r for r in WIN_RATES if r[0] == pattern]
        if not matches:
            return f'<tr><td colspan="5" class="no-pattern">No reference data for {pattern}</td></tr>'
        rows = []
        for pat, cond, wr, tier, note in matches:
            tc = tier_color(tier)
            wr_cls = "wr-high" if wr >= 80 else "wr-mid" if wr >= 60 else "wr-skip" if wr < 30 else "wr-low"
            rows.append(f\"\"\"
            <tr class="{'skip-row' if tier=='SKIP' else ''}">
              <td class="pattern">{pat}</td>
              <td class="cond">{cond}</td>
              <td class="wr-cell {wr_cls}">{wr:.0f}%</td>
              <td><span class="pill sm" style="border-color:{tc};color:{tc}">{tier}</span></td>
              <td class="note">{note}</td>
            </tr>\"\"\")
        return "\\n".join(rows)"""

# ── [C] Add active legend table inside signal_card, before regime-row ─────────

REGIME_ROW_ANCHOR = '          <div class="regime-row">'

ACTIVE_LEGEND_INSERTION = """          <div class="active-legend">
            <div class="legend-title-inline">WIN RATE REFERENCE — {pattern}</div>
            <table class="legend-inline">
              <thead>
                <tr>
                  <th>Pattern</th><th>Condition</th><th>WR</th><th>Tier</th><th>Note</th>
                </tr>
              </thead>
              <tbody>
                {active_legend_rows(pattern)}
              </tbody>
            </table>
          </div>

          <div class="regime-row">"""

# ── [D] Add CSS for active legend ─────────────────────────────────────────────

CSS_ANCHOR = '  /* ── Footer ── */'

CSS_ADDITION = """  /* ── Active legend (per card) ── */
  .active-legend {{ padding:0 0 0 0; border-bottom:1px solid var(--border); }}
  .legend-title-inline {{ padding:8px 16px 6px; font-size:10px; letter-spacing:2px;
                          color:var(--muted); text-transform:uppercase; font-weight:700; }}
  .legend-inline {{ width:100%; border-collapse:collapse; }}
  .legend-inline th {{ padding:6px 12px; background:var(--bg3); font-size:10px;
                       letter-spacing:1px; color:var(--muted); text-align:left;
                       text-transform:uppercase; border-bottom:1px solid var(--border); }}
  .legend-inline td {{ padding:6px 12px; border-bottom:1px solid var(--border);
                       vertical-align:middle; font-size:12px; }}
  .legend-inline tr:last-child td {{ border-bottom:none; }}
  .no-pattern {{ color:var(--muted); font-style:italic; text-align:center;
                 padding:12px !important; }}

  /* ── Footer ── */"""

# ─────────────────────────────────────────────────────────────────────────────

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def p_ok(msg):   print(f'  [OK  ] {msg}')
def p_skip(msg): print(f'  [SKIP] {msg}')
def p_dry(msg):  print(f'  [DRY ] {msg}')
def p_fail(msg): print(f'  [FAIL] {msg}')

def main():
    print('=' * 60)
    print('patch_dashboard_legend.py  --  Active legend filter')
    print('DRY RUN' if DRY else 'LIVE')
    print('=' * 60)

    if not os.path.exists(TARGET):
        print(f'[ERROR] Not found: {TARGET}')
        sys.exit(1)

    src = read_file(TARGET)

    if 'active_legend_rows' in src:
        p_skip('Already patched.')
        return

    print('\nPre-flight:')
    errors = 0
    for label, anchor in [
        ('[A] Global legend card',       LEGEND_CARD_OLD[:60]),
        ('[B] legend_rows() function',   'def legend_rows():'),
        ('[C] regime-row div anchor',    REGIME_ROW_ANCHOR),
        ('[D] CSS footer anchor',        CSS_ANCHOR),
    ]:
        if anchor in src:
            p_ok(f'Found: {label}')
        else:
            p_fail(f'NOT found: {label}')
            errors += 1

    if errors:
        print(f'\n[ABORT] {errors} anchor(s) missing.')
        sys.exit(1)

    new_src = src

    # [A] Remove global legend card
    new_src = new_src.replace(LEGEND_CARD_OLD, LEGEND_CARD_NEW, 1)
    p_ok('[A] Global legend card removed.')

    # [B] Replace legend_rows with active_legend_rows
    new_src = new_src.replace(LEGEND_FN_OLD, LEGEND_FN_NEW, 1)
    p_ok('[B] legend_rows() replaced with active_legend_rows(pattern).')

    # [C] Insert active legend table inside signal_card before regime-row
    # Only first occurrence — signal_card function has one regime-row
    new_src = new_src.replace(
        REGIME_ROW_ANCHOR,
        ACTIVE_LEGEND_INSERTION,
        1  # first occurrence only — inside signal_card
    )
    p_ok('[C] Active legend table inserted inside signal_card.')

    # [D] Add CSS
    new_src = new_src.replace(CSS_ANCHOR, CSS_ADDITION, 1)
    p_ok('[D] CSS added for active legend.')

    if DRY:
        p_dry('No files written.')
        return

    shutil.copy2(TARGET, TARGET + '.bak')
    write_file(TARGET, new_src)

    # Verify
    final = read_file(TARGET)
    print('\nVerification:')
    for label, token in [
        ('active_legend_rows defined',      'def active_legend_rows(pattern):'),
        ('active_legend_rows called',       'active_legend_rows(pattern)'),
        ('no-pattern fallback',             'No active ICT pattern'),
        ('legend-inline CSS class',         'legend-inline'),
        ('global legend card removed',      'Win Rate Reference — Full Year' ),
    ]:
        # last one should NOT be present
        if label == 'global legend card removed':
            sym = 'v' if token not in final else 'X'
        else:
            sym = 'v' if token in final else 'X'
        print(f'  [{sym}] {label}')

    print('\n' + '=' * 60)
    print('Dashboard legend patched.')
    print('Each symbol card now shows only its active ICT pattern rows.')
    print('Restart dashboard: python merdian_signal_dashboard.py')
    print('=' * 60)


if __name__ == '__main__':
    main()

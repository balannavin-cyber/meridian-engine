import sys

p = 'ingest_breadth_from_ticks.py'
s = open(p, encoding='utf-8').read()

before_no_ticks    = s.count('"NO_TICKS"')
before_write_fail  = s.count('"WRITE_FAILURE"')

s = s.replace('exit_reason="NO_TICKS",',      'exit_reason="SKIPPED_NO_INPUT",')
s = s.replace('exit_reason="WRITE_FAILURE",', 'exit_reason="DATA_ERROR",')

open(p, 'w', encoding='utf-8', newline='\n').write(s)

print(f'NO_TICKS replacements made: {before_no_ticks}')
print(f'WRITE_FAILURE replacements made: {before_write_fail}')
print('Saved.')

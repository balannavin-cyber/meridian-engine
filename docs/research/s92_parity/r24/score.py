import json,re,collections,csv
fx={f['fid']:f for f in json.load(open('fixtures_40.json'))}
mr={r['fid']:r for r in json.load(open('meridian_asof.json'))}
def n(s):
    if s is None: return None
    if isinstance(s,(int,float)): return float(s)
    t=str(s).replace('−','-').replace('–','-').replace(',','')
    m=re.search(r'[-+]?\d+(\.\d+)?',t); return float(m.group(0)) if m else None
def cr(s):
    if s is None: return None
    t=str(s).replace('−','-').replace(',','').upper()
    v=n(t)
    if v is None: return None
    if 'L CR' in t or 'LCR' in t.replace(' ',''): v*=1e5
    elif 'K CR' in t or 'KCR' in t.replace(' ',''): v*=1e3
    elif 'CR' in t: pass
    return v
def strikes(lst):
    out=[]
    for x in lst or []:
        v=n(str(x).split(':')[0]); 
        if v: out.append(v)
    return out
def regime_ref(s):
    t=str(s).upper()
    if any(k in t for k in ['POSITIVE','LONG','DAMPEN']): return 'LONG_GAMMA'
    if any(k in t for k in ['NEGATIVE','SHORT','AMPLIF']): return 'SHORT_GAMMA'
    return None
rows=[]
for fid,f in fx.items():
    m=mr.get(fid); F=f['fields']
    for fld in f['scoreable']:
        ref=F.get(fld); res=None; mer=None; detail=''
        if not m or (m.get('gss_ts_ist') is None and m.get('gm_ts_ist') is None):
            rows.append((fid,fld,ref,None,'NO_DATA','no MERIDIAN run that session')); continue
        if fld=='spot':
            mer=n(m['gm_spot'] or m['gss_spot']); r=n(ref)
            if r and mer: d=r-mer; res='MATCH' if abs(d)/r<=0.001 else 'DIFF'; detail=f'{d:+.1f} pts'
        elif fld in('net_gex','net_dealer_gamma'):
            r=cr(ref); mer=n(m['net_gex_cr'])
            if r is None or mer is None: res='NO_DATA' if mer is None else 'UNREADABLE'
            else: res='SIGN_MATCH' if (r>0)==(mer>0) else 'SIGN_DIFF'; detail=f'ref {r/1e5:+.2f}L Cr vs MERIDIAN {mer/1e5:+.2f}L Cr (ratio {r/mer:.2f})' if mer else ''
        elif fld=='regime':
            r=regime_ref(ref); mer=m['regime']
            res='NO_DATA' if mer is None else ('MATCH' if r==mer else 'DIFF')
        elif fld=='flip':
            r=n(ref); mer=n(m['legacy_flip'])
            if r is None: res='REF_ABSENT'
            elif mer is None: res='NO_DATA'
            else: d=r-mer; res='WITHIN_25' if abs(d)<=25 else 'DIFF'; detail=f'{d:+.0f} pts vs legacy flip_level'
        elif fld in ('pin_strike',):
            r=n(ref); mer=n(m['leader']); top=[t['strike'] for t in (m['top5'] or [])]
            res='MATCH' if r==mer else ('IN_TOP5' if r in top else 'DIFF'); detail=f'MERIDIAN leader {mer:.0f}' if mer else ''
        elif fld in ('max_gamma','max_gamma_strike','pos_gamma_peak'):
            r=n(ref); mer=n(m['pos_peak']); res='MATCH' if r==mer else 'DIFF'; detail=f'MERIDIAN +peak {mer:.0f}' if mer else ''
        elif fld=='neg_gamma_peak':
            r=n(ref); mer=n(m['neg_peak']); res='MATCH' if r==mer else 'DIFF'
        elif fld=='runner_up':
            r=n(ref); mer=n(m['runner_up']); top=[t['strike'] for t in (m['top5'] or [])]
            res='MATCH' if r==mer else ('IN_TOP5' if r in top else 'DIFF'); detail=f'MERIDIAN #2 {mer:.0f}' if mer else ''
        elif fld=='top5':
            rs=strikes(ref); top=[t['strike'] for t in (m['top5'] or [])]
            k=len(set(rs)&set(top)); mer=top
            res=f'{k}/{len(rs)}'; detail='leader same' if rs and top and rs[0]==top[0] else 'leader differs'
        elif fld=='hhi':
            r=n(ref); mer=n(m['hhi']); res='REPORTED'; detail=f'ref {r} vs MERIDIAN {mer} (ratio {r/mer:.2f})' if r and mer else ''
        elif fld=='top5_share':
            r=n(ref); mer=n(m['top5_share_pct']); res='WITHIN_5PP' if r and mer and abs(r-mer)<=5 else 'DIFF'; detail=f'ref {r}% vs {mer}%'
        elif fld in ('call_wall','put_wall'):
            r=n(ref); mer=n(m[fld]); 
            if r is None: res='UNREADABLE'
            elif mer is None: res='NO_DATA'
            else: res='MATCH' if r==mer else 'DIFF'; detail=f'{r-mer:+.0f} pts'
        elif fld=='dte':
            r=n(ref); mer=m['gss_dte']; res='MATCH' if r==mer else 'DIFF'; detail=f'ref {r:.0f} vs {mer}'
        rows.append((fid,fld,ref,mer,res,detail))
with open('scores.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['fid','field','reference','meridian','result','detail'])
    for r in rows: w.writerow([r[0],r[1],json.dumps(r[2],ensure_ascii=False),json.dumps(r[3]),r[4],r[5]])
agg=collections.defaultdict(collections.Counter)
for r in rows: agg[r[1]][r[4]]+=1
for k,v in sorted(agg.items()): print(k.ljust(18),dict(v))

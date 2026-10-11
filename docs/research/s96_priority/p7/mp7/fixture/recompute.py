# Independent second implementation (Python, from the raw fixture rows) of one cycle row of mp7_cycles.sql.
import json, csv, sys, datetime as dt
from decimal import Decimal as D
rows=json.load(open('rows.json'))
def ist(s): return dt.datetime.fromisoformat(s).strftime('%H:%M:%S')
def gap(dl,iv): return dl is None or (dl==0 and (iv or 0)==0)
def compute(sym, day, cyc):
    rs=[r for r in rows if r[1]==sym and r[0][:10]==day]
    front=min(r[2] for r in rs if r[2]>=day and ist(r[0])<='15:15:00')
    rs=[r for r in rs if r[2]==front]
    anc=min(r[0] for r in rs); assert ist(anc)<'09:15:00'
    A={(r[4],r[5]):D(str(r[6])) for r in rs if r[0]==anc}
    C={(r[4],r[5]):r for r in rs if ist(r[0])==cyc}
    strikes=sorted({k for k,_ in C})
    out={k:D(0) for k in ['book_call','book_put_v','book_put_p','flow_call','flow_put_v','flow_put_p','book_gap_oi_v','flow_gap_doi_v','flow_gap_doi_p','no_anchor_oi_qty','oi_qty']}
    for K in strikes:
        ce=C.get((K,'CE')); pe=C.get((K,'PE'))
        spot=D(str((ce or pe)[3]))
        cdl=None if ce is None else ce[7]; cgap= ce is not None and gap(ce[7],ce[8])
        call_ok = ce is not None and cdl is not None and not cgap
        for side,r in (('CE',ce),('PE',pe)):
            if r is None: continue
            oi=D(str(r[6])); out['oi_qty']+=oi
            g=gap(r[7],r[8]); dl=None if r[7] is None else D(str(r[7]))
            a=A.get((K,side)); doi=None if a is None else oi-a
            if doi is None: out['no_anchor_oi_qty']+=oi
            if side=='CE':
                b = D(0) if oi==0 else (None if g else dl*oi*spot/D('1e7'))
                if b is None: out['book_gap_oi_v']+=oi
                else: out['book_call']+=b
                f = None if doi is None else (D(0) if doi==0 else (None if g else dl*doi*spot/D('1e7')))
                if f is None and doi is not None: out['flow_gap_doi_v']+=abs(doi); out['flow_gap_doi_p']+=abs(doi)
                elif f is not None: out['flow_call']+=f
            else:
                bv = D(0) if oi==0 else (None if g else dl*oi*spot/D('1e7'))
                if bv is None: out['book_gap_oi_v']+=oi
                else: out['book_put_v']+=bv
                bp = D(0) if oi==0 else (None if not call_ok else (D(str(cdl))-1)*oi*spot/D('1e7'))
                if bp is not None: out['book_put_p']+=bp
                fv = None if doi is None else (D(0) if doi==0 else (None if g else dl*doi*spot/D('1e7')))
                fp = None if doi is None else (D(0) if doi==0 else (None if not call_ok else (D(str(cdl))-1)*doi*spot/D('1e7')))
                if doi is not None and fv is None: out['flow_gap_doi_v']+=abs(doi)
                if doi is not None and fp is None: out['flow_gap_doi_p']+=abs(doi)
                if fv is not None: out['flow_put_v']+=fv
                if fp is not None: out['flow_put_p']+=fp
    return out
sql={(r['symbol'],r['cycle_ist']):r for r in csv.DictReader(open(sys.argv[1]))}
worst=D(0); n=0
for (sym,cyc),r in sql.items():
    py=compute(sym,'2026-10-09',cyc); n+=1
    for k,v in py.items():
        diff=abs(D(r[k])-v); worst=max(worst,diff)
        if diff>D('1e-9'): print('MISMATCH',sym,cyc,k,r[k],v)
print('cycles compared',n,'max abs diff',worst)

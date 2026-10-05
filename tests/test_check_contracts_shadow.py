import sys; sys.path.insert(0,'.')
from datetime import datetime, timezone, timedelta
import check_contracts_shadow as m
U=timezone.utc
asof=datetime(2026,10,5,9,40,tzinfo=U)  # 15:10 IST
def win(vals, col='spot', n=4, rows=950, exp=2):
    w={}
    for i,v in enumerate(vals):
        t=asof-timedelta(minutes=5*(len(vals)-1-i))
        w[t]=[{col:v,'expiry_date':f'E{k%exp}','ts':t} for k in range(rows)]
    return w
ocs={'product':'ocs:N','cadence_min':5,'freshness_sla_min':10,'expected_per_cycle':{'rows':[800,1100],'expiries':[2,2]},'movement_cols':['spot'],'movement_window_cycles':3}
w=win([1,2,3,4]); nt=max(w)
r=m.own_status(ocs,nt,w[nt],w,asof,True,None); print('ocs normal ',r[0]); assert r[0]=='OK'
w=win([7,7,7,7]); r=m.own_status(ocs,nt,w[nt],w,asof,True,None); print('ocs 10-02  ',r[0],r[1]); assert r[0]=='STALE'
w=win([1,2,3,4],rows=400); r=m.own_status(ocs,nt,w[nt],w,asof,True,None); print('ocs partial',r[0],r[1]); assert r[0]=='DEGRADED'
old=asof-timedelta(minutes=30); r=m.own_status(ocs,old,[],{},asof,True,None); print('ocs stall  ',r[0],r[1]); assert r[0]=='MISSING'
r=m.own_status(ocs,None,[],{},asof,False,None); print('closed     ',r[0]); assert r[0]=='CLOSED'
daily={'product':'bid','cadence_min':1440,'freshness_sla_min':2880,'expected_per_cycle':{'rows':[1200,1400]},'movement_cols':[]}
r=m.own_status(daily,'2026-09-29',[{}]*815,{},asof,True,4); print('bid        ',r[0],r[1]); assert r[0]=='MISSING'
eil={'product':'eil','cadence_min':1440,'freshness_sla_min':1440,'expected_per_cycle':{'rows':[1200,1400]},'movement_cols':[]}
r=m.own_status(eil,asof,[{}]*1314,{},asof,True,0); print('eil        ',r[0]); assert r[0]=='OK'
wcb={'product':'wcb','cadence_min':5,'freshness_sla_min':10,'expected_per_cycle':{'rows':[1,1]},'movement_cols':['wcb_score'],'movement_window_cycles':3}
w=win([24.6]*4,col='wcb_score',rows=1,exp=1); r=m.own_status(wcb,nt,w[nt],w,asof,True,None); print('wcb own    ',r[0]); assert r[0]=='STALE'
own={'wcb':('STALE','frozen'),'bid':('MISSING','4 behind'),'eil':('OK',None),'gm':('OK',None),'ocs':('OK',None),'gch':('MISSING','no row')}
f=m.propagate(own,[('wcb','bid'),('wcb','eil'),('gch','gm'),('gm','ocs')]); print('propagated ',f); assert f['wcb'][0]=='STALE' and f['gm'][0]=='OK'
own={'gm':('OK',None),'ocs':('STALE','frozen')}
f=m.propagate(own,[('gm','ocs')]); print('gm<-ocs    ',f['gm']); assert f['gm'][0]=='STALE'
own={'gm':('CLOSED',None),'ocs':('MISSING','x')}
f=m.propagate(own,[('gm','ocs')]); assert f['gm'][0]=='CLOSED'
assert m.worse('CLOSED','OK')=='OK' and m.worse('STALE','MISSING')=='MISSING'
print('ALL PASS')

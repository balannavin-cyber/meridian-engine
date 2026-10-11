import random, math, datetime as dt, json
random.seed(7)
IST=dt.timezone(dt.timedelta(hours=5,minutes=30))
rows=[]; spots=[]
def N(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
SYM={'NIFTY':(25000,50,[dt.date(2026,10,13),dt.date(2026,10,20)]),
     'SENSEX':(82000,100,[dt.date(2026,10,8),dt.date(2026,10,15)])}
days={dt.date(2026,10,2):'frozen',dt.date(2026,10,7):'late',dt.date(2026,10,8):'normal',dt.date(2026,10,9):'normal'}
truth={}
for day,kind in days.items():
  for sym,(s0,step,exps) in SYM.items():
    times=[]
    if kind!='late': times.append(dt.datetime.combine(day,dt.time(8,35),IST))
    t=dt.datetime.combine(day,dt.time(9,15 if kind!='late' else 20),IST)
    while t<=dt.datetime.combine(day,dt.time(15,40),IST):
      if t.time()<=dt.time(15,15) or t.minute in (20,25,30,35,40): times.append(t)
      t+=dt.timedelta(minutes=5)
    front=[e for e in exps if e>=day]
    oi0={}
    for i,ts in enumerate(times):
      spot = s0 if kind=='frozen' else round(s0*(1+0.002*math.sin(i/7)+random.gauss(0,0.0005)),2)
      for e in front:
        T=max((e-day).days,0.2)/365
        for k in range(-12,13):
          K=s0+k*step
          if kind!='frozen' and e==front[0] and k==11 and i==0: continue   # strike absent at anchor
          if kind!='frozen' and e==front[0] and k==-11 and i==5: continue  # strike absent in one cycle
          for ot in ('CE','PE'):
            key=(sym,day,e,K,ot)
            if key not in oi0: oi0[key]=random.choice([0,0,1,2,5,10,40])*(65 if sym=='NIFTY' else 20)*100
            if i>0 and kind!='frozen' and random.random()<0.3:
              oi0[key]=max(0,oi0[key]+random.randint(-30,60)*(65 if sym=='NIFTY' else 20))
            sig=0.13+0.02*abs(k)/12
            d1=(math.log(spot/K)+0.5*sig*sig*T)/(sig*math.sqrt(T))
            dl=N(d1) if ot=='CE' else N(d1)-1
            iv=sig*100
            # gaps: deep ITM PE (k>=9) vendor drops greeks; one CE gap with NULL delta
            if ot=='PE' and k>=9: dl=0; iv=0
            if ot=='CE' and k==-10: dl=None
            dl = None if dl is None else round(dl,5)
            rows.append((ts.isoformat(),sym,e.isoformat(),spot,K,ot,oi0[key],dl,iv))
    for m in range(0,380):
      tt=dt.datetime.combine(day,dt.time(9,15),IST)+dt.timedelta(minutes=m)
      spots.append((tt.isoformat(),sym, s0 if kind=='frozen' else round(s0+random.gauss(0,20),2)))
with open('data.sql','w') as f:
  f.write("INSERT INTO trading_calendar VALUES ('2026-10-03',false),('2026-10-07',true),('2026-10-08',true),('2026-10-09',true);\n")
  f.write("INSERT INTO data_contamination_ranges VALUES ('X-OLD','spot','2026-03-27','2026-04-20','{market_spot_snapshots}');\n")
  for chunk in range(0,len(rows),2000):
    f.write("INSERT INTO option_chain_snapshots (ts,symbol,expiry_date,spot,strike,option_type,oi,delta,iv) VALUES\n")
    f.write(",\n".join("('%s','%s','%s',%s,%s,'%s',%s,%s,%s)"%(a,b,c,d,e,g,h,'NULL' if i is None else repr(i),j) for a,b,c,d,e,g,h,i,j in rows[chunk:chunk+2000])+";\n")
  f.write("INSERT INTO market_spot_snapshots (ts,symbol,spot) VALUES\n"+",\n".join("('%s','%s',%s)"%s for s in spots)+";\n")
json.dump(rows,open('rows.json','w'))
print(len(rows),len(spots))

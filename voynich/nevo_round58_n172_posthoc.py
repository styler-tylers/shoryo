#!/usr/bin/env python3
"""第 58 巡 N172 の事後の点検: 段落の頭の行を除いて、境目の規則の持ち越しを測り直す（かき混ぜの対照つき）。

    python3 voynich/nevo_round58_n172_posthoc.py
"""
import sys,random,math,statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collections import Counter
from nevo_round58 import table
from nevo_round9 import voynich
import corpus
V=voynich();a=corpus.make_parser('').parse_args([]);a.locus='P';_,L=corpus.load_lines(a)
ill={l.page.name:l.page.get('I') for l in L}
def run(lang,keep,shuffle=None):
    pt,_,last=V[lang]
    # paragraph-start flags per line
    starts={};i=0;prev_last=True
    for pg,ls in pt.items():
        st=[]
        for j,l in enumerate(ls):
            st.append(prev_last or j==0); prev_last=last[i]; i+=1
        starts[pg]=st
    P={pg:list(zip(ls,starts[pg])) for pg,ls in pt.items() if keep(pg)}
    if shuffle is not None:
        r=random.Random(shuffle); P={pg:r.sample(v,len(v)) for pg,v in P.items()}
    cab,ca=table({pg:[l for l,_ in v] for pg,v in P.items()});na=sum(ca.values());K=len(ca)+1
    def g(a,b):
        row=cab.get(a,Counter());pb=(ca.get(b,0)+1)/(na+K);pba=(row.get(b,0)+pb*5)/(sum(row.values())+5);return math.log2(pba/pb)
    rng=random.Random(5);obs=[];nul=[]
    for v in P.values():
        v=[x for x in v if x[0]]
        cand=[k for k in range(len(v)) if not v[k][1]]
        for i in range(len(v)-1):
            if v[i+1][1]: continue
            o=[k for k in cand if k!=i+1]
            if not o: continue
            obs.append(g(v[i][0][-1][-1],v[i+1][0][0][0]))
            nul.append(statistics.mean(g(v[i][0][-1][-1],v[rng.choice(o)][0][0][0]) for _ in range(20)))
    return statistics.mean(obs)-statistics.mean(nul),len(obs)
for lang in 'AB':
    keep=lambda pg: ill[pg]!='T'
    print(lang,'段落の頭を除く',run(lang,keep),'かき混ぜ',[round(run(lang,keep,s)[0],3) for s in range(3)])
print('B 文字だけ',run('B',lambda pg: ill[pg]=='T'))

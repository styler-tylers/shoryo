#!/usr/bin/env python3
"""第 42 巡 N127 の事後の点検: 同じ語の組を 1 度だけ数える形と、離れた行での同じ量。

    python3 voynich/nevo_round42_n127_posthoc.py <gabc の場所>
"""
import random, statistics, sys
from collections import Counter
sys.path.insert(0, "/home/user/shoryo/voynich")
from nevo_round9 import voynich
from nevo_round42 import chant_lines, paged

def subs(a, b, dedupe):
    out = set() if dedupe else []
    A, B = (set(a), set(b)) if dedupe else (a, b)
    for w in A:
        for v in B:
            if len(w) == len(v) and w != v:
                d = [(x, y) for x, y in zip(w, v) if x != y]
                if len(d) == 1:
                    (out.add if dedupe else out.append)((w, v, d[0]) if dedupe else d[0])
    return [x[2] for x in out] if dedupe else out

def stat(pages, far, dedupe, rng, runs=200):
    groups = []
    for ls in pages.values():
        L = [l[1:-1] for l in ls if len(l) >= 3]
        for i in range(len(L)):
            js = [j for j in range(len(L)) if j - i >= 10] if far else ([i + 1] if i + 1 < len(L) else [])
            for j in js:
                s = subs(L[i], L[j], dedupe)
                if len(s) >= 2:
                    groups.append(s)
    frac = lambda gs: sum(max(Counter(g).values()) >= 2 for g in gs) / len(gs)
    obs = frac(groups); pool = [x for g in groups for x in g]; nul = []
    for _ in range(runs):
        rng.shuffle(pool); it = iter(pool); nul.append(frac([[next(it) for _ in g] for g in groups]))
    m, sd = statistics.mean(nul), statistics.pstdev(nul)
    top = Counter(x for g in groups for x, k in Counter(g).items() if k >= 2).most_common(6)
    return obs, m, obs / m, (obs - m) / sd, len(groups), top

V = voynich(); rng = random.Random(7)
texts = [(f"ヴォイニッチ {l}", V[l][0]) for l in "AB"] + [("聖歌 R1", paged([[tuple(w) for w in l] for l in chant_lines(sys.argv[1])], 10**9))]
for name, P in texts:
    for far in (False, True):
        for dd in (False, True):
            o, m, r, z, n, top = stat(P, far, dd, rng)
            tops = "  ".join(f"{''.join(a)}→{''.join(b)} {k}" for (a, b), k in top) if not far else ""
            print(f"  {name:<12} {'離れた行（10 行以上）' if far else '隣の行':<14} {'同じ語の組は 1 度だけ' if dd else 'そのまま':<14} {o:.3f} 対 {m:.3f}  比 {r:.2f}  z {z:+.1f}（組 {n}）  {tops}", flush=True)

#!/usr/bin/env python3
"""nēvo による解析 第 24 巡: N71（境目の規則の形が近い言語）・N70/N72（境目に合わせて語を選ぶ）。

    python3 voynich/nevo_round24.py <Caesar> --nat <自然言語 …>
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob  # noqa: E402
from nevo_round16 import boundary_dists, reselect, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round23 import VN, VV, pairs_of  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def H(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


def features(pairs, vowels):
    ea, sb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    mi = line_unit.mi(pairs)
    t = Counter((a in vowels, b in vowels) for a, b in pairs)
    lor = math.log(((t[(True, True)] + .5) * (t[(False, False)] + .5)) / ((t[(True, False)] + .5) * (t[(False, True)] + .5)))
    n = len(pairs)
    return {"語末の情報量": H(ea), "語頭の情報量": H(sb), "境目の結び付き": mi, "結び付き÷情報量": mi / min(H(ea), H(sb)),
            "上位3語末": sum(v for _, v in ea.most_common(3)) / n, "交代": lor}


def n71(V, nat):
    print("=== N71 境目の規則の形が近い言語 ===")
    F = {name: features(pr, VN) for name, pr in nat.items()}
    keys = list(next(iter(F.values())))
    mu = {k: statistics.mean(F[n][k] for n in F) for k in keys}
    sd = {k: statistics.pstdev(F[n][k] for n in F) or 1 for k in keys}
    print("  " + " ".join(f"{k:>10}" for k in keys))
    for name, f in F.items():
        print(f"  {name:<10}" + " ".join(f"{f[k]:>10.3f}" for k in keys))
    for lang in ("A", "B"):
        f = features(pairs_of([l for ls in V[lang][0].values() for l in ls]), VV)
        print(f"  ヴォイニッチ{lang} " + " ".join(f"{f[k]:>10.3f}" for k in keys))
        d = {n: math.sqrt(sum(((f[k] - F[n][k]) / sd[k]) ** 2 for k in keys)) for n in F}
        print("     近い順: " + ", ".join(f"{n} {v:.2f}" for n, v in sorted(d.items(), key=lambda x: x[1])))
    sys.stdout.flush()


def firstglyph_source(caesar, G, rng, n=300000, K=8):
    gen = Counter(G.word(rng) for _ in range(n))
    fg = Counter()
    for w, c in gen.items():
        fg[w[0]] += c
    top = [g for g, _ in fg.most_common(K)]
    groups = defaultdict(list)
    for w, _ in gen.most_common():
        groups[w[0] if w[0] in top else "他"].append(w)
    share = {g: sum(gen[w] for w in ws) for g, ws in groups.items()}
    types = [w for w, _ in Counter(caesar).most_common()]
    T = len(types)
    variants = {t: [ws[min(len(ws) - 1, r * len(ws) // T)] for ws in groups.values()] for r, t in enumerate(types)}
    w2t = {}
    for t, vs in variants.items():
        for w in vs:
            w2t.setdefault(w, t)
    gk = list(groups)
    pick = lambda t: variants[t][rng.choices(range(len(gk)), [share[g] for g in gk])[0]]  # noqa: E731
    half = len(caesar) // 2
    it = iter([pick(w) for w in caesar[:half]])
    edge = [pick(w) for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None)), variants, w2t


def nolex_condition(P, G, pt, rng, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    byg = defaultdict(list)
    for w, c in gen.items():
        byg[w[0]].append((w, c))
    T = defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            if len(l) >= 4:
                for a, b in zip(l[1:-1], l[2:-1]):
                    T[a[-1]][b[0]] += 1
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            prevset = set(w for x in ls[max(0, li - 3):li] for w in x)
            for i in range(1, len(l)):
                w = l[i]
                d = T.get(new[-1][-1])
                if w not in prevset and d:
                    gs = [g for g in d if byg.get(g)]
                    if gs:
                        g = rng.choices(gs, [d[x] for x in gs])[0]
                        ws, cs = zip(*byg[g])
                        w = rng.choices(ws, cs)[0]
                new.append(w)
            ls[li] = new
    return P


def lex_source(G, rng, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    ws, cs = zip(*gen.items())
    f = lambda: rng.choices(ws, cs)[0]  # noqa: E731
    return f, f


def dshare(P):
    c = Counter(w[0] for ls in P.values() for l in ls for w in l)
    return c["d"] / sum(c.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("caesar")
    ap.add_argument("--nat", nargs="*", default=[])
    a = ap.parse_args()
    rng = random.Random(2026)
    V = voynich()
    nat = {}
    for p in [a.caesar] + a.nat:
        ws = words_any(Path(p))[:30000]
        nat[Path(p).stem] = pairs_of([[tuple(w) for w in l] for _, ls in line_unit.wrap(ws, 37) for l in ls])
    n71(V, nat)
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(a.caesar))]
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        print(f"     d- で始まる語 {dshare(pt):.1%}", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        dists = boundary_dists(pt)
        runs, ds = [], []
        for seed in (1, 2, 3):
            i, e, variants, w2t = firstglyph_source(caesar, LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            P = reselect(P, variants, w2t, dists, random.Random(seed + 20))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
            ds.append(dshare(P))
        summarize("N70a 最初の字形ごとの書き方", runs)
        print(f"     d- で始まる語 {statistics.mean(ds):.1%}（{min(ds):.1%}〜{max(ds):.1%}）", flush=True)
        runs = []
        for seed in (1, 2, 3):
            i, e = lex_source(LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG), cap=25000)
            P = nolex_condition(P, LG, pt, random.Random(seed + 20))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("N70b 平文なし・境目を条件に選ぶ", runs)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

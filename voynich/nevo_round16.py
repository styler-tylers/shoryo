#!/usr/bin/env python3
"""nēvo による解析 第 16 巡: N45（同音異字型の符号）・N46（種を複数にした判定）・N47（語の長さの歪度の分解）。

    python3 voynich/nevo_round16.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_entropy  # noqa: E402
from nevo_round9 import skew, voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import positions, strength  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
SHOW = ["8量", "h2", "歪度", "T1頭", "T1中", "T1末", "G1", "G10", "隣", "またぐ", "行頭だけ"]


def homophone_source(caesar, G, K, rng, n=300000):
    """平文の語の種類に、型で出やすい語を K 個ずつ当てる。型の語の数が足りないときは、
    よく出る語から K 個ずつ当て、足りなくなった稀な語には 1 個ずつ当てる（全ての種類に最低 1 個）。"""
    gen = Counter(G.word(rng) for _ in range(n))
    lex = [w for w, _ in gen.most_common()]
    types = [w for w, _ in Counter(caesar).most_common()]
    tries = 0
    while len(lex) < len(types) and tries < 10 * n:
        w = G.word(rng)
        tries += 1
        if w not in gen:
            gen[w] = 0
            lex.append(w)
    variants, pos = {}, 0
    for r, t in enumerate(types):
        left = len(types) - r - 1
        k = max(1, min(K, len(lex) - pos - left))
        variants[t] = lex[pos:pos + k] or [lex[-1]]
        pos += k
    w2t = {w: t for t, vs in variants.items() for w in vs}
    print(f"     （K = {K}: 型の語 {len(lex)} 種類、平文の語 {len(types)} 種類、K 個を当てた種類 "
          f"{sum(len(v) == K for v in variants.values())}）")
    half = len(caesar) // 2
    it = iter([rng.choice(variants[w]) for w in caesar[:half]])
    edge = [rng.choice(variants[w]) for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None)), variants, w2t


def boundary_dists(pt):
    first, firstp, last = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            if len(l) < 4:
                continue
            for i, (w, p) in enumerate(zip(l, positions(l))):
                last[p][w[-1]] += 1
                if i >= 1:
                    first[(p, l[i - 1][-1])][w[0]] += 1
                    firstp[p][w[0]] += 1
    return first, firstp, last


def reselect(P, variants, w2t, dists, rng):
    first, firstp, last = dists
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w, p = l[i], positions(l)[i]
                t = w2t.get(w)
                if t is None:
                    new.append(w)
                    continue
                fd = first[(p, new[-1][-1])]
                if sum(fd.values()) < 20:
                    fd = firstp[p]
                ld = last[p]
                cands = variants[t]
                wts = [(fd[c[0]] + 0.5) * (ld[c[-1]] + 0.5) for c in cands]
                new.append(rng.choices(cands, wts)[0])
            ls[li] = new
    return P


def summarize(label, runs):
    keys = SHOW + ["2語目", "-m"]
    out = []
    for k in keys:
        vals = [r[k] for r in runs]
        if k == "8量":
            out.append(f"{k} " + "/".join(v.split("/")[0] for v in vals))
        else:
            out.append(f"{k} {statistics.mean(vals):.3f}[{min(vals):.3f}〜{max(vals):.3f}]")
    print(f"  {label}: " + "  ".join(out))


def with_strength(m, P):
    s2, sm = strength([l for ls in P.values() for l in ls])
    m["2語目"], m["-m"] = s2, sm
    return m


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        G = LinkedGrammar(pt)
        C = Compat(G, pt)
        print(f"\n######## 言語 {lang} ########")
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        print("=== N45 同音異字型の符号（β 0, 種 3 通り）===")
        dists = boundary_dists(pt)
        for K in (1, 4, 8):
            runs = []
            for seed in (1, 2, 3):
                i, e, variants, w2t = homophone_source(caesar, G, K, random.Random(seed))
                P = build12(i, e, G, C, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(G))
                P = reselect(P, variants, w2t, dists, random.Random(seed + 20))
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(f"K = {K}", runs)
        print("=== N46 種 5 通りでのやり直し（N37/N40 のモデル）===")
        runs = []
        for seed in (1, 2, 3, 4, 5):
            i, e, _ = matched_source(caesar, G, random.Random(seed))
            P = build12(i, e, G, C, random.Random(seed + 10), beta=0.4, compat=True, wfun=gram_prob(G))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("N37/N40 のモデル", runs)
        print("=== N47 語の長さの歪度の分解 ===")
        r = random.Random(5)
        vw = [w for ls in pt.values() for l in ls for w in l]
        print(f"  ヴォイニッチ {lang}: {skew([len(w) for w in vw]):.2f}")
        print(f"  (i) 型から独立に選ぶ: {skew([len(G.word(r)) for _ in range(20000)]):.2f}")
        i, e, stream = matched_source(caesar, G, random.Random(3))
        print(f"  (ii) 頻度を合わせた符号表: {skew([len(w) for w in stream]):.2f}")
        for label, kw in (("(iii) ＋写し（そのまま）", dict(beta=0.0, mut=0.0, q=0.0, short_last=False)),
                          ("(iv) ＋写しで一部を替える", dict(beta=0.0, mut=0.5, q=0.0, short_last=False)),
                          ("(v) 全ての手順", dict(beta=0.4, mut=0.5))):
            i, e, _ = matched_source(caesar, G, random.Random(3))
            P = build12(i, e, G, C, random.Random(11), compat=True, wfun=gram_prob(G), **kw)
            print(f"  {label}: {skew([len(w) for ls in P.values() for l in ls for w in l]):.2f}")


if __name__ == "__main__":
    main()

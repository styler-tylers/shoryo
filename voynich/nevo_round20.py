#!/usr/bin/env python3
"""nēvo による解析 第 20 巡: N58（語頭の欄がある語・空の語の 2 通りの書き方）・N59（長さと頻度を同時に満たす割り当て）。

    python3 voynich/nevo_round20.py <Caesar>
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob  # noqa: E402
from nevo_round14 import positions  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def two_class_source(caesar, G, rng, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    headed = [w for w, _ in gen.most_common() if split(w)[0]]
    headless = [w for w, _ in gen.most_common() if not split(w)[0]]
    types = [w for w, _ in Counter(caesar).most_common()]
    variants = {}
    for r, t in enumerate(types):
        vs = []
        if r < len(headed):
            vs.append(headed[r])
        if r < len(headless):
            vs.append(headless[r])
        variants[t] = vs or [G.word(rng)]
    w2t = {w: t for t, vs in variants.items() for w in vs}
    half = len(caesar) // 2
    it = iter([rng.choice(variants[w]) for w in caesar[:half]])
    edge = [rng.choice(variants[w]) for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    print(f"     （語頭あり {len(headed)}・語頭なし {len(headless)} 種類、平文 {len(types)} 種類）")
    return (lambda: next(it, None)), (lambda: next(et, None)), variants, w2t


def choose_class(P, variants, w2t, dists, rng):
    first, firstp, last = dists
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w, p = l[i], positions(l)[i]
                t = w2t.get(w)
                if t is None or len(variants[t]) < 2:
                    new.append(w)
                    continue
                fd = first[(p, new[-1][-1])]
                if sum(fd.values()) < 20:
                    fd = firstp[p]
                cands = variants[t]
                wts = [(fd[c[0]] + 0.5) * (last[p][c[-1]] + 0.5) for c in cands]
                new.append(rng.choices(cands, wts)[0])
            ls[li] = new
    return P


def windowed_source(caesar, G, rng, W=50, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    lex = [w for w, _ in gen.most_common()]
    types = [w for w, _ in Counter(caesar).most_common()]
    while len(lex) < len(types):
        lex.append(G.word(rng))
    book = {}
    for s in range(0, len(types), W):
        ts = sorted(types[s:s + W], key=len)
        cs = sorted(lex[s:s + len(ts)], key=len)
        book.update(zip(ts, cs))
    half = len(caesar) // 2
    it = iter([book[w] for w in caesar[:half]])
    edge = [book[w] for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None))


def dshare(P):
    c = Counter(w[0] for ls in P.values() for l in ls for w in l)
    return c["d"] / sum(c.values())


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        print(f"     d- で始まる語 {dshare(pt):.1%}")
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        dists = boundary_dists(pt)
        runs, ds = [], []
        for seed in (1, 2, 3):
            i, e, variants, w2t = two_class_source(caesar, LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            P = choose_class(P, variants, w2t, dists, random.Random(seed + 20))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
            ds.append(dshare(P))
        summarize("N58 語頭あり・なしの 2 通り", runs)
        print(f"     d- で始まる語 {sum(ds) / 3:.1%}（{min(ds):.1%}〜{max(ds):.1%}）", flush=True)
        G = LinkedGrammar(pt)
        C = Compat(G, pt)
        runs = []
        for seed in (1, 2):
            i, e = windowed_source(caesar, G, random.Random(seed))
            P = build12(i, e, G, C, random.Random(seed + 10), beta=0.4, compat=True, wfun=gram_prob(G))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("N59 窓の中で長さをそろえる", runs)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 15 巡: N42（位置と境目を同時に決める）・N43（言語 A の行をまたぐつながりの分解）。

    python3 voynich/nevo_round15.py <Caesar>
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import KEYS, measure, show, split  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import pos_dists, positions, strength  # noqa: E402


def joint_dist(pt):
    j = defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            if len(l) < 4:
                continue
            for i, (w, p) in enumerate(zip(l, positions(l))):
                if i >= 1:
                    j[(p, l[i - 1][-1])][split(w)[0]] += 1
    return j


def apply_joint(P, G, j, hd, ed, gamma, rng):
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w, p = l[i], positions(l)[i]
                h, m, e = split(w)
                if rng.random() < gamma:
                    dist = j[(p, new[-1][-1])]
                    if sum(dist.values()) < 5:
                        dist = hd[p]
                    hs = [x for x in dist if G.mh[x][m] > 0] or [h]
                    h = rng.choices(hs, [dist[x] + 0.01 for x in hs])[0]
                    if p == "行の最後":
                        key = m[-1] if m else ("H",) + h
                        es = [x for x in ed[p] if G.em[key][x] > 0] or [e]
                        e = rng.choices(es, [ed[p][x] + 0.01 for x in es])[0]
                new.append((h + m + e) or w)
            ls[li] = new
    return P


lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def n42(V, caesar, rng):
    print("=== N42 位置と境目を同時に決めるモデル ===")
    print(f"  {'':<26}" + " ".join(f"{k:>7}" for k in KEYS))
    for lang in ("A", "B"):
        pt = V[lang][0]
        G, C = LinkedGrammar(pt), Compat(LinkedGrammar(pt), pt)
        C.G = G
        hd, ed = pos_dists(pt)
        j = joint_dist(pt)
        show(f"ヴォイニッチ {lang}", measure(pt, V[lang][2], rng))
        s2, sm = strength([l for ls in pt.values() for l in ls])
        print(f"     位置の型: 2 語目 sh/ch {s2:.0%}、行の最後 -m {sm:.1%}")
        for gamma in (0.4, 0.7):
            i, e, _ = matched_source(caesar, G, random.Random(3))
            P = build12(i, e, G, C, random.Random(11), beta=0.0, compat=True, wfun=gram_prob(G))
            P = apply_joint(P, G, j, hd, ed, gamma, random.Random(23))
            show(f"モデル {lang} γ = {gamma}", measure(P, lastf(P), rng))
            s2, sm = strength([l for ls in P.values() for l in ls])
            print(f"     位置の型: 2 語目 sh/ch {s2:.0%}、行の最後 -m {sm:.1%}")


def n43(V, caesar, rng):
    print("\n=== N43 言語 A のモデルの行をまたぐつながり（またぐ − 基準）===")
    pt = V["A"][0]
    G = LinkedGrammar(pt)
    C = Compat(G, pt)
    r0 = line_unit.l1(list(pt.items()), lambda w: "".join(w[-2:]), lambda w: "".join(w[:2]), rng)
    print(f"  ヴォイニッチ A: {r0['行をまたぐ'] - r0['無関係']:+.3f}")
    variants = [("(a) そのまま", {}, False), ("(b) 行頭の印なし", {"q": 0.0}, False),
                ("(c) 行末を短い方から選ばない", {"short_last": False}, False),
                ("(d) 端の語を型から独立に", {}, True), ("(e) 写しなし", {"c": 0.0}, False),
                ("(f) 境目の規則なし", {"beta": 0.0}, False)]
    for label, kw, indep in variants:
        vals = []
        for seed in (1, 2, 3):
            i, e, _ = matched_source(caesar, G, random.Random(seed))
            if indep:
                r = random.Random(seed + 50)
                e = lambda r=r: G.word(r)  # noqa: E731
            args = dict(beta=0.4, compat=True, wfun=gram_prob(G))
            args.update(kw)
            P = build12(i, e, G, C, random.Random(seed + 10), **args)
            rr = line_unit.l1(list(P.items()), lambda w: "".join(w[-2:]), lambda w: "".join(w[:2]), rng)
            vals.append(rr["行をまたぐ"] - rr["無関係"])
        print(f"  {label:<28} " + "  ".join(f"{v:+.3f}" for v in vals) + f"   平均 {sum(vals) / 3:+.3f}")


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    n42(V, caesar, rng)
    n43(V, caesar, rng)


if __name__ == "__main__":
    main()

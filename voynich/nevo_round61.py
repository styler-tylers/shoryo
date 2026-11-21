#!/usr/bin/env python3
"""nēvo による解析 第 61 巡: N181（長い芯の中身）・N182（モデルと頁の 1 行目）・N183（行をまたぐ量の順位）。

    python3 voynich/nevo_round61.py
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from line_unit import mi  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round59 import GALLOWS, flagged, pval  # noqa: E402

G_ALL = {"k", "t", "p", "f", "ckh", "cth", "cph", "cfh"}
G_PAR = {"p", "f", "cph", "cfh"}


def cores(ls):
    return [g for l in ls for w in l for g in split(w)[1]]


def share(ls, S):
    c = cores(ls)
    return sum(g in S for g in c) / len(c)


def nongal_len(ls):
    return statistics.mean(sum(g not in G_ALL for g in split(w)[1]) for l in ls for w in l)


def core_len(ls):
    return statistics.mean(len(split(w)[1]) for l in ls for w in l)


def gstart(ls):
    return statistics.mean(w[0] in GALLOWS for l in ls for w in l)


def obs_mi(F):
    e2, h2 = (lambda w: "".join(w[-2:])), (lambda w: "".join(w[:2]))
    pairs = []
    for v in F.values():
        v = [(l, st) for l, st in v if l]
        for i in range(len(v) - 1):
            if not v[i + 1][1]:
                pairs.append((e2(v[i][0][-1]), h2(v[i + 1][0][0])))
    return mi(pairs)


def shuffle_keep_starts(F, r):
    out = {}
    for pg, v in F.items():
        idx = [k for k, (_, st) in enumerate(v) if not st]
        moved = r.sample([v[k] for k in idx], len(idx))
        nv = list(v)
        for k, x in zip(idx, moved):
            nv[k] = x
        out[pg] = nv
    return out


def rank(F, r, runs=200):
    o = obs_mi(F)
    xs = [obs_mi(shuffle_keep_starts(F, r)) for _ in range(runs)]
    return sum(x < o for x in xs) / runs


def main():
    V = voynich()
    rng = random.Random(2026)
    print("=== N181 長い芯の中身 ===", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        first = [l for v in F.values() for l, st in v if st and l]
        other = [l for v in F.values() for l, st in v if not st and l]
        print(f"  ---- 言語 {lang}", flush=True)
        for name, f in (("芯の中の絞首台", lambda ls: share(ls, G_ALL)), ("段落の頭の絞首台", lambda ls: share(ls, G_PAR)),
                        ("絞首台を除いた芯の字形の数", nongal_len)):
            o, b, p = pval(first, other, f, rng)
            print(f"    {name:<16} 最初の行 {o:.4f}  それ以外 {b:.4f}  比 {o / b:.2f}  p {p:.3f}", flush=True)
        cf, co = Counter(cores(first)), Counter(cores(other))
        nf, no = sum(cf.values()), sum(co.values())
        d = sorted(set(cf) | set(co), key=lambda g: -abs(cf[g] / nf - co[g] / no))[:8]
        print("    芯の字形の割合の差の上位: " + "、".join(f"{g} {cf[g] / nf:.1%}/{co[g] / no:.1%}" for g in d), flush=True)

    print("=== N182 モデルと頁の 1 行目 ===", flush=True)
    models = {}
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        p_ = V[lang][0]
        LG = LengthGrammar(p_)
        M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=sum(len(l) for ls in p_.values() for l in ls), **kw)
        models[lang] = M
        for name, P in ((f"ヴォイニッチ {lang}", p_), (f"モデル {lang}", M)):
            first = [ls[0] for ls in P.values() if ls and ls[0]]
            other = [l for ls in P.values() for l in ls[1:] if l]
            o, b, p = pval(first, other, core_len, rng)
            g1, g0 = gstart(first), gstart(other)
            print(f"  {name:<14} 頁の 1 行目 {len(first)}  芯の長さ {o:.3f}／{b:.3f}（差 {o - b:+.3f}, p {p:.3f}）  絞首台で始まる語 {g1:.1%}／{g0:.1%}（比 {g1 / g0:.2f}）", flush=True)

    print("=== N183 行をまたぐ量の順位 ===", flush=True)
    r = random.Random(7)
    checks = []
    for s_ in range(20):
        F = shuffle_keep_starts(flagged(V, "B"), random.Random(100 + s_))
        checks.append(rank(F, r, runs=100))
    print(f"  確かめ（並べ替えた頁を本物と見なす, 言語 B, 20 回）: 順位の平均 {statistics.mean(checks):.2f}（{min(checks):.2f}〜{max(checks):.2f}）  "
          f"{'通る' if 0.35 <= statistics.mean(checks) <= 0.65 else '通らない'}", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        FM = {pg: [(l, j == 0) for j, l in enumerate(ls)] for pg, ls in models[lang].items()}
        for name, G in ((f"ヴォイニッチ {lang}", F), (f"モデル {lang}", FM)):
            k = rank(G, r)
            print(f"  {name:<14} 順位 {k:.3f}  {'0.05〜0.95 の中' if 0.05 <= k <= 0.95 else '外'}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 60 巡: N178（段落の最初の行の長い語）・N179（言語 B の段落の最初の行の語末）・N180（直した「またぐ」）。

    python3 voynich/nevo_round60.py
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
from nevo_round59 import GALLOWS, draw, flagged, pval, shuffled  # noqa: E402


def matagu(F, rng, runs=50):
    e2, h2 = (lambda w: "".join(w[-2:])), (lambda w: "".join(w[:2]))
    obs, pools = [], []
    for v in F.values():
        v = [(l, st) for l, st in v if l]
        cand = [k for k in range(len(v)) if not v[k][1]]
        for i in range(len(v) - 1):
            if v[i + 1][1]:
                continue
            o = [k for k in cand if k != i + 1]
            if not o:
                continue
            obs.append((e2(v[i][0][-1]), h2(v[i + 1][0][0])))
            pools.append([h2(v[k][0][0]) for k in o])
    m = mi(obs)
    nul = [mi([(a, rng.choice(p)) for (a, _), p in zip(obs, pools)]) for _ in range(runs)]
    return m - statistics.mean(nul)


def main():
    V = voynich()
    rng = random.Random(2026)
    print("=== N178 段落の最初の行の長い語 ===", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        first = [l for v in F.values() for l, st in v if st and l]
        other = [l for v in F.values() for l, st in v if not st and l]
        print(f"  ---- 言語 {lang}", flush=True)
        fs = [("語全体", lambda ls: statistics.mean(len(w) for l in ls for w in l))]
        fs += [(n, lambda ls, k=k: statistics.mean(len(split(w)[k]) for l in ls for w in l)) for k, n in enumerate(("語頭", "芯", "語末"))]
        fs.append(("絞首台で始まる語を除く", lambda ls: statistics.mean([len(w) for l in ls for w in l if w[0] not in GALLOWS])))
        for name, f in fs:
            o, b, p = pval(first, other, f, rng)
            print(f"    {name:<12} 最初の行 {o:.3f}  それ以外 {b:.3f}  差 {o - b:+.3f}  p {p:.3f}", flush=True)

    print("=== N179 言語 B の段落の最初の行の語末 ===", flush=True)
    F = flagged(V, "B")
    first = [l for v in F.values() for l, st in v if st and l]
    other = [l for v in F.values() for l, st in v if not st and l]
    share = lambda ls: (lambda c: {k: x / sum(c.values()) for k, x in c.items()})(Counter("".join(split(w)[2]) or "（なし）" for l in ls for w in l))  # noqa: E731
    sf, so = share(first), share(other)
    keys = set(sf) | set(so)
    diff = {k: sf.get(k, 0) - so.get(k, 0) for k in keys}
    n = sum(map(len, first))
    null = {k: [] for k in keys}
    for _ in range(1000):
        sx = share(draw(other, n, rng))
        for k in keys:
            null[k].append(abs(sx.get(k, 0) - so.get(k, 0)))
    tot = sum(abs(v) for v in diff.values())
    top = sorted(keys, key=lambda k: -abs(diff[k]))
    for k in top[:10]:
        q = sorted(null[k])[974]
        print(f"  {k:<8} 最初の行 {sf.get(k, 0):.1%}  それ以外 {so.get(k, 0):.1%}  差 {diff[k]:+.1%}  {'＊' if abs(diff[k]) > q else ''}", flush=True)
    print(f"  上位 3 つの割合 {sum(abs(diff[k]) for k in top[:3]) / tot:.0%}（差の絶対値の合計 {tot:.1%}）", flush=True)

    print("=== N180 直した「またぐ」 ===", flush=True)
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        F = flagged(V, lang)
        p_ = V[lang][0]
        LG = LengthGrammar(p_)
        M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=sum(len(l) for ls in p_.values() for l in ls), **kw)
        FM = {pg: [(l, j == 0) for j, l in enumerate(ls)] for pg, ls in M.items()}
        for name, G in ((f"ヴォイニッチ {lang}", F), (f"モデル {lang}", FM)):
            ctrl = sorted(matagu(shuffled(G, s_), random.Random(5)) for s_ in range(20))
            lo, hi = ctrl[1], ctrl[18]
            v = matagu(G, random.Random(5))
            print(f"  {name:<14} 対照 {lo:+.4f}〜{hi:+.4f}（{'0 を含む' if lo <= 0 <= hi else '0 を含まない'}）  値 {v:+.4f}  {'対照の中' if lo <= v <= hi else '対照の外'}", flush=True)


if __name__ == "__main__":
    main()

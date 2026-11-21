#!/usr/bin/env python3
"""nēvo による解析 第 59 巡: N175（文字だけの頁の欄の長さ）・N176（段落の最初の行）・N177（過去の行をまたぐ量の点検）。

    python3 voynich/nevo_round59.py
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from line_unit import mi as mi_pairs  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import skew, split  # noqa: E402
from nevo_round40 import joint, mi as mi_joint, top_k  # noqa: E402
from nevo_round54 import js  # noqa: E402

GALLOWS = {"p", "t", "k", "f"}


def flagged(V, lang):
    """{頁: [(行, 段落の最初か)]}"""
    pt, _, last = V[lang]
    out, i, prev = {}, 0, True
    for pg, ls in pt.items():
        out[pg] = []
        for j, l in enumerate(ls):
            out[pg].append((l, prev or j == 0))
            prev = last[i]
            i += 1
    return out


def shuffled(F, seed):
    r = random.Random(seed)
    return {pg: r.sample(v, len(v)) for pg, v in F.items()}


# ---------------------------------------------------------------- (1) l1 の「またぐ」
def l1x(F, exclude, rng, runs=50):
    end_fn, head_fn = (lambda w: "".join(w[-2:])), (lambda w: "".join(w[:2]))
    cross, firsts = [], {}
    for pg, v in F.items():
        for (a, _), (b, sb) in zip(v, v[1:]):
            if a and b and not (exclude and sb):
                cross.append((pg, end_fn(a[-1]), head_fn(b[0])))
        firsts[pg] = [head_fn(l[0]) for l, st in v if l and not (exclude and st)]
    pages = [p for p in firsts if firsts[p]]
    m_cross = mi_pairs([(a, b) for _, a, b in cross])
    nul = []
    for _ in range(runs):
        nul.append(mi_pairs([(a, rng.choice(firsts[rng.choice([p for p in pages if p != pg])])) for pg, a, _ in cross]))
    return m_cross - statistics.mean(nul)


# ---------------------------------------------------------------- (2) 第 40 巡の cross
def cross40x(F, exclude, rng, runs=200):
    words = [w for v in F.values() for l, _ in v for w in l]
    cls = top_k(words, 30)
    ids = {}
    pages = [[([ids.setdefault(cls(w), len(ids)) for w in l], st) for l, st in v if len(l) >= 3] for v in F.values()]
    pages = [p for p in pages if len(p) >= 3]
    K = len(ids) + 1
    A, B, owner = [], [], []
    firsts = []
    for pi, p in enumerate(pages):
        firsts.append([l[0] for l, st in p if not (exclude and st)] or [l[0] for l, _ in p])
        for i in range(len(p) - 1):
            if exclude and p[i + 1][1]:
                continue
            A.append(p[i][0][-1])
            B.append(p[i + 1][0][0])
            owner.append(pi)
    a, b = np.array(A), np.array(B)
    obs = mi_joint(joint(a, b, K))
    nul = [mi_joint(joint(a, np.array([rng.choice(firsts[pi]) for pi in owner]), K)) for _ in range(runs)]
    return obs - float(np.mean(nul)), (obs - float(np.mean(nul))) / float(np.std(nul))


# ---------------------------------------------------------------- (3) 第 47 巡の crossing
def crossingx(F, exclude, rng, runs=20):
    obs, nul = [], [[] for _ in range(runs)]
    for v in F.values():
        v = [(l, st) for l, st in v if l]
        cand = [k for k in range(len(v)) if not (exclude and v[k][1])]
        for i in range(len(v) - 1):
            if exclude and v[i + 1][1]:
                continue
            o = [k for k in cand if k != i + 1]
            if not o:
                continue
            obs.append((v[i][0][-1][-1], v[i + 1][0][0][0]))
            for r in range(runs):
                nul[r].append((v[i][0][-1][-1], v[rng.choice(o)][0][0][0]))
    return mi_pairs(obs) - statistics.mean(mi_pairs(x) for x in nul)


def sk(lines_):
    return skew([len(w) for l in lines_ for w in l])


def mean_len(lines_):
    return statistics.mean(len(w) for l in lines_ for w in l)


def draw(pool, n, rng):
    out, c = [], 0
    for l in rng.sample(pool, len(pool)):
        if c >= n:
            break
        out.append(l)
        c += len(l)
    return out


def pval(target, pool, f, rng, runs=1000):
    o = f(target)
    n = sum(map(len, target))
    return o, f(pool), sum(f(draw(pool, n, rng)) >= o for _ in range(runs)) / runs


def main():
    V = voynich()
    a = corpus.make_parser("").parse_args([])
    a.locus = "P"
    _, L = corpus.load_lines(a)
    ill = {ln.page.name: ln.page.get("I") for ln in L}
    rng = random.Random(2026)

    print("=== N175 文字だけの頁の欄の長さ ===", flush=True)
    pt = V["B"][0]
    T = [l for pg, ls in pt.items() if ill[pg] == "T" for l in ls]
    Pp = [l for pg, ls in pt.items() if ill[pg] != "T" for l in ls]
    for k, name in ((None, "語全体"), (0, "語頭"), (1, "芯"), (2, "語末")):
        f = (lambda ls: mean_len(ls)) if k is None else (lambda ls, k=k: statistics.mean(len(split(w)[k]) for l in ls for w in l))
        o, b, p = pval(T, Pp, f, rng)
        print(f"  {name:<4} 文字だけ {o:.3f}  図のある頁 {b:.3f}  差 {o - b:+.3f}  p {p:.3f}", flush=True)

    print("=== N176 段落の最初の行 ===", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        first = [l for v in F.values() for l, st in v if st and l]
        other = [l for v in F.values() for l, st in v if not st and l]
        print(f"  ---- 言語 {lang}: 段落の最初の行 {len(first)}（{sum(map(len, first))} 語）、それ以外 {len(other)}", flush=True)
        for name, f in (("語の長さの平均", mean_len), ("歪度", sk),
                        ("絞首台で始まる語", lambda ls: statistics.mean(w[0] in GALLOWS for l in ls for w in l))):
            o, b, p = pval(first, other, f, rng)
            print(f"    {name:<10} 最初の行 {o:.3f}  それ以外 {b:.3f}  p {p:.3f}", flush=True)
        endc = lambda ls: Counter("".join(split(w)[2]) for l in ls for w in l)  # noqa: E731
        d = js(endc(first), endc(other))
        n = sum(map(len, first))
        null = []
        for _ in range(1000):
            x = draw(other, n, rng)
            y = draw(other, n, rng)
            null.append(js(endc(x), endc(y)))
        null.sort()
        print(f"    語末の欄の差 {d:.4f} ビット  それ以外どうしの 97.5% {null[974]:.4f}  {'超える' if d > null[974] else '超えない'}", flush=True)

    print("=== N177 過去の行をまたぐ量の点検 ===", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        print(f"  ---- 言語 {lang}", flush=True)
        for name, fn in (("(1) またぐ（l1）", lambda F_, ex: l1x(F_, ex, random.Random(5))),
                         ("(2) 第 40 巡 cross", lambda F_, ex: cross40x(F_, ex, random.Random(5))[0]),
                         ("(3) 第 47 巡 crossing", lambda F_, ex: crossingx(F_, ex, random.Random(5)))):
            ctrl = sorted(fn(shuffled(F, s_), True) for s_ in range(20))
            lo, hi = ctrl[1], ctrl[18]
            orig, fixed = fn(F, False), fn(F, True)
            print(f"    {name:<20} 対照（直した量, 5〜95%）{lo:+.4f}〜{hi:+.4f}  {'0 を含む' if lo <= 0 <= hi else '0 を含まない'}"
                  f"  | 元 {orig:+.4f}  直した {fixed:+.4f}  差 {fixed - orig:+.4f}  {'対照の中' if lo <= fixed <= hi else '対照の外'}", flush=True)


if __name__ == "__main__":
    main()

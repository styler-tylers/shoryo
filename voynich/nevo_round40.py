#!/usr/bin/env python3
"""nēvo による解析 第 40 巡（第 4 段の 2 巡目）: N118（1 つ飛びの独立）・N119（モデルのどの部品が作るか）・N120（行をまたぐ結び付き）。

    python3 voynich/nevo_round40.py n118|n120 <langs の場所> <langs3 の場所>
    python3 voynich/nevo_round40.py n119
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402


def mi(J):
    n = J.sum()
    if n == 0:
        return 0.0
    P = J / n
    E = np.outer(P.sum(1), P.sum(0))
    m = P > 0
    return float((P[m] * np.log2(P[m] / E[m])).sum())


def stats3(lines, K):
    """lines: 種類の番号の行のリスト。隣どうし・1 つ飛び・鎖で説明できる分。"""
    AB, AC, BC = np.zeros((K, K)), np.zeros((K, K)), np.zeros((K, K))
    for l in lines:
        if len(l) >= 3:
            a = np.asarray(l)
            np.add.at(AB, (a[:-2], a[1:-1]), 1)
            np.add.at(AC, (a[:-2], a[2:]), 1)
            np.add.at(BC, (a[1:-1], a[2:]), 1)
    rs = BC.sum(1, keepdims=True)
    rs[rs == 0] = 1
    return mi(AB), mi(AC), mi(AB @ (BC / rs))


def excess(lines, K, rng, shuf=5):
    obs = np.array(stats3(lines, K))
    nul = np.zeros(3)
    for _ in range(shuf):
        nul += np.array(stats3([rng.sample(l, len(l)) for l in lines], K))
    adj, skp, ch = obs - nul / shuf
    return adj, skp, skp - ch


def boot(f, lines, rng, B=100):
    vals = np.array([f([lines[rng.randrange(len(lines))] for _ in lines]) for _ in range(B)])
    return np.percentile(vals, [2.5, 97.5], axis=0)


CLASSERS = {
    "上位 30 語": lambda words, kind: top_k(words, 30),
    "上位 100 語": lambda words, kind: top_k(words, 100),
    "語の両端": lambda words, kind: (lambda w: (split(w)[0], split(w)[2])) if kind == "v" else (lambda w: (w[0], w[-1])),
}


def top_k(words, k):
    top = {w for w, _ in Counter(words).most_common(k)}
    return lambda w: w if w in top else None


def coded_lines(P, cls):
    ids = {}
    inner = [[ids.setdefault(cls(w), len(ids)) for w in l[1:-1]] for ls in P.values() for l in ls if len(l) >= 5]
    return inner, len(ids)


def report118(name, P, kind, rng):
    words = [w for ls in P.values() for l in ls for w in l]
    out = []
    for cname, mk in CLASSERS.items():
        inner, K = coded_lines(P, mk(words, kind))
        adj, skp, ex = excess(inner, K, rng)
        lo, hi = boot(lambda ls: excess(ls, K, rng, shuf=3)[2], inner, rng)
        out.append((lo, hi))
        print(f"  {name:<30} {cname:<8} 隣どうし {adj:+.4f}  1 つ飛び {skp:+.4f}  余り {ex:+.4f}［{lo:+.4f}〜{hi:+.4f}］", flush=True)
    return out


def natural(base, base3, cap):
    files = {"Caesar（ラテン語）": base / "pg218.txt", "Descartes（ラテン語）": base / "pg23306.txt", "Dante（イタリア語）": base / "pg1012.txt",
             "Culpeper（英語）": base3 / "pg49513.txt", "ウェールズ語": base3 / "pg67424.txt", "アイルランド語": base3 / "pg50913.txt"}
    return {k: [tuple(w) for w in words_any(p)[:cap]] for k, p in files.items()}


def n118(base, base3):
    V = voynich()
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        nat = natural(base, base3, cap)
        res = {}
        for name, ws in nat.items():
            print(f"  （{name}: {len(ws)} 語）", flush=True)
            res[name] = report118(name, dict(line_unit.wrap(ws, 37)), "n", rng)
        LG = LengthGrammar(pt)
        caesar = ["".join(w) for w in natural(base, base3, 30000)["Caesar（ラテン語）"]]
        _, _, coded = matched_source(caesar, LG, random.Random(1))
        res["符号表だけ"] = report118("符号表だけ（Caesar）", dict(line_unit.wrap(coded[:cap], 37)), "v", rng)
        v = report118(f"ヴォイニッチ {lang}", pt, "v", rng)
        ok = [v[i][0] <= 0 and all(r[i][0] > 0 for r in res.values()) for i in range(3)]
        print(f"  → 分け方ごとの判定（ヴォイニッチの幅が 0 を含み、平文ありの全てで下の端 > 0）: {ok}  {'確かめられた' if sum(ok) >= 2 else '確かめられない'}", flush=True)
        for i, cname in enumerate(CLASSERS):
            bad = [k for k, r in res.items() if r[i][0] <= 0]
            print(f"     {cname}: ヴォイニッチ［{v[i][0]:+.4f}〜{v[i][1]:+.4f}］  下の端が 0 以下の平文あり: {bad or 'なし'}", flush=True)
        Pc = dict(line_unit.wrap(nat["Caesar（ラテン語）"], 37))
        r2 = random.Random(5)
        rot = {k: [(lambda l, j: l[j:] + l[:j])(l, r2.randrange(len(l))) for l in ls] for k, ls in Pc.items()}
        report118("Caesar・行ごとに並びを回す", rot, "n", rng)
        half = {k: [l[::2] for l in ls] for k, ls in dict(line_unit.wrap(nat["Caesar（ラテン語）"], 74)).items()}
        report118("Caesar・語を 1 つおきに抜く", half, "n", rng)


def n119():
    V = voynich()
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = {"A": 0.4, "B": 0.6}[lang]
        kw = dict(mark=0.25) if lang == "A" else dict(mark=0.12, live=True)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        for name, over in (("基準", {}), ("写しなし", dict(c=0.0)), ("言い回しのくり返しなし", dict(mu=0.0)), ("行の並びを回さない", dict(rot=False))):
            for seed in (1, 2):
                P = build34(LG, LC, pt, random.Random(seed), **{**dict(c=c, cap=cap), **kw, **over})
                words = [w for ls in P.values() for l in ls for w in l]
                inner, K = coded_lines(P, top_k(words, 30))
                adj, skp, ex = excess(inner, K, rng)
                lo, hi = boot(lambda ls: excess(ls, K, rng, shuf=3)[2], inner, rng)
                print(f"  {name:<14} 種 {seed}: 隣どうし {adj:+.4f}  1 つ飛び {skp:+.4f}  余り {ex:+.4f}［{lo:+.4f}〜{hi:+.4f}］", flush=True)


def cross(P, rng, B=100, shuf=20):
    words = [w for ls in P.values() for l in ls for w in l]
    cls = top_k(words, 30)
    ids = {}
    pages = [[[ids.setdefault(cls(w), len(ids)) for w in l] for l in ls if len(l) >= 3] for ls in P.values()]
    pages = [p for p in pages if len(p) >= 3]
    K = len(ids)
    pairs = [(p[i][-1], p[i + 1][0], pi) for pi, p in enumerate(pages) for i in range(len(p) - 1)]
    firsts = [[l[0] for l in p] for p in pages]

    def val(sample):
        J = np.zeros((K, K))
        for a, b, _ in sample:
            J[a, b] += 1
        nul = 0.0
        for _ in range(shuf):
            N = np.zeros((K, K))
            for a, _, pi in sample:
                N[a, rng.choice(firsts[pi])] += 1
            nul += mi(N)
        return mi(J) - nul / shuf

    v = val(pairs)
    bs = [val([pairs[rng.randrange(len(pairs))] for _ in pairs]) for _ in range(B)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    inner = [l for p in pages for l in p]
    adj = excess(inner, K, rng)[0]
    return v, lo, hi, adj


def n120(base, base3):
    V = voynich()
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = {"A": 0.4, "B": 0.6}[lang]
        kw = dict(mark=0.25) if lang == "A" else dict(mark=0.12, live=True)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        groups = {"平文あり": [], "平文なし": []}
        for name, ws in natural(base, base3, cap).items():
            groups["平文あり"].append((name, dict(line_unit.wrap(ws, 37))))
        caesar = ["".join(w) for w in natural(base, base3, 30000)["Caesar（ラテン語）"]]
        _, _, coded = matched_source(caesar, LG, random.Random(1))
        groups["平文あり"].append(("符号表だけ（Caesar）", dict(line_unit.wrap(coded[:cap], 37))))
        it = iter(coded)
        src = lambda: next(it, None)  # noqa: E731
        groups["平文あり"].append(("平文ありのモデル（符号表＋写し）", build12(src, src, LG, LC, random.Random(11), c=0.4, beta=0.0, compat=True, wfun=gram_prob(LG), cap=cap)))
        for seed in (1, 2):
            groups["平文なし"].append((f"最良のモデル 種 {seed}", build34(LG, LC, pt, random.Random(seed), c=c, cap=cap, **kw)))
        vals = {}
        for g, ps in groups.items():
            vals[g] = []
            for name, P in ps:
                v, lo, hi, adj = cross(P, rng)
                vals[g].append(v)
                print(f"  {g}・{name:<28} 行をまたぐ {v:+.4f}［{lo:+.4f}〜{hi:+.4f}］  行の中の隣どうし {adj:+.4f}", flush=True)
        v, lo, hi, adj = cross(pt, rng)
        print(f"  ヴォイニッチ {lang:<32} 行をまたぐ {v:+.4f}［{lo:+.4f}〜{hi:+.4f}］  行の中の隣どうし {adj:+.4f}", flush=True)
        a, b = vals["平文あり"], vals["平文なし"]
        gap = max(min(a) - max(b), min(b) - max(a))
        spread = max(max(a) - min(a), max(b) - min(b))
        print(f"  → 平文あり {min(a):+.4f}〜{max(a):+.4f}  平文なし {min(b):+.4f}〜{max(b):+.4f}  すき間 {gap:+.4f}  広がり {spread:.4f}  {'分かれた' if gap > 0 and gap > spread else '分かれない'}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "n119":
        n119()
    else:
        {"n118": n118, "n120": n120}[sys.argv[1]](Path(sys.argv[2]), Path(sys.argv[3]))

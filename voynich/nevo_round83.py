#!/usr/bin/env python3
"""nēvo による解析 第 83 巡: N242（言語 A と B の違いと節の違いの大きさ）・N243（書き手 2 と 5）。第 270 節の事前の登録どおり。

    python3 voynich/nevo_round83.py
"""
import random, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round82 import pages  # noqa: E402


def cos(a, b):
    return 1 - a @ b / (np.linalg.norm(a) * np.linalg.norm(b))


def strength(A, B):
    ca, cb = A.mean(0), B.mean(0)
    within = np.mean([cos(x, ca) for x in A] + [cos(x, cb) for x in B])
    return cos(ca, cb) / within


def loo(X, lab, rng, nperm=2000):
    names = sorted(set(lab))

    def bacc(lab):
        pred = []
        for i in range(len(X)):
            m = np.ones(len(X), bool); m[i] = False
            pred.append(max(names, key=lambda g: -cos(X[i], X[m & (lab == g)].mean(0))))
        pred = np.array(pred)
        return np.mean([(pred[lab == g] == g).mean() for g in names])
    a0 = bacc(lab); cnt = 0
    for _ in range(nperm):
        p = lab.copy(); rng.shuffle(p); cnt += bacc(p) >= a0 - 1e-12
    return a0, (cnt + 1) / (nperm + 1)


def main():
    W, meta = pages()
    by = defaultdict(list)
    for p, k in meta.items():
        by[k].append(p)
    h1 = sorted(random.Random(2032).sample(sorted(by[("1", "A", "H")]), 20))
    G = {"A本草": h1, "B本草": sorted(by[("2", "B", "H")]), "B生物": sorted(by[("2", "B", "B")]), "A薬学": sorted(by[("1", "A", "P")])}
    allp = [p for v in G.values() for p in v]
    top = [w for w, _ in Counter(w for p in allp for w in W[p]).most_common(100)]
    vec = lambda p: np.array([Counter(W[p])[w] for w in top], float) / max(1, sum(Counter(W[p])[w] for w in top))  # noqa: E731
    M = {g: np.array([vec(p) for p in v]) for g, v in G.items()}
    pairs = {"(i) 言語 A と B（本草）": ("A本草", "B本草"), "(ii) B の中の節（本草と生物）": ("B本草", "B生物"), "(iii) A の中の節（本草と薬学）": ("A本草", "A薬学")}
    print("=== N242 分かれの強さ ===")
    val = {k: strength(M[a], M[b]) for k, (a, b) in pairs.items()}
    for k, v in val.items():
        print(f"  {k:<26} {v:.3f}")
    rng = np.random.default_rng(2033)
    boot = defaultdict(list)
    for _ in range(2000):
        R = {g: m[rng.integers(0, len(m), len(m))] for g, m in M.items()}
        s = {k: strength(R[a], R[b]) for k, (a, b) in pairs.items()}
        ks = list(pairs)
        boot["(i)−(ii)"].append(s[ks[0]] - s[ks[1]]); boot["(i)−(iii)"].append(s[ks[0]] - s[ks[2]])
    for k, v in boot.items():
        lo, hi = np.percentile(v, [2.5, 97.5])
        print(f"  差 {k}: {np.mean(v):+.3f}  95% 区間 {lo:+.3f}〜{hi:+.3f}  {'0 を含まない' if lo > 0 or hi < 0 else '0 を含む'}")
    print("=== N243 書き手 2 と 5（本草, B）、対照に 2 と 3 ===")
    gl = {p: [g for w in W[p] for g in ivtff.glyphs(w)] for p in by[("2", "B", "H")] + by[("5", "B", "H")] + by[("3", "B", "H")]}

    def feats(ps, kind):
        if kind == "字形の頻度":
            top = [g for g, _ in Counter(g for p in ps for g in gl[p]).most_common(30)]
            return np.array([[Counter(gl[p])[g] for g in top] for p in ps], float)
        if kind == "語の欄の形":
            sp = {p: [split(tuple(ivtff.glyphs(w))) for w in W[p]] for p in ps}
            hs = [h for h, _ in Counter(tuple(x[0]) for p in ps for x in sp[p]).most_common(15)]
            es = [e for e, _ in Counter(tuple(x[2]) for p in ps for x in sp[p]).most_common(15)]
            return np.array([[sum(tuple(x[0]) == h for x in sp[p]) for h in hs] + [sum(tuple(x[2]) == e for x in sp[p]) for e in es] for p in ps], float)
        return np.array([[sum(len(ivtff.glyphs(w)) == L for w in W[p]) for L in range(1, 11)] for p in ps], float)
    for hb in ("5", "3"):
        ps = sorted(by[("2", "B", "H")]) + sorted(by[(hb, "B", "H")])
        lab = np.array(["2"] * len(by[("2", "B", "H")]) + [hb] * len(by[(hb, "B", "H")]))
        for kind in ("字形の頻度", "語の欄の形", "語の長さの分布"):
            X = feats(ps, kind); X = X / X.sum(1, keepdims=True)
            a, p = loo(X, lab, random.Random(2032))
            print(f"  書き手 2 と {hb}  {kind:<8} 正答率 {a:.3f}  並べ替えの p {p:.4f}", flush=True)


if __name__ == "__main__":
    main()

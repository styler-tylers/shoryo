#!/usr/bin/env python3
"""第 86 巡の事後の点検: 分かれの強さの「戻して選び直す」区間は、同じ頁が重なって組の中の距離が縮み、強さを大きく見せる。
戻さずに 7 割の頁を選ぶ（2,000 回）区間で、第 83〜86 巡の比べ方を確かめ直す。

    python3 voynich/nevo_round86_posthoc.py
"""
import random, sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round83 import strength  # noqa: E402
from nevo_round85 import fol, pages_q  # noqa: E402


def sub(X, rng, f=0.7):
    k = max(2, int(round(len(X) * f)))
    return X[rng.choice(len(X), k, replace=False)]


def words_mat(groups, W):
    allp = [p for g in groups for p in g]
    top = [w for w, _ in Counter(w for p in allp for w in W[p]).most_common(100)]
    M = lambda ps: np.array([[Counter(W[p])[w] for w in top] for p in ps], float) / np.array([[max(1, sum(Counter(W[p])[w] for w in top))] for p in ps])  # noqa: E731
    return [M(g) for g in groups]


def show(name, pairs, n=2000, seed=2040):
    """pairs: {名: (XA, XB)}。点の値と、戻さない 7 割の区間、と組どうしの差"""
    rng = np.random.default_rng(seed)
    R = {k: [] for k in pairs}
    for _ in range(n):
        for k, (a, b) in pairs.items():
            R[k].append(strength(sub(a, rng), sub(b, rng)))
    print(f"--- {name}")
    for k, (a, b) in pairs.items():
        lo, hi = np.percentile(R[k], [2.5, 97.5])
        print(f"  {k:<34} 点 {strength(a, b):.3f}  7 割の中央値 {np.median(R[k]):.3f}  区間 {lo:.3f}〜{hi:.3f}")
    ks = list(pairs)
    for o in ks[1:]:
        d = np.array(R[ks[0]]) - np.array(R[o]); lo, hi = np.percentile(d, [2.5, 97.5])
        print(f"  差 {ks[0]} − {o}: 区間 {lo:+.3f}〜{hi:+.3f}  {'0 を含まない' if lo > 0 or hi < 0 else '0 を含む'}")
    return R


def main():
    W, meta = pages_q()
    sel = lambda h, i, qs=None: sorted([p for p, (H, L, I, Q) in meta.items() if H == h and I == i and (qs is None or Q in qs)], key=fol)  # noqa: E731
    h1 = sorted(random.Random(2032).sample(sel("1", "H"), 20))
    a, b, c, d = words_mat([h1, sel("2", "H"), sel("2", "B"), sel("1", "P")], W)
    show("N242 言語 A と B・B の中の節・A の中の節", {"(i) A と B": (a, b), "(ii) B 本草と生物": (b, c), "(iii) A 本草と薬学": (a, d)})
    a, b, c, e, f = words_mat([sel("1", "H", "DEFG"), sel("2", "H", "DEFG"), sel("1", "H", "ABC"), sel("2", "H", "E"), sel("2", "H", "DFG")], W)
    show("N246 同じ綴じの A と B・綴じの違い", {"(1) 同じ綴じの A と B": (a, b), "(2) A の中の綴じ": (c, a), "(3) B の中の綴じ": (e, f)})
    A, B = sel("1", "H", "DEFG"), sel("2", "H", "DEFG"); ps = A + B
    sp = {p: [split(tuple(ivtff.glyphs(w))) for w in W[p]] for p in ps}
    pr = {}
    for k, j in (("語末 (E)", 2), ("語頭 (H)", 0), ("芯 (C)", 1)):
        it = {p: [tuple(x[j]) for x in sp[p]] for p in ps}
        top = [t for t, _ in Counter(x for p in ps for x in it[p]).most_common(30)]
        X = np.array([[Counter(it[p])[t] for t in top] for p in ps], float); X /= np.maximum(1, X.sum(1, keepdims=True))
        pr[k] = (X[:len(A)], X[len(A):])
    show("N248 欄ごとの書き手 1 と 2", pr)
    x3, x2 = words_mat([sel("3", "H", "Q"), sel("2", "H", "DEFG")], W)
    show("N249 書き手 3 と 2 の本草", {"書き手 3 と 2": (x3, x2)})


if __name__ == "__main__":
    main()

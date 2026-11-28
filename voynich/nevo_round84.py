#!/usr/bin/env python3
"""nēvo による解析 第 84 巡: N244（題材と書き手）・N245（書き手 2 と 5 の字形）。第 274 節の事前の登録どおり。

    python3 voynich/nevo_round84.py
"""
import random, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round82 import pages  # noqa: E402
from nevo_round83 import cos, strength  # noqa: E402


class _R:
    def __init__(self, p):
        self.pvalue = p


def mannwhitneyu(a, b, n=5000, seed=2036):
    """両側の Mann–Whitney。U の並べ替え（n 回）で p を出す（scipy が無いため）"""
    a, b = list(a), list(b)
    U = lambda x, y: sum((i > j) + 0.5 * (i == j) for i in x for j in y)  # noqa: E731
    mu = len(a) * len(b) / 2; d0 = abs(U(a, b) - mu)
    allv = a + b; rr = random.Random(seed); c = 0
    for _ in range(n):
        rr.shuffle(allv); c += abs(U(allv[:len(a)], allv[len(a):]) - mu) >= d0 - 1e-12
    return _R((c + 1) / (n + 1))


def mat(ps, W, top):
    X = np.array([[Counter(W[p])[w] for w in top] for p in ps], float)
    return X / np.maximum(1, X.sum(1, keepdims=True))


def disp(X):
    c = X.mean(0)
    return np.mean([cos(x, c) for x in X])


def bh(ps):
    n = len(ps); o = np.argsort(ps); q = np.empty(n); m = 1.0
    for r, i in reversed(list(enumerate(o, 1))):
        m = min(m, ps[i] * n / r); q[i] = m
    return q


def main():
    W, meta = pages()
    by = defaultdict(list)
    for p, k in meta.items():
        by[k].append(p)
    H1, H2 = sorted(by[("1", "A", "H")]), sorted(by[("2", "B", "H")])
    top = [w for w, _ in Counter(w for p in H1 + H2 for w in W[p]).most_common(100)]
    X1, X2 = mat(H1, W, top), mat(H2, W, top)
    r = random.Random(2034)
    d1 = np.mean([disp(X1[r.sample(range(len(H1)), 20)]) for _ in range(200)])
    d2 = disp(X2)
    rng = np.random.default_rng(2035); diffs = []
    for _ in range(2000):
        s1 = X1[rng.choice(len(H1), 20, replace=True)]; s2 = X2[rng.integers(0, len(H2), len(H2))]
        diffs.append(disp(s2) - disp(s1))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print("=== N244 ===")
    print(f"  (1) 本草の中のばらつき: 書き手 1 {d1:.3f}（20 頁 × 200 回の平均）、書き手 2 {d2:.3f}。差（2 − 1）{d2 - d1:+.3f}  95% 区間 {lo:+.3f}〜{hi:+.3f}  {'0 を含む' if lo <= 0 <= hi else '0 を含まない'}")
    H3h, H3s = sorted(by[("3", "B", "H")]), sorted(by[("3", "B", "S")])
    top3 = [w for w, _ in Counter(w for p in H3h + H3s for w in W[p]).most_common(100)]
    print(f"  (2) 書き手 3 の本草（{len(H3h)}）と星（{len(H3s)}）の分かれの強さ {strength(mat(H3h, W, top3), mat(H3s, W, top3)):.3f}（書き手 1 の本草と薬学 0.619）")
    print("=== N245 書き手 2 と 5（本草）===")
    P2, P5 = H2, sorted(by[("5", "B", "H")])
    gl = {p: [g for w in W[p] for g in ivtff.glyphs(w)] for p in P2 + P5}
    rank = [g for g, _ in Counter(g for p in P2 + P5 for g in gl[p]).most_common(30)]
    freq = lambda p, g: Counter(gl[p])[g] / len(gl[p])  # noqa: E731
    ps = [mannwhitneyu([freq(p, g) for p in P2], [freq(p, g) for p in P5]).pvalue for g in rank]
    q = bh(np.array(ps))
    hit = [(i + 1, g, ps[i], q[i], np.mean([freq(p, g) for p in P2]), np.mean([freq(p, g) for p in P5])) for i, g in enumerate(rank) if q[i] < 0.10]
    print(f"  字形 30 個のうち q < 0.10: {len(hit)}")
    for rk, g, p, qq, a, b in hit:
        print(f"    {rk:>2} 位 {g:<5} 書き手 2 {a:.4f}・書き手 5 {b:.4f}  p {p:.4f}  q {qq:.3f}")
    print(f"  そのうち 11 位以下: {sum(rk > 10 for rk, *_ in hit)}")
    for i in np.argsort(ps)[:6]:
        print(f"    （参考, p の小さい順）{i + 1:>2} 位 {rank[i]:<5} 2: {np.mean([freq(p, rank[i]) for p in P2]):.4f} 5: {np.mean([freq(p, rank[i]) for p in P5]):.4f} p {ps[i]:.4f} q {q[i]:.3f}")
    sp = {p: [split(tuple(ivtff.glyphs(w))) for w in W[p]] for p in P2 + P5}
    for slot, name in ((0, "語頭"), (2, "語末")):
        kinds = [k for k, _ in Counter(tuple(x[slot]) for p in P2 + P5 for x in sp[p]).most_common(15)]
        f = lambda p, k: sum(tuple(x[slot]) == k for x in sp[p]) / len(sp[p])  # noqa: E731
        pp = [mannwhitneyu([f(p, k) for p in P2], [f(p, k) for p in P5]).pvalue for k in kinds]
        qq = bh(np.array(pp))
        for i in range(len(kinds)):
            if qq[i] < 0.10:
                print(f"  {name} {''.join(kinds[i]) or '（無し）':<6} 2: {np.mean([f(p, kinds[i]) for p in P2]):.4f} 5: {np.mean([f(p, kinds[i]) for p in P5]):.4f}  p {pp[i]:.4f} q {qq[i]:.3f}")
        print(f"  {name}: q < 0.10 は {sum(qq < 0.10)} / 15")


if __name__ == "__main__":
    main()

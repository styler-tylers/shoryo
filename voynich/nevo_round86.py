#!/usr/bin/env python3
"""nēvo による解析 第 86 巡: N248（書き手 1 と 2 の違いの欄）・N249（書き手 3）。第 280 節の事前の登録どおり。

    python3 voynich/nevo_round86.py
"""
import sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round83 import strength  # noqa: E402
from nevo_round85 import fol, pages_q  # noqa: E402


def profile(ps, items):
    top = [k for k, _ in Counter(x for p in ps for x in items[p]).most_common(30)]
    X = np.array([[Counter(items[p])[k] for k in top] for p in ps], float)
    return X / np.maximum(1, X.sum(1, keepdims=True))


def boot(A, B, seed, n=2000):
    rng = np.random.default_rng(seed)
    return [strength(A[rng.integers(0, len(A), len(A))], B[rng.integers(0, len(B), len(B))]) for _ in range(n)]


def main():
    W, meta = pages_q()
    sel = lambda h, i, qs: sorted([p for p, (H, L, I, Q) in meta.items() if H == h and I == i and Q in qs], key=fol)  # noqa: E731
    A, B = sel("1", "H", "DEFG"), sel("2", "H", "DEFG")
    ps = A + B
    sp = {p: [split(tuple(ivtff.glyphs(w))) for w in W[p]] for p in ps}
    kinds = {"語頭 (H)": {p: [tuple(x[0]) for x in sp[p]] for p in ps},
             "芯 (C)": {p: [tuple(x[1]) for x in sp[p]] for p in ps},
             "語末 (E)": {p: [tuple(x[2]) for x in sp[p]] for p in ps},
             "（参考）字形 (G)": {p: [g for w in W[p] for g in ivtff.glyphs(w)] for p in ps}}
    print(f"=== N248 綴じ D〜G の本草: 書き手 1 {len(A)} 頁・書き手 2 {len(B)} 頁 ===")
    S, R = {}, {}
    rng = np.random.default_rng(2038)
    idxA = [rng.integers(0, len(A), len(A)) for _ in range(2000)]
    idxB = [rng.integers(0, len(B), len(B)) for _ in range(2000)]
    for k, it in kinds.items():
        X = profile(ps, it); XA, XB = X[:len(A)], X[len(A):]
        S[k] = strength(XA, XB)
        R[k] = np.array([strength(XA[a], XB[b]) for a, b in zip(idxA, idxB)])
        lo, hi = np.percentile(R[k], [2.5, 97.5])
        print(f"  {k:<12} 分かれの強さ {S[k]:.3f}  95% 区間 {lo:.3f}〜{hi:.3f}")
    for o in ("語頭 (H)", "芯 (C)"):
        d = R["語末 (E)"] - R[o]; lo, hi = np.percentile(d, [2.5, 97.5])
        print(f"  差 語末 − {o}: {S['語末 (E)'] - S[o]:+.3f}  95% 区間 {lo:+.3f}〜{hi:+.3f}  {'0 を含まない' if lo > 0 or hi < 0 else '0 を含む'}")
    print("=== N249 書き手 3 と 2 の本草 ===")
    H3, H2 = sel("3", "H", "Q"), sel("2", "H", "DEFG")
    top = [w for w, _ in Counter(w for p in H3 + H2 for w in W[p]).most_common(100)]
    M = lambda ps: np.array([[Counter(W[p])[w] for w in top] for p in ps], float) / np.array([[max(1, sum(Counter(W[p])[w] for w in top))] for p in ps])  # noqa: E731
    X3, X2 = M(H3), M(H2)
    s = strength(X3, X2); b = boot(X3, X2, 2039); lo, hi = np.percentile(b, [2.5, 97.5])
    print(f"  書き手 3（{len(H3)} 頁）と 2（{len(H2)} 頁）: {s:.3f}  95% 区間 {lo:.3f}〜{hi:.3f}  （基準: B の中の綴じ 0.442・A と B 1.557）")
    print(f"  (a) 下の端 > 0.442: {'はい' if lo > 0.442 else 'いいえ'}  (b) 上の端 < 1.557: {'はい' if hi < 1.557 else 'いいえ'}")


if __name__ == "__main__":
    main()

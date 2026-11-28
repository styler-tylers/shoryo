#!/usr/bin/env python3
"""nēvo による解析 第 87 巡: N250（書き手 1 と 2 の語末の型）・N251（綴じ F の書き手 2 と 5）。第 283 節の事前の登録どおり。

    python3 voynich/nevo_round87.py
"""
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round83 import strength  # noqa: E402
from nevo_round84 import bh, mannwhitneyu  # noqa: E402
from nevo_round85 import fol, pages_q  # noqa: E402


def main():
    W, meta = pages_q()
    sel = lambda h, qs: sorted([p for p, (H, L, I, Q) in meta.items() if H == h and I == "H" and Q in qs], key=fol)  # noqa: E731
    end = lambda p: ["".join(split(tuple(ivtff.glyphs(w)))[2]) or "∅" for w in W[p]]  # noqa: E731
    A, B = sel("1", "DEFG"), sel("2", "DEFG")
    E = {p: end(p) for p in A + B}
    kinds = [k for k, _ in Counter(x for p in A + B for x in E[p]).most_common(12)]
    sh = lambda p, k: E[p].count(k) / len(E[p])  # noqa: E731
    ps = [mannwhitneyu([sh(p, k) for p in A], [sh(p, k) for p in B], seed=2041).pvalue for k in kinds]
    q = bh(np.array(ps))
    print(f"=== N250 語末の型（書き手 1 {len(A)} 頁・書き手 2 {len(B)} 頁, 頁ごとの割合の中央値）===")
    for k, p_, qq in zip(kinds, ps, q):
        print(f"  {k:<5} 書き手 1 {np.median([sh(p, k) for p in A]):.3f}  書き手 2 {np.median([sh(p, k) for p in B]):.3f}  p {p_:.4f}  q {qq:.4f}{'  ＊' if qq < 0.05 else ''}")
    print("  綴じごとの dy（中央値）:")
    for Q in "DEFG":
        a = [sh(p, "dy") for p in sel("1", Q)]; b = [sh(p, "dy") for p in sel("2", Q)]
        print(f"    綴じ {Q}: 書き手 1 {np.median(a):.3f}（{len(a)} 頁）  書き手 2 {np.median(b):.3f}（{len(b)} 頁）  {'2 が高い' if np.median(b) > np.median(a) else '2 が高くない'}")
    print("=== N251 綴じ F の書き手 2 と 5 ===")
    P2 = sel("2", "F"); P5 = sorted([p for p, (H, L, I, Q) in meta.items() if H == "5" and I == "H" and Q == "F"], key=fol)
    ps8 = P2 + P5
    gl = {p: [g for w in W[p] for g in ivtff.glyphs(w)] for p in ps8}
    E8 = {p: end(p) for p in ps8}
    for name, it in (("字形 30 個", gl), ("語末の型 12 種", E8)):
        top = [k for k, _ in Counter(x for p in ps8 for x in it[p]).most_common(30 if name.startswith("字形") else 12)]
        X = np.array([[it[p].count(k) for k in top] for p in ps8], float); X /= X.sum(1, keepdims=True)
        s0 = strength(X[:4], X[4:]); cnt = tot = 0
        for idx in combinations(range(8), 4):
            rest = [i for i in range(8) if i not in idx]
            tot += 1; cnt += strength(X[list(idx)], X[rest]) >= s0 - 1e-12
        print(f"  {name:<12} 分かれの強さ {s0:.3f}  付け替え 70 通りの p {cnt / tot:.3f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 85 巡: N246（同じ綴じの中の言語 A と B）・N247（書き手 2 と 5 の語末, 綴じ F）。第 277 節の事前の登録どおり。

    python3 voynich/nevo_round85.py
"""
import re, sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus, ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round83 import strength  # noqa: E402


def pages_q():
    args = corpus.make_parser("").parse_args([]); args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    W, meta = defaultdict(list), {}
    for ln in lines:
        W[ln.page.name] += ivtff.words(ln.raw, opts)
        meta[ln.page.name] = (ln.page.get("H"), ln.page.get("L"), ln.page.get("I"), ln.page.get("Q"))
    return W, meta


def fol(p):
    m = re.match(r"f(\d+)([rv])(\d*)", p)
    return (int(m.group(1)), m.group(2), m.group(3))


def main():
    W, meta = pages_q()
    sel = lambda h, i, qs: sorted([p for p, (H, L, I, Q) in meta.items() if H == h and I == i and Q in qs], key=fol)  # noqa: E731
    A_DG, B_DG = sel("1", "H", "DEFG"), sel("2", "H", "DEFG")
    A_AC = sel("1", "H", "ABC")
    B_E, B_DFG = sel("2", "H", "E"), sel("2", "H", "DFG")
    allp = A_DG + B_DG + A_AC
    top = [w for w, _ in Counter(w for p in allp for w in W[p]).most_common(100)]
    M = lambda ps: np.array([[Counter(W[p])[w] for w in top] for p in ps], float) / np.array([[max(1, sum(Counter(W[p])[w] for w in top))] for p in ps])  # noqa: E731
    G = {"A_DG": M(A_DG), "B_DG": M(B_DG), "A_AC": M(A_AC), "B_E": M(B_E), "B_DFG": M(B_DFG)}
    pairs = {"(1) 同じ綴じの A と B": ("A_DG", "B_DG"), "(2) A の中の綴じ（A〜C と D〜G）": ("A_AC", "A_DG"), "(3) B の中の綴じ（E と D・F・G）": ("B_E", "B_DFG")}
    print(f"=== N246（頁: A_DG {len(A_DG)}・B_DG {len(B_DG)}・A_AC {len(A_AC)}・B_E {len(B_E)}・B_DFG {len(B_DFG)}）===")
    for k, (a, b) in pairs.items():
        print(f"  {k:<26} {strength(G[a], G[b]):.3f}")
    rng = np.random.default_rng(2037); d12, d13 = [], []
    for _ in range(2000):
        R = {g: m[rng.integers(0, len(m), len(m))] for g, m in G.items()}
        s1 = strength(R["A_DG"], R["B_DG"])
        d12.append(s1 - strength(R["A_AC"], R["A_DG"])); d13.append(s1 - strength(R["B_E"], R["B_DFG"]))
    for name, d in (("(1)−(2)", d12), ("(1)−(3)", d13)):
        lo, hi = np.percentile(d, [2.5, 97.5])
        print(f"  差 {name}: {np.mean(d):+.3f}  95% 区間 {lo:+.3f}〜{hi:+.3f}  {'0 を含まない' if lo > 0 or hi < 0 else '0 を含む'}")
    print("=== N247 綴じ F の書き手 2 と 5（r で終わる語の割合）===")
    rshare = lambda p: np.mean([tuple(split(tuple(ivtff.glyphs(w)))[2]) [-1:] == ("r",) for w in W[p]])  # noqa: E731
    F2, F5 = sel("2", "H", "F"), sel("5", "H", "F")
    a = [rshare(p) for p in F2]; b = [rshare(p) for p in F5]
    print("  書き手 2:", " ".join(f"{p} {v:.3f}" for p, v in zip(F2, a)))
    print("  書き手 5:", " ".join(f"{p} {v:.3f}" for p, v in zip(F5, b)))
    allv = a + b; U0 = sum(x > y for x in a for y in b) + 0.5 * sum(x == y for x in a for y in b)
    mu = len(a) * len(b) / 2; cnt = tot = 0
    for idx in combinations(range(8), 4):
        x = [allv[i] for i in idx]; y = [allv[i] for i in range(8) if i not in idx]
        U = sum(i > j for i in x for j in y) + 0.5 * sum(i == j for i in x for j in y)
        tot += 1; cnt += abs(U - mu) >= abs(U0 - mu) - 1e-12
    print(f"  完全に分かれる: {'はい' if min(a) > max(b) else 'いいえ'}  U {U0}  正確な両側 p {cnt / tot:.3f}")
    print("=== 記述: 綴じ D〜H の言語 B の本草の頁（綴じの順）===")
    for p in sorted([p for p, (H, L, I, Q) in meta.items() if L == "B" and I == "H"], key=fol):
        H, L, I, Q = meta[p]
        print(f"  {p:<7} 綴じ {Q} 書き手 {H}  r で終わる語 {rshare(p):.3f}  語 {len(W[p])}")


if __name__ == "__main__":
    main()

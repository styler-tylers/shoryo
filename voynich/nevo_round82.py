#!/usr/bin/env python3
"""nēvo による解析 第 82 巡: N241（書き手と言語と節）。第 267 節の事前の登録どおり。

    python3 voynich/nevo_round82.py
"""
import random, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus, ivtff  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round73 import line_excess  # noqa: E402


def pages():
    args = corpus.make_parser("").parse_args([]); args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    W, meta = defaultdict(list), {}
    for ln in lines:
        W[ln.page.name] += ivtff.words(ln.raw, opts)
        meta[ln.page.name] = (ln.page.get("H"), ln.page.get("L"), ln.page.get("I"))
    return W, meta


def classify(groups, W, rng, nperm=2000):
    """groups: {名: [頁]}。1 つ抜きの最近傍の重心（余弦）。釣り合いを取った正答率と並べ替えの p"""
    pg = [p for ps in groups.values() for p in ps]
    lab = np.array([g for g, ps in groups.items() for _ in ps])
    top = [w for w, _ in Counter(w for p in pg for w in W[p]).most_common(100)]
    X = np.array([[Counter(W[p])[w] for w in top] for p in pg], float)
    X /= X.sum(1, keepdims=True)
    names = list(groups)

    def bacc(lab):
        pred = []
        for i in range(len(pg)):
            m = np.ones(len(pg), bool); m[i] = False
            best, bs = None, -2
            for g in names:
                c = X[m & (lab == g)].mean(0)
                s = X[i] @ c / (np.linalg.norm(X[i]) * np.linalg.norm(c))
                if s > bs:
                    best, bs = g, s
            pred.append(best)
        pred = np.array(pred)
        return np.mean([(pred[lab == g] == g).mean() for g in names])
    a0 = bacc(lab)
    cnt = 0
    for _ in range(nperm):
        perm = lab.copy(); rng.shuffle(perm)
        cnt += bacc(perm) >= a0 - 1e-12
    return a0, (cnt + 1) / (nperm + 1)


def main():
    W, meta = pages()
    by = defaultdict(list)
    for p, (h, l, i) in meta.items():
        by[(h, l, i)].append(p)
    herb = lambda h, l: sorted(by[(h, l, "H")])  # noqa: E731
    rng = random.Random(2032)
    h1 = sorted(rng.sample(herb("1", "A"), 20))
    combos = [("(1) 書き手 2 と 3（本草, B）", {"2": herb("2", "B"), "3": herb("3", "B")}),
              ("(2) 書き手 2 と 5（本草, B）", {"2": herb("2", "B"), "5": herb("5", "B")}),
              ("(3) 書き手 3 と 5（本草, B）", {"3": herb("3", "B"), "5": herb("5", "B")}),
              ("(4) 書き手 1（A）と 2（B）（本草）", {"1": h1, "2": herb("2", "B")}),
              ("(5) 書き手 2 の本草と生物", {"本草": herb("2", "B"), "生物": sorted(by[("2", "B", "B")])})]
    print("=== (a)〜(c) 語の選び方で分けられるか ===", flush=True)
    for name, g in combos:
        a, p = classify(g, W, random.Random(2032))
        print(f"  {name:<28} 頁 {'・'.join(str(len(v)) for v in g.values()):<7} 釣り合いを取った正答率 {a:.3f}  並べ替えの p {p:.4f}", flush=True)
    print("=== (d) 隣の行の似かたの余り（言語 B, 書き手ごと） ===", flush=True)
    V = voynich()
    F = flagged(V, "B")
    for h in ("2", "3", "5"):
        Fe = {pg: [l for l, st in v if not st] for pg, v in F.items() if meta.get(pg, (None,))[0] == h}
        x = line_excess(Fe, random.Random(2))
        ctrl = sorted(line_excess({k: random.Random(s).sample(v, len(v)) for k, v in Fe.items()}, random.Random(2)) for s in range(20))
        print(f"  書き手 {h}（{len(Fe)} 頁）余り {x:+.4f}  対照 {ctrl[1]:+.4f}〜{ctrl[18]:+.4f}  {'超える' if x > ctrl[18] else '超えない'}", flush=True)


if __name__ == "__main__":
    main()

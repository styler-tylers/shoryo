#!/usr/bin/env python3
"""nēvo による解析 第 27 巡: N81（離れた頁どうしの話題のまとまり）・N79（全ての量を一度に合わせる）。

    python3 voynich/nevo_round27.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import pos_dists  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round18 import apply_family2  # noqa: E402
from nevo_round25 import score  # noqa: E402
from nevo_round26 import build_cond2  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
BINS = [("1", 1, 1), ("2〜5", 2, 5), ("6〜20", 6, 20), ("21〜", 21, 10 ** 9)]


def page_sim(name, P):
    pages = list(P.values())
    allw = Counter(w for ls in pages for l in ls for w in l)
    top = {w for w, _ in allw.most_common(50)}
    sets = [set(w for l in ls for w in l) - top for ls in pages]
    sets = [s for s in sets if s]
    jac = lambda a, b: len(a & b) / len(a | b)  # noqa: E731
    byd = defaultdict(list)
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            byd[j - i].append(jac(sets[i], sets[j]))
    base = statistics.mean(v for vs in byd.values() for v in vs)
    S = {}
    for label, lo, hi in BINS:
        vals = [v for d, vs in byd.items() if lo <= d <= hi for v in vs]
        S[label] = statistics.mean(vals) / base if vals else float("nan")
    print(f"  {name:<28} 頁 {len(sets):>3}  " + "  ".join(f"S({k}) {v:.2f}" for k, v in S.items())
          + f"   S(2〜5)÷S(21〜) {S['2〜5'] / S['21〜']:.2f}", flush=True)


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    print("=== N81 離れた頁どうしの話題のまとまり ===")
    models = {}
    for lang in ("A", "B"):
        pt = V[lang][0]
        page_sim(f"ヴォイニッチ {lang}", pt)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        gr = random.Random(7)
        gen = Counter(LG.word(gr) for _ in range(300000))
        by_tail = defaultdict(set)
        for w in gen:
            by_tail[w[1:]].add(w)
        i, e, _ = matched_source(caesar, LG, random.Random(1))
        P = build12(i, e, LG, LC, random.Random(11), beta=0.0, compat=True, wfun=gram_prob(LG))
        P = apply_family2(P, LG, gen, by_tail, boundary_dists(pt), pos_dists(pt)[1], 0.3, random.Random(21), False)
        page_sim(f"平文あり（N51 の作り方）{lang}", P)
        P = build_cond2(LG, LC, pt, random.Random(1), mu=0.1)
        page_sim(f"平文なし（N77, μ 0.1）{lang}", P)
        models[lang] = (LG, LC)
    print("\n=== N79 全ての量を一度に合わせる（平文なし, γ 2, 種 2 通り）===")
    for lang in ("A", "B"):
        pt = V[lang][0]
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        LG, LC = models[lang]
        print(f"-- 言語 {lang}", flush=True)
        for mu in (0.05, 0.1):
            for c in (0.25, 0.4):
                runs = []
                for seed in (1, 2):
                    P = build_cond2(LG, LC, pt, random.Random(seed), mu=mu, c=c, gamma=2.0)
                    runs.append(with_strength(measure(P, lastf(P), rng), P))
                summarize(f"μ {mu} c {c}", runs)
                score(f"μ {mu} c {c}", runs, ref)
                sys.stdout.flush()


if __name__ == "__main__":
    main()

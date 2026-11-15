#!/usr/bin/env python3
"""nēvo による解析 第 18 巡: N51（最初の字形だけが違う組）・N52（語末だけが違う組）・N53（長さの枠と音節の数）。

    python3 voynich/nevo_round18.py <Caesar> <その他の文章 …>
"""

from __future__ import annotations

import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_entropy  # noqa: E402
from nevo_round9 import skew, voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import pos_dists, positions  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def apply_family2(P, G, gen, by_tail, dists, ed, eps, rng, end_select):
    first, firstp, last = dists
    heads = list(G.hk)
    ends = list(G.ek)
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w, p = l[i], positions(l)[i]
                h, m, e = split(w)
                cands = list(dict.fromkeys([c for c in (hh + m + e for hh in heads) if c] + list(by_tail.get(w[1:], ()))))
                mx = max(gen[c] for c in cands) or 1
                fd = first[(p, new[-1][-1])]
                if sum(fd.values()) < 20:
                    fd = firstp[p]
                ld = last[p]
                wts = [(fd[c[0]] + 0.5) * (ld[c[-1]] + 0.5) * (gen[c] / mx + eps) for c in cands]
                w = rng.choices(cands, wts)[0]
                if end_select and p in ("内側の最後", "行の最後"):
                    h, m, _ = split(w)
                    key = m[-1] if m else ("H",) + h
                    ec = [x for x in ends if G.em[key][x] > 0] or [split(w)[2]]
                    tot = sum(G.em[key][x] for x in ec) or 1
                    cands2 = [(h + m + x) or w for x in ec]
                    wts2 = [(ed[p][x] + 0.5) * (G.em[key][x] / tot + eps) for x in ec]
                    w = rng.choices(cands2, wts2)[0]
                new.append(w)
            ls[li] = new
    return P


def syllables(w):
    return max(1, len(re.findall(r"[aeiouy]+", w)))


def n53(paths):
    print("\n=== N53 長さの枠と音節の数（語の出現ごとの歪度）===")
    for p in paths:
        ws = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        print(f"  {p.stem:<10} 文字の数 {skew([len(w) for w in ws]):+.2f}   音節の数 {skew([syllables(w) for w in ws]):+.2f}   "
              f"（平均 文字 {sum(map(len, ws)) / len(ws):.2f}・音節 {sum(map(syllables, ws)) / len(ws):.2f}）")


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:]]
    caesar = ["".join(w) for w in unit_entropy.latin_words(paths[0])]
    rng = random.Random(2026)
    n53(paths)
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        G = LengthGrammar(pt)
        C = Compat(G, pt)
        gr = random.Random(7)
        gen = Counter(G.word(gr) for _ in range(300000))
        by_tail = defaultdict(set)
        for w in gen:
            by_tail[w[1:]].add(w)
        dists = boundary_dists(pt)
        _, ed = pos_dists(pt)
        for label, end_sel in (("N51 最初の字形だけが違う組", False), ("N52 ＋ 語末だけが違う組", True)):
            runs = []
            for seed in (1, 2, 3):
                i, e, _ = matched_source(caesar, G, random.Random(seed))
                P = build12(i, e, G, C, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(G))
                P = apply_family2(P, G, gen, by_tail, dists, ed, 0.3, random.Random(seed + 20), end_sel)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(label, runs)
            sys.stdout.flush()


if __name__ == "__main__":
    main()

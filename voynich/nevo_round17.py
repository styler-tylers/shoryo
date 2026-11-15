#!/usr/bin/env python3
"""nēvo による解析 第 17 巡: N48（語頭だけが違う組から選ぶ）・N49（語の長さを先に決める型）。

    python3 voynich/nevo_round17.py <Caesar>
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import positions  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def apply_family(P, G, dists, eps, rng):
    first, firstp, last = dists
    heads = list(G.hk)
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w, p = l[i], positions(l)[i]
                _, m, e = split(w)
                tot = sum(G.mh[h][m] for h in heads)
                cands, pg = [], []
                for h in heads:
                    c = h + m + e
                    if c and c not in cands:
                        cands.append(c)
                        pg.append((G.mh[h][m] / tot if tot else 0.0) + eps)
                fd = first[(p, new[-1][-1])]
                if sum(fd.values()) < 20:
                    fd = firstp[p]
                ld = last[p]
                wts = [(fd[c[0]] + 0.5) * (ld[c[-1]] + 0.5) * g for c, g in zip(cands, pg)]
                new.append(rng.choices(cands, wts)[0])
            ls[li] = new
    return P


class LengthGrammar(LinkedGrammar):
    def __init__(self, pages_t):
        super().__init__(pages_t)
        self.lengths = [len(w) for ls in pages_t.values() for l in ls for w in l]

    def word(self, rng):
        L = rng.choice(self.lengths)
        w = None
        for _ in range(200):
            w = super().word(rng)
            if len(w) == L:
                return w
        return w


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        G = LinkedGrammar(pt)
        C = Compat(G, pt)
        dists = boundary_dists(pt)
        print("=== N48 語頭だけが違う組から選ぶ（β 0, 種 3 通り）===", flush=True)
        for eps in (0.05, 0.3):
            runs = []
            for seed in (1, 2, 3):
                i, e, _ = matched_source(caesar, G, random.Random(seed))
                P = build12(i, e, G, C, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(G))
                P = apply_family(P, G, dists, eps, random.Random(seed + 20))
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(f"ε = {eps}", runs)
            sys.stdout.flush()
        print("=== N49 語の長さを先に決める型（N46 の手順, 種 3 通り）===", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        runs = []
        for seed in (1, 2, 3):
            i, e, _ = matched_source(caesar, LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.4, compat=True, wfun=gram_prob(LG))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("長さを先に決める", runs)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

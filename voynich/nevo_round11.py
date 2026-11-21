#!/usr/bin/env python3
"""nēvo による解析 第 11 巡: N30（欄が結び付いた語の型）・N31（境目の規則を弱める）・N32（語と語の結び付きの中身）。

    python3 voynich/nevo_round11.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round2 import ed1  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import KEYS, Grammar, build, measure, show, source_wp, split  # noqa: E402


class LinkedGrammar(Grammar):
    def __init__(self, pages_t):
        super().__init__(pages_t)
        self.mh, self.em = defaultdict(Counter), defaultdict(Counter)
        for ls in pages_t.values():
            for l in ls:
                for w in l:
                    h, m, e = split(w)
                    self.mh[h][m] += 1
                    self.em[m[-1] if m else ("H",) + h][e] += 1

    def _pick(self, c, rng):
        k, w = zip(*c.items())
        return rng.choices(k, w)[0]

    def word(self, rng):
        while True:
            h = rng.choices(self.hk, self.hw)[0]
            m = self._pick(self.mh[h], rng)
            e = self._pick(self.em[m[-1] if m else ("H",) + h], rng)
            if h + m + e:
                return h + m + e

    def new_head(self, w, rng):
        _, m, e = split(w)
        cands = [h for h in self.hk if self.mh[h][m] > 0] or list(self.hk)
        h = rng.choices(cands, [self.h[x] for x in cands])[0]
        return (h + m + e) or w


def n32(V, rng, runs=50):
    print("\n=== N32 語と語の組み合わせの結び付きの中身 ===")
    for lang in ("A", "B"):
        pt = V[lang][0]
        inner = [l[1:-1] for ls in pt.values() for l in ls if len(l) >= 4]
        pairs = [(a, b) for l in inner for a, b in zip(l, l[1:])]

        def excess(ps, collect=False):
            obs = line_unit.mi(ps)
            groups = defaultdict(list)
            for i, (a, b) in enumerate(ps):
                groups[(a[-1], b[0])].append(i)
            nulls, exp = [], Counter()
            for _ in range(runs):
                bs = [b for _, b in ps]
                for idx in groups.values():
                    sh = [ps[i][1] for i in idx]
                    rng.shuffle(sh)
                    for i, b in zip(idx, sh):
                        bs[i] = b
                null = [(a, b) for (a, _), b in zip(ps, bs)]
                nulls.append(line_unit.mi(null))
                if collect:
                    exp.update(null)
            return obs - statistics.mean(nulls), exp

        ex_all, exp = excess(pairs, collect=True)
        sub = [(a, b) for a, b in pairs if a != b and not ed1(a, b)]
        ex_sub, _ = excess(sub)
        same = sum(a == b for a, b in pairs)
        sim = sum(ed1(a, b) for a, b in pairs)
        print(f"  言語 {lang}: 組 {len(pairs)}（同じ語 {same}、1 字形違い {sim}）  超過: 全て {ex_all:.3f}、"
              f"同じ・1 字形違いを除く {ex_sub:.3f}  → 同じ・似た語の組で説明 {1 - ex_sub / ex_all:.0%}")
        obs_c = Counter(pairs)
        top = sorted(obs_c, key=lambda k: -(obs_c[k] - exp[k] / runs))[:15]
        print("   上回る組: " + ", ".join(f"{''.join(a)} {''.join(b)} {obs_c[(a, b)]}（{exp[(a, b)] / runs:.1f}）" for a, b in top))


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    LG = {lang: LinkedGrammar(V[lang][0]) for lang in ("A", "B")}
    lastf = lambda P: [i == len(ls) - 1 for ls in P.values() for i in range(len(ls))]  # noqa: E731
    print(f"  {'':<26}" + " ".join(f"{k:>7}" for k in KEYS))
    for lang in ("A", "B"):
        pt, _, last = V[lang]
        show(f"ヴォイニッチ {lang}", measure(pt, last, rng))
    print("\n=== N30 欄が結び付いた語の型（β 0.2, 行末は 2 語の短い方, 幅のばらつき）===")
    for gl in ("A", "B"):
        i, e = source_wp(caesar, LG[gl], random.Random(3))
        P = build(i, e, LG[gl], random.Random(11), beta=0.2, vary=True, short_last=True, n_last=2)
        show(f"結び付いた型 欄 {gl}", measure(P, lastf(P), rng))
    print("\n=== N31 境目の規則の強さ（欄 B）===")
    for beta in (0.1, 0.2, 0.3):
        i, e = source_wp(caesar, LG["B"], random.Random(3))
        P = build(i, e, LG["B"], random.Random(11), beta=beta, vary=True, short_last=True, n_last=2)
        show(f"β = {beta}", measure(P, lastf(P), rng))
    n32(V, rng)


if __name__ == "__main__":
    main()

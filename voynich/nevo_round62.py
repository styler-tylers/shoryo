#!/usr/bin/env python3
"""nēvo による解析 第 62 巡: N184（モデルに段落の最初の行の規則）・N185（p/f の語の位置）・N186（頁の 1 行目と頁の途中の段落）。

    python3 voynich/nevo_round62.py
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round59 import GALLOWS, flagged  # noqa: E402
from nevo_round61 import G_PAR, core_len, gstart, share  # noqa: E402

SWAP = {"k": "p", "t": "f", "ckh": "cph", "cth": "cfh"}
ADD = (["ch"] * 3) + ["sh"] + (["o"] * 2)


def rewrite(w, rng, r=0.9, a=0.4):
    h, c, e = split(w)
    c = [SWAP[g] if g in SWAP and rng.random() < r else g for g in c]
    if rng.random() < a:
        c.insert(rng.randint(0, len(c)), rng.choice(ADD))
    return tuple(h) + tuple(c) + tuple(e)


def with_rule(M, frac, rng):
    F = {}
    out = {}
    for pg, ls in M.items():
        flags = [j == 0 or rng.random() < frac for j in range(len(ls))]
        out[pg] = [[rewrite(w, rng) for w in l] if f else l for l, f in zip(ls, flags)]
        F[pg] = list(zip(out[pg], flags))
    return out, F


def stats(F):
    first = [l for v in F.values() for l, st in v if st and l]
    other = [l for v in F.values() for l, st in v if not st and l]
    return (core_len(first) - core_len(other), share(first, G_PAR) / max(1e-9, share(other, G_PAR)), gstart(first) / gstart(other))


def main():
    V = voynich()
    print("=== N184 モデルに段落の最初の行の規則 ===", flush=True)
    for lang, kw, frac in (("A", dict(c=0.4, mark=0.25), 0.15), ("B", dict(c=0.6, mark=0.12, live=True), 0.19)):
        p_ = V[lang][0]
        ref = measure(p_, V[lang][2], random.Random(2026))
        LG = LengthGrammar(p_)
        M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=sum(len(l) for ls in p_.values() for l in ls), **kw)
        d, pr, gr = stats(flagged(V, lang))
        print(f"  ---- 言語 {lang}: ヴォイニッチ 芯の差 {d:+.3f}  段落の頭の絞首台 {pr:.1f} 倍  絞首台で始まる語 {gr:.2f} 倍", flush=True)
        F0 = {pg: [(l, j == 0) for j, l in enumerate(ls)] for pg, ls in M.items()}
        d0, pr0, gr0 = stats(F0)
        print(f"  モデル（規則なし, 頁の 1 行目） 芯の差 {d0:+.3f}  段落の頭の絞首台 {pr0:.1f} 倍  絞首台で始まる語 {gr0:.2f} 倍", flush=True)
        three("モデル（規則なし）", [l for ls in M.values() for l in ls])
        report("規則なし", M, ref, random.Random(2026))
        M2, F2 = with_rule(M, frac, random.Random(9))
        d2, pr2, gr2 = stats(F2)
        print(f"  モデル（規則あり）              芯の差 {d2:+.3f}  段落の頭の絞首台 {pr2:.1f} 倍  絞首台で始まる語 {gr2:.2f} 倍", flush=True)
        three("モデル（規則あり）", [l for ls in M2.values() for l in ls])
        report("規則あり", M2, ref, random.Random(2026))

    print("=== N185 p/f の語の位置 ===", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        has = lambda w: any(g in G_PAR for g in split(w)[1])  # noqa: E731
        pos = {1: [], 2: [], 3: [], 4: []}
        oth = []
        for v in F.values():
            for l, st in v:
                for i, w in enumerate(l):
                    (pos[min(i + 1, 4)] if st else oth).append(has(w))
        rates = {k: statistics.mean(x) for k, x in pos.items()}
        o = statistics.mean(oth)
        print(f"  言語 {lang}: 1 語目 {rates[1]:.1%}  2 語目 {rates[2]:.1%}  3 語目 {rates[3]:.1%}  4 語目以降 {rates[4]:.1%}  それ以外の行 {o:.1%}  "
              f"| 1 語目 ÷ 4 語目以降 {rates[1] / rates[4]:.1f}  4 語目以降 ÷ それ以外 {rates[4] / o:.1f}", flush=True)

    print("=== N186 頁の 1 行目と頁の途中の段落 ===", flush=True)
    for lang in ("A", "B"):
        F = flagged(V, lang)
        pf = [l for v in F.values() for j, (l, st) in enumerate(v) if st and j == 0 and l]
        mid = [l for v in F.values() for j, (l, st) in enumerate(v) if st and j > 0 and l]
        other = [l for v in F.values() for l, st in v if not st and l]
        co, so = core_len(other), share(other, G_PAR)
        print(f"  言語 {lang}: 頁の 1 行目 {len(pf)} 行 芯の差 {core_len(pf) - co:+.3f}  段落の頭の絞首台 {share(pf, G_PAR) / so:.1f} 倍"
              f"  | 頁の途中の段落 {len(mid)} 行 芯の差 {core_len(mid) - co:+.3f}  段落の頭の絞首台 {share(mid, G_PAR) / so:.1f} 倍", flush=True)


if __name__ == "__main__":
    main()

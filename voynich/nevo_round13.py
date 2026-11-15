#!/usr/bin/env python3
"""nēvo による解析 第 13 巡: N36（頻度を合わせた符号表）・N37（頻度をずらさない写し）・N38（行の中の位置の偏り）。

    python3 voynich/nevo_round13.py <Caesar>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import KEYS, measure, show, split  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402
from nevo_round12 import Compat, build12, h2_of  # noqa: E402
from word_grammar import ENDS  # noqa: E402


def matched_source(caesar, G, rng, n=200000):
    gen = Counter(G.word(rng) for _ in range(n))
    lex = [w for w, _ in gen.most_common()]
    types = [w for w, _ in Counter(caesar).most_common()]
    while len(lex) < len(types):
        w = G.word(rng)
        if w not in gen:
            gen[w] = 0
            lex.append(w)
    book = dict(zip(types, lex))
    half = len(caesar) // 2
    it = iter([book[w] for w in caesar[:half]])
    edge = [book[w] for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None)), [book[w] for w in caesar]


def gram_prob(G):
    def p(w):
        h, m, e = split(w)
        ph = G.h[h] / sum(G.h.values())
        pm = G.mh[h][m] / max(1, sum(G.mh[h].values()))
        key = m[-1] if m else ("H",) + h
        pe = G.em[key][e] / max(1, sum(G.em[key].values()))
        return max(ph * pm * pe, 1e-9)
    return p


def n38(V):
    print("\n=== N38 行の中の位置による語の種類の偏り（|z| > 3）===")
    endcls = lambda w: next(("".join(e) for e in ENDS if len(w) >= len(e) and w[-len(e):] == e), "その他")  # noqa: E731
    headcls = lambda w: "".join(split(w)[0]) or "なし"  # noqa: E731
    for lang in ("A", "B"):
        pt = V[lang][0]
        for label, cls in (("語頭の欄", headcls), ("語末の欄", endcls)):
            tab = defaultdict(Counter)
            for ls in pt.values():
                for l in ls:
                    if len(l) < 4:
                        continue
                    tab["行の 1 語目"][cls(l[0])] += 1
                    tab["行の最後"][cls(l[-1])] += 1
                    inner = l[1:-1]
                    tab["内側の 1 語目"][cls(inner[0])] += 1
                    tab["内側の最後"][cls(inner[-1])] += 1
                    for w in inner[1:-1]:
                        tab["内側の中ほど"][cls(w)] += 1
            rows = ["行の 1 語目", "内側の 1 語目", "内側の中ほど", "内側の最後", "行の最後"]
            cols = sorted(set().union(*tab.values()))
            N = sum(sum(tab[r].values()) for r in rows)
            out = []
            for r in rows:
                rn = sum(tab[r].values())
                for c in cols:
                    cn = sum(tab[x][c] for x in rows)
                    e = rn * cn / N
                    z = (tab[r][c] - e) / math.sqrt(e * (1 - rn / N) * (1 - cn / N)) if e > 0 else 0
                    if abs(z) > 3:
                        out.append((r, c, tab[r][c], e, z))
            print(f"  言語 {lang} {label}:")
            for r in rows:
                items = sorted([x for x in out if x[0] == r], key=lambda x: -abs(x[4]))[:6]
                if items:
                    print(f"    {r:<8} " + "、".join(f"{c} {'多' if z > 0 else '少'}（{o}/{e:.0f}, z {z:+.1f}）" for _, c, o, e, z in items))


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    G = LinkedGrammar(V["B"][0])
    C = Compat(G, V["B"][0])
    print("=== N36 頻度を合わせた符号表 ===")
    i, e, stream = matched_source(caesar, G, random.Random(3))
    print(f"  ヴォイニッチ B h2 2.10 ／ (ii) でたらめな符号表 2.38（N34） ／ (ii') 頻度を合わせた符号表: h2 {h2_of(stream):.2f}")
    print("\n=== N37 頻度をずらさない写し（＋全ての手順, 欄 B）===")
    print(f"  {'':<26}" + " ".join(f"{k:>7}" for k in KEYS))
    show("ヴォイニッチ B", measure(V["B"][0], V["B"][2], rng))
    lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
    p = gram_prob(G)
    for label, wf in (("写し 1/長さ²", None), ("写し 型の出やすさ", p)):
        i, e, _ = matched_source(caesar, G, random.Random(3))
        P = build12(i, e, G, C, random.Random(11), beta=0.4, compat=True, wfun=wf)
        show(label, measure(P, lastf(P), rng))
    n38(V)


if __name__ == "__main__":
    main()

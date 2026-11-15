#!/usr/bin/env python3
"""nēvo による解析 第 14 巡: N41（位置か境目か）・N39（位置の型をモデルに）・N40（言語 A）。

    python3 voynich/nevo_round14.py <Caesar>
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
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402

POS = ["行の 1 語目", "内側の 1 語目", "内側の中ほど", "内側の最後", "行の最後"]


def positions(l):
    """4 語以上の行の各語の位置の名前。"""
    n = len(l)
    out = ["行の 1 語目", "内側の 1 語目"] + ["内側の中ほど"] * (n - 4) + ["内側の最後", "行の最後"]
    return out


def pos_dists(pt):
    hd, ed = defaultdict(Counter), defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            if len(l) < 4:
                continue
            for w, p in zip(l, positions(l)):
                h, _, e = split(w)
                hd[p][h] += 1
                ed[p][e] += 1
    return hd, ed


def strength(lines_):
    sec, last = Counter(), Counter()
    for l in lines_:
        if len(l) < 4:
            continue
        sec[split(l[1])[0] in (("sh",), ("ch",))] += 1
        last[split(l[-1])[2] == ("m",)] += 1
    return sec[True] / max(1, sum(sec.values())), last[True] / max(1, sum(last.values()))


def n41(V):
    print("=== N41 2 語目の sh-/ch- は位置の規則か、境目の規則か ===")
    for lang in ("A", "B"):
        strata = defaultdict(lambda: [0, 0, 0, 0])  # 2 語目: 該当, 全体 / 中ほど: 該当, 全体
        for ls in V[lang][0].values():
            for l in ls:
                if len(l) < 4:
                    continue
                for i, (w, p) in enumerate(zip(l, positions(l))):
                    if p not in ("内側の 1 語目", "内側の中ほど"):
                        continue
                    k = l[i - 1][-1]
                    hit = split(w)[0] in (("sh",), ("ch",))
                    s = strata[k]
                    if p == "内側の 1 語目":
                        s[0] += hit
                        s[1] += 1
                    else:
                        s[2] += hit
                        s[3] += 1
        o = e = var = 0.0
        raw = [0, 0, 0, 0]
        for a, n1, b, n2 in strata.values():
            raw = [raw[0] + a, raw[1] + n1, raw[2] + b, raw[3] + n2]
            if n1 == 0 or n2 == 0:
                continue
            N, M = n1 + n2, a + b
            o += a
            e += n1 * M / N
            var += n1 * n2 * M * (N - M) / (N * N * (N - 1)) if N > 1 else 0
        z = (o - e) / math.sqrt(var) if var else float("nan")
        print(f"  言語 {lang}: 2 語目の sh/ch {raw[0]}/{raw[1]}（{raw[0] / raw[1]:.0%}）、中ほど {raw[2]}/{raw[3]}（{raw[2] / raw[3]:.0%}）。"
              f"前の語の最後の字形で層に分けると 観測 {o:.0f} 期待 {e:.1f}  z = {z:+.1f}")


def apply_template(P, G, hd, ed, pi, rng):
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = []
            for w, p in zip(l, positions(l)):
                h, m, e = split(w)
                if rng.random() < pi:
                    hs = [x for x in hd[p] if G.mh[x][m] > 0] or [h]
                    h = rng.choices(hs, [hd[p][x] + 0.01 for x in hs])[0]
                    if p == "行の最後":
                        key = m[-1] if m else ("H",) + h
                        es = [x for x in ed[p] if G.em[key][x] > 0] or [e]
                        e = rng.choices(es, [ed[p][x] + 0.01 for x in es])[0]
                new.append((h + m + e) or w)
            ls[li] = new
    return P


def run(lang, V, caesar, rng, pis):
    G = LinkedGrammar(V[lang][0])
    C = Compat(G, V[lang][0])
    hd, ed = pos_dists(V[lang][0])
    lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
    pt = V[lang][0]
    show(f"ヴォイニッチ {lang}", measure(pt, V[lang][2], rng))
    s2, sm = strength([l for ls in pt.values() for l in ls])
    print(f"     位置の型: 2 語目 sh/ch {s2:.0%}、行の最後 -m {sm:.1%}")
    for pi in pis:
        i, e, _ = matched_source(caesar, G, random.Random(3))
        P = build12(i, e, G, C, random.Random(11), beta=0.4, compat=True, wfun=gram_prob(G))
        if pi:
            P = apply_template(P, G, hd, ed, pi, random.Random(19))
        show(f"モデル {lang} π = {pi}", measure(P, lastf(P), rng))
        s2, sm = strength([l for ls in P.values() for l in ls])
        print(f"     位置の型: 2 語目 sh/ch {s2:.0%}、行の最後 -m {sm:.1%}")


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    n41(V)
    print(f"\n  {'':<26}" + " ".join(f"{k:>7}" for k in KEYS))
    print("=== N39 位置の型をモデルに（言語 B）===")
    run("B", V, caesar, rng, (0.0, 0.5))
    print("=== N40 言語 A ===")
    run("A", V, caesar, rng, (0.0, 0.5))


if __name__ == "__main__":
    main()

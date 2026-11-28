#!/usr/bin/env python3
"""nēvo による解析 第 19 巡: N57（単純な逆読み）・N54（対数で長さを寄せる符号表）・N55（言語 A の語の頭）・N56（語頭と語末を同時に）。

    python3 voynich/nevo_round19.py <Caesar> <その他の文章 …>
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import self_citation as sc  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import pos_dists, positions  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round18 import apply_family2  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def H(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values())


def profile(words_t, pages_str, char_mode):
    e = unit_entropy.entropies([list(w) for w in words_t])
    sc.CHAR_MODE = char_mode
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    same, _ = word_families.pairs(pages_str)
    c = Counter(p for p, _, _ in same)
    n = max(1, len(same))
    hf = H(Counter(w[0] for w in words_t))
    hl = H(Counter(w[-1] for w in words_t))
    return f"h1 {e['h1']:.2f} h2 {e['h2']:.2f}  T1 頭 {c['語頭'] / n:.0%} 中 {c['語中'] / n:.0%} 末 {c['語末'] / n:.0%}  最初/最後の情報量 {hf / hl:.2f}"


def n57(V, paths):
    print("=== N57 単純な逆読み ===")
    for lang in ("A", "B"):
        pt, ps, _ = V[lang]
        words = [w for ls in pt.values() for l in ls for w in l]
        print(f"  ヴォイニッチ {lang} そのまま : {profile(words, ps, False)}")
        rp = {k: [["".join(reversed(w)) for w in l] for l in ls] for k, ls in pt.items()}
        print(f"  ヴォイニッチ {lang} 逆読み   : {profile([w[::-1] for w in words], rp, False)}")
    for p in paths:
        ws = ["".join(w) for w in unit_entropy.latin_words(p)][:20000]
        pages = {pg: ls for pg, ls in line_unit.wrap(ws, 37)}
        print(f"  {p.stem:<10} そのまま     : {profile([tuple(w) for w in ws], pages, True)}")
        rp = {pg: [[w[::-1] for w in l] for l in ls] for pg, ls in pages.items()}
        print(f"  {p.stem:<10} 逆読み       : {profile([tuple(w[::-1]) for w in ws], rp, True)}")
    sys.stdout.flush()


def centered_source(caesar, G, muv, sdv, rng, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    by_len = defaultdict(list)
    for w, _ in gen.most_common():
        by_len[len(w)].append(w)
    pos = defaultdict(int)
    types = [w for w, _ in Counter(caesar).most_common()]
    lnl = [math.log(len(t)) for t in types]
    m, s = statistics.mean(lnl), statistics.pstdev(lnl)
    book = {}
    for t, x in zip(types, lnl):
        Lt = max(1, round(muv + sdv / s * (x - m)))
        for L in sorted(by_len, key=lambda L: (abs(L - Lt), L)):
            if pos[L] < len(by_len[L]):
                book[t] = by_len[L][pos[L]]
                pos[L] += 1
                break
        else:
            book[t] = G.word(rng)
    half = len(caesar) // 2
    it = iter([book[w] for w in caesar[:half]])
    edge = [book[w] for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None))


def apply_joint2(P, G, gen, by_tail, dists, ed, eps, rng):
    first, firstp, last = dists
    heads, ends = list(G.hk), list(G.ek)
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w, p = l[i], positions(l)[i]
                h, m, e = split(w)
                base = list(dict.fromkeys([c for c in (hh + m + e for hh in heads) if c] + list(by_tail.get(w[1:], ()))))
                cands = []
                for b in base:
                    bh, bm, _ = split(b)
                    key = bm[-1] if bm else ("H",) + bh
                    for x in [x for x in ends if G.em[key][x] > 0] or [split(b)[2]]:
                        c = (bh + bm + x) or b
                        if c not in cands:
                            cands.append(c)
                mx = max(gen[c] for c in cands) or 1
                fd = first[(p, new[-1][-1])]
                if sum(fd.values()) < 20:
                    fd = firstp[p]
                wts = [(fd[c[0]] + 0.5) * (ed[p][split(c)[2]] + 0.5) * (last[p][c[-1]] + 0.5) * (gen[c] / mx + eps) for c in cands]
                new.append(rng.choices(cands, wts)[0])
            ls[li] = new
    return P


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:]]
    caesar = ["".join(w) for w in unit_entropy.latin_words(paths[0])]
    rng = random.Random(2026)
    V = voynich()
    n57(V, paths)
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        lens = [len(w) for ls in pt.values() for l in ls for w in l]
        muv, sdv = statistics.mean(lens), statistics.pstdev(lens)
        G = LinkedGrammar(pt)
        C = Compat(G, pt)
        runs = []
        for seed in (1, 2):
            i, e = centered_source(caesar, G, muv, sdv, random.Random(seed))
            P = build12(i, e, G, C, random.Random(seed + 10), beta=0.4, compat=True, wfun=gram_prob(G))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("N54 対数で寄せる符号表", runs)
        sys.stdout.flush()
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        gr = random.Random(7)
        gen = Counter(LG.word(gr) for _ in range(300000))
        by_tail = defaultdict(set)
        for w in gen:
            by_tail[w[1:]].add(w)
        dists = boundary_dists(pt)
        _, ed = pos_dists(pt)
        # N55
        i, e, _ = matched_source(caesar, LG, random.Random(1))
        P = build12(i, e, LG, LC, random.Random(11), beta=0.0, compat=True, wfun=gram_prob(LG))
        P = apply_family2(P, LG, gen, by_tail, dists, ed, 0.3, random.Random(21), False)
        vf = Counter(w[0] for ls in pt.values() for l in ls for w in l)
        mf = Counter(w[0] for ls in P.values() for l in ls for w in l)
        nv, nm = sum(vf.values()), sum(mf.values())
        diff = sorted(set(vf) | set(mf), key=lambda g: -abs(vf[g] / nv - mf[g] / nm))[:8]
        print("  N55 最初の字形の割合（ヴォイニッチ → モデル N51）: " + ", ".join(f"{g} {vf[g] / nv:.1%}→{mf[g] / nm:.1%}" for g in diff))
        for name, PP in (("ヴォイニッチ", pt), ("モデル N51", P)):
            pairs = [(a[-1], b[0]) for ls in PP.values() for l in ls if len(l) >= 4 for a, b in zip(l[1:-1], l[2:-1])]
            print(f"     境目の結び付き I(前の最後; 次の最初) {name}: {line_unit.mi(pairs):.3f}（{len(pairs)} 組）")
        sys.stdout.flush()
        # N56
        runs = []
        for seed in (1, 2, 3):
            i, e, _ = matched_source(caesar, LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            P = apply_joint2(P, LG, gen, by_tail, dists, ed, 0.3, random.Random(seed + 20))
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("N56 語頭と語末を同時に", runs)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

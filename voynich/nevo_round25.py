#!/usr/bin/env python3
"""nēvo による解析 第 25 巡: N73（平文なしに写しを戻す）・N74（平文あり・なしの比較）・N75（最初の字形の組を細かく）。

    python3 voynich/nevo_round25.py <Caesar>
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
from nevo_round14 import positions, pos_dists  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round18 import apply_family2  # noqa: E402
from nevo_round24 import firstglyph_source  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def first_table(pt):
    T = defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            if len(l) >= 4:
                for a, b in zip(l[1:-1], l[2:-1]):
                    T[a[-1]][b[0]] += 1
    return T


def build_cond(G, C, pt, rng, c=0.4, q=0.25, width=37, cap=30000, lpp=25, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    byg = defaultdict(lambda: ([], []))
    for w, k in gen.items():
        byg[w[0]][0].append(w)
        byg[w[0]][1].append(k)
    allw, allc = zip(*gen.items())
    T = first_table(pt)
    wfun = gram_prob(G)

    def fresh(prev):
        d = T.get(prev[-1]) if prev else None
        if d:
            gs = [g for g in d if byg[g][0]]
            if gs:
                g = rng.choices(gs, [d[x] for x in gs])[0]
                return rng.choices(*byg[g])[0]
        return rng.choices(allw, allc)[0]

    lines, inner, cur, cur_len, total = [], [], [], 0, 0
    W = width

    def pick():
        recent = inner[-10:]
        ws = [(1 / (len(recent) - i), l) for i, l in enumerate(recent) if l]
        if not ws:
            return None
        r = rng.random() * sum(x for x, _ in ws)
        line = ws[-1][1]
        for x, l in ws:
            r -= x
            if r <= 0:
                line = l
                break
        return rng.choices(line, [wfun(w) for w in line])[0]

    def close(line):
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        a = fresh(None)
        b = min([fresh(None), fresh(None)], key=len)
        if rng.random() < q:
            a = (rng.choice("ptk"),) + a
        inner.append(list(line))
        lines.append([a] + line + [b])

    while total < cap:
        w = None
        if rng.random() < c:
            w = pick()
            if w is not None and rng.random() < 0.5:
                w = C.mutate(w, rng)
        if w is None:
            w = fresh(cur[-1] if cur else None)
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > W - 12:
            close(cur)
            total += len(cur) + 2
            cur, cur_len, add = [], 0, len(w)
            W = width * rng.uniform(0.7, 1.3)
        cur.append(w)
        cur_len += add
    if cur:
        close(cur)
    return {f"p{i // lpp}": lines[i:i + lpp] for i in range(0, len(lines), lpp)}


TOL = {"h2": 0.15, "歪度": 0.15, "T1頭": 0.08, "T1中": 0.08, "T1末": 0.08, "T2": 0.10, "T3": 4, "V2": 0.05, "V3": 0.10,
       "V4": 0.07, "G1": 0.30, "G10": 0.30, "隣": 0.07, "行頭だけ": 0.08, "2語目": 0.08, "-m": 0.05, "行長CV": 0.08,
       "末/内": 0.10, "境目%2": 0.10, "境目%語": 0.10}


def score(label, runs, ref):
    avg = {k: statistics.mean(r[k] for r in runs if isinstance(r[k], (int, float)) and r[k] == r[k]) for k in TOL}
    n8 = statistics.mean(int(r["8量"].split("/")[0]) for r in runs)
    ex = statistics.mean(r["またぐ"] for r in runs)
    ok = {k: abs(avg[k] - ref[k]) <= TOL[k] for k in TOL}
    ok["8量≥7"] = n8 >= 7
    ok["またぐ≤0.03"] = ex <= 0.03
    hit = sum(ok.values())
    print(f"  {label}: {hit}/{len(ok)} 入る  外れ: " + ", ".join(f"{k}（{avg[k]:.2f} 対 {ref[k]:.2f}）" if k in avg else k for k, v in ok.items() if not v))
    return hit


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        summarize(f"ヴォイニッチ {lang}", [ref])
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        runs73 = []
        for seed in (1, 2, 3):
            P = build_cond(LG, LC, pt, random.Random(seed))
            runs73.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("N73 平文なし・写しあり", runs73)
        sys.stdout.flush()
        gen = Counter(LG.word(random.Random(7)) for _ in range(300000))
        by_tail = defaultdict(set)
        for w in gen:
            by_tail[w[1:]].add(w)
        dists = boundary_dists(pt)
        _, ed = pos_dists(pt)
        runs51 = []
        for seed in (1, 2, 3):
            i, e, _ = matched_source(caesar, LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            P = apply_family2(P, LG, gen, by_tail, dists, ed, 0.3, random.Random(seed + 20), False)
            runs51.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("平文あり（N51 の作り方）", runs51)
        print("=== N74 23 の量での比較 ===")
        score("平文あり（N51）", runs51, ref)
        score("平文なし（N73）", runs73, ref)
        sys.stdout.flush()
        first, firstp, _ = dists
        runs75 = []
        for seed in (1, 2, 3):
            fg = Counter()
            for w, k in gen.items():
                fg[w[0]] += k
            K = sum(1 for g, k in fg.items() if k / sum(fg.values()) >= 0.005)
            i, e, variants, w2t = firstglyph_source(caesar, LG, random.Random(seed), K=K)
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            rs = random.Random(seed + 20)
            for ls in P.values():
                for li, l in enumerate(ls):
                    if len(l) < 4:
                        continue
                    new = [l[0]]
                    for j in range(1, len(l)):
                        w, p = l[j], positions(l)[j]
                        t = w2t.get(w)
                        if t is None:
                            new.append(w)
                            continue
                        fd = first[(p, new[-1][-1])]
                        if sum(fd.values()) < 20:
                            fd = firstp[p]
                        cands = variants[t]
                        new.append(rs.choices(cands, [fd[x[0]] + 0.5 for x in cands])[0])
                    ls[li] = new
            runs75.append(with_strength(measure(P, lastf(P), rng), P))
        summarize(f"N75 最初の字形の組を細かく（K = {K}）", runs75)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

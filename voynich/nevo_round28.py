#!/usr/bin/env python3
"""nēvo による解析 第 28 巡: N82（語彙がゆっくり移り変わる仕組み）・N83（項目ごとに話題が変わる平文）。

    python3 voynich/nevo_round28.py <Caesar> <Culpeper>
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import pos_dists  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round18 import apply_family2  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round25 import first_table, score  # noqa: E402
from nevo_round27 import page_sim  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def build_drift(G, C, pt, rng, rho, size=600, mu=0.1, c=0.4, gamma=2.0, q=0.25, width=37, cap=30000, lpp=25, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    allw, allc = zip(*gen.items())

    def sample_new(k, exclude):
        out = set()
        while len(out) < k:
            w = rng.choices(allw, allc)[0]
            if w not in exclude:
                out.add(w)
        return out

    active = sample_new(size, set())
    T = first_table(pt)
    marg = Counter()
    for d in T.values():
        marg.update(d)
    mt = sum(marg.values())
    wfun = gram_prob(G)
    follow = defaultdict(Counter)

    def byg():
        b = defaultdict(lambda: ([], []))
        for w in active:
            b[w[0]][0].append(w)
            b[w[0]][1].append(gen[w])
        return b

    groups = byg()

    def cond_w(prev, w):
        d = T.get(prev[-1]) if prev else None
        if not d:
            return 1.0
        return ((d[w[0]] + 0.5) / sum(d.values()) / ((marg[w[0]] + 0.5) / mt)) ** gamma

    def fresh(prev):
        if prev and mu and follow[prev] and rng.random() < mu:
            k, v = zip(*follow[prev].items())
            return rng.choices(k, v)[0]
        d = T.get(prev[-1]) if prev else None
        if d:
            gs = [g for g in d if groups[g][0]]
            if gs:
                g = rng.choices(gs, [d[x] for x in gs])[0]
                return rng.choices(*groups[g])[0]
        ws = list(active)
        return rng.choices(ws, [gen[w] for w in ws])[0]

    lines, inner, cur, cur_len, total = [], [], [], 0, 0
    W = width

    def pick(prev):
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
        return rng.choices(line, [wfun(w) * cond_w(prev, w) for w in line])[0]

    def close(line):
        nonlocal active, groups
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        a = fresh(None)
        b = min([fresh(None), fresh(None)], key=len)
        if rng.random() < q:
            a = (rng.choice("ptk"),) + a
        inner.append(list(line))
        full = [a] + line + [b]
        for x, y in zip(full[1:-1], full[2:-1]):
            follow[x][y] += 1
        lines.append(full)
        if len(lines) % lpp == 0:
            out = set(rng.sample(sorted(active), int(rho * size)))
            active = (active - out) | sample_new(len(out), active)
            groups = byg()

    while total < cap:
        prev = cur[-1] if cur else None
        w = None
        if rng.random() < c:
            w = pick(prev)
            if w is not None and rng.random() < 0.5:
                w = C.mutate(w, rng)
        if w is None:
            w = fresh(prev)
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


def main() -> None:
    cae, cul = Path(sys.argv[1]), Path(sys.argv[2])
    rng = random.Random(2026)
    V = voynich()
    print("=== 参照: 平文そのもの（文字, 25 行で 1 頁）===")
    words = {}
    for p in (cae, cul):
        ws = words_any(p)[:30000]
        words[p.stem] = ws
        page_sim(p.stem, {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in line_unit.wrap(ws, 37)})
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        page_sim(f"ヴォイニッチ {lang}", pt)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        print("=== N82 語彙がゆっくり移り変わる（平文なし）===", flush=True)
        for rho in (0.1, 0.3):
            runs = []
            for seed in (1, 2):
                P = build_drift(LG, LC, pt, random.Random(seed), rho)
                page_sim(f"ρ {rho} 種 {seed}", P)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(f"ρ {rho}", runs)
            score(f"ρ {rho}", runs, ref)
            sys.stdout.flush()
        print("=== N83 Culpeper の平文ありのモデル ===", flush=True)
        gr = random.Random(7)
        gen = Counter(LG.word(gr) for _ in range(300000))
        by_tail = defaultdict(set)
        for w in gen:
            by_tail[w[1:]].add(w)
        runs = []
        for seed in (1, 2):
            i, e, _ = matched_source(words[cul.stem], LG, random.Random(seed))
            P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            P = apply_family2(P, LG, gen, by_tail, boundary_dists(pt), pos_dists(pt)[1], 0.3, random.Random(seed + 20), False)
            page_sim(f"Culpeper の平文あり 種 {seed}", P)
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("Culpeper の平文あり", runs)
        score("Culpeper の平文あり", runs, ref)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

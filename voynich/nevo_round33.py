#!/usr/bin/env python3
"""nēvo による解析 第 33 巡: N97（遠くからの写し）・N98（行の位置を語の選び方に入れる）・N99（採点の大きさをそろえる）。

    python3 voynich/nevo_round33.py n97|n98|n99
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round13 import gram_prob  # noqa: E402
from nevo_round14 import positions  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round25 import first_table, score  # noqa: E402
from nevo_round26 import build_cond2  # noqa: E402
from nevo_round27 import page_sim  # noqa: E402
from nevo_round29 import build_fav  # noqa: E402
from nevo_round31 import V_AFF, V_CORE, retain  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
POS = ("行の 1 語目", "内側の 1 語目", "内側の最後", "行の最後")


def build33(G, C, pt, rng, far=0.0, D=500, pos=False, mu=0.1, c=0.4, gamma=2.0, q=0.25, width=37, cap=30000, lpp=25, n=300000):
    """N77 の作り方（γ 2）＋ 遠くからの写し（far）＋ 行の位置での選び直し（pos）。"""
    gen = Counter(G.word(rng) for _ in range(n))
    allw, allc = zip(*gen.items())
    byg = defaultdict(lambda: ([], []))
    for w, k in gen.items():
        byg[w[0]][0].append(w)
        byg[w[0]][1].append(k)
    T = first_table(pt)
    marg = Counter()
    for d in T.values():
        marg.update(d)
    mt = sum(marg.values())
    wfun = gram_prob(G)
    follow = defaultdict(Counter)
    # 位置ごとの分布
    first, firstp, last = boundary_dists(pt)
    first1 = Counter(l[0][0] for ls in pt.values() for l in ls if len(l) >= 4)
    lastall = Counter()
    for d in last.values():
        lastall.update(d)
    la = sum(lastall.values())
    posw = {}
    for p in POS:
        tot = sum(last[p].values())
        ratio = {x: ((last[p][x] + 0.5) / tot) / ((lastall[x] + 0.5) / la) for x in lastall}
        posw[p] = {g: [k * ratio.get(w[-1], 0.5 / tot * la) for w, k in zip(*byg[g])] for g in byg}

    def pos_word(p, prev):
        if p == "行の 1 語目":
            fd = first1
        else:
            fd = first[(p, prev[-1])]
            if sum(fd.values()) < 20:
                fd = firstp[p]
        gs = [g for g in fd if g in posw[p]]
        if not gs:
            return fresh(prev)
        g = rng.choices(gs, [fd[x] for x in gs])[0]
        return rng.choices(byg[g][0], posw[p][g])[0]

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
            gs = [g for g in d if byg[g][0]]
            if gs:
                g = rng.choices(gs, [d[x] for x in gs])[0]
                return rng.choices(*byg[g])[0]
        return rng.choices(allw, allc)[0]

    lines, inner, cur, cur_len, total = [], [], [], 0, 0
    W = width

    def pick(prev):
        line = None
        if far and len(inner) > 10 and rng.random() < far:
            hi = min(D, len(inner))
            d = int(round(math.exp(rng.uniform(math.log(10), math.log(hi)))))
            line = inner[-d] or None
        if line is None:
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
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        if pos:
            full = [None] + list(line) + [None]
            full[0] = pos_word(POS[0], None)
            if len(full) >= 4:
                full[1] = pos_word(POS[1], full[0])
                full[-2] = pos_word(POS[2], full[-3])
            full[-1] = pos_word(POS[3], full[-2])
        else:
            a = fresh(None)
            b = min([fresh(None), fresh(None)], key=len)
            if rng.random() < q:
                a = (rng.choice("ptk"),) + a
            full = [a] + line + [b]
        inner.append(list(full[1:-1]))
        for x, y in zip(full[1:-1], full[2:-1]):
            follow[x][y] += 1
        lines.append(full)

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


def run(V, rng, title, confs, sim=True):
    print(f"=== {title} ===", flush=True)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        print(f"######## 言語 {lang}（{cap} 語にそろえる）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        for name, f in confs:
            runs = []
            for seed in (1, 2):
                P = f(LG, LC, pt, random.Random(seed), cap)
                if sim:
                    page_sim(f"{name} 種 {seed}", P)
                    retain(f"{name} {lang} 種 {seed}", P, V_CORE, V_AFF)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(name, runs)
            for r in runs:  # 定義できない値（語 × 語の結び付きが 0 以下）は外れとして数える
                for k, v in r.items():
                    if isinstance(v, float) and v != v:
                        r[k] = -9.0
            score(name, runs, ref)
            sys.stdout.flush()


if __name__ == "__main__":
    V = voynich()
    rng = random.Random(2026)
    part = sys.argv[1]
    if part == "n99":
        run(V, rng, "N99 採点の大きさをそろえる", [
            ("平文なしの最良", lambda G, C, pt, r, cap: build_cond2(G, C, pt, r, mu=0.1, c=0.4, gamma=2.0, cap=cap)),
            ("好みの芯", lambda G, C, pt, r, cap: build_fav(G, C, pt, r, 0.5, size=60, core=True, cap=cap))], sim=False)
    elif part == "n97":
        run(V, rng, "N97 遠くからの写し", [
            ("c 0.4 λ 0.5", lambda G, C, pt, r, cap: build33(G, C, pt, r, far=0.5, c=0.4, cap=cap)),
            ("c 0.6 λ 0.5", lambda G, C, pt, r, cap: build33(G, C, pt, r, far=0.5, c=0.6, cap=cap))])
    elif part == "n98":
        run(V, rng, "N98 行の位置を語の選び方に入れる", [
            ("土台＋位置", lambda G, C, pt, r, cap: build33(G, C, pt, r, pos=True, cap=cap)),
            ("土台＋位置＋遠くからの写し", lambda G, C, pt, r, cap: build33(G, C, pt, r, pos=True, far=0.5, c=0.6, cap=cap))])

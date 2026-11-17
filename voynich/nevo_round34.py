#!/usr/bin/env python3
"""nēvo による解析 第 34 巡: N100（行の仕組みの仕上げ）・N101（頁のまとまりを採点に入れる）・N102（1 回だけの語）。

    python3 voynich/nevo_round34.py n100|n101|n102
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round13 import gram_prob  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round25 import first_table, score  # noqa: E402
from nevo_round30 import ratio  # noqa: E402
from nevo_round31 import V_AFF, V_CORE, surrogate  # noqa: E402
from nevo_round33 import POS  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
C_LANG = {"A": 0.4, "B": 0.6}
REF_SIM = {"A": 1.35, "B": 1.41}


def build34(G, C, pt, rng, c=0.4, mark=0.0, mu2=0.0, phis=(0.0, 0.0), sizes=(300, 60), rho=0.05, live=False, mut=0.5, favpos=False,
            mu=0.1, gamma=2.0, width=37, cap=30000, lpp=25, n=300000):
    """N98 の「土台 ＋ 位置」に、頭の印（mark）・位置の語の言い回しのくり返し（mu2）・好みの語と芯（phis）・
    毎回型から作る（live）・写しを替える割合（mut）を足したもの。"""
    gen = Counter(G.word(rng) for _ in range(n))
    allw, allc = zip(*gen.items())
    byg = defaultdict(lambda: ([], []))
    for w, k in gen.items():
        byg[w[0]][0].append(w)
        byg[w[0]][1].append(k)
    # 好みの語・芯
    keys, skips = (lambda w: w, V_CORE), (50, 10)
    members, pools, favs, fgs = [], [], [], []
    for key, sk in zip(keys, skips):
        cnt, mem = Counter(), defaultdict(list)
        for w, k in gen.items():
            cnt[key(w)] += k
            mem[key(w)].append(w)
        skip = {u for u, _ in cnt.most_common(sk)}
        pools.append(tuple(zip(*[(u, k) for u, k in cnt.items() if u not in skip])))
        members.append(mem)

    def sample_new(i, k, exclude):
        out = set()
        while len(out) < k:
            u = rng.choices(*pools[i])[0]
            if u not in exclude:
                out.add(u)
        return out

    def groups_of(i):
        b = defaultdict(lambda: ([], []))
        for u in favs[i]:
            for w in members[i][u]:
                b[w[0]][0].append(w)
                b[w[0]][1].append(gen[w])
        return b

    for i in range(2):
        favs.append(sample_new(i, sizes[i], set()) if phis[i] else set())
        fgs.append(groups_of(i))
    T = first_table(pt)
    marg = Counter()
    for d in T.values():
        marg.update(d)
    mt = sum(marg.values())
    wfun = gram_prob(G)
    follow = defaultdict(Counter)
    first, firstp, last = boundary_dists(pt)
    first1 = Counter(l[0][0] for ls in pt.values() for l in ls if len(l) >= 4)
    lastall = Counter()
    for d in last.values():
        lastall.update(d)
    la = sum(lastall.values())
    pratio, posw = {}, {}
    for p in POS:
        tot = sum(last[p].values())
        pratio[p] = defaultdict(lambda tot=tot: 0.5 / tot * la, {x: ((last[p][x] + 0.5) / tot) / ((lastall[x] + 0.5) / la) for x in lastall})
        posw[p] = {g: [k * pratio[p][w[-1]] for w, k in zip(*byg[g])] for g in byg}

    def pos_word(p, prev):
        if p == POS[0]:
            fd = first1
        else:
            fd = first[(p, prev[-1])]
            if sum(fd.values()) < 20:
                fd = firstp[p]
            if mu2 and follow[prev] and rng.random() < mu2:
                ks = list(follow[prev])
                return rng.choices(ks, [follow[prev][w] * (fd[w[0]] + 0.5) * pratio[p][w[-1]] for w in ks])[0]
        gs = [g for g in fd if g in posw[p]]
        if not gs:
            return fresh(prev)
        g = rng.choices(gs, [fd[x] for x in gs])[0]
        if favpos and fgs[0][g][0] and rng.random() < phis[0]:  # 第 35 巡 N103: 位置で選ぶときも好みの語から
            ws, ks = fgs[0][g]
            return rng.choices(ws, [k * pratio[p][w[-1]] for w, k in zip(ws, ks)])[0]
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
        r, which = rng.random(), None
        for i in range(2):
            if r < phis[i]:
                which = i
                break
            r -= phis[i]
        d = T.get(prev[-1]) if prev else None
        if d:
            gs = [g for g in d if byg[g][0]]
            if gs:
                g = rng.choices(gs, [d[x] for x in gs])[0]
                if which is not None and fgs[which][g][0]:
                    return rng.choices(*fgs[which][g])[0]
                if live:
                    for _ in range(40):
                        w = G.word(rng)
                        if w and w[0] == g:
                            return w
                return rng.choices(*byg[g])[0]
        return rng.choices(allw, allc)[0]

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
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        full = [None] + list(line) + [None]
        full[0] = pos_word(POS[0], None)
        if mark and rng.random() < mark:
            full[0] = (rng.choice("ptk"),) + full[0]
        if len(full) >= 4:
            full[1] = pos_word(POS[1], full[0])
            full[-2] = pos_word(POS[2], full[-3])
        full[-1] = pos_word(POS[3], full[-2])
        inner.append(list(full[1:-1]))
        for x, y in zip(full[1:-1], full[2:-1]):
            follow[x][y] += 1
        lines.append(full)
        if len(lines) % lpp == 0:
            for i in range(2):
                if phis[i]:
                    out = set(rng.sample(sorted(favs[i]), max(1, int(rho * sizes[i]))))
                    favs[i] = (favs[i] - out) | sample_new(i, len(out), favs[i])
                    fgs[i] = groups_of(i)

    while total < cap:
        prev = cur[-1] if cur else None
        w = None
        if rng.random() < c:
            w = pick(prev)
            if w is not None and rng.random() < mut:
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


def sim_ret(P):
    r0 = ratio(P)
    rm = statistics.mean(ratio(surrogate(P, V_CORE, random.Random(s))[0]) for s in range(5))
    return r0, (rm - 1) / (r0 - 1) if abs(r0 - 1) > 0.02 else float("nan")


def scored(name, lang, builder, ref, rng, extra=False):
    runs, sims = [], []
    for seed in (1, 2):
        P = builder(random.Random(seed))
        sims.append(sim_ret(P))
        runs.append(with_strength(measure(P, lastf(P), rng), P))
    summarize(name, runs)
    for r in runs:
        for k, v in r.items():
            if isinstance(v, float) and v != v:
                r[k] = -9.0
    hit = score(name, runs, ref)
    s = statistics.mean(x for x, _ in sims)
    rets = [y for _, y in sims if y == y]
    ret = statistics.mean(rets) if rets else float("nan")
    print(f"  {name}: まとまり {s:.2f}（{sims[0][0]:.2f}・{sims[1][0]:.2f}）  芯を保つ置き換えで残る {ret:.0%}", flush=True)
    if extra:
        ok1 = abs(s - REF_SIM[lang]) <= 0.10
        if lang == "A":
            ok2 = ret == ret and abs(ret - 0.71) <= 0.15
            print(f"  {name}: 24 の量で {hit + ok1 + ok2}/24（まとまり {'入る' if ok1 else '外れ'}・残る割合 {'入る' if ok2 else '外れ'}）", flush=True)
        else:
            print(f"  {name}: 23 の量で {hit + ok1}/23（まとまり {'入る' if ok1 else '外れ'}）", flush=True)


def main():
    V = voynich()
    rng = random.Random(2026)
    part = sys.argv[1]
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語、写し {c}）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        b = lambda **kw: (lambda r: build34(LG, LC, pt, r, c=c, cap=cap, **kw))  # noqa: E731
        if part == "n100":
            scored("土台＋位置（写しを言語ごとに）", lang, b(), ref, rng)
            scored("(i) ＋頭の印", lang, b(mark=0.25), ref, rng)
            scored("(ii) ＋頭の印＋位置の語の言い回し", lang, b(mark=0.25, mu2=0.3), ref, rng)
        elif part == "n102":
            scored("(a) 毎回型から作る", lang, b(live=True), ref, rng)
            scored("(b) 写しを替える割合 0.8", lang, b(mut=0.8), ref, rng)
        elif part == "n101":
            grid = []
            for pw in (0.0, 0.3, 0.5):
                for pc in (0.0, 0.3):
                    for rho in (0.05, 0.02):
                        if pw == pc == 0:
                            continue
                        P = b(mark=0.25, mu2=0.3, phis=(pw, pc), rho=rho)(random.Random(1))
                        s, ret = sim_ret(P)
                        grid.append((pw, pc, rho, s, ret))
                        print(f"  φw {pw} φc {pc} ρ {rho}: まとまり {s:.2f}  芯を保つ置き換えで残る {ret:.0%}", flush=True)
            inside = [g for g in grid if abs(g[3] - REF_SIM[lang]) <= 0.10]
            if inside:
                best = min(inside, key=lambda g: (g[0] + g[1], -g[2]))
            else:
                best = min(grid, key=lambda g: abs(g[3] - REF_SIM[lang]))
            print(f"  選んだ設定: φw {best[0]} φc {best[1]} ρ {best[2]}（許容の幅に入った設定 {len(inside)}）", flush=True)
            scored(f"選んだ設定（φw {best[0]} φc {best[1]} ρ {best[2]}）", lang, b(mark=0.25, mu2=0.3, phis=best[:2], rho=best[2]), ref, rng, extra=True)
            scored("好みなし（N100 の (ii)）", lang, b(mark=0.25, mu2=0.3), ref, rng, extra=True)


if __name__ == "__main__":
    main()

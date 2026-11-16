#!/usr/bin/env python3
"""nēvo による解析 第 32 巡: N94（混ぜたモデル）・N95（言語 B の語頭・語末の移り変わり）・N96（頁の半分で作って残りで採点）。

    python3 voynich/nevo_round32.py n94|n95|n96
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round13 import gram_prob  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round25 import first_table, score  # noqa: E402
from nevo_round26 import build_cond2  # noqa: E402
from nevo_round27 import page_sim  # noqa: E402
from nevo_round29 import build_fav  # noqa: E402
from nevo_round30 import jac  # noqa: E402
from nevo_round31 import V_AFF, V_CORE, retain, surrogate  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def build_mix(G, C, pt, rng, phis, sizes=(300, 60, 30), rho=0.05, mu=0.1, c=0.4, gamma=2.0, q=0.25, width=37, cap=30000, lpp=25, n=300000):
    """好みの語・芯・語頭語末の組を、確率 phis = (φw, φc, φa) で混ぜる。"""
    gen = Counter(G.word(rng) for _ in range(n))
    allw, allc = zip(*gen.items())
    keys = (lambda w: w, V_CORE, V_AFF)
    skips = (50, 10, 5)
    byg = defaultdict(lambda: ([], []))
    for w, k in gen.items():
        byg[w[0]][0].append(w)
        byg[w[0]][1].append(k)
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

    for i in range(3):
        favs.append(sample_new(i, sizes[i], set()) if phis[i] else set())
        fgs.append(groups_of(i))
    T = first_table(pt)
    marg = Counter()
    for d in T.values():
        marg.update(d)
    mt = sum(marg.values())
    wfun = gram_prob(G)
    follow = defaultdict(Counter)

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
        for i in range(3):
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
            for i in range(3):
                if phis[i]:
                    out = set(rng.sample(sorted(favs[i]), max(1, int(rho * sizes[i]))))
                    favs[i] = (favs[i] - out) | sample_new(i, len(out), favs[i])
                    fgs[i] = groups_of(i)

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


def n94(V, rng):
    print("=== N94 混ぜたモデル ===", flush=True)
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"######## 言語 {lang} ########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        for name, phis in (("設定 X（芯＋語）", (0.25, 0.35, 0.0)), ("設定 Y（芯＋語＋語頭語末）", (0.2, 0.25, 0.25))):
            runs = []
            for seed in (1, 2):
                P = build_mix(LG, LC, pt, random.Random(seed), phis)
                page_sim(f"{name} 種 {seed}", P)
                retain(f"{name} {lang} 種 {seed}", P, V_CORE, V_AFF)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(name, runs)
            score(name, runs, ref)
            sys.stdout.flush()


def meta_of():
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    return {ln.page.name: {k: ln.page.get(k) for k in "QBIFH"} for ln in lines}


def ratio_same(P, sect):
    pages = list(P.items())
    allw = Counter(w for _, ls in pages for l in ls for w in l)
    top = {w for w, _ in allw.most_common(50)}
    sets = [(sect[k], set(w for l in ls for w in l) - top) for k, ls in pages]
    num, den = [], []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            if sets[i][0] != sets[j][0] or not sets[i][1] or not sets[j][1]:
                continue
            d = j - i
            if 2 <= d <= 5:
                num.append(jac(sets[i][1], sets[j][1]))
            elif d >= 21:
                den.append(jac(sets[i][1], sets[j][1]))
    return statistics.mean(num) / statistics.mean(den), len(num), len(den)


def eta2(vals, groups):
    m = statistics.mean(vals)
    tot = sum((v - m) ** 2 for v in vals)
    by = defaultdict(list)
    for v, g in zip(vals, groups):
        by[g].append(v)
    between = sum(len(vs) * (statistics.mean(vs) - m) ** 2 for vs in by.values())
    return between / tot if tot else 0.0


def n95(V):
    meta = meta_of()
    print("=== N95 (1) 同じ挿絵の種類の頁の組だけで見たまとまりと、置き換えで残る割合 ===")
    for lang in ("A", "B"):
        pt = V[lang][0]
        sect = {k: meta[k]["I"] for k in pt}
        r0, n1, n2 = ratio_same(pt, sect)
        out = [f"  ヴォイニッチ {lang}  元 {r0:.2f}（組 {n1}・{n2}）"]
        for label, key in (("語頭・語末を保つ", V_AFF), ("芯を保つ", V_CORE)):
            rs = [ratio_same(surrogate(pt, key, random.Random(s))[0], sect)[0] for s in range(5)]
            m = statistics.mean(rs)
            out.append(f"{label} {m:.2f}[{min(rs):.2f}〜{max(rs):.2f}] 残る {(m - 1) / (r0 - 1):.0%}")
        print("   ".join(out), flush=True)
    print("\n=== N95 (2) 頁ごとの語頭・語末の割合のばらつきを説明する割合（η²）===")
    for lang in ("A", "B"):
        pt = {k: [w for l in ls for w in l] for k, ls in V[lang][0].items()}
        pt = {k: ws for k, ws in pt.items() if len(ws) >= 60}
        names = list(pt)
        fac = {f: [meta[k][f] for k in names] for f in "IQH"}
        print(f"--- 言語 {lang}（頁 {len(names)}、挿絵 {dict(Counter(fac['I']))}、書き手 {dict(Counter(fac['H']))}、綴じ {len(set(fac['Q']))}）---")
        for part, idx in (("語頭", 0), ("語末", 2)):
            cnt = Counter(split(w)[idx] for ws in pt.values() for w in ws)
            rows = []
            for u, _ in cnt.most_common(12):
                vals = [sum(split(w)[idx] == u for w in ws) / len(ws) for ws in pt.values()]
                bi = defaultdict(list)
                for v, g in zip(vals, fac["I"]):
                    bi[g].append(v)
                res = [v - statistics.mean(bi[g]) for v, g in zip(vals, fac["I"])]
                rows.append(("".join(u) or "（なし）", statistics.mean(vals), statistics.pstdev(vals) / (statistics.mean(vals) or 1),
                             eta2(vals, fac["I"]), eta2(vals, fac["Q"]), eta2(vals, fac["H"]), eta2(res, fac["Q"]), eta2(res, fac["H"])))
            rows.sort(key=lambda r: -r[2])
            print(f"  {part}: 字形 / 平均の割合 / ばらつき（標準偏差÷平均）/ η² 挿絵 / 綴じ / 書き手 / 挿絵を引いたあとの 綴じ / 書き手")
            for r in rows:
                print(f"    {r[0]:<8} {r[1]:.3f}  {r[2]:.2f}   {r[3]:.2f}  {r[4]:.2f}  {r[5]:.2f}   {r[6]:.2f}  {r[7]:.2f}")
            w = [r[1] for r in rows]
            avg = lambda i: sum(r[i] * x for r, x in zip(rows, w)) / sum(w)  # noqa: E731
            print(f"    割合で重みを付けた平均: 挿絵 {avg(3):.2f}  綴じ {avg(4):.2f}  書き手 {avg(5):.2f}   挿絵を引いたあと 綴じ {avg(6):.2f}  書き手 {avg(7):.2f}")


def n95b(V):
    """事後: N95 (1) を、各頁 60 語にそろえて測り直す（頁の長さの影響を除く）。"""
    meta = meta_of()
    print("=== N95 (1') 各頁 60 語にそろえた測り直し（事後）===")
    for lang in ("A", "B"):
        pt = {k: ls for k, ls in V[lang][0].items() if sum(len(l) for l in ls) >= 60}
        sect = {k: meta[k]["I"] for k in pt}

        def eq(P, seed):
            r = random.Random(seed)
            return {k: [r.sample([w for l in ls for w in l], 60)] for k, ls in P.items()}

        for scope, f in (("全ての組", lambda P: __import__("nevo_round30").ratio(P)), ("同じ挿絵の種類の組", lambda P: ratio_same(P, sect)[0])):
            r0 = statistics.mean(f(eq(pt, s)) for s in range(10))
            out = [f"  ヴォイニッチ {lang} {scope}  元 {r0:.2f}"]
            for label, key in (("語頭・語末を保つ", V_AFF), ("芯を保つ", V_CORE)):
                rs = [f(eq(surrogate(pt, key, random.Random(s))[0], s)) for s in range(10)]
                m = statistics.mean(rs)
                out.append(f"{label} {m:.2f}[{min(rs):.2f}〜{max(rs):.2f}] 残る {(m - 1) / (r0 - 1):.0%}")
            print("   ".join(out), flush=True)


def n96(V, rng):
    print("=== N96 頁の半分で作り、偶数番目の頁で採点 ===", flush=True)
    for lang in ("A", "B"):
        pt, last = V[lang][0], V[lang][2]
        names = list(pt)
        lastp, i = {}, 0
        for k in names:
            lastp[k] = last[i:i + len(pt[k])]
            i += len(pt[k])
        half = {s: {k: pt[k] for j, k in enumerate(names) if j % 2 == s} for s in (0, 1)}
        ref_last = [x for k in half[0] for x in lastp[k]]
        ref = with_strength(measure(half[0], ref_last, rng), half[0])
        print(f"######## 言語 {lang}（偶数番目 {len(half[0])} 頁、奇数番目 {len(half[1])} 頁）########", flush=True)
        summarize("基準（偶数番目の頁）", [ref])
        for cond, s in (("内", 0), ("外", 1)):
            src = half[s]
            LG = LengthGrammar(src)
            LC = Compat(LG, src)
            for name, f in (("平文なしの最良", lambda sd: build_cond2(LG, LC, src, random.Random(sd), mu=0.1, c=0.4, gamma=2.0)),
                            ("好みの芯", lambda sd: build_fav(LG, LC, src, random.Random(sd), 0.5, size=60, core=True))):
                runs = []
                for seed in (1, 2):
                    P = f(seed)
                    runs.append(with_strength(measure(P, lastf(P), rng), P))
                summarize(f"{name}・{cond}", runs)
                score(f"{name}・{cond}", runs, ref)
                sys.stdout.flush()


if __name__ == "__main__":
    V = voynich()
    rng = random.Random(2026)
    {"n94": lambda: n94(V, rng), "n95": lambda: n95(V), "n95b": lambda: n95b(V), "n96": lambda: n96(V, rng)}[sys.argv[1]]()

#!/usr/bin/env python3
"""nēvo による解析 第 29 巡: N85（話題を薄める手順）・N86（平文なしの語彙の移り変わり）・N87（綴じの単位）。

    python3 voynich/nevo_round29.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round14 import pos_dists, positions  # noqa: E402
from nevo_round16 import boundary_dists, summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round18 import apply_family2  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round25 import first_table, score  # noqa: E402
from nevo_round27 import BINS, page_sim  # noqa: E402
from nevo_round28 import build_drift  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
copyP = lambda P: {k: [list(l) for l in ls] for k, ls in P.items()}  # noqa: E731


def family_keep(P, G, gen, by_tail, dists, eps, rng, freq):
    """apply_family2 と同じ選び直しを、freq に入る語だけに掛ける。"""
    first, firstp, last = dists
    heads = list(G.hk)
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            pos = positions(l)
            for i in range(1, len(l)):
                w, p = l[i], pos[i]
                if w not in freq:
                    new.append(w)
                    continue
                h, m, e = split(w)
                cands = list(dict.fromkeys([c for c in (hh + m + e for hh in heads) if c] + list(by_tail.get(w[1:], ()))))
                mx = max(gen[c] for c in cands) or 1
                fd = first[(p, new[-1][-1])]
                if sum(fd.values()) < 20:
                    fd = firstp[p]
                ld = last[p]
                wts = [(fd[c[0]] + 0.5) * (ld[c[-1]] + 0.5) * (gen[c] / mx + eps) for c in cands]
                new.append(rng.choices(cands, wts)[0])
            ls[li] = new
    return P


def build_fav(G, C, pt, rng, phi, rho=0.05, size=300, mu=0.1, c=0.4, gamma=2.0, q=0.25, width=37, cap=30000, lpp=25, n=300000):
    """N77 の作り方 ＋ 確率 phi で「いま好んで使う語」から選ぶ。頁ごとに rho を入れ替える。"""
    gen = Counter(G.word(rng) for _ in range(n))
    top = {w for w, _ in gen.most_common(50)}
    allw, allc = zip(*gen.items())
    pool = [(w, k) for w, k in gen.items() if w not in top]
    pw, pc = zip(*pool)
    byg = defaultdict(lambda: ([], []))
    for w, k in gen.items():
        byg[w[0]][0].append(w)
        byg[w[0]][1].append(k)

    def sample_new(k, exclude):
        out = set()
        while len(out) < k:
            w = rng.choices(pw, pc)[0]
            if w not in exclude:
                out.add(w)
        return out

    fav = sample_new(size, set())

    def groups_of():
        b = defaultdict(lambda: ([], []))
        for w in fav:
            b[w[0]][0].append(w)
            b[w[0]][1].append(gen[w])
        return b

    fg = groups_of()
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
        usefav = rng.random() < phi
        d = T.get(prev[-1]) if prev else None
        if d:
            gs = [g for g in d if byg[g][0]]
            if gs:
                g = rng.choices(gs, [d[x] for x in gs])[0]
                if usefav and fg[g][0]:
                    return rng.choices(*fg[g])[0]
                return rng.choices(*byg[g])[0]
        if usefav:
            ws = sorted(fav)
            return rng.choices(ws, [gen[w] for w in ws])[0]
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
        nonlocal fav, fg
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
            out = set(rng.sample(sorted(fav), int(rho * size)))
            fav = (fav - out) | sample_new(len(out), fav)
            fg = groups_of()

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


def n87(V):
    print("\n=== N87 綴じの単位・挿絵の種類と頁のまとまり ===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    meta = {ln.page.name: (ln.page.get("Q"), ln.page.get("B"), ln.page.get("I"), ln.page.get("F")) for ln in lines}
    jac = lambda a, b: len(a & b) / len(a | b)  # noqa: E731
    for lang in ("A", "B"):
        pt = V[lang][0]
        allw = Counter(w for ls in pt.values() for l in ls for w in l)
        top = {w for w, _ in allw.most_common(50)}
        pg = [(k, set(w for l in ls for w in l) - top) for k, ls in pt.items()]
        pg = [(k, s) for k, s in pg if s]
        pairs = []
        for i in range(len(pg)):
            for j in range(i + 1, len(pg)):
                a, b = meta[pg[i][0]], meta[pg[j][0]]
                pairs.append((j - i, jac(pg[i][1], pg[j][1]), a, b))
        base = statistics.mean(p[1] for p in pairs)
        print(f"\n--- 言語 {lang}（頁 {len(pg)}、挿絵の種類 {dict(Counter(meta[k][2] for k, _ in pg))}）---")

        def row(name, sel):
            out = []
            for label, lo, hi in BINS:
                v = [p[1] for p in pairs if lo <= p[0] <= hi and sel(p)]
                out.append((label, statistics.mean(v) / base if len(v) >= 20 else None, len(v)))
            s = "  ".join(f"S({k}) {'—' if x is None else format(x, '.2f')}（{n}）" for k, x, n in out)
            d = {k: x for k, x, _ in out}
            r = f"{d['2〜5'] / d['21〜']:.2f}" if d["2〜5"] and d["21〜"] else "—"
            print(f"  {name:<24} {s}   S(2〜5)÷S(21〜) {r}")

        row("全ての頁の組", lambda p: True)
        row("同じ挿絵の種類", lambda p: p[2][2] == p[3][2])
        row("違う挿絵の種類", lambda p: p[2][2] != p[3][2])
        for kind in sorted({m[2] for m in (meta[k] for k, _ in pg)}):
            row(f"挿絵 {kind} どうし", lambda p, kind=kind: p[2][2] == p[3][2] == kind)
        row("同じ挿絵・同じ綴じ", lambda p: p[2][2] == p[3][2] and p[2][0] == p[3][0])
        row("同じ挿絵・違う綴じ", lambda p: p[2][2] == p[3][2] and p[2][0] != p[3][0])
        same_q = lambda p: p[2][0] == p[3][0]  # noqa: E731
        for name, sel in (("同じ綴じ・同じ紙（別の葉）", lambda p: same_q(p) and p[2][1] == p[3][1] and p[2][3] != p[3][3]),
                          ("同じ綴じ・違う紙", lambda p: same_q(p) and p[2][1] != p[3][1]),
                          ("同じ綴じ・同じ挿絵・同じ紙（別の葉）", lambda p: same_q(p) and p[2][2] == p[3][2] and p[2][1] == p[3][1] and p[2][3] != p[3][3]),
                          ("同じ綴じ・同じ挿絵・違う紙", lambda p: same_q(p) and p[2][2] == p[3][2] and p[2][1] != p[3][1])):
            v = [p[1] for p in pairs if sel(p)]
            dm = statistics.mean(p[0] for p in pairs if sel(p)) if v else 0
            print(f"  {name:<24} 重なり ÷ 全体 {statistics.mean(v) / base if len(v) >= 20 else float('nan'):.2f}（組 {len(v)}、平均の距離 {dm:.1f}）")


def main() -> None:
    cae = Path(sys.argv[1])
    rng = random.Random(2026)
    V = voynich()
    n87(V)
    sys.stdout.flush()
    caesar = words_any(cae)[:30000]
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        page_sim(f"ヴォイニッチ {lang}", pt)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        gr = random.Random(7)
        gen = Counter(LG.word(gr) for _ in range(300000))
        by_tail = defaultdict(set)
        for w in gen:
            by_tail[w[1:]].add(w)
        bd, pd = boundary_dists(pt), pos_dists(pt)[1]
        print("=== N85 手順を 1 つずつ足す（Caesar）===", flush=True)
        runs = []
        for seed in (1, 2):
            i, e, coded = matched_source(caesar, LG, random.Random(seed))
            page_sim(f"段 0 符号表だけ 種 {seed}", dict(line_unit.wrap(coded, 37)))
            for c, name in ((0.0, "段 1 行の組み立て"), (0.4, "段 2 ＋写し")):
                it = iter(coded)
                src = lambda: next(it, None)  # noqa: E731
                P = build12(src, src, LG, LC, random.Random(seed + 10), c=c, beta=0.0, compat=True, wfun=gram_prob(LG))
                page_sim(f"{name} 種 {seed}", P)
            P3 = apply_family2(copyP(P), LG, gen, by_tail, bd, pd, 0.3, random.Random(seed + 20), False)
            page_sim(f"段 3 ＋選び直し 種 {seed}", P3)
            freq = {w for w, _ in Counter(coded).most_common(200)}
            P3k = family_keep(copyP(P), LG, gen, by_tail, bd, 0.3, random.Random(seed + 20), freq)
            page_sim(f"段 3' 上位200語だけ選び直し 種 {seed}", P3k)
            runs.append(with_strength(measure(P3k, lastf(P3k), rng), P3k))
            Pr = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
            page_sim(f"参照a 端かき混ぜ・選び直しなし 種 {seed}", Pr)
            Pr = apply_family2(Pr, LG, gen, by_tail, bd, pd, 0.3, random.Random(seed + 20), False)
            page_sim(f"参照b いまのモデル 種 {seed}", Pr)
        summarize("段 3'", runs)
        score("段 3'", runs, ref)
        sys.stdout.flush()
        print("=== N86 平文なしの語彙の移り変わり ===", flush=True)
        confs = [("(a) 一覧 3000・ρ 0.03", lambda s: build_drift(LG, LC, pt, random.Random(s), 0.03, size=3000)),
                 ("(b) 好みの語 φ 0.3", lambda s: build_fav(LG, LC, pt, random.Random(s), 0.3)),
                 ("(b) 好みの語 φ 0.5", lambda s: build_fav(LG, LC, pt, random.Random(s), 0.5))]
        for name, f in confs:
            runs = []
            for seed in (1, 2):
                P = f(seed)
                page_sim(f"{name} 種 {seed}", P)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(name, runs)
            score(name, runs, ref)
            sys.stdout.flush()


if __name__ == "__main__":
    main()

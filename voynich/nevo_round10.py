#!/usr/bin/env python3
"""nēvo による解析 第 10 巡: N27（語の型から作るモデル）・N28（行の作り方）・N29（平文の有無を見分ける）。

    python3 voynich/nevo_round10.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402
from nevo_round2 import ed1, similar_words  # noqa: E402
from nevo_round5 import share_first_only  # noqa: E402
from nevo_round9 import adj_diff, g1_g10, m_measures, skew, voynich  # noqa: E402
from word_grammar import ENDS, HEADS  # noqa: E402


def split(g):
    head = ()
    for h in HEADS:
        if g[:len(h)] == h and len(g) > len(h):
            head, g = h, g[len(h):]
            break
    end = ()
    for e in ENDS:
        if len(g) >= len(e) and g[-len(e):] == e:
            end, g = e, g[:-len(e)]
            break
    return head, g, end


class Grammar:
    def __init__(self, pages_t):
        self.h, self.m, self.e = Counter(), Counter(), Counter()
        for ls in pages_t.values():
            for l in ls:
                for w in l:
                    a, b, c = split(w)
                    self.h[a] += 1
                    self.m[b] += 1
                    self.e[c] += 1
        self.hk, self.hw = zip(*self.h.items())
        self.mk, self.mw = zip(*self.m.items())
        self.ek, self.ew = zip(*self.e.items())
        self.heads = [h for h, _ in self.h.most_common(6)]
        self.mid_glyphs = [g for m in self.mk for g in m] or ["e"]

    def word(self, rng):
        while True:
            w = rng.choices(self.hk, self.hw)[0] + rng.choices(self.mk, self.mw)[0] + rng.choices(self.ek, self.ew)[0]
            if w:
                return w

    def new_head(self, w, rng):
        _, m, e = split(w)
        return (rng.choices(self.hk, self.hw)[0] + m + e) or w


def source_wp(caesar, G, rng):
    book, used = {}, set()
    for t in dict.fromkeys(caesar):
        for _ in range(20):
            w = G.word(rng)
            if w not in used:
                break
        book[t] = w
        used.add(w)
    half = len(caesar) // 2
    it = iter([book[w] for w in caesar[:half]])
    edge = [book[w] for w in caesar[half:]]
    rng.shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None))


def source_wn(G, rng, n_types=8000):
    lex = list(dict.fromkeys(G.word(rng) for _ in range(30000)))[:n_types]
    wts = [1 / r for r in range(1, len(lex) + 1)]
    f = lambda: rng.choices(lex, wts)[0]  # noqa: E731
    return f, f


def build(inner_src, edge_src, G, rng, c=0.4, beta=0.5, q=0.25, vary=False, short_last=False, width=37, cap=30000, lpp=25, n_last=3):
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
        return rng.choices(line, [1 / len(w) ** 2 for w in line])[0]

    def mutate(w):
        h, m, e = split(w)
        if m and rng.random() < 0.5:
            i = rng.randrange(len(m))
            m = m[:i] + (rng.choice(G.mid_glyphs),) + m[i + 1:]
            return h + m + e
        return G.new_head(w, rng)

    def close(line):
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        a = edge_src()
        if short_last:
            cands = [edge_src() for _ in range(n_last)]
            b = None if None in cands else min(cands, key=len)
        else:
            b = edge_src()
        if a is None or b is None:
            return False
        if rng.random() < q:
            a = (rng.choice("ptk"),) + a
        full = [a] + line + [b]
        for i in range(2, len(full) - 1):
            if rng.random() < beta:
                hd = G.heads[hash((full[i - 1][-1], "b")) % len(G.heads)]
                _, m, e = split(full[i])
                full[i] = (hd + m + e) or full[i]
        inner.append(list(line))
        lines.append(full)
        return True

    while total < cap:
        w = None
        if rng.random() < c:
            w = pick()
            if w is not None and rng.random() < 0.5:
                w = mutate(w)
        if w is None:
            w = inner_src()
            if w is None:
                break
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > W - 12:
            if not close(cur):
                cur = []
                break
            total += len(cur) + 2
            cur, cur_len, add = [], 0, len(w)
            W = width * rng.uniform(0.7, 1.3) if vary else width
        cur.append(w)
        cur_len += add
    if cur:
        close(cur)
    return {f"p{i // lpp}": lines[i:i + lpp] for i in range(0, len(lines), lpp)}


def n21_fracs(lines_, rng, runs=20):
    inner = [l[1:-1] for l in lines_ if len(l) >= 4]
    pairs = [(a, b) for l in inner for a, b in zip(l, l[1:])]
    out = []
    for fa, fb in ((lambda w: w[-2:], lambda w: w[:2]), (lambda w: w, lambda w: w)):
        obs = line_unit.mi([(fa(a), fb(b)) for a, b in pairs])
        n1, n2 = [], []
        groups = defaultdict(list)
        for i, (a, b) in enumerate(pairs):
            groups[(a[-1], b[0])].append(i)
        for _ in range(runs):
            ps = []
            for l in inner:
                x = list(l)
                rng.shuffle(x)
                ps += [(fa(a), fb(b)) for a, b in zip(x, x[1:])]
            n1.append(line_unit.mi(ps))
            bs = [b for _, b in pairs]
            for idx in groups.values():
                sh = [pairs[i][1] for i in idx]
                rng.shuffle(sh)
                for i, b in zip(idx, sh):
                    bs[i] = b
            n2.append(line_unit.mi([(fa(a), fb(b)) for (a, _), b in zip(pairs, bs)]))
        b1, b2 = statistics.mean(n1), statistics.mean(n2)
        out.append((b2 - b1) / (obs - b1) if obs > b1 else float("nan"))
    return out


def measure(pages_t, last, rng):
    words = [w for ls in pages_t.values() for l in ls for w in l]
    lines_ = [l for ls in pages_t.values() for l in ls]
    e = unit_entropy.entropies([list(w) for w in words])
    strs = ["".join(w) for w in words]
    v = null_generator.vocab_stats(strs)
    k, n = scmp.judge(e, v)
    lens = [len(w) for w in words]
    pages_str = {pg: [["".join(w) for w in l] for l in ls] for pg, ls in pages_t.items()}
    sc.CHAR_MODE = False
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    same, _ = word_families.pairs(pages_str)
    c = Counter(p for p, _, _ in same)
    nn = max(1, len(same))
    t2, t3 = sct.t2_t3(words)
    r = line_unit.l1(list(pages_t.items()), lambda w: "".join(w[-2:]), lambda w: "".join(w[:2]), rng)
    mm = m_measures(lines_, last)
    g1, g10 = g1_g10(pages_t, rng)
    fr = n21_fracs(lines_, rng)
    return {"8量": f"{k}/{n}", "h2": e["h2"], "V2": v["V2 1回だけ"], "V3": v["V3 Zipf"], "V4": v["V4 Heaps"],
            "長CV": statistics.pstdev(lens) / statistics.mean(lens), "歪度": skew(lens),
            "T1頭": c["語頭"] / nn, "T1中": c["語中"] / nn, "T1末": c["語末"] / nn, "T2": t2, "T3": t3,
            "またぐ": r["行をまたぐ"] - r["無関係"], "行頭だけ": share_first_only(list(pages_str.items())),
            "G1": g1, "G10": g10, "隣": adj_diff(lines_, rng), "行長CV": mm["m2 行長 CV"], "末/内": mm["m3 最後/内側"],
            "境目%2": fr[0], "境目%語": fr[1]}


KEYS = ["8量", "h2", "V2", "V3", "V4", "長CV", "歪度", "T1頭", "T1中", "T1末", "T2", "T3", "またぐ", "行頭だけ",
        "G1", "G10", "隣", "行長CV", "末/内", "境目%2", "境目%語"]


def show(name, m):
    print(f"  {name:<24}" + " ".join(f"{m[k]:>7}" if isinstance(m[k], str) else f"{m[k]:>7.3f}" for k in KEYS))


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    print(f"  {'':<24}" + " ".join(f"{k:>7}" for k in KEYS))
    for lang in ("A", "B"):
        pt, _, last = V[lang]
        show(f"ヴォイニッチ {lang}", measure(pt, last, rng))
    G = {lang: Grammar(V[lang][0]) for lang in ("A", "B")}
    lastf = lambda P: [i == len(ls) - 1 for ls in P.values() for i in range(len(ls))]  # noqa: E731
    print("\n=== N27 W-P（語の型 ＋ 平文の符号表）===")
    for gl in ("A", "B"):
        i, e = source_wp(caesar, G[gl], random.Random(3))
        P = build(i, e, G[gl], random.Random(11))
        show(f"W-P 欄 {gl}", measure(P, lastf(P), rng))
    print("\n=== N28 行の作り方（幅のばらつき ＋ 行末に短い語）===")
    for gl in ("A", "B"):
        i, e = source_wp(caesar, G[gl], random.Random(3))
        P = build(i, e, G[gl], random.Random(11), vary=True, short_last=True)
        show(f"W-P＋行 欄 {gl}", measure(P, lastf(P), rng))
    print("\n=== N29 平文の有無（欄 B, 行の工夫あり, 種 3 通り）===")
    for seed in (1, 2, 3):
        i, e = source_wp(caesar, G["B"], random.Random(seed))
        P = build(i, e, G["B"], random.Random(seed + 10), vary=True, short_last=True)
        show(f"W-P 種 {seed}", measure(P, lastf(P), rng))
    for seed in (1, 2, 3):
        i, e = source_wn(G["B"], random.Random(seed))
        P = build(i, e, G["B"], random.Random(seed + 10), vary=True, short_last=True)
        show(f"W-N 種 {seed}", measure(P, lastf(P), rng))


if __name__ == "__main__":
    main()

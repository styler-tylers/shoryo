#!/usr/bin/env python3
"""nēvo による解析 第 12 巡: N33（語の種類の並び）・N34（h2 の分解）・N35（種類の交代のモデル）。

    python3 voynich/nevo_round12.py <Caesar>
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import glyph_roles  # noqa: E402
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import KEYS, measure, show, source_wp, split  # noqa: E402
from nevo_round11 import LinkedGrammar  # noqa: E402


def H(c: Counter) -> float:
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values())


def cmi(trip):
    return (H(Counter((a, b) for a, b, _ in trip)) + H(Counter((b, c) for _, b, c in trip))
            - H(Counter(b for _, b, _ in trip)) - H(Counter(trip)))


def class_tests(name, lines_, cls, rng, runs=50):
    inner = [l[1:-1] for l in lines_ if len(l) >= 4]
    pairs = [(a, b) for l in inner for a, b in zip(l, l[1:])]
    obs = line_unit.mi([(cls(a), cls(b)) for a, b in pairs])
    groups = defaultdict(list)
    for i, (a, b) in enumerate(pairs):
        groups[(a[-1], b[0])].append(i)
    nulls = []
    for _ in range(runs):
        bs = [b for _, b in pairs]
        for idx in groups.values():
            sh = [pairs[i][1] for i in idx]
            rng.shuffle(sh)
            for i, b in zip(idx, sh):
                bs[i] = b
        nulls.append(line_unit.mi([(cls(a), cls(b)) for (a, _), b in zip(pairs, bs)]))
    pa = (sum(x >= obs for x in nulls) + 1) / (runs + 1)
    trips = [(cls(a), cls(b), cls(c)) for l in inner for a, b, c in zip(l, l[1:], l[2:])]
    ob = cmi(trips)
    nb = []
    for _ in range(runs):
        t = []
        for l in inner:
            x = list(l)
            rng.shuffle(x)
            t += [(cls(a), cls(b), cls(c)) for a, b, c in zip(x, x[1:], x[2:])]
        nb.append(cmi(t))
    pb = (sum(x >= ob for x in nb) + 1) / (runs + 1)
    pos = defaultdict(Counter)
    for l in inner:
        if len(l) >= 3:
            pos["最初"][cls(l[0])] += 1
            pos["最後"][cls(l[-1])] += 1
            for w in l[1:-1]:
                pos["中ほど"][cls(w)] += 1
    keys = sorted(set().union(*pos.values()))
    g, _ = word_families.g_test([[pos[k][x] for x in keys] for k in ("最初", "中ほど", "最後")])
    pc = glyph_roles.chi2_sf(g, 2 * (len(keys) - 1))
    print(f"  {name:<16} (a) 2 つ組 {obs:.4f} 基準2 {statistics.mean(nulls):.4f} 超過 {obs - statistics.mean(nulls):+.4f} p = {pa:.3g}"
          f"  (b) 1 つ飛ばし {ob:.4f} 基準 {statistics.mean(nb):.4f} 超過 {ob - statistics.mean(nb):+.4f} p = {pb:.3g}"
          f"  (c) 位置 G = {g:.0f} p = {glyph_roles.fmt_p(pc)}")
    return obs - statistics.mean(nulls)


vclass = lambda w: "".join(split(w)[0]) or "なし"  # noqa: E731


class Compat:
    def __init__(self, G, pages_t):
        self.G = G
        self.bi = Counter()
        self.trans = defaultdict(Counter)
        for ls in pages_t.values():
            for l in ls:
                for w in l:
                    seq = ("#",) + w + ("#",)
                    self.bi.update(zip(seq, seq[1:]))
                inner = l[1:-1] if len(l) >= 4 else []
                for a, b in zip(inner, inner[1:]):
                    self.trans[split(a)[0]][split(b)[0]] += 1
        self.glyphs = Counter(g for (g, _) in self.bi if g != "#")

    def heads_for(self, m):
        hs = [h for h in self.G.hk if self.G.mh[h][m] > 0]
        return hs or list(self.G.hk)

    def mutate(self, w, rng):
        h, m, e = split(w)
        if m and rng.random() < 0.5:
            i = rng.randrange(len(m))
            full = h + m + e
            j = len(h) + i
            prev = full[j - 1] if j > 0 else "#"
            nxt = full[j + 1] if j + 1 < len(full) else "#"
            cands = [g for g in self.glyphs if g != m[i] and self.bi[(prev, g)] and self.bi[(g, nxt)]]
            if cands:
                g = rng.choices(cands, [self.glyphs[x] for x in cands])[0]
                return h + m[:i] + (g,) + m[i + 1:] + e
        hs = self.heads_for(m)
        return rng.choices(hs, [self.G.h[x] for x in hs])[0] + m + e or w


def build12(inner_src, edge_src, G, C, rng, c=0.4, beta=0.4, alpha=0.0, compat=True, q=0.25, width=37, cap=30000, lpp=25, wfun=None, short_last=True, mut=0.5):
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
        return rng.choices(line, [wfun(w) if wfun else 1 / len(w) ** 2 for w in line])[0]

    def plain_mutate(w):
        h, m, e = split(w)
        if m and rng.random() < 0.5:
            i = rng.randrange(len(m))
            return h + m[:i] + (rng.choice(G.mid_glyphs),) + m[i + 1:] + e
        return G.new_head(w, rng)

    def close(line):
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        a = edge_src()
        cands = [edge_src(), edge_src()]
        if a is None or None in cands:
            return False
        b = min(cands, key=len) if short_last else cands[0]
        if rng.random() < q:
            a = (rng.choice("ptk"),) + a
        full = [a] + line + [b]
        for i in range(2, len(full) - 1):
            _, m, e = split(full[i])
            if alpha and rng.random() < alpha:
                hs = C.heads_for(m)
                prevh = split(full[i - 1])[0]
                wts = [C.trans[prevh][h] + 0.1 for h in hs]
                full[i] = (rng.choices(hs, wts)[0] + m + e) or full[i]
            elif rng.random() < beta:
                hs = C.heads_for(m) if compat else G.heads
                full[i] = (hs[hash((full[i - 1][-1], "b")) % len(hs)] + m + e) or full[i]
        inner.append(list(line))
        lines.append(full)
        return True

    while total < cap:
        w = None
        if c and rng.random() < c:
            w = pick()
            if w is not None and rng.random() < mut:
                w = C.mutate(w, rng) if compat else plain_mutate(w)
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
            W = width * rng.uniform(0.7, 1.3)
        cur.append(w)
        cur_len += add
    if cur:
        close(cur)
    return {f"p{i // lpp}": lines[i:i + lpp] for i in range(0, len(lines), lpp)}


def h2_of(words):
    return unit_entropy.entropies([list(w) for w in words])["h2"]


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    print("=== N33 語の種類の並び ===")
    vx = {}
    for lang in ("A", "B"):
        pt = V[lang][0]
        vx[lang] = class_tests(f"ヴォイニッチ {lang}", [l for ls in pt.values() for l in ls], vclass, rng)
    top = [c for c, _ in Counter(w[0] for w in caesar).most_common(6)]
    lw = [tuple(w) for w in caesar[:20000]]
    ll = [l for _, ls in line_unit.wrap(["".join(w) for w in lw], 37) for l in ls]
    class_tests("Caesar（文字）", [[tuple(w) for w in l] for l in ll], lambda w: w[0] if w[0] in top else "他", rng)

    print("\n=== N34 h2 はどこで上がるか（欄 B の結び付いた型）===")
    G = LinkedGrammar(V["B"][0])
    C = Compat(G, V["B"][0])
    print(f"  ヴォイニッチ B: h2 {h2_of([w for ls in V['B'][0].values() for l in ls for w in l]):.2f}")
    r = random.Random(5)
    print(f"  (i) 型から独立に選ぶ: h2 {h2_of([G.word(r) for _ in range(20000)]):.2f}")
    i, e = source_wp(caesar, G, random.Random(3))
    stream = []
    while (w := i()) is not None:
        stream.append(w)
    print(f"  (ii) 符号表で並べただけ: h2 {h2_of(stream):.2f}")
    lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
    for label, kw in (("(iii) ＋写し（N30 の変え方）", dict(beta=0.0, compat=False)),
                      ("(iii') ＋写し（実在する 2 つ組の範囲）", dict(beta=0.0, compat=True)),
                      ("(iv) ＋境目の規則 β 0.4（合う語頭）", dict(beta=0.4, compat=True))):
        i, e = source_wp(caesar, G, random.Random(3))
        P = build12(i, e, G, C, random.Random(11), **kw)
        words = [w for ls in P.values() for l in ls for w in l]
        print(f"  {label}: h2 {h2_of(words):.2f}")
    print("\n=== N35 語の種類の交代を入れたモデル（欄 B）===")
    print(f"  {'':<26}" + " ".join(f"{k:>7}" for k in KEYS))
    show("ヴォイニッチ B", measure(V["B"][0], V["B"][2], rng))
    for label, alpha in (("(iv) 交代なし", 0.0), ("交代あり α 0.5", 0.5)):
        i, e = source_wp(caesar, G, random.Random(3))
        P = build12(i, e, G, C, random.Random(11), beta=0.4, alpha=alpha, compat=True)
        show(label, measure(P, lastf(P), rng))
        class_tests(f"   {label}", [l for ls in P.values() for l in ls], vclass, rng)
    print(f"  （目標: ヴォイニッチ B の (a) 超過 {vx['B']:+.4f} の ± 50%）")


if __name__ == "__main__":
    main()

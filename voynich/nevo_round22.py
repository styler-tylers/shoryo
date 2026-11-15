#!/usr/bin/env python3
"""nēvo による解析 第 22 巡: N64・N65（空白をまたぐ字形の規則）・N66（字形の流れに空白を後から入れるモデル）。

    python3 voynich/nevo_round22.py <文章 …>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round21 import words_any  # noqa: E402


def H(c: Counter) -> float:
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


def jsd(c1: Counter, c2: Counter) -> float:
    n1, n2 = sum(c1.values()), sum(c2.values())
    d = 0.0
    for k in set(c1) | set(c2):
        p, q = c1[k] / n1, c2[k] / n2
        m = (p + q) / 2
        if p:
            d += 0.5 * p * math.log2(p / m)
        if q:
            d += 0.5 * q * math.log2(q / m)
    return d


def space_stats(name, lines_):
    within, across = defaultdict(Counter), defaultdict(Counter)
    sp = Counter()
    pairs_in, pairs_ac = [], []
    for l in lines_:
        for wi, w in enumerate(l):
            for a, b in zip(w, w[1:]):
                within[a][b] += 1
                sp[(a, b, 0)] += 1
                pairs_in.append((a, b))
            if wi + 1 < len(l):
                a, b = w[-1], l[wi + 1][0]
                across[a][b] += 1
                sp[(a, b, 1)] += 1
                pairs_ac.append((a, b))
    tot = sum(sum(c.values()) for c in across.values())
    ja = sum(sum(across[x].values()) / tot * jsd(within[x], across[x]) for x in across if within[x])
    hs = H(Counter({k: v for k, v in Counter(s for (_, _, s), v in sp.items() for _ in [0]).items()}))
    total_s = Counter()
    for (a, b, s), v in sp.items():
        total_s[s] += v
    hs = H(total_s)
    byxy = defaultdict(Counter)
    for (a, b, s), v in sp.items():
        byxy[(a, b)][s] += v
    n = sum(total_s.values())
    hcond = sum(sum(c.values()) / n * H(c) for c in byxy.values())
    ratio = line_unit.mi(pairs_ac) / line_unit.mi(pairs_in)
    print(f"  {name:<26} (a) 規則の似かた JSD {ja:.3f}  (b) 空白の当てやすさ {1 - hcond / hs:.0%}  (c) またぐ ÷ 語の中 {ratio:.2f}")


def stream_model(pt, linelens, n_glyphs, rng, lpp=25):
    tri = defaultdict(Counter)
    spc = defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            g = [x for w in l for x in w]
            sps = []
            for wi, w in enumerate(l):
                sps += [0] * (len(w) - 1) + ([1] if wi + 1 < len(l) else [])
            seq = ["^", "^"] + g
            for i in range(2, len(seq)):
                tri[(seq[i - 2], seq[i - 1])][seq[i]] += 1
            for (a, b), s in zip(zip(g, g[1:]), sps):
                spc[(a, b)][s] += 1
    lines, made = [], 0
    while made < n_glyphs:
        L = rng.choice(linelens)
        prev = ("^", "^")
        g = []
        for _ in range(L):
            c = tri.get(prev) or tri[("^", "^")]
            k, v = zip(*c.items())
            x = rng.choices(k, v)[0]
            g.append(x)
            prev = (prev[1], x)
        words, cur = [], [g[0]]
        for a, b in zip(g, g[1:]):
            c = spc.get((a, b))
            p = c[1] / (c[0] + c[1]) if c else 0.2
            if rng.random() < p:
                words.append(tuple(cur))
                cur = [b]
            else:
                cur.append(b)
        words.append(tuple(cur))
        lines.append(words)
        made += L
    return {f"p{i // lpp}": lines[i:i + lpp] for i in range(0, len(lines), lpp)}


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:]]
    rng = random.Random(2026)
    V = voynich()
    print("=== N64・N65 空白をまたぐ字形の規則 ===")
    for lang in ("A", "B"):
        space_stats(f"ヴォイニッチ {lang}", [l for ls in V[lang][0].values() for l in ls])
    for p in paths:
        ws = words_any(p)[:30000]
        space_stats(p.stem, [[tuple(w) for w in l] for _, ls in line_unit.wrap(ws, 37) for l in ls])
    sys.stdout.flush()
    print("\n=== N66 字形の流れに空白を後から入れるモデル（種 3 通り）===")
    for lang in ("A", "B"):
        pt = V[lang][0]
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        linelens = [sum(len(w) for w in l) for ls in pt.values() for l in ls]
        n = sum(linelens)
        runs = []
        for seed in (1, 2, 3):
            P = stream_model(pt, linelens, n, random.Random(seed))
            runs.append(with_strength(measure(P, [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))], rng), P))
        summarize(f"空白を後から入れる {lang}", runs)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 26 巡: N76（写しと境目の両立）・N77（語の組の記憶）・N78（言語 A の境目の表で足りない組）。

    python3 voynich/nevo_round26.py
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
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round23 import pairs_of  # noqa: E402
from nevo_round25 import first_table  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def build_cond2(G, C, pt, rng, mu=0.0, c=0.4, q=0.25, width=37, cap=30000, lpp=25, n=300000):
    gen = Counter(G.word(rng) for _ in range(n))
    byg = defaultdict(lambda: ([], []))
    for w, k in gen.items():
        byg[w[0]][0].append(w)
        byg[w[0]][1].append(k)
    allw, allc = zip(*gen.items())
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
        return (d[w[0]] + 0.5) / sum(d.values()) / ((marg[w[0]] + 0.5) / mt)

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


def n78(pt, P):
    print("\n=== N78 言語 A の境目の表で、モデルに足りない組（点ごとの相互情報量の寄与の差）===")

    def contrib(pairs):
        c = Counter(pairs)
        n = len(pairs)
        a, b = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
        return {k: v / n * math.log2(v * n / (a[k[0]] * b[k[1]])) for k, v in c.items()}, c, n

    cv, nv_c, nv = contrib(pairs_of([l for ls in pt.values() for l in ls]))
    cm, nm_c, nm = contrib(pairs_of([l for ls in P.values() for l in ls]))
    print(f"  合計: ヴォイニッチ {sum(cv.values()):.3f}、モデル {sum(cm.values()):.3f}")
    diff = sorted(set(cv) | set(cm), key=lambda k: -(cv.get(k, 0) - cm.get(k, 0)))[:10]
    for k in diff:
        print(f"    -{k[0]}→{k[1]}-  寄与 ヴォイニッチ {cv.get(k, 0):+.4f}（{nv_c[k] / nv:.1%}）  モデル {cm.get(k, 0):+.4f}（{nm_c[k] / nm:.1%}）")


def main() -> None:
    rng = random.Random(2026)
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        print(f"     境目%語 {measure(pt, V[lang][2], rng)['境目%語']:.2f}")
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        keep = None
        for label, mu in (("N76 写しと境目の両立", 0.0), ("N77 ＋ 語の組の記憶 μ 0.3", 0.3)):
            runs = []
            for seed in (1, 2, 3):
                P = build_cond2(LG, LC, pt, random.Random(seed), mu=mu)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
                if seed == 1 and mu == 0.0:
                    keep = P
            summarize(label, runs)
            print(f"     境目%語 " + " ".join(f"{r['境目%語']:.2f}" for r in runs), flush=True)
        if lang == "A":
            n78(pt, keep)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

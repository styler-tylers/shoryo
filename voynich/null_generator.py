#!/usr/bin/env python3
"""意味の無い最小の生成モデルの検証（第 14 回）。

語は字形の 1 次マルコフ連鎖で作り、語の 20% は上の行・同じ行から写して、位置を選ばずに 1 字形を変える。
手順に入れていない性質（語彙の広がり、Zipf、語の家族の変わる位置、語頭の群の偏り、写しの減衰など）を、
本物のヴォイニッチと比べる。

    python3 voynich/null_generator.py
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import prefix_order  # noqa: E402
import self_citation as sc  # noqa: E402
import selfcite_model  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402

START, END = "^", "$"
PARAMS = {"p_new": 0.8, "p_above": 0.5, "sigma": 0.3, "p_mut": 0.8}


class Markov:
    def __init__(self, words: list[str]):
        self.t: dict[str, Counter] = defaultdict(Counter)
        for w in words:
            g = [START] + list(ivtff.glyphs(w)) + [END]
            for a, b in zip(g, g[1:]):
                self.t[a][b] += 1
        self.keys = {a: (list(c), list(c.values())) for a, c in self.t.items()}

    def p(self, a: str, b: str) -> float:
        c = self.t.get(a)
        return c[b] / sum(c.values()) if c else 0.0

    def word(self, rng) -> str:
        while True:
            g, cur = [], START
            while True:
                ks, ws = self.keys[cur]
                cur = rng.choices(ks, ws)[0]
                if cur == END:
                    break
                g.append(cur)
                if len(g) > 12:
                    break
            if 1 <= len(g) <= 12 and cur == END:
                return "".join(g)

    def mutate(self, w: str, rng) -> str:
        g = list(ivtff.glyphs(w))
        i = rng.randrange(len(g))
        prev = g[i - 1] if i > 0 else START
        nxt = g[i + 1] if i + 1 < len(g) else END
        ks, ws = self.keys[prev]
        cand = [(k, x) for k, x in zip(ks, ws) if k not in (END, g[i]) and self.p(k, nxt) > 0]
        if not cand:
            return w
        g[i] = rng.choices([k for k, _ in cand], [x for _, x in cand])[0]
        return "".join(g)


def generate(shape, mk: Markov, rng, p_new, p_above, sigma, p_mut):
    out = {}
    prev_last: list[list[str]] = []
    for page, lens in shape.items():
        lines: list[list[str]] = []
        for n in lens:
            line: list[str] = []
            for wi in range(n):
                pool = prev_last + lines
                if rng.random() < p_new or (not line and not pool):
                    line.append(mk.word(rng))
                    continue
                if pool and (rng.random() < p_above or not line):
                    ks = [k for k, _ in selfcite_model.DEPTH if k <= len(pool)]
                    k = rng.choices(ks, [p for kk, p in selfcite_model.DEPTH if kk in ks])[0]
                    src = pool[-k]
                    x = wi / (n - 1) if n > 1 else 0.5
                    pos = [(j / (len(src) - 1) if len(src) > 1 else 0.5) for j in range(len(src))]
                    w = rng.choices(src, [math.exp(-abs(x - q) / sigma) for q in pos])[0]
                else:
                    w = rng.choice(line)
                if rng.random() < p_mut:
                    w = mk.mutate(w, rng)
                line.append(w)
            lines.append(line)
        out[page] = lines
        prev_last = lines[-1:]
    return out


def zipf_slope(freq: Counter, top: int = 100) -> float:
    vals = sorted(freq.values(), reverse=True)[:top]
    xs = [math.log(r) for r in range(1, len(vals) + 1)]
    ys = [math.log(v) for v in vals]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def head_skew(pages) -> float:
    c = defaultdict(Counter)
    for ls in pages.values():
        for l in ls:
            for w in l:
                s = prefix_order.split(w)
                if s and s[0] in prefix_order.GROUP:
                    c[s[1]][prefix_order.GROUP[s[0]]] += 1
    big = [b for b, x in c.items() if sum(x.values()) >= 10]
    return sum(max(c[b].values()) / sum(c[b].values()) >= 0.8 for b in big) / len(big) if big else float("nan")


def stats(pages, rng) -> dict[str, float]:
    toks = [w for ls in pages.values() for l in ls for w in l]
    freq = Counter(toks)
    same, _ = word_families.pairs(pages)
    pos = Counter(p for p, _, _ in same)
    n = max(1, len(same))
    m = selfcite_model.measure(pages, rng, null_runs=2, trials=100)
    return {"Q1 異なり/1万語": len(set(toks[:10000])), "Q2 1回だけの割合": sum(v == 1 for v in freq.values()) / len(freq),
            "Q3 Zipf の傾き": zipf_slope(freq), "Q4 語の長さ": sum(len(ivtff.glyphs(w)) for w in toks) / len(toks),
            "Q5 語頭": pos["語頭"] / n, "Q5 語中": pos["語中"] / n, "Q5 語末": pos["語末"] / n,
            "Q6 語頭の群の偏り": head_skew(pages), "Q7 S1": m["S1"], "Q7 S2": m["S2"], "Q8 P2": m["P2"],
            "h2": unit_entropy.entropies([list(ivtff.glyphs(w)) for w in toks])["h2"]}


TOL = {"Q1 異なり/1万語": ("rel", 0.2), "Q2 1回だけの割合": ("abs", 0.10), "Q3 Zipf の傾き": ("abs", 0.15),
       "Q4 語の長さ": ("abs", 0.3), "Q5 語頭": ("abs", 0.10), "Q5 語中": ("abs", 0.10), "Q5 語末": ("abs", 0.10),
       "Q6 語頭の群の偏り": ("abs", 0.10), "Q7 S1": ("abs", 0.1), "Q7 S2": ("rel", 0.2), "Q8 P2": ("abs", 0.15)}


def ok(k, real, gen) -> str:
    if k not in TOL:
        return ""
    kind, t = TOL[k]
    good = abs(gen - real) <= (t * abs(real) if kind == "rel" else t)
    return "合う" if good else "外れ"


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        real = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        shape = {p: [len(l) for l in ls] for p, ls in real.items()}
        mk = Markov([w for ls in real.values() for l in ls for w in l])
        gen = generate(shape, mk, random.Random(1), **PARAMS)
        r, g = stats(real, rng), stats(gen, rng)
        print(f"=== 言語 {lang}（{len(real)} 頁）===")
        print(f"{'量':<18}{'本物':>9}{'生成':>9}  判定")
        for k in r:
            print(f"{k:<18}{r[k]:>9.3f}{g[k]:>9.3f}  {ok(k, r[k], g[k])}")
        hits = sum(ok(k, r[k], g[k]) == "合う" for k in TOL)
        print(f"合う量: {hits}/{len(TOL)}\n")


if __name__ == "__main__":
    main()

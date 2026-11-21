#!/usr/bin/env python3
"""nēvo による解析 第 45 巡: N135（項目の中の決まり文句）。

    python3 voynich/nevo_round45.py <Forme of Cury（Project Gutenberg 8102）>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from nevo_round44 import cury_recipes  # noqa: E402


def exactly_once(items):
    c = Counter()
    for it in items:
        for w, k in Counter(it).items():
            if k == 1:
                c[w] += 1
    return c


def formula(name, items, rng, runs=200):
    n = len(items)
    tot = Counter(w for it in items for w in it)
    cand = [w for w, k in tot.items() if k >= 0.3 * n]
    obs = exactly_once(items)
    pool = [w for it in items for w in it]
    lens = [len(it) for it in items]
    nul = {w: [] for w in cand}
    for _ in range(runs):
        rng.shuffle(pool)
        it, sh = iter(pool), []
        for L in lens:
            sh.append([next(it) for _ in range(L)])
        e = exactly_once(sh)
        for w in cand:
            nul[w].append(e[w])
    zs = []
    for w in cand:
        m, sd = statistics.mean(nul[w]), statistics.pstdev(nul[w])
        zs.append(((obs[w] - m) / sd if sd else 0.0, w, obs[w] / n, m / n))
    zs.sort(reverse=True)
    last = Counter(it[-1] for it in items)
    lw, lk = last.most_common(1)[0]
    top = "  ".join(f"「{w}」{o:.0%}（かき混ぜ {m:.0%}, z {z:+.1f}）" for z, w, o, m in zs[:3])
    print(f"  {name:<24} 項目 {n:>4}  候補の語 {len(cand):>3}  z の上位: {top}  ／ 最後の語「{lw}」{lk / n:.0%}", flush=True)
    return zs[0][0] if zs else float("nan")


def main(cury):
    rng = random.Random(2026)
    z = formula("Forme of Cury（処方集）", cury_recipes(cury), rng)
    print(f"  → 正の対照: {'通る' if z > 10 else '通らない'}（z > 10）", flush=True)
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    def paras(pred):
        out, cur = [], None
        for ln in lines:
            if not (pred(ln) and ln.locus_class == "P"):
                continue
            if "<%>" in ln.raw or cur is None:
                if cur:
                    out.append(cur)
                cur = []
            cur += ivtff.words(ln.raw, opts)
            if "<$>" in ln.raw:
                out.append(cur)
                cur = None
        if cur:
            out.append(cur)
        return [p for p in out if p]
    for name, pred in (("ヴォイニッチ レシピの部（T）", lambda ln: ln.page.get("Q") == "T"),
                       ("ヴォイニッチ 植物の部", lambda ln: ln.page.get("I") == "H"),
                       ("ヴォイニッチ 浴場の部", lambda ln: ln.page.get("I") == "B")):
        formula(name, paras(pred), rng)


if __name__ == "__main__":
    main(sys.argv[1])

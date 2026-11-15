#!/usr/bin/env python3
"""行の中の文法（第 17 回）。

G1 位置ごとの語頭・語末の分布 / G2 行の 1 語目と最後の語の結び付き / G3 行の中での語末の移り変わり

    python3 voynich/line_grammar.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import function_words  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
import word_grammar  # noqa: E402


def bin_of(n: int) -> int:
    return 0 if n <= 5 else 1 if n <= 7 else 2 if n <= 9 else 3


def g2(lines_, first_fn, last_fn, rng, trials=2000):
    ls = [l for l in lines_ if len(l) >= 4]
    firsts = [first_fn(l[0]) for l in ls]
    lasts = [last_fn(l[-1]) for l in ls]
    bins = [bin_of(len(l)) for l in ls]
    obs = line_unit.mi(list(zip(firsts, lasts)))
    idx = defaultdict(list)
    for i, b in enumerate(bins):
        idx[b].append(i)
    ge = 0
    null = []
    for _ in range(trials):
        sh = lasts[:]
        for ids in idx.values():
            vals = [lasts[i] for i in ids]
            rng.shuffle(vals)
            for i, v in zip(ids, vals):
                sh[i] = v
        m = line_unit.mi(list(zip(firsts, sh)))
        null.append(m)
        ge += m >= obs
    return obs, statistics.mean(null), (ge + 1) / (trials + 1), len(ls)


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    first2 = lambda w: "".join(ivtff.glyphs(w)[:2])  # noqa: E731
    endc = lambda w: word_grammar.parse(w)[2]  # noqa: E731
    headc = lambda w: word_grammar.parse(w)[0]  # noqa: E731
    for lang in ("A", "B"):
        ls = [ivtff.words(ln.raw, opts) for ln in lines if ln.page.get("L") == lang]
        ls = [l for l in ls if len(l) >= 4]
        print(f"=== 言語 {lang}（4 語以上の行 {len(ls)}）===")
        # G1
        pos = {"1語目": [l[0] for l in ls], "2語目": [l[1] for l in ls],
               "中ほど": [w for l in ls for w in l[2:-1]], "最後": [l[-1] for l in ls]}
        for name, fn in (("語頭", headc), ("語末", endc)):
            mid = Counter(fn(w) for w in pos["中ほど"])
            nm = sum(mid.values())
            print(f"G1 {name}（中ほどと比べて 2 倍以上 ↑ / 半分以下 ↓）")
            for p in ("1語目", "2語目", "最後"):
                c = Counter(fn(w) for w in pos[p])
                n = sum(c.values())
                ups = [f"{k} {c[k] / n:.0%}↑" for k in c if c[k] / n >= 2 * mid[k] / nm and c[k] >= 10]
                downs = [f"{k} {c[k] / n:.0%}↓" for k in mid if mid[k] / nm >= 0.03 and c[k] / n <= 0.5 * mid[k] / nm]
                print(f"   {p}: " + ", ".join(ups + downs))
        # G2
        obs, null, p, n = g2(ls, first2, endc, rng)
        print(f"G2 1 語目の始めの 2 字形 × 最後の語の語末: 相互情報量 {obs:.3f}、入れ替え {null:.3f}、"
              f"差 {obs - null:+.3f}、p = {p:.4f}（{n} 行）")
        # G3
        print("G3 行の中の相対位置（5 つに分ける）ごとの語末の割合 と 順位相関")
        for e in ("dy", "y", "l", "r", "aiin"):
            shares = []
            for b in range(5):
                ws = [w for l in ls for i, w in enumerate(l) if min(4, int(5 * i / len(l))) == b]
                shares.append(sum(endc(w) == e for w in ws) / len(ws))
            rho = function_words.spearman(list(range(5)), shares)
            print(f"   -{e:<5} " + " ".join(f"{x:.0%}" for x in shares) + f"   相関 {rho:+.1f}")
        print()

    width = 37
    for p in map(Path, sys.argv[1:]):
        words = ["".join(w) for w in unit_entropy.latin_words(p)]
        wr = [l for _, ls in line_unit.wrap(words, width) for l in ls]
        se = [l for _, ls in line_unit.sentences(p) for l in ls]
        for name, L in (("紙の幅で折り返し", wr), ("1 行に 1 文", se)):
            obs, null, pv, n = g2(L, lambda w: w[:2], lambda w: w[-2:], rng, trials=500)
            print(f"参照 {p.stem}（{name}）G2: 相互情報量 {obs:.3f}、入れ替え {null:.3f}、差 {obs - null:+.3f}、"
                  f"p = {pv:.4f}（{n} 行）")


if __name__ == "__main__":
    main()

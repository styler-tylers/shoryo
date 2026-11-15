#!/usr/bin/env python3
"""音節の暗号（E2）で、ヴォイニッチの他の性質も出るか（第 21 回 第 2 段階）。

T1 語の家族の変わる位置 / T2 語の 1 つ目の単位が 2 つ目でどれだけ決まるか /
T3 語の中の結び付き（1-2 番目 ÷ 1-最後）/ T4 行をまたぐ語のつながり R

    python3 voynich/syllable_code_tests.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import scripts_compare  # noqa: E402
import self_citation as sc  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402


def entropy(c: Counter) -> float:
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values())


def t2_t3(words: list[tuple]):
    two = [w for w in words if len(w) >= 2]
    h1 = entropy(Counter(w[0] for w in two))
    pairs = Counter((w[0], w[1]) for w in two)
    sec = Counter(w[1] for w in two)
    h_cond = entropy(pairs) - entropy(sec)
    three = [w for w in words if len(w) >= 3]
    mi12 = line_unit.mi([(w[0], w[1]) for w in three])
    mi1l = line_unit.mi([(w[0], w[-1]) for w in three])
    return 1 - h_cond / h1, mi12 / mi1l if mi1l else float("inf")


def measure(name, pages, units_of, rng):
    """pages: {頁: [[語, …], …]}（語は文字列）。units_of: 語 → 単位のタプル。"""
    same, base = word_families.pairs(pages)
    pos = Counter(p for p, _, _ in same)
    n = max(1, len(same))
    words = [units_of(w) for ls in pages.values() for l in ls for w in l]
    t2, t3 = t2_t3(words)
    paras = [(p, ls) for p, ls in pages.items()]
    first2 = lambda w: "".join(units_of(w)[:2])  # noqa: E731
    last2 = lambda w: "".join(units_of(w)[-2:])  # noqa: E731
    r = line_unit.l1(paras, last2, first2, rng)
    print(f"{name:<26} T1 語頭 {pos['語頭'] / n:.0%} 語中 {pos['語中'] / n:.0%} 語末 {pos['語末'] / n:.0%}（{len(same)} 組）"
          f"  T2 {t2:.2f}  T3 {t3:.1f}  T4 R = {r['R'] if r else float('nan'):.2f}")


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    sc.CHAR_MODE = False
    for lang in ("A", "B"):
        pages = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        measure(f"ヴォイニッチ {lang}", pages, lambda w: tuple(ivtff.glyphs(w)), rng)
    for p in map(Path, sys.argv[1:]):
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        for label, words in (("元", lw), ("E2 音節の暗号", ["".join(scripts_compare.syllable_code(w)) for w in lw])):
            sc.CHAR_MODE = True
            sc.glyph_tuple.cache_clear()
            sc.distance.cache_clear()
            wrapped = line_unit.wrap(words, 37)
            pages = {pg: ls for pg, ls in wrapped}
            measure(f"ラテン語 {p.stem} {label}", pages, lambda w: tuple(w), rng)
    print("\n「合う」の範囲: T1 語末 ≤ 25%、T2 ヴォイニッチ ±0.1、T3 ≥ 2、T4 R ≤ 0.2（T4 は外れると予想）")


if __name__ == "__main__":
    main()

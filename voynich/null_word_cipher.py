#!/usr/bin/env python3
"""暗号の研究 実験 2: 行頭・行末に空文字の語を置く E4。

    python3 voynich/null_word_cipher.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402


def null_word(rng, final: bool) -> str:
    n = rng.randint(1, 2 if final else 3)
    w = ""
    for _ in range(n):
        nu = rng.randrange(6)
        w += scmp.ONSET[(nu // 2) * 4 + rng.randrange(4)] + scmp.NUCLEUS[nu]
    return w + ("Z" if final else "")


def main() -> None:
    for p in map(Path, sys.argv[1:]):
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        enc = ["".join(scmp.syllable_code_e4(w)) for w in lw]
        wrapped = line_unit.wrap(enc, 37)
        for name, pp, qq in (("(a) p 0.35, q 0.15", 0.35, 0.15), ("(b) p = q = 1", 1.0, 1.0)):
            rng = random.Random(2026)
            pages, words = {}, []
            starts, only_start = 0, 0
            for page, ls in wrapped:
                out = []
                for l in ls:
                    l2 = list(l)
                    if rng.random() < pp:
                        l2 = [null_word(rng, False)] + l2
                    if rng.random() < qq:
                        l2 = l2 + [null_word(rng, True)]
                    out.append(l2)
                pages[page] = out
                words += [w for l in out for w in l]
            not_first = set(w for ls in pages.values() for l in ls for w in l[1:])
            firsts = [l[0] for ls in pages.values() for l in ls]
            share = sum(w not in not_first for w in firsts) / len(firsts)
            e = unit_entropy.entropies([list(w) for w in words])
            v = null_generator.vocab_stats(words)
            k, n = scmp.judge(e, v)
            print(f"=== {p.stem} {name} ===")
            print(f"  8 つの量: h1 {e['h1']:.2f}, h2 {e['h2']:.2f}, h2/h1 {e['h2/h1']:.2f}, 語の長さ {e['語の長さ']:.2f}, "
                  + ", ".join(f"{a} {b:.3f}" for a, b in v.items()) + f"  → 範囲に入る {k}/{n}")
            print(f"  行頭の語のうち行頭だけの語: {share:.0%}（ヴォイニッチ 32%）")
            sc.CHAR_MODE = True
            sc.glyph_tuple.cache_clear()
            sc.distance.cache_clear()
            sct.measure("  T1〜T4", pages, lambda w: tuple(w), random.Random(2026))


if __name__ == "__main__":
    main()

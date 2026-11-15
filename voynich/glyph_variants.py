#!/usr/bin/env python3
"""暗号の研究 実験 3: 字形の変化形を数える。

台つきの字形（cth ckh cph cfh）を t k p f に、sh を ch に戻し、稀な字形（@nnn;）を 1 つにまとめて、
字形の種類と h1・h2・h2/h1 がどう変わるかを、言語 A・B の段落テキストで測る。

    python3 voynich/glyph_variants.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import unit_entropy  # noqa: E402

VAR = {"cth": "t", "ckh": "k", "cph": "p", "cfh": "f", "sh": "ch"}


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        ws = [list(ivtff.glyphs(w)) for ln in lines if ln.page.get("L") == lang for w in ivtff.words(ln.raw, opts)]
        v1 = [[VAR.get(g, g) for g in w] for w in ws]
        v2 = [["@" if g.startswith("@") else g for g in w] for w in v1]
        for name, x in (("元", ws), ("変化形を戻す", v1), ("稀な字形もまとめる", v2)):
            e = unit_entropy.entropies(x)
            c = Counter(g for w in x for g in w)
            print(f"言語 {lang} {name:<12} 種類 {e['種類'] - 1:>3}（語の区切りを除く）  h1 {e['h1']:.2f} h2 {e['h2']:.2f} "
                  f"h2/h1 {e['h2/h1']:.2f}  1 回だけの字形 {sum(1 for v in c.values() if v == 1)}  "
                  f"10 回未満 {sum(1 for v in c.values() if v < 10)}")
        c = Counter(g for w in ws for g in w)
        print("   多い字形:", " ".join(f"{g}:{n}" for g, n in c.most_common(25)))


if __name__ == "__main__":
    main()

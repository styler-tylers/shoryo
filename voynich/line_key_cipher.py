#!/usr/bin/env python3
"""暗号の研究 実験 1: 行ごとに表を替える E4（K 枚の表を行ごとに順に使う）。

8 つの量（h1, h2, h2/h1, 語の長さ, V1〜V4）と T1〜T4 を、K = 1, 2, 4 で比べる。

    python3 voynich/line_key_cipher.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402


def e4_keyed(word: str, table: int) -> str:
    t = f"T{table}:"
    parts = re.findall(r"[^aeiouy]*[aeiouy]+", word)
    tail = word[len("".join(parts)):]
    if not parts:
        return scmp.CODA[scmp._h(t + word, 4)]
    out = []
    for p in parts:
        m = re.match(r"([^aeiouy]*)([aeiouy]+)", p)
        n = scmp._h(t + "n" + m.group(2), 6)
        g = n // 2
        out += [scmp.ONSET[g * 4 + scmp._h(t + "o" + m.group(1), 4)], scmp.NUCLEUS[n]]
    if tail:
        out.append(scmp.CODA[scmp._h(t + "c" + tail, 4)])
    return "".join(out)


def main() -> None:
    rng = random.Random(2026)
    for p in map(Path, sys.argv[1:]):
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        base = [e4_keyed(w, 0) for w in lw]          # 語の長さは表によらない
        wrapped = line_unit.wrap(base, 37)            # 行と頁を先に作る
        # 平文の語を、行ごとに対応づけ直す
        idx = 0
        layout = []
        for page, ls in wrapped:
            plines = []
            for l in ls:
                plines.append(lw[idx:idx + len(l)])
                idx += len(l)
            layout.append((page, plines))
        for K in (1, 2, 4):
            pages, words, line_no = {}, [], 0
            for page, plines in layout:
                enc = []
                for pl in plines:
                    enc.append([e4_keyed(w, line_no % K) for w in pl])
                    line_no += 1
                pages[page] = enc
                words += [w for l in enc for w in l]
            e = unit_entropy.entropies([list(w) for w in words])
            v = null_generator.vocab_stats(words)
            k, n = scmp.judge(e, v)
            print(f"=== {p.stem} K = {K} ===")
            print(f"  8 つの量: h1 {e['h1']:.2f}, h2 {e['h2']:.2f}, h2/h1 {e['h2/h1']:.2f}, 語の長さ {e['語の長さ']:.2f}, "
                  + ", ".join(f"{a} {b:.3f}" for a, b in v.items()) + f"  → 範囲に入る {k}/{n}")
            sc.CHAR_MODE = True
            sc.glyph_tuple.cache_clear()
            sc.distance.cache_clear()
            sct.measure(f"  T1〜T4", pages, lambda w: tuple(w), rng)


if __name__ == "__main__":
    main()

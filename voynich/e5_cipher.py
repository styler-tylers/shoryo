#!/usr/bin/env python3
"""暗号の研究 実験 9: 前後の両方に合わせる音節の暗号 E5。

頭の記号の群 g = (次の母音の群 + 同じ語の前の音節の母音の群) mod 3（語の最初の音節では前を 0）。
他は E4 と同じ。E4 と E5 で、8 つの量・T1〜T4・Q2 を測る。

    python3 voynich/e5_cipher.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import glyph_slots  # noqa: E402
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402


def syllable_code_e5(word: str) -> list[str]:
    parts = re.findall(r"[^aeiouy]*[aeiouy]+", word)
    tail = word[len("".join(parts)):]
    if not parts:
        return [scmp.CODA[scmp._h(word, 4)]]
    out, prev_g = [], 0
    for p in parts:
        m = re.match(r"([^aeiouy]*)([aeiouy]+)", p)
        n = scmp._h("n" + m.group(2), 6)
        g = (n // 2 + prev_g) % 3
        out += [scmp.ONSET[g * 4 + scmp._h("o" + m.group(1), 4)], scmp.NUCLEUS[n]]
        prev_g = n // 2
    if tail:
        out.append(scmp.CODA[scmp._h("c" + tail, 4)])
    return out


def main() -> None:
    rng = random.Random(2026)
    for p in map(Path, sys.argv[1:]):
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        for name, code in (("E4", scmp.syllable_code_e4), ("E5", syllable_code_e5)):
            ws = [code(w) for w in lw]
            e = unit_entropy.entropies(ws)
            v = null_generator.vocab_stats(["".join(w) for w in ws])
            k, n = scmp.judge(e, v)
            print(f"=== {p.stem} {name} ===")
            print(f"  8 つの量: h1 {e['h1']:.2f}, h2 {e['h2']:.2f}, h2/h1 {e['h2/h1']:.2f}, 語の長さ {e['語の長さ']:.2f}, "
                  + ", ".join(f"{a} {b:.3f}" for a, b in v.items()) + f"  → 範囲に入る {k}/{n}")
            sc.CHAR_MODE = True
            sc.glyph_tuple.cache_clear()
            sc.distance.cache_clear()
            pages = {pg: ls for pg, ls in line_unit.wrap(["".join(w) for w in ws], 37)}
            sct.measure("  T1〜T4", pages, lambda w: tuple(w), rng)
            glyph_slots.slot_report("  Q1・Q2（A〜D）", [(w, {}) for w in ws],
                                    lambda g: g if g in "ABCD" else None, lambda g: g, rng)


if __name__ == "__main__":
    main()

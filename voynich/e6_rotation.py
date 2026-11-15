#!/usr/bin/env python3
"""暗号の研究 実験 12（前の母音の群で頭の記号を決める E6）と実験 13（行ごとに語の並びを回す）。

    python3 voynich/e6_rotation.py <ラテン語のテキスト …>
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
from e5_cipher import syllable_code_e5  # noqa: E402
from e5_tuning import add_nulls, q2  # noqa: E402


def code_e6(word: str, m: float) -> list[str]:
    parts = re.findall(r"[^aeiouy]*[aeiouy]+", word)
    tail = word[len("".join(parts)):]
    if not parts:
        return [scmp.CODA[scmp._h(word, 4)]]
    out, prev_g = [], None
    for i, p in enumerate(parts):
        mm = re.match(r"([^aeiouy]*)([aeiouy]+)", p)
        n = scmp._h("n" + mm.group(2), 6)
        use_prev = prev_g is not None and scmp._h(f"m{word}:{i}", 10000) < m * 10000
        g = prev_g if use_prev else n // 2
        out += [scmp.ONSET[g * 4 + scmp._h("o" + mm.group(1), 4)], scmp.NUCLEUS[n]]
        prev_g = n // 2
    if tail:
        out.append(scmp.CODA[scmp._h("c" + tail, 4)])
    return out


def exp12(paths, rng):
    print("=== 実験 12: E6（確率 m で前の母音の群に合わせる）===")
    target = {"A": (2.30, 33, 24), "B": (2.10, 36, 36)}
    for p in paths:
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        for m in (0.25, 0.5, 0.75):
            ws = [code_e6(x, m) for x in lw]
            e = unit_entropy.entropies(ws)
            v = null_generator.vocab_stats(["".join(w) for w in ws])
            k, n = scmp.judge(e, v)
            qn, qp = q2(ws, rng)
            fit = [lang for lang, (h2, a, b) in target.items()
                   if abs(e["h2"] - h2) <= 0.10 and abs(qn * 100 - a) <= 10 and abs(qp * 100 - b) <= 10]
            print(f"  {p.stem} m = {m:<4}  h2 {e['h2']:.2f}  h2/h1 {e['h2/h1']:.2f}  Q2 後ろ {qn:.0%} 前 {qp:.0%}  "
                  f"8 つの量 {k}/{n}  → 合う: {', '.join(fit) or 'なし'}")


def rotate(pages, rng):
    out = []
    for page, ls in pages:
        new = []
        for l in ls:
            k = rng.randrange(len(l))
            new.append(l[k:] + l[:k])
        out.append((page, new))
    return out


def exp13(paths, rng):
    print("\n=== 実験 13: 行ごとに語の並びを回す ===")
    for p in paths:
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        wrapped = line_unit.wrap(["".join(syllable_code_e5(x)) for x in lw], 37)
        rot = rotate(wrapped, random.Random(7))
        settings = {"(i) 回さない": wrapped, "(ii) 回す": rot,
                    "(iii) 回す ＋ 空文字": add_nulls(rot, 0.35, 0.15, random.Random(2026))}
        for name, pages in settings.items():
            words = [w for _, ls in pages for l in ls for w in l]
            e = unit_entropy.entropies([list(w) for w in words])
            v = null_generator.vocab_stats(words)
            k, n = scmp.judge(e, v)
            not_first = set(w for _, ls in pages for l in ls for w in l[1:])
            firsts = [l[0] for _, ls in pages for l in ls]
            share = sum(w not in not_first for w in firsts) / len(firsts)
            r = line_unit.l1(pages, lambda w: w[-2:], lambda w: w[:2], rng)
            print(f"  {p.stem} {name:<12} R {r['R']:.2f}  またぐ−基準 {r['行をまたぐ'] - r['無関係']:+.3f}  "
                  f"行の中−基準 {r['行の中'] - r['無関係']:+.3f}  行頭だけの語 {share:.0%}  8 つの量 {k}/{n}")
            sc.CHAR_MODE = True
            sc.glyph_tuple.cache_clear()
            sc.distance.cache_clear()
            sct.measure("     T1〜T4", dict(pages), lambda w: tuple(w), rng)


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:]]
    rng = random.Random(2026)
    exp12(paths, rng)
    exp13(paths, rng)


if __name__ == "__main__":
    main()

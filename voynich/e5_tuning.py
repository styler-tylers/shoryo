#!/usr/bin/env python3
"""暗号の研究 実験 10（合わせる強さ w で言語 A・B）と実験 11（E5 ＋ 句の区切り ＋ 空文字）。

    python3 voynich/e5_tuning.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import random
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import glyph_slots  # noqa: E402
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import null_word_cipher  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import unit_entropy  # noqa: E402
from e5_cipher import syllable_code_e5  # noqa: E402


def code_w(word: str, w: float) -> list[str]:
    parts = re.findall(r"[^aeiouy]*[aeiouy]+", word)
    tail = word[len("".join(parts)):]
    if not parts:
        return [scmp.CODA[scmp._h(word, 4)]]
    out, prev_g = [], 0
    for i, p in enumerate(parts):
        m = re.match(r"([^aeiouy]*)([aeiouy]+)", p)
        n = scmp._h("n" + m.group(2), 6)
        use5 = scmp._h(f"w{word}:{i}", 10000) < w * 10000
        g = (n // 2 + (prev_g if use5 else 0)) % 3
        out += [scmp.ONSET[g * 4 + scmp._h("o" + m.group(1), 4)], scmp.NUCLEUS[n]]
        prev_g = n // 2
    if tail:
        out.append(scmp.CODA[scmp._h("c" + tail, 4)])
    return out


def q2(ws, rng):
    B, bn, bp = [], [], []
    for gs in ws:
        seq = ["#"] + gs + ["#"]
        for i in range(1, len(seq) - 1):
            B.append(seq[i] in "ABCD")
            bn.append(seq[i + 1])
            bp.append(seq[i - 1])
    hb = glyph_slots.h(B)
    return glyph_slots.corrected(B, bn, rng, 20) / hb, glyph_slots.corrected(B, bp, rng, 20) / hb


def exp10(paths, rng):
    print("=== 実験 10: 合わせる強さ w ===")
    target = {"A": (2.30, 33, 24), "B": (2.10, 36, 36)}
    for p in paths:
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        for w in (0, 0.25, 0.5, 0.75, 1):
            ws = [code_w(x, w) for x in lw]
            e = unit_entropy.entropies(ws)
            qn, qp = q2(ws, rng)
            fit = [lang for lang, (h2, a, b) in target.items()
                   if abs(e["h2"] - h2) <= 0.10 and abs(qn * 100 - a) <= 10 and abs(qp * 100 - b) <= 10]
            print(f"  {p.stem} w = {w:<4}  h2 {e['h2']:.2f}  h2/h1 {e['h2/h1']:.2f}  Q2 後ろ {qn:.0%} 前 {qp:.0%}"
                  f"  → 合う: {', '.join(fit) or 'なし'}")


def clause_lines(path: Path, width=37, lines_per_page=25):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*\* ?START.*?\*\*\*(.*)\*\*\* ?END", text, re.S)
    text = (m.group(1) if m else text).lower()
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u"), ("ï", "i"), ("ë", "e")):
        text = text.replace(a, b)
    lines, total = [], 0
    for cl in re.split(r"[.;:?!,]", text):
        ws = ["".join(syllable_code_e5(x)) for x in re.findall(r"[a-z]+", cl)]
        if not ws:
            continue
        for _, ls in line_unit.wrap(ws, width, 10 ** 9):
            lines += ls
        total += len(ws)
        if total >= 30000:
            break
    return [(f"p{i // lines_per_page}", lines[i:i + lines_per_page]) for i in range(0, len(lines), lines_per_page)]


def add_nulls(pages, pp, qq, rng):
    out = []
    for page, ls in pages:
        new = []
        for l in ls:
            l2 = list(l)
            if rng.random() < pp:
                l2 = [null_word_cipher.null_word(rng, False)] + l2
            if rng.random() < qq:
                l2 = l2 + [null_word_cipher.null_word(rng, True)]
            new.append(l2)
        out.append((page, new))
    return out


def exp11(paths, rng):
    print("\n=== 実験 11: E5 ＋ 句の区切り ＋ 空文字 ===")
    for p in paths:
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        wrapped = line_unit.wrap(["".join(syllable_code_e5(x)) for x in lw], 37)
        clause = clause_lines(p)
        settings = {"(i) 折り返し": wrapped, "(ii) 句の区切り": clause,
                    "(iii) 句 ＋ 空文字": add_nulls(clause, 0.35, 0.15, random.Random(2026)),
                    "(iv) 折り返し ＋ 空文字": add_nulls(wrapped, 0.35, 0.15, random.Random(2026))}
        for name, pages in settings.items():
            words = [w for _, ls in pages for l in ls for w in l]
            e = unit_entropy.entropies([list(w) for w in words])
            v = null_generator.vocab_stats(words)
            k, n = scmp.judge(e, v)
            not_first = set(w for _, ls in pages for l in ls for w in l[1:])
            firsts = [l[0] for _, ls in pages for l in ls]
            share = sum(w not in not_first for w in firsts) / len(firsts)
            lens = [sum(len(w) for w in l) + len(l) - 1 for _, ls in pages for l in ls]
            cv = statistics.pstdev(lens) / statistics.mean(lens)
            r = line_unit.l1(pages, lambda w: w[-2:], lambda w: w[:2], rng)
            ex = r["行をまたぐ"] - r["無関係"]
            ok = (r["R"] <= 0.2 or ex <= 0.005) and 0.24 <= share <= 0.40
            print(f"  {p.stem} {name:<14} R {r['R']:.2f}  またぐ−基準 {ex:+.3f}  行頭だけの語 {share:.0%}  "
                  f"行の長さの変動係数 {cv:.2f}  8 つの量 {k}/{n}  行 {len(lens)}{'  ← 両方合う' if ok else ''}")


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:]]
    rng = random.Random(2026)
    exp10(paths, rng)
    exp11(paths, rng)


if __name__ == "__main__":
    main()

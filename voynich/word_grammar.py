#!/usr/bin/env python3
"""語の組み立ての表（第 10 回 第 4 段階）。語頭 × 芯の始まり × 語末。

    python3 voynich/word_grammar.py
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

HEADS = [("q", "o"), ("q",), ("o",), ("ch",), ("sh",), ("y",)]
ENDS = [("a", "i", "i", "n"), ("a", "i", "n"), ("i", "i", "n"), ("i", "n"), ("d", "y"), ("y",), ("l",), ("r",),
        ("m",), ("s",), ("n",)]


def parse(word: str):
    g = tuple(ivtff.glyphs(word))
    head = "なし"
    for h in HEADS:
        if g[:len(h)] == h and len(g) > len(h):
            head, g = "".join(h), g[len(h):]
            break
    end = "その他"
    for e in ENDS:
        if len(g) >= len(e) and g[-len(e):] == e:
            end, g = "".join(e), g[:-len(e)]
            break
    core = g[0] if g else "なし"
    return head, core, end


def table(pairs, title, min_exp=10):
    c = Counter(pairs)
    rows = Counter(a for a, _ in pairs)
    cols = Counter(b for _, b in pairs)
    n = len(pairs)
    g = 0.0
    avoid, prefer = [], []
    for a in rows:
        for b in cols:
            e = rows[a] * cols[b] / n
            o = c[(a, b)]
            if o:
                g += 2 * o * math.log(o / e)
            if e >= min_exp and o <= 0.2 * e:
                avoid.append((e, a, b, o))
            if e >= min_exp / 2 and o >= 3 * e:
                prefer.append((o / e, a, b, o, e))
    df = (len(rows) - 1) * (len(cols) - 1)
    print(f"{title}: G = {g:.0f}（自由度 {df}）")
    avoid.sort(reverse=True)
    prefer.sort(reverse=True)
    print("   避ける組（期待 → 観測）: " + ", ".join(f"{a}+{b}（{e:.0f} → {o}）" for e, a, b, o in avoid[:14]))
    print("   好む組（観測/期待）: " + ", ".join(f"{a}+{b}（{o}, {r:.1f} 倍）" for r, a, b, o, e in prefer[:14]))


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        words = [w for ln in lines if ln.page.get("L") == lang for w in ivtff.words(ln.raw, opts)]
        parsed = [parse(w) for w in words]
        print(f"=== 言語 {lang}（{len(words)} 語）===")
        print("語頭: " + ", ".join(f"{k} {v / len(parsed):.0%}" for k, v in Counter(h for h, _, _ in parsed).most_common()))
        print("語末: " + ", ".join(f"{k} {v / len(parsed):.0%}" for k, v in Counter(e for _, _, e in parsed).most_common()))
        print("芯の始まり: " + ", ".join(f"{k} {v / len(parsed):.0%}" for k, v in Counter(c for _, c, _ in parsed).most_common(10)))
        table([(h, e) for h, _, e in parsed], "G1 語頭 × 語末")
        table([(c, e) for _, c, e in parsed], "G2 芯の始まり × 語末")
        table([(h, c) for h, c, _ in parsed], "G3 語頭 × 芯の始まり")
        tri = Counter(parsed)
        cum, k = 0, 0
        for _, v in tri.most_common():
            cum += v
            k += 1
            if cum >= 0.9 * len(parsed):
                break
        print(f"G4 3 つ組の種類 {len(tri)}、上位 {k} 種類で延べ数の 90%")
        print("   上位 10: " + ", ".join(f"{h}+{c}…+{e} {v / len(parsed):.1%}" for (h, c, e), v in tri.most_common(10)))
        print()


if __name__ == "__main__":
    main()

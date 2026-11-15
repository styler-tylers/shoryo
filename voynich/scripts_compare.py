#!/usr/bin/env python3
"""ヨーロッパ以外の文字と中世の略記との比較（第 20 回）。

ヘブライ語・中国語・日本語の文章と、中世の略記に書き換えたラテン語で、第 12 回の情報量（h1, h2）と
第 14 回の語彙の使い方（V1〜V4）を測る。

    python3 voynich/scripts_compare.py --hebrew <…> --chinese <…> --japanese <…> --latin <…>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import null_generator  # noqa: E402
import unit_entropy  # noqa: E402

V_RANGE = {"h2": (1.83, 2.52), "h2/h1": (0.32, 0.80), "h1": (3.54, 4.19)}


def body(path: Path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*\* ?START.*?\*\*\*(.*)\*\*\* ?END", t, re.S)
    return m.group(1) if m else t


def hebrew_words(path: Path) -> list[list[str]]:
    t = re.sub(r"[ְ-ׇ]", "", body(path))  # 母音記号があれば除く
    return [list(w) for w in re.findall(r"[א-ת]+", t)]


def cjk_chars(path: Path, kana: bool) -> list[str]:
    pat = r"[一-鿿ぁ-ゟァ-ヺ]" if kana else r"[一-鿿]"
    return re.findall(pat, body(path))


WHOLE = {"et": "⁊", "est": "÷", "quod": "ꝙ", "non": "ñ"}
PREFIX = [("prae", "p̄"), ("per", "ꝑ"), ("pro", "ꝓ"), ("con", "ꝯ"), ("com", "ꝯ")]
SUFFIX = [("orum", "oꝝ"), ("que", "q;"), ("tur", "t᷑"), ("us", "ꝰ"), ("um", "ū")]
MACRON = {"a": "ā", "e": "ē", "i": "ī", "o": "ō", "u": "ū"}


def abbreviate(w: str) -> list[str]:
    """ラテン語の語を中世の略記の記号の並びに置き換える（記号 1 つを 1 単位）。"""
    if w in WHOLE:
        return [WHOLE[w]]
    head, tail = [], []
    for p, s in PREFIX:
        if w.startswith(p) and len(w) > len(p) + 1:
            head, w = [s], w[len(p):]
            break
    for p, s in SUFFIX:
        if w.endswith(p) and len(w) > len(p):
            tail, w = [s], w[:-len(p)]
            break
    mid = []
    i = 0
    while i < len(w):
        if i + 1 < len(w) and w[i] in MACRON and w[i + 1] in "mn" and i + 2 < len(w):
            mid.append(MACRON[w[i]])
            i += 2
        else:
            mid.append(w[i])
            i += 1
    return head + mid + tail


def show(name, e, v=None):
    hit = all(V_RANGE[k][0] <= e[k] <= V_RANGE[k][1] for k in V_RANGE)
    line = (f"{name:<30}{e['種類']:>6}{e['h1']:>7.2f}{e['h2']:>7.2f}{e['h2/h1']:>7.2f}"
            f"{e['語の長さ']:>7.2f}  {'← 範囲に入る' if hit else ''}")
    print(line)
    if v:
        print(" " * 30 + "  " + ", ".join(f"{k} {x:.3f}" for k, x in v.items()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hebrew", nargs="*", type=Path, default=[])
    ap.add_argument("--chinese", nargs="*", type=Path, default=[])
    ap.add_argument("--japanese", nargs="*", type=Path, default=[])
    ap.add_argument("--latin", nargs="*", type=Path, default=[])
    a = ap.parse_args()
    print(f"{'文章':<30}{'種類':>6}{'h1':>7}{'h2':>7}{'h2/h1':>7}{'語長':>7}")
    print("ヴォイニッチの範囲: h1 3.84〜3.89, h2 2.03〜2.32, h2/h1 0.52〜0.60（判定は ±0.3・±0.2 の余裕）\n")
    for p in a.hebrew:
        ws = hebrew_words(p)
        show(f"ヘブライ語 {p.stem}", unit_entropy.entropies(ws), null_generator.vocab_stats(["".join(w) for w in ws]))
    for p in a.chinese:
        ch = cjk_chars(p, kana=False)
        e = unit_entropy.entropies([[c] for c in ch])  # 区切りの記号が毎回入らないよう、後で区切りなしで計算し直す
        seq = [[c for c in ch[:30000]]]
        e = unit_entropy.entropies(seq, 30000)
        show(f"中国語 {p.stem}（字）", e, null_generator.vocab_stats(ch))
    for p in a.japanese:
        ch = cjk_chars(p, kana=True)
        show(f"日本語 {p.stem}（かな＋漢字）", unit_entropy.entropies([ch[:30000]], 30000))
        kana = [c for c in ch if "ぁ" <= c <= "ヺ"]
        show(f"日本語 {p.stem}（かなだけ）", unit_entropy.entropies([kana[:30000]], 30000))
    for p in a.latin:
        ws = ["".join(w) for w in unit_entropy.latin_words(p)]
        ab = [abbreviate(w) for w in ws]
        show(f"ラテン語 {p.stem}（元の文字）", unit_entropy.entropies([list(w) for w in ws]))
        show(f"ラテン語 {p.stem}（中世の略記）", unit_entropy.entropies(ab), null_generator.vocab_stats(["".join(w) for w in ab]))
    print("\n自然言語の語彙の範囲（第 14 回）: V1 1511〜4793, V2 0.491〜0.681, V3 −0.869〜−0.572, V4 0.597〜0.783")
    print("ヴォイニッチ: V1 2335〜3029, V2 0.69〜0.70, V3 −0.72〜−0.73, V4 0.64〜0.73")


if __name__ == "__main__":
    main()

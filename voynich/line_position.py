#!/usr/bin/env python3
"""ヴォイニッチ手稿 行頭・行末分析スクリプト。

行の中の位置（行頭・行中・行末）によって、単語や字形の出方が変わるかを調べる。
自然言語の文章なら、行の折り返しは単語の中身とほぼ無関係なはずなので、
偏りがあれば「行」が書き手にとって意味のある単位だった手がかりになる。

  1. 位置別の平均語長: 行の何語目かによって語の長さが変わるか
  2. 行頭に多い語・字形: 行頭の語を行中の語と比べ、多いもの（対数尤度比 G²）
  3. 行末に多い語・字形: 行末の語を行中の語と比べ、多いもの
  4. 段落の最初の行: 段落の最初の行に多い字形と、段落の最初の語の語頭

既定では段落テキスト（--locus P）だけを対象にする。ラベルや円形テキストは
1 行が 1 語だったり行の区切りが物理的でなかったりするため。

使い方の例:
    python3 voynich/line_position.py
    python3 voynich/line_position.py --by L        # 言語 A / B それぞれについて
    python3 voynich/line_position.py --illustration H --top 10

標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

GALLOWS = {"k", "t", "p", "f", "ckh", "cth", "cph", "cfh"}


# ---------------------------------------------------------------------------
# データ構造と集計
# ---------------------------------------------------------------------------


@dataclass
class TextLine:
    words: list[str]
    paragraph_start: bool  # 段落の最初の行（<%> を含む）
    paragraph_end: bool  # 段落の最後の行（<$> を含む）


def text_lines(lines: list[ivtff.Line], opts: ivtff.Options) -> list[TextLine]:
    result = []
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        if ws:
            result.append(TextLine(ws, "<%>" in ln.raw, "<$>" in ln.raw))
    return result


@dataclass
class Positions:
    """位置ごとに集めた単語。"""

    first: Counter  # 行頭の語（全行）
    last: Counter  # 行末の語（全行）
    middle: Counter  # 行頭・行末以外の語
    para_first: Counter  # 段落の最初の語
    line_first_other: Counter  # 段落の最初でない行の行頭の語
    line_last_other: Counter  # 段落の最後でない行の行末の語


def collect(tls: list[TextLine]) -> Positions:
    """3 語以上の行について、行頭・行中・行末の語を集める。

    2 語以下の行は行中が無いので、比較に使わない。
    """
    pos = Positions(*(Counter() for _ in range(6)))
    for tl in tls:
        if len(tl.words) < 3:
            continue
        pos.first[tl.words[0]] += 1
        pos.last[tl.words[-1]] += 1
        pos.middle.update(tl.words[1:-1])
        if tl.paragraph_start:
            pos.para_first[tl.words[0]] += 1
        else:
            pos.line_first_other[tl.words[0]] += 1
        if not tl.paragraph_end:
            pos.line_last_other[tl.words[-1]] += 1
    return pos


def first_glyphs(words: Counter, n: int = 1) -> Counter:
    out = Counter()
    for w, c in words.items():
        gs = ivtff.glyphs(w)
        if len(gs) >= n:
            out["".join(gs[:n])] += c
    return out


def last_glyphs(words: Counter, n: int = 1) -> Counter:
    out = Counter()
    for w, c in words.items():
        gs = ivtff.glyphs(w)
        if len(gs) >= n:
            out["".join(gs[-n:])] += c
    return out


def glyph_counts(words: Counter) -> Counter:
    out = Counter()
    for w, c in words.items():
        for g in ivtff.glyphs(w):
            out[g] += c
    return out


def length_by_position(tls: list[TextLine], span: int) -> tuple[list, list]:
    """行頭から span 語・行末から span 語の、位置ごとの平均語長（字形数）と件数。

    行頭側と行末側が重ならないよう、2*span 語以上の行だけを使う。
    """
    head = [[0, 0] for _ in range(span)]
    tail = [[0, 0] for _ in range(span)]
    for tl in tls:
        if len(tl.words) < 2 * span:
            continue
        for i in range(span):
            head[i][0] += len(ivtff.glyphs(tl.words[i]))
            head[i][1] += 1
            tail[i][0] += len(ivtff.glyphs(tl.words[-1 - i]))
            tail[i][1] += 1
    return head, tail


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def print_compare(title: str, target: Counter, ref: Counter, names: tuple[str, str],
                  top: int, min_count: int, label_fmt: str = "{}") -> None:
    """target で ref より多い項目を G² の順に表示する。"""
    c, d = sum(target.values()), sum(ref.values())
    if not c or not d:
        return
    rows = corpus.distinctive(target, ref, c, d, min_count)[:top]
    print(f"--- {title} ---")
    if not rows:
        print("（有意に多いものはありません）\n")
        return
    labels = [label_fmt.format(item) for _, item, _, _ in rows]
    width = max([len(s) for s in labels] + [6])
    print(f"{ljust('', width)}  {rjust('G²', 7)}  {rjust(names[0], 15)}  "
          f"{rjust(names[1], 15)}  {rjust('倍率', 6)}")
    for label, (g2, _, a, b) in zip(labels, rows):
        ratio = (a / c) / (b / d) if b else float("inf")
        ratio_s = f"{ratio:.1f}" if b else "∞"
        print(f"{label:<{width}}  {g2:>7.1f}  {a:>6} ({a / c:>6.2%})  "
              f"{b:>6} ({b / d:>6.2%})  {ratio_s:>6}")
    print()


def print_lengths(tls: list[TextLine], span: int) -> None:
    head, tail = length_by_position(tls, span)
    n = head[0][1]
    if not n:
        return
    print(f"--- 位置別の平均語長（字形数, {2 * span} 語以上の行 {n} 行）---")
    cols = [f"{i + 1}語目" for i in range(span)] + ["…"] + \
           [f"末{'-' + str(i) if i else ''}" for i in reversed(range(span))]
    vals = [f"{s / k:.2f}" for s, k in head] + ["…"] + \
           [f"{s / k:.2f}" for s, k in reversed(tail)]
    print("  ".join(rjust(c, 6) for c in cols))
    print("  ".join(rjust(v, 6) for v in vals))
    print("（末 = 行末の語, 末-1 = その 1 つ前）\n")


def report(title: str, tls: list[TextLine], args) -> None:
    pos = collect(tls)
    n_lines = sum(1 for tl in tls if len(tl.words) >= 3)
    n_para = sum(1 for tl in tls if tl.paragraph_start and len(tl.words) >= 3)
    n_words = sum(len(tl.words) for tl in tls)
    print(f"=== {title} ===")
    print(f"行数: {len(tls)}（うち 3 語以上で比較に使う行: {n_lines}, 段落の最初の行: {n_para}）")
    print(f"1 行あたりの平均語数: {n_words / max(len(tls), 1):.2f}\n")

    print_lengths(tls, args.span)

    top, mc = args.top, args.min_count
    # 段落の最初の行は行頭にガロウズが極端に多いので、行頭の比較からは除き、別に扱う。
    first, note = pos.line_first_other, "段落の最初の行を除く"
    names = ("行頭", "行中")
    print_compare(f"行頭に多い語（行中と比較, {note}）", first, pos.middle, names, top, mc)
    print_compare(f"行頭の語の語頭字形（行中の語と比較, {note}）",
                  first_glyphs(first), first_glyphs(pos.middle), names, top, mc, "{}-")
    print_compare(f"行頭の語の語頭 2 字形（行中の語と比較, {note}）",
                  first_glyphs(first, 2), first_glyphs(pos.middle, 2), names, top, mc, "{}-")

    # 段落の最後の行は途中で終わる短い行なので、行末の比較からは除く。
    last, note = pos.line_last_other, "段落の最後の行を除く"
    names = ("行末", "行中")
    print_compare(f"行末に多い語（行中と比較, {note}）", last, pos.middle, names, top, mc)
    print_compare(f"行末の語の語尾字形（行中の語と比較, {note}）",
                  last_glyphs(last), last_glyphs(pos.middle), names, top, mc, "-{}")
    print_compare(f"行末の語の語尾 2 字形（行中の語と比較, {note}）",
                  last_glyphs(last, 2), last_glyphs(pos.middle, 2), names, top, mc, "-{}")

    para_lines = Counter()
    other_lines = Counter()
    for tl in tls:
        (para_lines if tl.paragraph_start else other_lines).update(tl.words)
    print_compare("段落の最初の行に多い字形（他の行と比較, 全位置）",
                  glyph_counts(para_lines), glyph_counts(other_lines),
                  ("段落1行目", "他の行"), top, mc)
    print_compare("段落の最初の語の語頭字形（他の行の行頭の語と比較）",
                  first_glyphs(pos.para_first), first_glyphs(pos.line_first_other),
                  ("段落頭", "他の行頭"), top, mc, "{}-")

    gallows = sum(c for g, c in first_glyphs(pos.para_first).items() if g in GALLOWS)
    total = sum(pos.para_first.values())
    if total:
        print(f"段落の最初の語のうち、ガロウズ字形（k t p f と台付き）で始まるもの: "
              f"{gallows}/{total} ({gallows / total:.1%})\n")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None):
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）の行頭・行末分析")
    p.add_argument("--top", type=int, default=12, help="各表に表示する件数（既定: 12）")
    p.add_argument("--span", type=int, default=4,
                   help="位置別の平均語長で、行頭・行末から何語目まで見るか（既定: 4）")
    args = p.parse_args(argv)
    if args.locus is None:
        args.locus = "P"
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    print(f"転写ファイル: {path.name}\n")
    report(corpus.filter_title(args), text_lines(lines, opts), args)

    if args.by:
        groups: dict[str, list[ivtff.Line]] = {}
        for ln in lines:
            groups.setdefault(ln.page.get(args.by), []).append(ln)
        for key in sorted(groups):
            report(corpus.group_label(args.by, key), text_lines(groups[key], opts), args)


if __name__ == "__main__":
    main()

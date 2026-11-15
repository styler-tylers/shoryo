#!/usr/bin/env python3
"""語の家族: 同じ頁に出る「字形 1 つ違い」の語の組で、語のどこが変わるか（第 10 回）。

notes/2026-11-15 ヴォイニッチ手稿 語の家族.md の事前の記録のとおり。

    python3 voynich/word_families.py
    python3 voynich/word_families.py --control pg218.txt pg23306.txt   # ラテン語の参照（F2）
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import self_citation as sc  # noqa: E402

POS = ["語頭", "語中", "語末"]


def edit(a: tuple, b: tuple):
    """字形 1 つ違いの 2 語の、変わる位置（長い方の語で数える）と種類。違いが 1 つでなければ None。"""
    if len(a) == len(b):
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        if len(diff) != 1:
            return None
        i, n, kind, change = diff[0], len(a), "置き換え", (a[diff[0]], b[diff[0]])
    else:
        if len(a) < len(b):
            a, b = b, a
        if len(a) != len(b) + 1:
            return None
        i = next((k for k in range(len(b)) if a[k] != b[k]), len(b))
        if a[:i] + a[i + 1:] != b:
            return None
        # 同じ字形が続く場合（例: ee → e）は、どこを消しても同じ。いちばん後ろの位置にそろえる
        while i + 1 < len(a) and a[i + 1] == a[i]:
            i += 1
        n, kind, change = len(a), "挿入・削除", (a[i],)
    pos = "語頭" if i == 0 else "語末" if i == n - 1 else "語中"
    return pos, kind, change


def pairs(pages: dict[str, list[list[str]]], min_glyphs: int = 3, min_freq: int = 3):
    freq = Counter(w for ls in pages.values() for l in ls for w in l)
    words = [w for w, c in freq.items() if c >= min_freq and len(sc.glyph_tuple(w)) >= min_glyphs]
    on_page = defaultdict(set)
    for p, ls in pages.items():
        for l in ls:
            for w in l:
                on_page[w].add(p)
    by_len = defaultdict(list)
    for w in words:
        by_len[len(sc.glyph_tuple(w))].append(w)
    same, base = [], []
    for w in words:
        n = len(sc.glyph_tuple(w))
        for v in by_len[n] + by_len[n + 1]:
            if v <= w and len(sc.glyph_tuple(v)) == n:
                continue  # 同じ長さの組は 1 回だけ数える
            e = edit(sc.glyph_tuple(w), sc.glyph_tuple(v))
            if e is None:
                continue
            (same if on_page[w] & on_page[v] else base).append(e)
    return same, base


def g_test(rows: list[list[int]]) -> tuple[float, float]:
    """分割表の G 検定。戻り値: (G, p)。自由度 (r-1)(c-1) のカイ二乗分布で近似。"""
    R, C = len(rows), len(rows[0])
    tot = sum(map(sum, rows))
    rs = [sum(r) for r in rows]
    cs = [sum(r[j] for r in rows) for j in range(C)]
    g = 0.0
    for i in range(R):
        for j in range(C):
            o = rows[i][j]
            e = rs[i] * cs[j] / tot
            if o > 0:
                g += 2 * o * math.log(o / e)
    df = (R - 1) * (C - 1)
    # カイ二乗分布の上側確率（自由度 2 なら exp(-x/2)）
    p = math.exp(-g / 2) if df == 2 else float("nan")
    return g, p


def show(title: str, same, base, detail: bool) -> None:
    def dist(xs):
        c = Counter(p for p, _, _ in xs)
        n = len(xs)
        return [c[k] for k in POS], n

    cs, ns = dist(same)
    cb, nb = dist(base)
    print(f"=== {title} ===")
    print(f"{'':<16}" + "".join(f"{k:>8}" for k in POS) + f"{'組の数':>8}")
    print(f"{'同じ頁の家族':<16}" + "".join(f"{x / ns:>8.1%}" for x in cs) + f"{ns:>8}")
    print(f"{'基準（一緒に出ない）':<14}" + "".join(f"{x / nb:>8.1%}" for x in cb) + f"{nb:>8}")
    if ns and nb:
        g, p = g_test([cs, cb])
        print(f"F1 G = {g:.1f}, p = {p:.2g}（自由度 2）")
    kinds = Counter(k for _, k, _ in same)
    print(f"編集の種類（同じ頁の家族）: " + ", ".join(f"{k} {v / ns:.0%}" for k, v in kinds.items()))
    if detail:
        sub = Counter(tuple(sorted(c)) for _, k, c in same if k == "置き換え")
        ins = Counter(c[0] for _, k, c in same if k == "挿入・削除")
        print("F3 多い置き換え（字形 ↔ 字形）: " + ", ".join(f"{a}↔{b} {n}" for (a, b), n in sub.most_common(15)))
        print("F3 多い挿入・削除の字形: " + ", ".join(f"{g} {n}" for g, n in ins.most_common(10)))
        pos_sub = defaultdict(Counter)
        for p, k, c in same:
            pos_sub[p][(k, tuple(sorted(c)))] += 1
        for p in POS:
            print(f"   {p}で多い変化: " + ", ".join(
                f"{'↔'.join(c)}{'（挿入・削除）' if k != '置き換え' else ''} {n}" for (k, c), n in pos_sub[p].most_common(6)))
    print()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="語の家族の変わる位置")
    ap.add_argument("--control", nargs="*", type=Path, help="対照のラテン語テキスト（F2）")
    args = ap.parse_args(argv)
    if args.control:
        sc.CHAR_MODE = True
        for path in args.control:
            pages = sc.text_pages(path, 8, 25)
            same, base = pairs(pages)
            show(f"対照 {path.name}（文字単位）", same, base, detail=False)
        return
    base_args = corpus.make_parser("").parse_args([])
    base_args.locus = "P"
    _, lines = corpus.load_lines(base_args)
    opts = corpus.word_options(base_args)
    for lang in ("A", "B"):
        pages = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        same, base = pairs(pages)
        show(f"ヴォイニッチ 言語 {lang}（{len(pages)} 頁）", same, base, detail=True)


if __name__ == "__main__":
    main()

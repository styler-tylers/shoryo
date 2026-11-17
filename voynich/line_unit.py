#!/usr/bin/env python3
"""行は意味の単位か（第 16 回）。

L1 行をまたぐ語のつながり（前の語の語末 × 後ろの語の語頭 の相互情報量）
L2 段落の中の行の長さのばらつき
参照: ラテン語を文字数で折り返した文章と、1 行に 1 文の文章

    python3 voynich/line_unit.py <ラテン語のテキスト …>
"""

from __future__ import annotations

import math
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import unit_entropy  # noqa: E402
import word_grammar  # noqa: E402


def mi(pairs) -> float:
    n = len(pairs)
    cxy = Counter(pairs)
    cx = Counter(a for a, _ in pairs)
    cy = Counter(b for _, b in pairs)
    return sum(c / n * math.log2(c * n / (cx[a] * cy[b])) for (a, b), c in cxy.items())


def l1(paragraphs, end_fn, head_fn, rng, runs=50):
    """paragraphs: [(頁, [行の語のリスト, …])]。R と各 MI を返す。"""
    within, cross = [], []
    firsts_by_page = {}
    for page, ls in paragraphs:
        for l in ls:
            within += [(end_fn(a), head_fn(b)) for a, b in zip(l, l[1:])]
        for a, b in zip(ls, ls[1:]):
            cross.append((page, end_fn(a[-1]), head_fn(b[0])))
        firsts_by_page.setdefault(page, []).extend(head_fn(l[0]) for l in ls)
    n = len(cross)
    if n < 100:
        return None
    pages = list(firsts_by_page)
    m_cross = mi([(a, b) for _, a, b in cross])
    m_within, m_null = [], []
    for _ in range(runs):
        m_within.append(mi(rng.sample(within, n)))
        null = []
        for page, a, _ in cross:
            q = rng.choice([p for p in pages if p != page]) if len(pages) > 1 else page
            null.append((a, rng.choice(firsts_by_page[q])))
        m_null.append(mi(null))
    mw, mn = statistics.mean(m_within), statistics.mean(m_null)
    r = (m_cross - mn) / (mw - mn) if mw > mn else float("nan")
    return {"組": n, "行の中": mw, "行をまたぐ": m_cross, "無関係": mn, "R": r}


def voynich_paragraphs(lines, lang, opts):
    paras, cur, page = [], [], None
    L = [ln for ln in lines if ln.page.get("L") == lang]
    for ln in L:
        ws = ivtff.words(ln.raw, opts)
        if not ws:
            continue
        if ln.position == "@" or ln.page.name != page:
            if cur:
                paras.append((page, cur))
            cur, page = [], ln.page.name
        cur.append(ws)
    if cur:
        paras.append((page, cur))
    return paras


def line_len(ws, glyphs=True) -> int:
    return sum(len(ivtff.glyphs(w)) if glyphs else len(w) for w in ws) + len(ws) - 1


def cv_by_page(paragraphs, glyphs=True) -> float:
    by_page: dict[str, list[int]] = {}
    for page, ls in paragraphs:
        for l in ls[:-1]:  # 段落の最後の行を除く
            by_page.setdefault(page, []).append(line_len(l, glyphs))
    cvs = [statistics.pstdev(v) / statistics.mean(v) for v in by_page.values() if len(v) >= 4]
    return statistics.median(cvs)


def wrap(words, width: int, lines_per_page: int = 25):
    lines, cur, n = [], [], 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur and n + add > width:
            lines.append(cur)
            cur, n = [], 0
            add = len(w)
        cur.append(w)
        n += add
    if cur:
        lines.append(cur)
    return [(f"p{i // lines_per_page}", lines[i:i + lines_per_page]) for i in range(0, len(lines), lines_per_page)]


def sentences(path: Path, lines_per_page: int = 25):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*\* ?START.*?\*\*\*(.*)\*\*\* ?END", text, re.S)
    text = (m.group(1) if m else text).lower()
    sents = [re.findall(r"[a-z]+", s) for s in re.split(r"[.;:?!]", text)]
    sents = [s for s in sents if s]
    return [(f"p{i // lines_per_page}", sents[i:i + lines_per_page]) for i in range(0, len(sents), lines_per_page)]


def show(name, r):
    if r is None:
        print(f"  {name}: 組が 100 未満のため判定しない")
        return
    print(f"  {name:<28} 組 {r['組']:>5}  行の中 {r['行の中']:.3f}  行をまたぐ {r['行をまたぐ']:.3f}  無関係 {r['無関係']:.3f}  R = {r['R']:.2f}")


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    vend = lambda w: word_grammar.parse(w)[2]  # noqa: E731
    vhead = lambda w: word_grammar.parse(w)[0]  # noqa: E731
    lend = lambda w: w[-2:]  # noqa: E731
    lhead = lambda w: w[:2]  # noqa: E731
    print("=== L1 行をまたぐ語のつながり（前の語の語末 × 後ろの語の語頭 の相互情報量, ビット）===")
    vp = {lang: voynich_paragraphs(lines, lang, opts) for lang in ("A", "B")}
    for lang in ("A", "B"):
        show(f"ヴォイニッチ {lang}", l1(vp[lang], vend, vhead, rng))
    width = round(statistics.mean(line_len(l) for _, ls in vp["A"] for l in ls[:-1]))
    print(f"  （ラテン語の折り返しの幅: ヴォイニッチ A の段落の行の平均 {width} 字）")
    lat = {}
    for p in map(Path, sys.argv[1:]):
        words = ["".join(w) for w in unit_entropy.latin_words(p)]
        lat[p.stem] = (wrap(words, width), sentences(p))
        show(f"ラテン語 {p.stem}（文字数で折り返し）", l1(lat[p.stem][0], lend, lhead, rng))
        show(f"ラテン語 {p.stem}（1 行に 1 文）", l1(lat[p.stem][1], lend, lhead, rng))

    print("\n=== L2 段落の中の行の長さの変動係数（頁ごとの中央値, 段落の最後の行を除く）===")
    for lang in ("A", "B"):
        print(f"  ヴォイニッチ {lang}: {cv_by_page(vp[lang]):.3f}")
    for name, (wr, se) in lat.items():
        print(f"  ラテン語 {name}: (a) 文字数で折り返し {cv_by_page(wr, glyphs=False):.3f}、(b) 1 行に 1 文 {cv_by_page(se, glyphs=False):.3f}")


if __name__ == "__main__":
    main()

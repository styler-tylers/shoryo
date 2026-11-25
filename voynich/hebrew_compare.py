#!/usr/bin/env python3
"""ヴォイニッチの文章を、本物のヘブライ語の文章と比べる（第 12 回の「次のアクション」）。

第 12 回では、子音だけを書く文字を「ヨーロッパの言語から母音を消す」という近似でしか試せなかった。
ここでは本物のヘブライ文字の文章（母音記号・アクセント記号を除いた子音の綴り）で、
同じ量（h0, h1, h2, h2/h1, 語の長さ）と、字形の「語の中の位置への偏り」を測る。

ヘブライ文字には、語末でだけ使う形（語末形: ך ם ן ף ץ）がある。
ヴォイニッチにも語頭・語末にしか出ない字形があるので、この性質も比べる。

    python3 voynich/hebrew_compare.py <Sefaria の JSON …>

JSON は Sefaria の API（v3, return_format=text_only）から取得したもの:
    https://www.sefaria.org/api/v3/texts/Genesis?version=hebrew&return_format=text_only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import self_citation as sc  # noqa: E402
import word_families as wf  # noqa: E402
from unit_entropy import entropies, show  # noqa: E402

FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
_MARKS = re.compile(r"[֑-ׇ]")  # 母音記号（ニクード）・アクセント記号・メテグなど
_WORD = re.compile(r"[א-ת]+")


def flatten(x):
    return [y for z in x for y in flatten(z)] if isinstance(x, list) else [x]


def hebrew_words(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = " ".join(flatten(data["versions"][0]["text"]))
    text = re.sub(r"<[^>]+>", " ", text)  # HTML のタグ
    text = re.sub(r"\([^)]*\)", " ", text)  # 聖書の箇所の注記（出典）
    text = text.replace("־", " ")  # マカフ（語をつなぐ横線）は語の区切りとする
    text = _MARKS.sub("", text)
    return _WORD.findall(text)


def positional(words: list[list[str]], min_count: int = 100, share: float = 0.9):
    """出現 min_count 回以上の単位のうち、語の中の 1 つの位置（語頭・語中・語末）に share 以上偏るもの。"""
    pos = defaultdict(Counter)
    for w in words:
        if len(w) < 2:
            continue
        for i, u in enumerate(w):
            pos[u]["語頭" if i == 0 else "語末" if i == len(w) - 1 else "語中"] += 1
    rows = []
    for u, c in pos.items():
        n = sum(c.values())
        if n >= min_count:
            where, k = c.most_common(1)[0]
            rows.append((u, n, where, k / n))
    biased = sorted([r for r in rows if r[3] >= share], key=lambda r: -r[1])
    return len(rows), biased


def hebrew_pages(words: list[str], words_per_line: int = 8, lines_per_page: int = 25):
    """第 10 回の対照（self_citation.text_pages）と同じく、語を機械的に行・頁に折り返す。語末形はまとめる。"""
    ws = ["".join(FINALS.get(c, c) for c in w) for w in words]
    lines = [ws[i:i + words_per_line] for i in range(0, len(ws), words_per_line)]
    return {f"p{k}": lines[k:k + lines_per_page] for k in range(0, len(lines), lines_per_page)}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("texts", nargs="+", type=Path, help="Sefaria の JSON ファイル")
    args = ap.parse_args(argv)

    base = corpus.make_parser("").parse_args([])
    base.locus = "P"
    _, lines = corpus.load_lines(base)
    opts = corpus.word_options(base)
    voy = {"A": [], "B": []}
    for ln in lines:
        if ln.page.get("L") in voy:
            voy[ln.page.get("L")] += [ivtff.glyphs(w) for w in ivtff.words(ln.raw, opts)]

    heb = {}
    for path in args.texts:
        ws = hebrew_words(path)
        heb[path.stem] = ws

    print(f"{'文章':<28}{'種類':>5}{'h0':>7}{'h1':>7}{'h2':>7}{'h2/h1':>8}{'語の長さ':>6}")
    for L, ws in voy.items():
        show(f"ヴォイニッチ {L}（字形）", entropies(ws))
    for name, ws in heb.items():
        show(f"{name[:18]}（語末形あり）", entropies([list(w) for w in ws]))
        show(f"{name[:18]}（語末形をまとめる）", entropies([[FINALS.get(c, c) for c in w] for w in ws]))
    print()
    print("語の中の 1 つの位置に 9 割以上偏る単位（出現 100 回以上の単位のうち）:")
    for L, ws in voy.items():
        n, biased = positional(ws)
        print(f"  ヴォイニッチ {L}: {len(biased)} / {n} — "
              + "、".join(f"{u}({w} {s:.0%})" for u, _, w, s in biased))
    for name, ws in heb.items():
        n, biased = positional([list(w) for w in ws])
        print(f"  {name}: {len(biased)} / {n} — "
              + "、".join(f"{u}({w} {s:.0%})" for u, _, w, s in biased))

    # 第 10 回と同じ「1 字違いの語の家族は語のどこが変わるか」をヘブライ語で測る
    print()
    sc.CHAR_MODE = True
    for name, ws in heb.items():
        same, base = wf.pairs(hebrew_pages(ws))
        wf.show(f"{name}（文字単位、語末形をまとめる）", same, base, detail=False)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ヴォイニッチ手稿 「自己引用」説の検証スクリプト。

自己引用説（Timm & Schinner）: 書き手は、少し前に書いた語（同じ行の前の語や、上の行の語）を
写しながら字を少しずつ変えて、新しい語を作っていった、とする説。

予測と検証:
  1. 近くの語の「写し」: ある語とほぼ同じ語（同じ語 / 字形が 1 つだけ違う語）が、
     同じ行の前の語や 1 つ上の行にある割合を、同じグループ（言語）の別の頁の
     同じ位置の行と比べる（別の頁の行では写しは起こり得ないので、偶然の一致の基準になる）。
  2. 行の距離による減衰: k 行上（k = 1〜8）にほぼ同じ語がある割合。写しなら近い行ほど高い。
     同じ頁の話題の共通性だけなら、頁の中で距離によらずほぼ一定のはず。
  3. 縦の位置: 1 つ上の行の「字形が 1 つだけ違う語」が、真上（行の中の相対位置が近い）にあるか。
     話題の共通性では語の横位置は揃わないので、真上に偏れば「上の行を見て写した」ことを示す。

    python3 voynich/self_citation.py
    python3 voynich/self_citation.py --language B
    python3 voynich/self_citation.py --file IT2a-n.txt

標準ライブラリのみで動作する。既定は段落テキスト（--locus P）で、言語 A・B を分けて比べる。
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from corpus import ljust, rjust  # noqa: E402


CHAR_MODE = False  # 対照の自然言語テキストでは、字形ではなく文字で数える


@lru_cache(maxsize=None)
def glyph_tuple(word: str) -> tuple:
    return tuple(word) if CHAR_MODE else tuple(ivtff.glyphs(word))


@lru_cache(maxsize=2_000_000)
def distance(a: str, b: str) -> int:
    """字形単位の編集距離（挿入・削除・置換を 1 と数える）。"""
    if a == b:
        return 0
    x, y = glyph_tuple(a), glyph_tuple(b)
    if abs(len(x) - len(y)) > 1:
        return 2  # 2 以上なら区別しなくてよい
    prev = list(range(len(y) + 1))
    for i, gx in enumerate(x, 1):
        cur = [i] + [0] * len(y)
        for j, gy in enumerate(y, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (gx != gy))
        prev = cur
    return prev[-1]


def best(word: str, window: list[str]) -> int:
    """window の中で word に最も近い語との距離（0 = 同じ語, 1 = 字形 1 つ違い, 2 = それ以上）。"""
    d = 2
    for w in window:
        d = min(d, distance(word, w))
        if d == 0:
            break
    return d


# ---------------------------------------------------------------------------
# データ
# ---------------------------------------------------------------------------


def text_pages(path: Path, words_per_line: int, lines_per_page: int) -> dict[str, list[list[str]]]:
    """対照用: 普通のテキストファイルの語を、決まった語数の行・行数の頁に折り返す。

    Project Gutenberg の前置き・後書き（*** START / *** END の外）は除く。
    折り返しは機械的なので、行の区切りと語の中身は無関係（写しの起こらない自然言語の基準）。
    """
    import re
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*\* ?START.*?\*\*\*(.*)\*\*\* ?END", text, re.S)
    if m:
        text = m.group(1)
    words = re.findall(r"[a-zà-ÿ]+", text.lower())
    pages: dict[str, list[list[str]]] = {}
    per_page = words_per_line * lines_per_page
    for n, start in enumerate(range(0, len(words) - per_page + 1, per_page)):
        chunk = words[start:start + per_page]
        pages[f"p{n + 1}"] = [chunk[i:i + words_per_line] for i in range(0, per_page, words_per_line)]
    return pages


def page_lines(lines: list[ivtff.Line], opts) -> dict[str, list[list[str]]]:
    pages: dict[str, list[list[str]]] = defaultdict(list)
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        if ws:
            pages[ln.page.name].append(ws)
    return {p: ls for p, ls in pages.items() if len(ls) >= 3}


# ---------------------------------------------------------------------------
# 検証 1: 近くの語の写し
# ---------------------------------------------------------------------------


def copy_rates(pages, source_of) -> tuple[int, int, int]:
    """各語について、同じ行の前の語 + 1 つ上の行（source_of が返す行）にほぼ同じ語があるか。

    source_of(page, line_index) -> (同じ行の代わりに使う行, 上の行) を返す。
    戻り値: (同じ語あり, 字形 1 つ違いの語あり（同じ語は無い）, 対象の語数)
    """
    exact = near = total = 0
    for page, ls in pages.items():
        for li in range(1, len(ls)):
            same_line, above = source_of(page, li)
            if same_line is None or above is None:
                continue
            line = ls[li]
            for wi, w in enumerate(line):
                window = same_line[:wi] + above
                d = best(w, window)
                total += 1
                if d == 0:
                    exact += 1
                elif d == 1:
                    near += 1
    return exact, near, total


def null_source(pages, rng):
    """同じグループの別の頁の、同じ行番号あたりの行を使う（写しの起こり得ない基準）。"""
    names = list(pages)

    def source(page, li):
        other = rng.choice([n for n in names if n != page])
        ols = pages[other]
        if len(ols) < 2:
            return None, None
        j = min(li, len(ols) - 1)
        j = max(j, 1)
        return ols[j], ols[j - 1]

    return source


# ---------------------------------------------------------------------------
# 検証 2: 行の距離による減衰
# ---------------------------------------------------------------------------


def decay(pages, max_k: int, rng, null_runs: int):
    """k 行上の行に、ほぼ同じ語（距離 1 以下, 同じ語を含む）がある割合。同じ頁と、別の頁の行の基準。"""
    names = list(pages)
    rows = []
    for k in range(1, max_k + 1):
        hit = tot = 0
        for ls in pages.values():
            for li in range(k, len(ls)):
                for w in ls[li]:
                    tot += 1
                    hit += best(w, ls[li - k]) <= 1
        nh = nt = 0
        for _ in range(null_runs):
            for page, ls in pages.items():
                for li in range(k, len(ls)):
                    other = pages[rng.choice([n for n in names if n != page])]
                    ref = other[min(li - k, len(other) - 1)]
                    for w in ls[li]:
                        nt += 1
                        nh += best(w, ref) <= 1
        rows.append((k, hit / tot if tot else 0, nh / nt if nt else 0, tot))
    return rows


# ---------------------------------------------------------------------------
# 検証 3: 縦の位置
# ---------------------------------------------------------------------------


def vertical_alignment(pages, rng, trials: int, inner: bool = False, other_page: bool = False):
    """1 つ上の行の「字形が 1 つだけ違う語」の、行の中の相対位置の差。

    戻り値: (実際の平均の差, 上の行の語の順番を入れ替えた場合の平均の差, p 値, 組の数)
    相対位置 = 語の順番 /（行の語数 − 1）。差が小さいほど「真上」。
    """
    pairs = []  # (行, 上の行, 語の位置 wi, 上の行で距離 1 の語の位置のリスト)
    names = list(pages)
    for page, ls in pages.items():
        for li in range(1, len(ls)):
            line, above = ls[li], ls[li - 1]
            if other_page:  # 対照: 上の行の代わりに、別の頁の同じあたりの行を使う（写しは起こり得ない）
                other = pages[rng.choice([n for n in names if n != page])]
                above = other[min(li - 1, len(other) - 1)]
            if len(line) < 2 or len(above) < 2:
                continue
            if inner and (len(line) < 4 or len(above) < 4):
                continue
            for wi, w in enumerate(line):
                if inner and wi in (0, len(line) - 1):
                    continue
                hits = [aj for aj, a in enumerate(above) if distance(w, a) == 1
                        and not (inner and aj in (0, len(above) - 1))]
                if hits:
                    pairs.append((len(line), len(above), wi, hits))

    def mean_gap(perm: bool) -> float:
        gaps = []
        for n_line, n_above, wi, hits in pairs:
            x = wi / (n_line - 1)
            if perm:
                if inner:  # 行頭・行末を除いた位置の中だけで入れ替える
                    middle = list(range(1, n_above - 1))
                    shuffled = middle[:]
                    rng.shuffle(shuffled)
                    order = dict(zip(middle, shuffled))
                else:
                    order = list(range(n_above))
                    rng.shuffle(order)
                hits = [order[h] for h in hits]
            gaps.append(min(abs(x - h / (n_above - 1)) for h in hits))
        return sum(gaps) / len(gaps) if gaps else float("nan")

    obs = mean_gap(False)
    null = [mean_gap(True) for _ in range(trials)]
    p = (sum(1 for v in null if v <= obs) + 1) / (trials + 1)
    return obs, sum(null) / len(null), p, len(pairs)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def report(title: str, pages, args, rng) -> None:
    n_words = sum(len(l) for ls in pages.values() for l in ls)
    print(f"=== {title}: {len(pages)} 頁, {n_words} 語 ===\n")

    def own(page, li):
        return pages[page][li], pages[page][li - 1]

    e, n, t = copy_rates(pages, own)
    ne = nn = nt = 0
    for _ in range(args.null_runs):
        a, b, c = copy_rates(pages, null_source(pages, rng))
        ne, nn, nt = ne + a, nn + b, nt + c
    print("--- 検証 1: 同じ行の前の語と 1 つ上の行に、ほぼ同じ語があるか ---")
    print(f"{ljust('', 26)}{rjust('同じ語', 10)}{rjust('字形1つ違い', 12)}{rjust('どちらか', 10)}")
    print(f"{ljust('実際（同じ頁）', 26)}{e / t:>10.1%}{n / t:>12.1%}{(e + n) / t:>10.1%}")
    print(f"{ljust('基準（別の頁の同じ位置の行）', 26)}{ne / nt:>10.1%}{nn / nt:>12.1%}{(ne + nn) / nt:>10.1%}")
    print(f"{ljust('倍率', 26)}{(e / t) / (ne / nt):>10.2f}{(n / t) / (nn / nt):>12.2f}"
          f"{((e + n) / t) / ((ne + nn) / nt):>10.2f}\n")

    print("--- 検証 2: k 行上の行に、ほぼ同じ語（同じ語か字形 1 つ違い）があるか ---")
    print(f"{rjust('k', 3)}{rjust('同じ頁', 9)}{rjust('別の頁', 9)}{rjust('倍率', 7)}{rjust('語数', 8)}")
    for k, same, other, tot in decay(pages, args.max_k, rng, max(1, args.null_runs // 4)):
        ratio = same / other if other else float("nan")
        print(f"{k:>3}{same:>9.1%}{other:>9.1%}{ratio:>7.2f}{tot:>8}")
    print("写しなら k が小さいほど倍率が高い。頁の話題の共通性だけなら、倍率は k によらずほぼ一定。\n")

    obs, null, p, n_pairs = vertical_alignment(pages, rng, args.trials)
    print("--- 検証 3: 上の行の「字形 1 つ違い」の語は真上にあるか ---")
    print(f"組 {n_pairs}。行の中の相対位置の差: 実際 {obs:.3f}、上の行の語順を入れ替えた場合 {null:.3f}"
          f"（p = {p:.4f}）")
    obs, null, p, n_pairs = vertical_alignment(pages, rng, args.trials, inner=True)
    print(f"行頭・行末の語を除いた場合: 組 {n_pairs}。実際 {obs:.3f}、入れ替え {null:.3f}（p = {p:.4f}）")
    obs, null, p, n_pairs = vertical_alignment(pages, rng, args.trials, inner=True, other_page=True)
    print(f"対照（上の行の代わりに別の頁の行, 行頭・行末を除く）: 組 {n_pairs}。実際 {obs:.3f}、入れ替え {null:.3f}"
          f"（p = {p:.4f}）")
    print("差が小さく p も小さければ、上の行の真上あたりの語を見て書いた（写した）ことを示す。")
    print("別の頁の行でも同じ偏りが出るなら、それは写しではなく「行の中の位置ごとに語の型が決まっている」ため。")
    print("行頭・行末には決まった型の語が多い（第 2 回）ので、それを除いても偏りが残るかが重要。\n")


def main(argv=None) -> None:
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）: 自己引用説の検証")
    p.add_argument("--null-runs", type=int, default=8, help="基準（別の頁）の繰り返し回数（既定: 8）")
    p.add_argument("--max-k", type=int, default=8, help="検証 2 で見る最大の行の距離（既定: 8）")
    p.add_argument("--trials", type=int, default=500, help="検証 3 の並べ替えの回数（既定: 500）")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--control", type=Path,
                   help="対照の自然言語テキスト（例: Project Gutenberg のラテン語の本）。指定するとこちらを分析する")
    p.add_argument("--words-per-line", type=int, default=8, help="対照テキストの 1 行の語数（既定: 8）")
    p.add_argument("--lines-per-page", type=int, default=25, help="対照テキストの 1 頁の行数（既定: 25）")
    args = p.parse_args(argv)
    if args.control:
        global CHAR_MODE
        CHAR_MODE = True
        rng = random.Random(args.seed)
        pages = text_pages(args.control, args.words_per_line, args.lines_per_page)
        print(f"対照テキスト: {args.control.name}（{args.words_per_line} 語/行, {args.lines_per_page} 行/頁に機械的に折り返し）\n")
        report("対照", pages, args, rng)
        return
    if args.locus is None:
        args.locus = "P"
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(args.seed)
    print(f"転写ファイル: {path.name}\n")
    groups: dict[str, list[ivtff.Line]] = defaultdict(list)
    for ln in lines:
        groups[ln.page.get("L")].append(ln)
    for key in sorted(groups):
        if key not in ("A", "B"):
            continue
        pages = page_lines(groups[key], opts)
        if len(pages) >= 5:
            report(f"{corpus.filter_title(args)}・言語 {key}", pages, args, rng)


if __name__ == "__main__":
    main()

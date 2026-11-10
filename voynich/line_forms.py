#!/usr/bin/env python3
"""ヴォイニッチ手稿 行頭形・行末形の検証スクリプト。

行頭の語は `y-` `s-` `d-` で始まることが多く、行末の語は `-m` で終わることが多い
（line_position.py の結果）。これが「ふつうの語に、行頭だけで付く字形が加わったもの」
「ふつうの語の語尾が、行末だけ別の形になったもの」なのかを確かめる。

  1. 行頭形: 行頭の語から最初の字形を取り除いた残り（語幹）が、行中でふつうに使われる語か。
     同じ字形で始まる行中の語について同じことをした場合と比べる。
     行頭で取り除いた残りの方がずっと多く「行中の語」になるなら、最初の字形は行頭だけの付加物らしい。
  2. 行末形: 行末の `-m` で終わる語の最後の字形を別の語尾に置き換えたとき、行中の語になるか。
     どの語尾に置き換えたときに最もよく一致するかを、行中の `-m` 語と比べる。

使い方の例:
    python3 voynich/line_forms.py
    python3 voynich/line_forms.py --initial y,s,d,o --final m,g
    python3 voynich/line_forms.py --language B

標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_position  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

DEFAULT_REPLACEMENTS = ["", "n", "in", "iin", "r", "l", "s", "y", "dy"]


# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------


def strip_first(word: str) -> tuple[str, str] | None:
    """最初の字形と残りに分ける。1 字形だけの語は None。"""
    gs = ivtff.glyphs(word)
    if len(gs) < 2:
        return None
    return gs[0], "".join(gs[1:])


def strip_last(word: str) -> tuple[str, str] | None:
    """残りと最後の字形に分ける。1 字形だけの語は None。"""
    gs = ivtff.glyphs(word)
    if len(gs) < 2:
        return None
    return "".join(gs[:-1]), gs[-1]


def stem_rate(words: Counter, glyph: str, vocab: Counter, min_count: int) -> tuple[int, int]:
    """glyph で始まる語のうち、glyph を取り除いた残りが vocab で min_count 回以上使われる語の数。

    戻り値: (一致した出現数, glyph で始まる語の出現数)
    """
    hit = total = 0
    for w, c in words.items():
        parts = strip_first(w)
        if not parts or parts[0] != glyph:
            continue
        total += c
        if vocab[parts[1]] >= min_count:
            hit += c
    return hit, total


def replace_rate(words: Counter, glyph: str, repl: str, vocab: Counter,
                 min_count: int) -> tuple[int, int]:
    """glyph で終わる語の最後の字形を repl に置き換えたとき、vocab で min_count 回以上使われる語の数。"""
    hit = total = 0
    for w, c in words.items():
        parts = strip_last(w)
        if not parts or parts[1] != glyph:
            continue
        total += c
        candidate = parts[0] + repl
        if candidate != w and vocab[candidate] >= min_count:
            hit += c
    return hit, total


def stem_initials(words: Counter, glyph: str) -> Counter:
    """glyph で始まる語について、glyph を取り除いた残りの最初の字形の分布。"""
    out = Counter()
    for w, c in words.items():
        parts = strip_first(w)
        if parts and parts[0] == glyph:
            out[ivtff.glyphs(parts[1])[0]] += c
    return out


def word_initials(words: Counter) -> Counter:
    out = Counter()
    for w, c in words.items():
        gs = ivtff.glyphs(w)
        if gs:
            out[gs[0]] += c
    return out


def cosine(a: Counter, b: Counter) -> float:
    dot = sum(v * b[k] for k, v in a.items())
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def only_at_start(words: Counter, glyph: str, middle: Counter, min_count: int) -> tuple[int, int]:
    """glyph で始まる語のうち、語そのものは行中でほとんど使われない（min_count 回未満）のに、
    glyph を取り除いた残りは行中の語である、という語の出現数。"""
    hit = total = 0
    for w, c in words.items():
        parts = strip_first(w)
        if not parts or parts[0] != glyph:
            continue
        total += c
        if middle[w] < min_count <= middle[parts[1]]:
            hit += c
    return hit, total


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def fmt_rate(hit: int, total: int) -> str:
    return f"{hit:>5}/{total:<5} {hit / total:>6.1%}" if total else f"{'-':>18}"


def print_initial(first: Counter, middle: Counter, glyphs: list[str], min_count: int,
                  examples: int) -> None:
    print("--- 行頭形: 最初の字形を取り除くと、行中でふつうに使われる語になるか ---")
    print(f"（「行中の語」= 行中で {min_count} 回以上使われる語。出現数で数える）")
    print(f"{ljust('字形', 6)}  {rjust('行頭の語', 18)}  {rjust('行中の語（対照）', 18)}  "
          f"{rjust('倍率', 5)}  {rjust('G²', 7)}")
    for g in glyphs:
        a, c = stem_rate(first, g, middle, min_count)
        b, d = stem_rate(middle, g, middle, min_count)
        if not c or not d:
            print(f"{g + '-':<6}  {fmt_rate(a, c)}  {fmt_rate(b, d)}")
            continue
        ratio = (a / c) / (b / d) if b else float("inf")
        g2 = corpus.log_likelihood(a, b, c, d) if a + b else 0.0
        print(f"{g + '-':<6}  {fmt_rate(a, c)}  {fmt_rate(b, d)}  {ratio:>5.2f}  {g2:>7.1f}")
    print("倍率 > 1 で G² が大きいほど、行頭の語の方が「字形 + ふつうの語」になっている。\n")

    general = word_initials(middle)
    top = [g for g, _ in general.most_common(8)]
    print("--- 取り除いた残りは、どんな字形で始まるか（残りの語頭字形の分布）---")
    print("行頭形の仮説が正しければ、行頭の語の残りは「行中の語全体」と同じように始まるはず。")
    print("近さ = 行中の語全体の語頭字形の分布とのコサイン類似度（1 に近いほど同じ）")
    print(f"{ljust('', 16)}" + "".join(rjust(g, 6) for g in top) + rjust("近さ", 7))
    total = sum(general.values())
    print(ljust("行中の語全体", 16) + "".join(f"{general[g] / total:>6.0%}" for g in top))
    for g in glyphs:
        for label, src in (("行頭", first), ("行中", middle)):
            dist = stem_initials(src, g)
            n = sum(dist.values())
            if not n:
                continue
            cells = "".join(f"{dist[x] / n:>6.0%}" for x in top)
            print(ljust(f"{g}- {label}の残り", 16) + cells + f"{cosine(dist, general):>7.2f}")
    print()

    print("--- 行頭だけに現れる語: 語そのものは行中でほぼ使われないが、残りは行中の語 ---")
    for g in glyphs:
        a, c = only_at_start(first, g, middle, min_count)
        if c:
            print(f"  {g}- で始まる行頭の語のうち {a}/{c} ({a / c:.1%})")
    print()

    for g in glyphs:
        rows = []
        for w, c in first.items():
            parts = strip_first(w)
            if parts and parts[0] == g:
                rows.append((c, w, parts[1]))
        rows.sort(reverse=True)
        if not rows or not examples:
            continue
        print(f"  {g}- で始まる行頭の語（多い順）: 語 [行頭/行中] → 残り [行中]")
        for c, w, stem in rows[:examples]:
            print(f"    {w:<12} [{c:>3}/{middle[w]:>3}] → {stem:<10} [{middle[stem]:>4}]")
        print()


def print_final(last: Counter, middle: Counter, glyphs: list[str], repls: list[str],
                min_count: int, examples: int) -> None:
    print("--- 行末形: 最後の字形を別の語尾に置き換えると、行中でふつうに使われる語になるか ---")
    for g in glyphs:
        print(f"[-{g} で終わる語]")
        print(f"{ljust('置き換え', 10)}  {rjust('行末の語', 18)}  {rjust('行中の語（対照）', 18)}  "
              f"{rjust('倍率', 5)}  {rjust('G²', 7)}")
        best = None
        for r in repls:
            a, c = replace_rate(last, g, r, middle, min_count)
            b, d = replace_rate(middle, g, r, middle, min_count)
            label = f"-{g} → " + (f"-{r}" if r else "（削除）")
            if not c or not d:
                print(f"{ljust(label, 10)}  {fmt_rate(a, c)}  {fmt_rate(b, d)}")
                continue
            ratio = (a / c) / (b / d) if b else float("inf")
            g2 = corpus.log_likelihood(a, b, c, d) if a + b else 0.0
            print(f"{ljust(label, 10)}  {fmt_rate(a, c)}  {fmt_rate(b, d)}  {ratio:>5.2f}  {g2:>7.1f}")
            if best is None or a > best[0]:
                best = (a, r)
        print()
        rows = []
        for w, c in last.items():
            parts = strip_last(w)
            if parts and parts[1] == g:
                rows.append((c, w, parts[0]))
        rows.sort(reverse=True)
        if rows and examples:
            shown = [r for r in repls if r][:5]
            print(f"  -{g} で終わる行末の語（多い順）: 語 [行末/行中] と、置き換えた語の行中の出現数")
            print("    " + ljust("", 18) + "".join(rjust(f"-{r}", 8) for r in shown))
            for c, w, base in rows[:examples]:
                cells = "".join(rjust(str(middle[base + r]), 8) for r in shown)
                print(f"    {w:<10} [{c:>3}/{middle[w]:>3}]" + cells)
            print()


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None):
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）の行頭形・行末形の検証")
    p.add_argument("--initial", default="y,s,d,o,q,ch,sh",
                   help="行頭形を調べる字形（既定: y,s,d,o,q,ch,sh）")
    p.add_argument("--final", default="m,g",
                   help="行末形を調べる字形（既定: m,g）")
    p.add_argument("--replace", default=",".join(DEFAULT_REPLACEMENTS),
                   help="行末の字形を置き換える語尾の候補（空 = 削除。既定: "
                        + ",".join(r or "（空）" for r in DEFAULT_REPLACEMENTS) + "）")
    p.add_argument("--vocab-min", type=int, default=2,
                   help="「行中の語」とみなす行中での最小出現数（既定: 2）")
    p.add_argument("--examples", type=int, default=10, help="例として表示する語の数（既定: 10）")
    args = p.parse_args(argv)
    if args.locus is None:
        args.locus = "P"
    return args


def report(title: str, lines: list[ivtff.Line], args, opts) -> None:
    tls = line_position.text_lines(lines, opts)
    pos = line_position.collect(tls)
    if not any(tl.paragraph_start for tl in tls):
        first, last = pos.first, pos.last
        note = "段落記号が無いため全行を使用"
    else:
        first, last = pos.line_first_other, pos.line_last_other
        note = "行頭は段落の最初の行を、行末は段落の最後の行を除く"
    print(f"=== {title}（{note}）===")
    print(f"行頭の語 {sum(first.values())}, 行末の語 {sum(last.values())}, "
          f"行中の語 {sum(pos.middle.values())}\n")
    initial = [g for g in args.initial.split(",") if g]
    final = [g for g in args.final.split(",") if g]
    repls = args.replace.split(",")
    print_initial(first, pos.middle, initial, args.vocab_min, args.examples)
    print_final(last, pos.middle, final, repls, args.vocab_min, args.examples)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    print(f"転写ファイル: {path.name}\n")
    report(corpus.filter_title(args), lines, args, opts)
    if args.by:
        groups: dict[str, list[ivtff.Line]] = {}
        for ln in lines:
            groups.setdefault(ln.page.get(args.by), []).append(ln)
        for key in sorted(groups):
            report(corpus.group_label(args.by, key), groups[key], args, opts)


if __name__ == "__main__":
    main()

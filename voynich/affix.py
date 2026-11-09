#!/usr/bin/env python3
"""ヴォイニッチ手稿 語頭・語尾分析スクリプト。

単語を EVA の字形単位（ch, sh, cth などは 1 字形）に分けて、次を出力する。

  1. 字形の位置分布: 各字形が語頭・語中・語末のどこに現れるか
  2. 語頭・語尾の頻度: 長さ 1〜N 字形の語頭（接頭部）・語尾（接尾部）の頻度と、
     それを持つ異なり語数（どれだけ多くの語に付くか＝生産性の目安）
  3. 語頭×語尾のクロス表: 語頭と語尾の組み合わせの偏り（観測値/期待値）
  4. （--by 指定時）グループごとの特徴的な語頭・語尾（対数尤度比 G²）

使い方の例:
    python3 voynich/affix.py                       # 全体
    python3 voynich/affix.py --by L                # 言語 A / B の比較
    python3 voynich/affix.py --cross 2,2 --max-len 4
    python3 voynich/affix.py --types               # 異なり語単位で数える

標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from corpus import ljust, rjust  # noqa: E402


# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------


def glyph_positions(words: Counter) -> dict[str, Counter]:
    """字形ごとに 語頭/語中/語末/単独 の出現数を数える。"""
    result: dict[str, Counter] = {}
    for word, n in words.items():
        gs = ivtff.glyphs(word)
        if len(gs) == 1:
            result.setdefault(gs[0], Counter())["単独"] += n
            continue
        for i, g in enumerate(gs):
            pos = "語頭" if i == 0 else "語末" if i == len(gs) - 1 else "語中"
            result.setdefault(g, Counter())[pos] += n
    return result


def affixes(words: Counter, length: int, suffix: bool) -> tuple[Counter, Counter, Counter]:
    """長さ length 字形の語頭（suffix=True なら語尾）を数える。

    戻り値: (出現数, 異なり語数, その語頭・語尾だけで 1 語になっている出現数)
    """
    tokens, types, whole = Counter(), Counter(), Counter()
    for word, n in words.items():
        gs = ivtff.glyphs(word)
        if len(gs) < length:
            continue
        part = "".join(gs[-length:] if suffix else gs[:length])
        tokens[part] += n
        types[part] += 1
        if len(gs) == length:
            whole[part] += n
    return tokens, types, whole


def all_affixes(words: Counter, max_len: int) -> tuple[Counter, Counter]:
    """長さ 1〜max_len の語頭・語尾をまとめて数える（グループ比較用）。"""
    pre, suf = Counter(), Counter()
    for length in range(1, max_len + 1):
        p, _, _ = affixes(words, length, suffix=False)
        s, _, _ = affixes(words, length, suffix=True)
        pre.update({f"{k}-": v for k, v in p.items()})
        suf.update({f"-{k}": v for k, v in s.items()})
    return pre, suf


def cross_table(words: Counter, pre_len: int, suf_len: int) -> Counter:
    """語頭（pre_len 字形）×語尾（suf_len 字形）の組み合わせを数える。

    語頭と語尾が重ならないよう、pre_len + suf_len 字形以上の語だけを対象にする。
    """
    table = Counter()
    for word, n in words.items():
        gs = ivtff.glyphs(word)
        if len(gs) < pre_len + suf_len:
            continue
        table["".join(gs[:pre_len]), "".join(gs[-suf_len:])] += n
    return table


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def print_positions(words: Counter, min_count: int) -> None:
    pos = glyph_positions(words)
    cols = ["語頭", "語中", "語末", "単独"]
    print("--- 字形の位置分布（各字形の出現のうち、どの位置にあるか）---")
    print(f"{ljust('字形', 6)}  {rjust('出現数', 7)}  " + "  ".join(rjust(c, 6) for c in cols))
    for g, c in sorted(pos.items(), key=lambda kv: -sum(kv[1].values())):
        total = sum(c.values())
        if total < min_count:
            continue
        cells = []
        for col in cols:
            share = c[col] / total
            mark = "*" if share >= 0.9 else " "
            cells.append(f"{share:>5.1%}{mark}")
        print(f"{g:<6}  {total:>7}  " + "  ".join(cells))
    print("（* は 90% 以上がその位置に集中している字形）\n")


def print_affixes(words: Counter, length: int, suffix: bool, top: int) -> None:
    tokens, types, whole = affixes(words, length, suffix)
    total = sum(tokens.values())
    if not total:
        return
    kind = "語尾" if suffix else "語頭"
    print(f"--- {kind}（{length} 字形）: 対象 {total} 語 ---")
    rows = tokens.most_common(top)
    width = max([len(a) for a, _ in rows] + [6]) + 1
    print(f"{ljust(kind, width)}  {rjust('出現数', 7)}  {rjust('割合', 7)}  "
          f"{rjust('異なり語', 8)}  {rjust('うち単独語', 10)}")
    for part, n in rows:
        label = f"-{part}" if suffix else f"{part}-"
        print(f"{label:<{width}}  {n:>7}  {n / total:>7.2%}  {types[part]:>8}  {whole[part]:>10}")
    print()


def print_cross(words: Counter, pre_len: int, suf_len: int, top: int) -> None:
    table = cross_table(words, pre_len, suf_len)
    total = sum(table.values())
    if not total:
        return
    pre_tot, suf_tot = Counter(), Counter()
    for (p, s), n in table.items():
        pre_tot[p] += n
        suf_tot[s] += n
    pres = [p for p, _ in pre_tot.most_common(top)]
    sufs = [s for s, _ in suf_tot.most_common(top)]
    cell = 12
    print(f"--- 語頭（{pre_len} 字形）× 語尾（{suf_len} 字形）: 対象 {total} 語 ---")
    print("各セル: 出現数 (観測値/期待値)。期待値は語頭と語尾が独立だと仮定したときの値。")
    print("1 より大きいと「よく組み合わさる」、小さいと「避け合う」。")
    print(" " * 8 + "".join(rjust(f"-{s}", cell) for s in sufs))
    for p in pres:
        cells = []
        for s in sufs:
            n = table[p, s]
            expected = pre_tot[p] * suf_tot[s] / total
            ratio = n / expected if expected else 0
            cells.append(rjust(f"{n} ({ratio:.1f})", cell))
        print(f"{p + '-':<8}" + "".join(cells))
    print()


def print_group_affixes(label: str, group: Counter, rest: Counter,
                        max_len: int, top: int, min_count: int) -> None:
    c, d = sum(group.values()), sum(rest.values())
    if not c or not d:
        return
    g_pre, g_suf = all_affixes(group, max_len)
    r_pre, r_suf = all_affixes(rest, max_len)
    for kind, g, r in (("語頭", g_pre, r_pre), ("語尾", g_suf, r_suf)):
        scored = corpus.distinctive(g, r, c, d, min_count)[:top]
        print(f"--- {label} の特徴的な{kind}（他群と比べて多い, 対数尤度比 G²）---")
        width = max([len(item) for _, item, _, _ in scored] + [6])
        print(f"{ljust(kind, width)}  {rjust('G²', 8)}  {rjust('この群', 14)}  {rjust('他群', 14)}")
        for g2, item, a, b in scored:
            print(f"{item:<{width}}  {g2:>8.1f}  {a:>5} ({a / c:>6.2%})  {b:>5} ({b / d:>6.2%})")
        print()


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None):
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）の語頭・語尾分析")
    p.add_argument("--top", type=int, default=15, help="各表に表示する件数（既定: 15）")
    p.add_argument("--max-len", type=int, default=3,
                   help="語頭・語尾の最大長（字形数, 既定: 3）")
    p.add_argument("--cross", default="1,2",
                   help="クロス表の 語頭長,語尾長（字形数, 既定: 1,2）")
    p.add_argument("--cross-top", type=int, default=8,
                   help="クロス表に出す語頭・語尾の数（既定: 8）")
    p.add_argument("--min-glyph", type=int, default=50,
                   help="位置分布の表に出す字形の最小出現数（既定: 50）")
    p.add_argument("--types", action="store_true",
                   help="出現数ではなく異なり語（同じ語は 1 回）で数える")
    args = p.parse_args(argv)
    try:
        args.cross_lens = tuple(int(x) for x in args.cross.split(","))
        assert len(args.cross_lens) == 2 and min(args.cross_lens) >= 1
    except (ValueError, AssertionError):
        p.error("--cross は 1,2 のように 2 つの正の整数で指定してください")
    return args


def report(title: str, words: Counter, args) -> None:
    print(f"=== {title}: {sum(words.values())} 語（異なり {len(words)} 語）===\n")
    print_positions(words, args.min_glyph)
    for suffix in (False, True):
        for length in range(1, args.max_len + 1):
            print_affixes(words, length, suffix, args.top)
    print_cross(words, *args.cross_lens, args.cross_top)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    total = Counter()
    groups: dict[str, Counter] = {}
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        total.update(ws)
        if args.by:
            groups.setdefault(ln.page.get(args.by), Counter()).update(ws)

    if args.types:
        total = Counter(dict.fromkeys(total, 1))
        groups = {k: Counter(dict.fromkeys(v, 1)) for k, v in groups.items()}

    unit = "異なり語単位" if args.types else "出現数単位"
    print(f"転写ファイル: {path.name}（{unit}で集計）\n")
    report(corpus.filter_title(args), total, args)

    if args.by:
        for key in sorted(groups):
            label = corpus.group_label(args.by, key)
            print_group_affixes(label, groups[key], total - groups[key],
                                args.max_len, args.top, args.min_count)


if __name__ == "__main__":
    main()

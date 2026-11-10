#!/usr/bin/env python3
"""ヴォイニッチ手稿 単語頻度分析スクリプト。

ZL 転写ファイル（René Zandbergen, IVTFF 形式, EVA 表記）を読み込み、
単語の頻度表・基本統計・Zipf 指数を出力する。
ページ属性（Currier 言語・筆写者・挿絵種別・クワイア）やロカス種別で
絞り込み・グループ比較もできる。

使い方の例:
    python3 voynich/word_freq.py                     # 全体の上位 30 語
    python3 voynich/word_freq.py --top 50 --csv out/freq.csv
    python3 voynich/word_freq.py --language A        # Currier 言語 A のみ
    python3 voynich/word_freq.py --illustration H --locus P   # 植物セクションの本文
    python3 voynich/word_freq.py --by L              # 言語 A と B を比較
    python3 voynich/word_freq.py --by I --top 10     # 挿絵種別ごとに比較

標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import csv
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from corpus import distinctive, ljust, rjust  # noqa: E402


# ---------------------------------------------------------------------------
# 統計
# ---------------------------------------------------------------------------


def zipf_exponent(counter: Counter, max_rank: int = 1000) -> float | None:
    """順位-頻度の両対数回帰の傾きから Zipf 指数を推定する（自然言語では概ね 1）。"""
    freqs = [c for _, c in counter.most_common(max_rank)]
    if len(freqs) < 10:
        return None
    xs = [math.log(r) for r in range(1, len(freqs) + 1)]
    ys = [math.log(f) for f in freqs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return -sxy / sxx


def summary(counter: Counter) -> dict:
    tokens = sum(counter.values())
    types = len(counter)
    hapax = sum(1 for c in counter.values() if c == 1)
    mean_len = sum(len(w) * c for w, c in counter.items()) / tokens if tokens else 0
    return {
        "tokens": tokens,
        "types": types,
        "hapax": hapax,
        "ttr": types / tokens if tokens else 0,
        "mean_len": mean_len,
        "zipf": zipf_exponent(counter),
    }


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------


def print_summary(title: str, counter: Counter, n_lines: int, n_pages: int) -> None:
    s = summary(counter)
    zipf = f"{s['zipf']:.3f}" if s["zipf"] is not None else "-"
    print(f"=== {title} ===")
    print(f"ページ数         : {n_pages}")
    print(f"行数             : {n_lines}")
    print(f"総語数 (token)   : {s['tokens']}")
    print(f"異なり語数 (type): {s['types']}")
    print(f"1回だけの語      : {s['hapax']} ({s['hapax'] / max(s['types'], 1):.1%} of types)")
    print(f"タイプ/トークン比: {s['ttr']:.4f}")
    print(f"平均語長 (EVA字) : {s['mean_len']:.2f}")
    print(f"Zipf 指数        : {zipf}")
    print()


def print_table(counter: Counter, top: int) -> None:
    total = sum(counter.values())
    width = max([len(w) for w, _ in counter.most_common(top)] + [4])
    print(f"{rjust('順位', 4)}  {ljust('単語', width)}  {rjust('回数', 6)}  "
          f"{rjust('割合', 7)}  {rjust('累積', 7)}")
    cum = 0
    for rank, (word, count) in enumerate(counter.most_common(top), 1):
        cum += count
        print(f"{rank:>4}  {word:<{width}}  {count:>6}  {count / total:>7.2%}  {cum / total:>7.2%}")
    print()


def print_distinctive(name: str, counter: Counter, rest: Counter, top: int, min_count: int) -> None:
    c, d = sum(counter.values()), sum(rest.values())
    if not c or not d:
        return
    scored = distinctive(counter, rest, c, d, min_count)
    width = max([len(w) for _, w, _, _ in scored[:top]] + [4])
    print(f"--- {name} の特徴語（他群と比べて多い語, 対数尤度比 G²）---")
    print(f"{ljust('単語', width)}  {rjust('G²', 8)}  {rjust('この群', 14)}  {rjust('他群', 14)}")
    for g2, word, a, b in scored[:top]:
        print(f"{word:<{width}}  {g2:>8.1f}  {a:>5} ({a / c:>6.2%})  {b:>5} ({b / d:>6.2%})")
    print()


def write_csv(path: Path, counter: Counter) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = sum(counter.values())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "word", "count", "frequency"])
        for rank, (word, count) in enumerate(counter.most_common(), 1):
            w.writerow([rank, word, count, f"{count / total:.6f}"])
    print(f"CSV を書き出しました: {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None):
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）の単語頻度分析")
    p.add_argument("--top", type=int, default=30, help="表示する上位語数（既定: 30）")
    p.add_argument("--csv", type=Path, help="全語の頻度表を CSV に書き出す")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    counters: dict[str, Counter] = {}
    line_counts: Counter = Counter()
    page_sets: dict[str, set[str]] = {}
    total = Counter()
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        total.update(ws)
        if args.by:
            key = ln.page.get(args.by)
            counters.setdefault(key, Counter()).update(ws)
            line_counts[key] += 1
            page_sets.setdefault(key, set()).add(ln.page.name)

    print(f"転写ファイル: {path.name}\n")
    print_summary(corpus.filter_title(args), total, len(lines), len({ln.page.name for ln in lines}))
    print_table(total, args.top)

    if args.by:
        for key in sorted(counters):
            label = corpus.group_label(args.by, key)
            print_summary(label, counters[key], line_counts[key], len(page_sets[key]))
            print_table(counters[key], args.top)
            print_distinctive(label, counters[key], total - counters[key],
                              min(args.top, 15), args.min_count)

    if args.csv:
        write_csv(args.csv, total)


if __name__ == "__main__":
    main()

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

import argparse
import csv
import math
import sys
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402

ZL_URL = "https://www.voynich.nu/data/ZL3b-n.txt"
DEFAULT_FILE = Path(__file__).resolve().parent / "data" / "ZL3b-n.txt"

GROUP_LABELS = {
    "L": {"A": "言語 A", "B": "言語 B"},
    "I": ivtff.ILLUSTRATION_TYPES,
}


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------


def ensure_data(path: Path) -> Path:
    """転写ファイルが無ければ voynich.nu からダウンロードする。"""
    if path.exists():
        return path
    if path != DEFAULT_FILE:
        sys.exit(f"エラー: ファイルが見つかりません: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"転写ファイルをダウンロードします: {ZL_URL}", file=sys.stderr)
    req = urllib.request.Request(ZL_URL, headers={"User-Agent": "voynich-word-freq/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:  # noqa: BLE001
        sys.exit(
            f"エラー: ダウンロードに失敗しました ({e})。\n"
            f"手動で {ZL_URL} を取得し {path} に置くか、--file で指定してください。"
        )
    path.write_bytes(data)
    return path


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


def log_likelihood(a: int, b: int, c: int, d: int) -> float:
    """対数尤度比 G²。a: 対象群での出現数, b: 残りでの出現数, c/d: 各群の総語数。

    対象群で相対的に多ければ正、少なければ負の値を返す。
    """
    e1 = c * (a + b) / (c + d)
    e2 = d * (a + b) / (c + d)
    g2 = 0.0
    if a:
        g2 += a * math.log(a / e1)
    if b:
        g2 += b * math.log(b / e2)
    g2 *= 2
    return g2 if a / c >= b / d else -g2


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


def _width(text: str) -> int:
    """端末での表示幅（全角文字を 2 として数える）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def ljust(text: str, width: int) -> str:
    return text + " " * max(width - _width(text), 0)


def rjust(text: str, width: int) -> str:
    return " " * max(width - _width(text), 0) + text


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
    scored = []
    for word in set(counter) | set(rest):
        a, b = counter[word], rest[word]
        if a + b < min_count:
            continue
        scored.append((log_likelihood(a, b, c, d), word, a, b))
    scored.sort(reverse=True)
    width = max([len(w) for _, w, _, _ in scored[:top]] + [4])
    print(f"--- {name} の特徴語（他群と比べて多い語, 対数尤度比 G²）---")
    print(f"{ljust('単語', width)}  {rjust('G²', 8)}  {rjust('この群', 14)}  {rjust('他群', 14)}")
    for g2, word, a, b in scored[:top]:
        if g2 <= 0:
            break
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="ヴォイニッチ手稿（ZL 転写, EVA）の単語頻度分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "挿絵種別 (--illustration / --by I):\n"
            + "\n".join(f"  {k}: {v}" for k, v in ivtff.ILLUSTRATION_TYPES.items())
            + "\nロカス種別 (--locus):\n"
            + "\n".join(f"  {k}: {v}" for k, v in ivtff.LOCUS_CLASSES.items())
        ),
    )
    p.add_argument("--file", type=Path, default=DEFAULT_FILE,
                   help="IVTFF 転写ファイル（省略時は ZL3b を自動ダウンロード）")
    p.add_argument("--top", type=int, default=30, help="表示する上位語数（既定: 30）")
    p.add_argument("--csv", type=Path, help="全語の頻度表を CSV に書き出す")

    f = p.add_argument_group("絞り込み（カンマ区切りで複数指定可）")
    f.add_argument("--language", help="Currier 言語（A, B）")
    f.add_argument("--hand", help="筆写者（1〜5）")
    f.add_argument("--illustration", help="挿絵種別（H, A, C, Z, B, P, S, T）")
    f.add_argument("--quire", help="クワイア（A〜T）")
    f.add_argument("--page", help="ページ（例: f1r,f1v）")
    f.add_argument("--locus", help="ロカス種別（P=段落, L=ラベル, C=円形, R=放射状）")

    g = p.add_argument_group("比較")
    g.add_argument("--by", choices=list(ivtff.PAGE_VARIABLES),
                   help="ページ属性でグループ分けして比較（例: L=言語, H=筆写者, I=挿絵）")
    g.add_argument("--min-count", type=int, default=5,
                   help="特徴語の計算に使う最小出現数（既定: 5）")

    t = p.add_argument_group("単語化の設定")
    t.add_argument("--keep-uncertain", action="store_true",
                   help="判読不能文字 ? を含む単語も数える")
    t.add_argument("--drop-rare", action="store_true",
                   help="稀少文字 @nnn; を含む単語を除外する")
    t.add_argument("--comma-join", action="store_true",
                   help="カンマ（不確かなスペース）を区切りとみなさず連結する")
    t.add_argument("--alt", type=int, default=0,
                   help="異読 [a:o] のうち何番目を採用するか（0 始まり, 既定: 0）")
    return p.parse_args(argv)


def _split(value: str | None) -> set[str] | None:
    return {v.strip() for v in value.split(",") if v.strip()} if value else None


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path = ensure_data(args.file)
    lines = ivtff.parse_file(path)

    opts = ivtff.Options(
        alternative=args.alt,
        comma_is_space=not args.comma_join,
        drop_uncertain=not args.keep_uncertain,
        drop_rare=args.drop_rare,
    )

    page_filters = {
        "L": _split(args.language),
        "H": _split(args.hand),
        "I": _split(args.illustration),
        "Q": _split(args.quire),
    }
    pages_wanted = _split(args.page)
    locus_wanted = _split(args.locus)

    def selected(line: ivtff.Line) -> bool:
        for key, allowed in page_filters.items():
            if allowed and line.page.get(key) not in allowed:
                return False
        if pages_wanted and line.page.name not in pages_wanted:
            return False
        if locus_wanted and line.locus_class not in locus_wanted:
            return False
        return True

    lines = [ln for ln in lines if selected(ln)]
    if not lines:
        sys.exit("条件に合う行がありません。")

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

    filters = [f"{k}={v}" for k, v in vars(args).items()
               if k in ("language", "hand", "illustration", "quire", "page", "locus") and v]
    title = "全体" + (f"（{', '.join(filters)}）" if filters else "")
    print(f"転写ファイル: {path.name}\n")
    print_summary(title, total, len(lines), len({ln.page.name for ln in lines}))
    print_table(total, args.top)

    if args.by:
        labels = GROUP_LABELS.get(args.by, {})
        var_name = ivtff.PAGE_VARIABLES[args.by]
        for key in sorted(counters):
            if key == "?":
                label = f"{var_name} = 未指定"
            else:
                label = labels.get(key, f"{var_name} = {key}")
            print_summary(label, counters[key], line_counts[key], len(page_sets[key]))
            print_table(counters[key], args.top)
            print_distinctive(label, counters[key], total - counters[key],
                              min(args.top, 15), args.min_count)

    if args.csv:
        write_csv(args.csv, total)


if __name__ == "__main__":
    main()

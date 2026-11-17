#!/usr/bin/env python3
"""ヴォイニッチ手稿 ラベルの分析スクリプト。

ラベルは、絵の個々の部分（薬草のかけら・薬壺・ニンフ・星など）のすぐ横に書かれた 1〜数語。
「誰かが説明し、誰かが描いた」のなら、ラベルは絵の部分の名前で、本文はその部分に触れているはず。

  1. ラベルの性質: 種類ごとの数・異なり語数・繰り返し・長さ・語頭の字形を、本文（段落）の語と比べる
  2. 本文での言及: ラベルの語が、同じ頁の本文に出てくるか。
     ラベルを同じセクションの別の頁に入れ替えた場合と比べる（並べ替え検定）。
     完全一致のほか、語頭の o / y / q(o) を除いた「語幹」での一致も見る
  3. 繰り返し現れるラベル: 2 頁以上に出るラベルの一覧（同じ物に同じ名前が付いているかを画像で確かめる候補）
  4. 黄道十二宮の位置: 複数の星座の頁に出る同じニンフのラベルが、円の中の同じ位置（何番目か）にあるか。
     ラベルが「日付」や「順番」のような名前なら、同じ位置に来るはず

ラベルの種類（ZL のロカス種別）:
  Lf 薬学の薬草のかけら / Lc 薬学の薬壺 / Lz 黄道十二宮のニンフ / Ls 天文の星・月 /
  Ln 生物・浴場のニンフ / Lt 生物・浴場の管・池など / L0 その他 / La, Lp, Lx 少数

    python3 voynich/labels.py
    python3 voynich/labels.py --types Lf,Lc        # 薬学のラベルだけ
    python3 voynich/labels.py --min-glyphs 3

標準ライブラリのみで動作する。
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

LABEL_TYPES = {
    "Lf": "薬学: 薬草のかけら",
    "Lc": "薬学: 薬壺",
    "Lz": "黄道十二宮: ニンフ",
    "Ls": "天文: 星・月",
    "Ln": "生物・浴場: ニンフ",
    "Lt": "生物・浴場: 管・池など",
    "L0": "その他",
    "La": "天文・宇宙論",
    "Lp": "植物",
    "Lx": "その他（特殊）",
}

STEM_PREFIXES = ("qo", "o", "y", "q")


def stem(word: str) -> str:
    """語頭の qo / o / y / q を 1 つ除いた語幹（ラベルは o- で始まることが多いため）。"""
    for p in STEM_PREFIXES:
        if word.startswith(p) and len(word) > len(p) + 1:
            return word[len(p):]
    return word


# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------


def collect(lines: list[ivtff.Line], opts: ivtff.Options, types: set[str] | None, min_glyphs: int):
    """頁ごとのラベル語と本文語を集める。"""
    labels: dict[str, list[tuple[str, str]]] = defaultdict(list)  # 頁 -> [(語, 種類)]
    para: dict[str, Counter] = defaultdict(Counter)
    section: dict[str, str] = {}
    for ln in lines:
        section[ln.page.name] = ln.page.get("I")
        ws = ivtff.words(ln.raw, opts)
        if ln.locus_class == "L":
            if types and ln.locus_type not in types:
                continue
            for w in ws:
                if len(ivtff.glyphs(w)) >= min_glyphs:
                    labels[ln.page.name].append((w, ln.locus_type))
        elif ln.locus_class == "P":
            para[ln.page.name].update(ws)
    return labels, para, section


def mention_rate(label_pages: list[str], assign: dict[str, str], labels, para, use_stem: bool) -> tuple[int, int]:
    """ラベルの語が、割り当てた頁の本文に出る数。assign[ラベルの頁] = 本文を見る頁。"""
    hit = total = 0
    for page in label_pages:
        text = para[assign[page]]
        stems = {stem(w) for w in text} if use_stem else None
        for w, _ in labels[page]:
            total += 1
            if (stem(w) in stems) if use_stem else (w in text):
                hit += 1
    return hit, total


def mention_test(labels, para, section, trials: int, rng: random.Random, use_stem: bool):
    """同じ頁の本文での言及率と、ラベルを同じセクションの別の頁に入れ替えたときの言及率。"""
    pages = [p for p in labels if labels[p] and sum(para[p].values()) > 0]
    if not pages:
        return None
    observed = mention_rate(pages, {p: p for p in pages}, labels, para, use_stem)
    by_sec: dict[str, list[str]] = defaultdict(list)
    for p in pages:
        by_sec[section[p]].append(p)
    rates, ge = [], 0
    for _ in range(trials):
        assign = {}
        for sec_pages in by_sec.values():
            shuffled = sec_pages[:]
            rng.shuffle(shuffled)
            assign.update(zip(sec_pages, shuffled))
        h, t = mention_rate(pages, assign, labels, para, use_stem)
        rates.append(h / t)
        if h >= observed[0]:
            ge += 1
    return pages, observed, sum(rates) / len(rates), (ge + 1) / (trials + 1), by_sec


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def print_profile(labels, para) -> None:
    by_type: dict[str, Counter] = defaultdict(Counter)
    for items in labels.values():
        for w, t in items:
            by_type[t][w] += 1
    all_para = Counter()
    for c in para.values():
        all_para.update(c)
    para_tokens = sum(all_para.values())

    def first_share(counter: Counter, glyph: str) -> float:
        tot = sum(counter.values())
        return sum(c for w, c in counter.items() if ivtff.glyphs(w)[0] == glyph) / tot if tot else 0

    print("--- ラベルの性質（本文の語との比較）---")
    head = (f"{ljust('種類', 26)} {rjust('語数', 5)} {rjust('異なり', 6)} {rjust('平均長', 6)} "
            f"{rjust('o-始まり', 8)} {rjust('本文にも出る', 12)}")
    print(head)
    for t in sorted(by_type, key=lambda k: -sum(by_type[k].values())):
        c = by_type[t]
        n = sum(c.values())
        mean_len = sum(len(ivtff.glyphs(w)) * k for w, k in c.items()) / n
        in_para = sum(k for w, k in c.items() if w in all_para) / n
        print(f"{ljust(t + ' ' + LABEL_TYPES.get(t, ''), 26)} {n:>5} {len(c):>6} {mean_len:>6.2f} "
              f"{first_share(c, 'o'):>8.1%} {in_para:>12.1%}")
    mean_len = sum(len(ivtff.glyphs(w)) * k for w, k in all_para.items()) / para_tokens
    print(f"{ljust('（参考）本文の語', 26)} {para_tokens:>5} {len(all_para):>6} {mean_len:>6.2f} "
          f"{first_share(all_para, 'o'):>8.1%} {'-':>12}")
    print()


def print_mentions(labels, para, section, trials, rng) -> None:
    print("--- 本文での言及: ラベルの語は同じ頁の本文に出てくるか ---")
    print("対照 = ラベルを同じセクションの別の頁に入れ替えたときの平均。p = 入れ替えで実際以上になる割合。\n")
    for use_stem, name in ((False, "完全一致"), (True, "語幹で一致（語頭の qo/o/y/q を除く）")):
        res = mention_test(labels, para, section, trials, rng, use_stem)
        if res is None:
            print("（ラベルと本文の両方がある頁がありません）\n")
            return
        pages, (hit, total), null_rate, p, by_sec = res
        print(f"[{name}] 同じ頁 {hit}/{total} ({hit / total:.1%})  対照 {null_rate:.1%}  p = {p:.4f}")
    secs = ", ".join(f"{s}: {len(v)} 頁" for s, v in sorted(by_sec.items()))
    print(f"（対象: ラベルと本文の両方がある {len(pages)} 頁 ― {secs}）\n")


def print_repeats(labels, min_pages: int, top: int) -> None:
    where: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for page, items in labels.items():
        for w, t in items:
            where[w].append((page, t))
    rows = [(len({p for p, _ in v}), w, v) for w, v in where.items()]
    rows = [r for r in rows if r[0] >= min_pages]
    rows.sort(key=lambda r: (-r[0], -len(r[2]), r[1]))
    print(f"--- {min_pages} 頁以上に出るラベル（同じ物に同じ名前が付いているかを確かめる候補）---")
    for n_pages, w, v in rows[:top]:
        places = ", ".join(f"{p}({t})" for p, t in sorted(set(v)))
        print(f"  {w:<10} {n_pages} 頁: {places}")
    print(f"（該当 {len(rows)} 語）\n")


def circular_position_stat(pages: dict[str, list[str]]) -> tuple[float, int]:
    """同じラベルが別の頁に出る組について、円の中の相対位置（0〜1）の差（円周上の距離）の平均。"""
    occ: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for page, words in pages.items():
        n = len(words)
        for i, w in enumerate(words):
            occ[w].append((page, i / n))
    diffs = []
    for v in occ.values():
        for a in range(len(v)):
            for b in range(a + 1, len(v)):
                if v[a][0] != v[b][0]:
                    d = abs(v[a][1] - v[b][1])
                    diffs.append(min(d, 1 - d))
    return (sum(diffs) / len(diffs) if diffs else float("nan")), len(diffs)


def print_zodiac_positions(lines: list[ivtff.Line], opts, min_glyphs: int, trials: int, rng) -> None:
    pages: dict[str, list[str]] = defaultdict(list)
    for ln in lines:
        if ln.locus_type != "Lz":
            continue
        ws = [w for w in ivtff.words(ln.raw, opts) if len(ivtff.glyphs(w)) >= min_glyphs]
        if ws:
            pages[ln.page.name].append(ws[0])
    if len(pages) < 2:
        return
    obs, n_pairs = circular_position_stat(pages)
    if not n_pairs:
        return
    null = []
    for _ in range(trials):
        shuffled = {p: rng.sample(ws, len(ws)) for p, ws in pages.items()}
        null.append(circular_position_stat(shuffled)[0])
    p = (sum(1 for x in null if x <= obs) + 1) / (len(null) + 1)
    print("--- 黄道十二宮: 同じラベルは円の中の同じ位置にあるか ---")
    print(f"同じラベルが別の頁に出る組 {n_pairs} 組。相対位置の差（円周上, 0〜0.5）の平均 {obs:.3f}、"
          f"頁の中でラベルの順番を入れ替えた場合 {sum(null) / len(null):.3f}（p = {p:.4f}）")
    print("差が小さく p も小さければ、ラベルは円の中の位置（順番・日付など）に結びついた名前。\n")


def main(argv=None) -> None:
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）のラベルの分析")
    p.add_argument("--types", help="ラベルの種類（例: Lf,Lc）。省略時は全て")
    p.add_argument("--min-glyphs", type=int, default=2,
                   help="ラベルとして扱う語の最小字形数（1 字だけのラベルは記号の列が多いため, 既定: 2）")
    p.add_argument("--trials", type=int, default=5000, help="並べ替え検定の回数（既定: 5000）")
    p.add_argument("--repeat-pages", type=int, default=2, help="繰り返しラベルとみなす最小頁数（既定: 2）")
    p.add_argument("--top", type=int, default=30, help="繰り返しラベルの表示数（既定: 30）")
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args(argv)
    if args.locus is not None:
        p.error("--locus はこのスクリプトでは使えません（ラベルと本文を両方使うため）")
    args.locus = None
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    types = {t.strip() for t in args.types.split(",")} if args.types else None
    labels, para, section = collect(lines, opts, types, args.min_glyphs)
    rng = random.Random(args.seed)

    print(f"転写ファイル: {path.name}")
    print(f"=== {corpus.filter_title(args)}"
          f"{'（ラベル: ' + args.types + '）' if args.types else ''}"
          f": ラベル {sum(len(v) for v in labels.values())} 語（{args.min_glyphs} 字形以上）===\n")
    print_profile(labels, para)
    print_mentions(labels, para, section, args.trials, rng)
    print_repeats(labels, args.repeat_pages, args.top)
    if types is None or "Lz" in types:
        print_zodiac_positions(lines, opts, args.min_glyphs, min(args.trials, 5000), rng)


if __name__ == "__main__":
    main()

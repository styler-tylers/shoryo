#!/usr/bin/env python3
"""混在仮説の文章による検証（手順は notes/地上部と根の不一致の調査案.md に実行前に記録）。

「怪しい絵」（多数決で不一致の点数 2 以上、または M5 あり）の頁と「普通の絵」の頁で、
文章の性質（語の長さ・異なり語の割合・上位 50 語の分布）が違うかを、言語 A・B それぞれの中で並べ替え検定で調べる。

    python3 voynich/mix_text_test.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

NOTES = Path(__file__).resolve().parent / "notes"
FIRST_N = 60


def g2(table: list[list[int]]) -> float:
    rows = [sum(r) for r in table]
    cols = [sum(c) for c in zip(*table)]
    n = sum(rows)
    total = 0.0
    for i, r in enumerate(table):
        for j, o in enumerate(r):
            e = rows[i] * cols[j] / n
            if o > 0 and e > 0:
                total += o * math.log(o / e)
    return 2 * total


def page_words(file: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for ln in ivtff.parse_file(file):
        if ln.locus_class == "P":
            out.setdefault(ln.page.name, []).extend(ivtff.words(ln.raw, ivtff.Options()))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="混在仮説の文章による検証")
    ap.add_argument("--file", type=Path, default=corpus.DEFAULT_FILE)
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)

    cons = {r["頁"]: r for r in csv.DictReader(open(NOTES / "rater_consensus.csv", encoding="utf-8"))}
    sample = json.loads((NOTES / "anatomy_sample.json").read_text(encoding="utf-8"))
    lang = {p: "A" for p in sample["A"]} | {p: "B" for p in sample["B"]}
    words = page_words(corpus.ensure_data(args.file))

    def suspicious(r):
        return int(r["不一致の点数"]) >= 2 or r["M5"] == "1"

    print(f"転写ファイル: {args.file.name}")
    for L in ("A", "B"):
        pages = [p for p in cons if lang.get(p) == L and words.get(p)]
        grp = [suspicious(cons[p]) for p in pages]
        ws = [words[p] for p in pages]
        mlen = [sum(len(ivtff.glyphs(w)) for w in x) / len(x) for x in ws]
        ttr = [len(set(x[:FIRST_N])) / len(x[:FIRST_N]) for x in ws]
        total = Counter(w for x in ws for w in x)
        top = [w for w, _ in total.most_common(50)]
        idx = {w: i for i, w in enumerate(top)}
        vec = []
        for x in ws:
            v = [0] * 51
            for w in x:
                v[idx.get(w, 50)] += 1
            vec.append(v)

        def mean_diff(vals, g):
            a = [v for v, s in zip(vals, g) if s]
            b = [v for v, s in zip(vals, g) if not s]
            return sum(a) / len(a) - sum(b) / len(b)

        def table_g2(g):
            t = [[0] * 51, [0] * 51]
            for v, s in zip(vec, g):
                for k in range(51):
                    t[0 if s else 1][k] += v[k]
            return g2(t)

        stats = [("平均語長（字形）", lambda g: abs(mean_diff(mlen, g)), mlen),
                 (f"異なり語の割合（最初の {FIRST_N} 語）", lambda g: abs(mean_diff(ttr, g)), ttr),
                 ("上位 50 語の分布（G²）", table_g2, None)]
        n_s = sum(grp)
        print(f"\n=== 言語 {L}: 怪しい絵 {n_s} 頁、普通の絵 {len(pages) - n_s} 頁 ===")
        for name, stat, vals in stats:
            obs = stat(grp)
            g = grp[:]
            hits = 0
            for _ in range(args.trials):
                rng.shuffle(g)
                hits += stat(g) >= obs - 1e-12
            p = (hits + 1) / (args.trials + 1)
            if vals is not None:
                a = [v for v, s in zip(vals, grp) if s]
                b = [v for v, s in zip(vals, grp) if not s]
                desc = f"怪しい {sum(a) / len(a):.3f} / 普通 {sum(b) / len(b):.3f}"
            else:
                desc = f"G² = {obs:.1f}"
            print(f"  {name:<24} {desc:<32} p = {p:.4f}")
    print("\n6 検定のボンフェローニ補正の基準: p < 0.0083")


if __name__ == "__main__":
    main()

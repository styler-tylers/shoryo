#!/usr/bin/env python3
"""植物の根（クエリ）と薬学セクションの区画の、盲検の照合を集計する（H1〜H3）。

notes/器官らしい根の手本探し.md の第 8 段階（事前の記録）のとおり。
入力: <dir>/out/m1.csv … m3.csv（列 query,strip,score,note）、<dir>/key.json（記号 → {src: V|L, unit}）、
      <strips>/key.json（区画の記号 → 薬学の画像・列・段）
出力: notes/root_matching.csv

    python3 voynich/root_matching.py <dir> <strips_dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

import rater_aggregate

NOTES = Path(__file__).resolve().parent / "notes"


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """2×2 表 [[a, b], [c, d]] で、a が期待より大きい側の p（超幾何分布）。"""
    import math
    r1, c1, n = a + b, a + c, a + b + c + d
    hi = min(r1, c1)
    return sum(math.comb(c1, x) * math.comb(n - c1, r1 - x) for x in range(a, hi + 1)) / math.comb(n, r1)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="植物と薬学の根の照合の集計")
    ap.add_argument("dir", type=Path)
    ap.add_argument("strips", type=Path)
    ap.add_argument("--out", type=Path, default=NOTES / "root_matching.csv")
    args = ap.parse_args(argv)
    key = json.loads((args.dir / "key.json").read_text())
    skey = json.loads((args.strips / "key.json").read_text(encoding="utf-8"))
    raters = []
    for i in (1, 2, 3):
        with open(args.dir / "out" / f"m{i}.csv", encoding="utf-8") as f:
            raters.append({r["query"].strip(): r for r in csv.DictReader(f)})
    codes = [c for c in sorted(key) if all(c in r for r in raters)]
    if len(codes) < len(key):
        print(f"注意: 欠け {len(key) - len(codes)} 件")
    cut = set()
    xs = NOTES / "cross_section_consensus.csv"
    if xs.exists():
        with open(xs, encoding="utf-8") as f:
            cut = {r["画像"] for r in csv.DictReader(f) if r["断面"] == "1"}

    rows = []
    for c in codes:
        sc = [int(r[c]["score"]) for r in raters]
        st = [r[c]["strip"].strip() for r in raters]
        top, cnt = Counter(s for s in st if s != "none").most_common(1)[0] if any(s != "none" for s in st) else ("", 0)
        src = key[c]["src"]
        where = skey.get(top, {})
        rows.append({"クエリ": key[c]["unit"], "写本": "ヴォイニッチ" if src == "V" else "LJS 419",
                     "点": " ".join(map(str, sc)), "平均": sum(sc) / 3,
                     "区画": " ".join(st), "一致": int(cnt >= 2),
                     "一致した区画": f"{where.get('image', '')} 列{where.get('col', '')} 段{where.get('band', '')}" if cnt >= 2 else "",
                     "切り口": int(key[c]["unit"] in cut) if src == "V" else "",
                     "メモ": " | ".join(r[c]["note"].strip() for r in raters)})
    rows.sort(key=lambda r: (r["写本"], -r["平均"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"結果: {args.out}")
    print(f"点の一致度（Fleiss の κ, 0〜3）: "
          f"{rater_aggregate.fleiss_kappa([[r[c]['score'].strip() for r in raters] for c in codes]):.2f}\n")

    v = [r for r in rows if r["写本"] == "ヴォイニッチ"]
    lj = [r for r in rows if r["写本"] == "LJS 419"]
    for name, g in (("ヴォイニッチ", v), ("LJS 419", lj)):
        print(f"{name}: {len(g)} 枚、点の平均 {sum(r['平均'] for r in g) / len(g):.2f}、"
              f"点の分布 {dict(sorted(Counter(round(r['平均']) for r in g).items()))}、"
              f"2 体以上が同じ区画 {sum(r['一致'] for r in g)} 枚")

    scores = [r["平均"] for r in rows]
    labels = [r["写本"] for r in rows]

    def diff(ls):
        a = [s for s, l in zip(scores, ls) if l == "ヴォイニッチ"]
        b = [s for s, l in zip(scores, ls) if l != "ヴォイニッチ"]
        return sum(a) / len(a) - sum(b) / len(b)

    rng = random.Random(2026)
    obs = diff(labels)
    trials = 10000
    ge = 0
    for _ in range(trials):
        sh = labels[:]
        rng.shuffle(sh)
        ge += diff(sh) >= obs
    print(f"\nH1 点の平均の差（ヴォイニッチ − LJS 419）: {obs:+.2f}、p = {(ge + 1) / (trials + 1):.4f}（片側）")
    va, la = sum(r["一致"] for r in v), sum(r["一致"] for r in lj)
    print(f"H2 2 体以上が同じ区画: ヴォイニッチ {va}/{len(v)}、LJS 419 {la}/{len(lj)}、"
          f"p = {fisher_one_sided(va, len(v) - va, la, len(lj) - la):.4f}（Fisher, 片側）")
    c1 = [r["平均"] for r in v if r["切り口"] == 1]
    c0 = [r["平均"] for r in v if r["切り口"] == 0]
    if c1 and c0:
        print(f"H3（探索的）: 切り口ありの頁 {len(c1)} 枚 平均 {sum(c1) / len(c1):.2f}、"
              f"それ以外 {len(c0)} 枚 平均 {sum(c0) / len(c0):.2f}")
    print("\n点の高い対応（ヴォイニッチ, 平均 2 以上）:")
    for r in v:
        if r["平均"] >= 2:
            print(f"  {r['クエリ']:<10} 点 {r['点']}  区画 {r['区画']}  → {r['一致した区画']}  {r['メモ'][:100]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""薬学セクションの根の断片のうち、切り口・断面のある物の割合（G1）。

notes/器官らしい根の手本探し.md の第 7 段階（事前の記録）のとおり。
入力: <dir>/out/p1.csv … p3.csv（列 code,N,C,note）、<dir>/key.json（記号 → 画像・区画）
出力: notes/pharma_roots_counts.csv

    python3 voynich/pharma_roots.py <dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import rater_aggregate

NOTES = Path(__file__).resolve().parent / "notes"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="薬学セクションの根の断片の切り口の割合")
    ap.add_argument("dir", type=Path)
    ap.add_argument("--out", type=Path, default=NOTES / "pharma_roots_counts.csv")
    args = ap.parse_args(argv)
    key = json.loads((args.dir / "key.json").read_text(encoding="utf-8"))
    raters = [rater_aggregate.read(args.dir / "out" / f"p{i}.csv") for i in (1, 2, 3)]
    codes = [c for c in sorted(key) if all(c in r for r in raters)]
    if len(codes) < len(key):
        print(f"注意: 欠け {len(key) - len(codes)} 件")

    rows = []
    for c in codes:
        n = [int(r[c]["N"]) for r in raters]
        k = [min(int(r[c]["C"]), int(r[c]["N"])) for r in raters]
        v = key[c]
        rows.append({"画像": v["image"], "列": v["col"], "段": v["band"],
                     "N": " ".join(map(str, n)), "C": " ".join(map(str, k)),
                     "N平均": sum(n) / 3, "C平均": sum(k) / 3})
    rows.sort(key=lambda r: (r["画像"], r["列"], r["段"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"区画 {len(rows)} 個 → {args.out}\n")

    print("判定者ごと:")
    for i, r in enumerate(raters, 1):
        n = sum(int(r[c]["N"]) for c in codes)
        k = sum(min(int(r[c]["C"]), int(r[c]["N"])) for c in codes)
        print(f"  判定者 {i}: 根の断片 {n}、切り口あり {k}（{k / n:.0%}）")
    n = sum(r["N平均"] for r in rows)
    k = sum(r["C平均"] for r in rows)
    print(f"\nG1 3 体の平均: 根の断片 {n:.1f}、切り口あり {k:.1f}、割合 {k / n:.0%}")
    per = [r["C平均"] / r["N平均"] for r in rows if r["N平均"] >= 1]
    print(f"   区画ごとの割合の中央値 {statistics.median(per):.0%}（根の断片が 1 個以上の {len(per)} 区画）")
    print(f"   判定者間の一致（区画ごとの C の Kendall 的な目安として、C の値の Fleiss κ）: "
          f"{rater_aggregate.fleiss_kappa([[str(min(int(r[c]['C']), 3)) for r in raters] for c in codes]):.2f}")
    print("   基準: 30% 以上 → 薬種の描き方の読みを支持 / 15% 未満 → 支持しない / その間は保留\n")

    by = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        by[r["画像"]][0] += r["N平均"]
        by[r["画像"]][1] += r["C平均"]
    print("画像ごと:")
    for img, (n, k) in by.items():
        print(f"  {img:<22} 根 {n:5.1f}  切り口 {k:4.1f}（{k / n:.0%}）" if n else f"  {img:<22} 根 0")


if __name__ == "__main__":
    main()

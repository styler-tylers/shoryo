#!/usr/bin/env python3
"""「杯状の根の頭」（Y1）を、ヴォイニッチと本草書 4 冊で比べる。判定者 2 組で再現を確かめる。

notes/器官らしい根の手本探し.md の第 10 段階（事前の記録）のとおり。
入力: <dir>/out/y1.csv … y6.csv（列 code,Y1,Y2,note。y1〜y3 が組 A、y4〜y6 が組 B）、<dir>/key.json
出力: notes/cup_tops_consensus.csv

    python3 voynich/cup_tops.py <dir>
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import rater_aggregate
import sac_roots

NOTES = Path(__file__).resolve().parent / "notes"
ORDER = ["voynich", "ljs419", "oakspring_1455", "ljs46", "ljs62"]
NAMES = {"voynich": "ヴォイニッチ", "ljs419": "LJS 419（1400 年, ヴェネト）",
         "oakspring_1455": "Oak Spring（1455 年ごろ）", "ljs46": "LJS 46（1520 年）",
         "ljs62": "LJS 62（1400 年, 東地中海）"}


def cohen_kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="杯状の根の頭の比較")
    ap.add_argument("dir", type=Path)
    ap.add_argument("--out", type=Path, default=NOTES / "cup_tops_consensus.csv")
    args = ap.parse_args(argv)
    key = json.loads((args.dir / "key.json").read_text())
    raters = [rater_aggregate.read(args.dir / "out" / f"y{i}.csv") for i in range(1, 7)]
    codes = [c for c in sorted(key) if all(c in r for r in raters)]
    if len(codes) < len(key):
        print(f"注意: 欠け {len(key) - len(codes)} 件")
    groups = {"A": raters[:3], "B": raters[3:]}
    maj = {}
    for g, rs in groups.items():
        votes = [[r[c]["Y1"].strip() for r in rs] for c in codes]
        print(f"組 {g} の判定者間の一致度（Fleiss の κ）: {rater_aggregate.fleiss_kappa(votes):.2f}")
        maj[g] = [int(sum(int(x) for x in v) >= 2) for v in votes]
    print(f"2 組の多数決の一致（Cohen の κ）: {cohen_kappa(maj['A'], maj['B']):.2f}"
          f"（基準: 0.6 未満なら結論を出さない）\n")

    rows = []
    for i, c in enumerate(codes):
        rows.append({"写本": key[c]["ms"], "頁": key[c]["page"], "組A": maj["A"][i], "組B": maj["B"][i],
                     "票": "".join(r[c]["Y1"].strip() for r in raters),
                     "メモ": " | ".join(r[c]["note"].strip() for r in raters if r[c]["Y1"].strip() == "1")})
    rows.sort(key=lambda r: (ORDER.index(r["写本"]), str(r["頁"])))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"結果: {args.out}\n")

    for g in ("A", "B"):
        col = f"組{g}"
        v = [r[col] for r in rows if r["写本"] == "voynich"]
        vy, vn = sum(v), len(v)
        print(f"組 {g}: ヴォイニッチ {vy}/{vn}（{vy / vn:.0%}）")
        for ms in ORDER[1:]:
            x = [r[col] for r in rows if r["写本"] == ms]
            y, n = sum(x), len(x)
            p = sac_roots.fisher_two_sided(vy, vn - vy, y, n - y)
            mark = "  ← 補正後も有意" if p < 0.05 / 4 else ""
            print(f"   {NAMES[ms]:<28} {y}/{n}（{y / n:.0%}）  p = {p:.4f}{mark}")
        print()

    print("2 組とも「あり」の頁:")
    for r in rows:
        if r["組A"] and r["組B"]:
            print(f"  {NAMES[r['写本']]:<28} {str(r['頁']):<8} 票 {r['票']}  {r['メモ'][:90]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""切り口・断面のある根を、ヴォイニッチと他の本草書 3 冊で比べる（K1）。

notes/器官らしい根の手本探し.md の第 9 段階（事前の記録）のとおり。
入力: <dir>/out/x1.csv … x3.csv（列 code,X1,X2,note）、<dir>/key.json（記号 → {ms, page}）
出力: notes/xsec_herbals_consensus.csv

    python3 voynich/xsec_herbals.py <dir>
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import rater_aggregate
import sac_roots

NOTES = Path(__file__).resolve().parent / "notes"
NAMES = {"voynich": "ヴォイニッチ", "oakspring_1455": "Oak Spring 1455 年ごろ",
         "ljs46": "LJS 46（1520 年）", "ljs62": "LJS 62（1400 年, 東地中海）"}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="切り口の根を本草書 3 冊と比べる")
    ap.add_argument("dir", type=Path)
    ap.add_argument("--out", type=Path, default=NOTES / "xsec_herbals_consensus.csv")
    args = ap.parse_args(argv)
    key = json.loads((args.dir / "key.json").read_text())
    raters = [rater_aggregate.read(args.dir / "out" / f"x{i}.csv") for i in (1, 2, 3)]
    codes = [c for c in sorted(key) if all(c in r for r in raters)]
    if len(codes) < len(key):
        print(f"注意: 欠け {len(key) - len(codes)} 件")
    votes = [[r[c]["X1"].strip() for r in raters] for c in codes]
    print(f"判定者間の一致度（Fleiss の κ）: X1 {rater_aggregate.fleiss_kappa(votes):.2f}\n")

    rows = []
    for c, v in zip(codes, votes):
        yes = sum(int(x) for x in v) >= 2
        locs = Counter(r[c]["X2"].strip() for r in raters if r[c]["X1"].strip() == "1")
        rows.append({"写本": key[c]["ms"], "頁": key[c]["page"], "断面": int(yes), "票": "".join(v),
                     "場所": locs.most_common(1)[0][0] if yes else "",
                     "メモ": " | ".join(r[c]["note"].strip() for r in raters if r[c]["X1"].strip() == "1")})
    rows.sort(key=lambda r: (r["写本"], str(r["頁"])))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"多数決の結果: {args.out}\n")

    def count(ms):
        g = [r for r in rows if r["写本"] == ms]
        return sum(r["断面"] for r in g), len(g)

    vy, vn = count("voynich")
    print(f"{NAMES['voynich']}: {vy}/{vn}（{vy / vn:.0%}）  ※第 6 段階では 19/124（15%）")
    for ms in ("oakspring_1455", "ljs46", "ljs62"):
        y, n = count(ms)
        p = sac_roots.fisher_two_sided(vy, vn - vy, y, n - y)
        mark = "（補正後も有意）" if p < 0.05 / 3 else ""
        print(f"K1 {NAMES[ms]}: {y}/{n}（{y / n:.0%}）、ヴォイニッチとの差 p = {p:.4f}{mark}")
    print("\n断面ありの頁:")
    for r in rows:
        if r["断面"]:
            print(f"  {NAMES[r['写本']]:<26} {str(r['頁']):<8} 票 {r['票']} 場所 {r['場所']:<5} {r['メモ'][:110]}")


if __name__ == "__main__":
    main()

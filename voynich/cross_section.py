#!/usr/bin/env python3
"""断面・輪切りとして描かれた部分の有無（盲検の判定者 3 体）を集計し、F1〜F3 を検定する。

notes/器官らしい根の手本探し.md の第 6 段階（事前の記録）のとおり。

入力: <dir>/out/x1.csv … x3.csv（列 code,X1,X2,note）、<dir>/key.json（記号 → 画像の単位）
      notes/herbal_units.json（ヴォイニッチの画像の単位 → 頁・言語・クワイア）
出力: notes/cross_section_consensus.csv

    python3 voynich/cross_section.py <dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

import rater_aggregate
import sac_roots

NOTES = Path(__file__).resolve().parent / "notes"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="断面の根の集計")
    ap.add_argument("dir", type=Path)
    ap.add_argument("--out", type=Path, default=NOTES / "cross_section_consensus.csv")
    args = ap.parse_args(argv)
    key = json.loads((args.dir / "key.json").read_text())
    raters = [rater_aggregate.read(args.dir / "out" / f"x{i}.csv") for i in (1, 2, 3)]
    units = json.loads((NOTES / "herbal_units.json").read_text(encoding="utf-8"))
    codes = [c for c in sorted(key) if all(c in r for r in raters)]
    if len(codes) < len(key):
        print(f"注意: 欠け {len(key) - len(codes)} 件")

    x1 = [[r[c]["X1"].strip() for r in raters] for c in codes]
    print(f"判定者間の一致度（Fleiss の κ, {len(codes)} 枚）: X1 {rater_aggregate.fleiss_kappa(x1):.2f}")

    rows = []
    for c, v in zip(codes, x1):
        u = key[c]
        yes = sum(int(x) for x in v) >= 2
        locs = Counter(r[c]["X2"].strip() for r in raters if r[c]["X1"].strip() == "1")
        src = "ヴォイニッチ" if u in units else "LJS 419"
        info = units.get(u, {})
        rows.append({"画像": u, "写本": src, "断面": int(yes), "票": "".join(v),
                     "場所": locs.most_common(1)[0][0] if yes else "",
                     "言語": "/".join(info.get("L", [])), "クワイア": "/".join(info.get("Q", [])),
                     "メモ": " | ".join(r[c]["note"].strip() for r in raters if r[c]["X1"].strip() == "1")})
    rows.sort(key=lambda r: (r["写本"], r["画像"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"多数決の結果: {args.out}\n")

    v = [r for r in rows if r["写本"] == "ヴォイニッチ"]
    lj = [r for r in rows if r["写本"] == "LJS 419"]
    vy, ly = sum(r["断面"] for r in v), sum(r["断面"] for r in lj)
    p1 = sac_roots.fisher_two_sided(vy, len(v) - vy, ly, len(lj) - ly)
    print(f"F1 断面あり: ヴォイニッチ {vy}/{len(v)}（{vy / len(v):.0%}）、LJS 419 {ly}/{len(lj)}"
          f"（{ly / len(lj):.0%}）、p = {p1:.4f}（Fisher, 両側）")

    a = [r for r in v if r["言語"] == "A"]
    b = [r for r in v if r["言語"] == "B"]
    ay, by = sum(r["断面"] for r in a), sum(r["断面"] for r in b)
    p2 = sac_roots.fisher_two_sided(ay, len(a) - ay, by, len(b) - by)
    print(f"F2 言語: A {ay}/{len(a)}、B {by}/{len(b)}、p = {p2:.3f}（Fisher, 両側。言語が不明・混在の画像は除く）")

    hit = [r for r in v if r["断面"]]
    if hit:
        qs = [r["クワイア"] for r in v]
        obs = len({r["クワイア"] for r in hit})
        rng = random.Random(2026)
        trials = 10000
        sims = [len(set(rng.sample(qs, len(hit)))) for _ in range(trials)]
        p3 = (sum(s <= obs for s in sims) + 1) / (trials + 1)
        print(f"F3 クワイア: {obs} 個に分散 {dict(sorted(Counter(r['クワイア'] for r in hit).items()))}、"
              f"無作為なら平均 {sum(sims) / trials:.1f} 個、p = {p3:.3f}（少ない側）")
    print("\n場所: " + str(dict(Counter((r["写本"], r["場所"]) for r in rows if r["断面"]))))
    print("\n断面ありの画像:")
    for r in rows:
        if r["断面"]:
            print(f"  {r['写本']:<6} {r['画像']:<14} 票 {r['票']} 場所 {r['場所']:<5} 言語 {r['言語']:<3} "
                  f"クワイア {r['クワイア']:<3} {r['メモ'][:110]}")


if __name__ == "__main__":
    main()

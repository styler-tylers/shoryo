#!/usr/bin/env python3
"""袋・縞の根（R5）の頁が、言語・クワイア・書き手に偏るか。

notes/器官らしい根の手本探し.md の第 5 段階（事前の記録）のとおり。
盲検の多数決（rater_consensus.csv, rater_consensus_rep.csv）と ZL の頁の情報（$L 言語, $Q クワイア, $H 書き手）を使う。

    python3 voynich/sac_roots.py
"""

from __future__ import annotations

import csv
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

NOTES = Path(__file__).resolve().parent / "notes"
TYPES = {f"R{i}" for i in range(1, 9)}


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2×2 表 [[a, b], [c, d]] の Fisher の正確検定（両側）。"""
    r1, c1, n = a + b, a + c, a + b + c + d

    def p(x: int) -> float:
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)

    obs = p(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def load() -> list[dict]:
    rows = []
    for name in ("rater_consensus.csv", "rater_consensus_rep.csv"):
        with open(NOTES / name, encoding="utf-8") as f:
            rows += [r for r in csv.DictReader(f) if r["根の型"] in TYPES]
    return rows


def main() -> None:
    rows = load()
    meta = {}
    for ln in ivtff.parse_file(corpus.ensure_data(corpus.DEFAULT_FILE)):
        meta.setdefault(ln.page.name, ln.page)
    info = {r["頁"]: {k: meta[r["頁"]].get(k) for k in ("L", "Q", "H")} for r in rows}
    sac = [r for r in rows if r["根の型"] == "R5"]
    some = [r for r in rows if r["根の型"] != "R5" and "R5" in r["根の票"].split()]

    print(f"対象 {len(rows)} 頁、うち R5（多数決）{len(sac)} 頁\n")
    print("R5 の頁:")
    for r in sac:
        i = info[r["頁"]]
        print(f"  {r['頁']:<6} 票 {r['根の票']:<10} 言語 {i['L']}  クワイア {i['Q']}  書き手 {i['H']}  "
              f"不一致 {r['不一致の点数']}")
    print("\n参考: 1 体以上が R5 とした頁:")
    for r in some:
        i = info[r["頁"]]
        print(f"  {r['頁']:<6} 票 {r['根の票']:<10} 多数決 {r['根の型']}  言語 {i['L']}  クワイア {i['Q']}")
    print()

    # E1 言語
    la = sum(info[r["頁"]]["L"] == "A" for r in sac)
    lb = len(sac) - la
    ta = sum(info[r["頁"]]["L"] == "A" for r in rows)
    tb = len(rows) - ta
    p1 = fisher_two_sided(la, lb, ta - la, tb - lb)
    print(f"E1 言語: R5 は A {la}・B {lb}、それ以外は A {ta - la}・B {tb - lb}、p = {p1:.3f}（Fisher, 両側）")

    # E2 クワイア
    qs = [info[r["頁"]]["Q"] for r in rows]
    obs = len({info[r["頁"]]["Q"] for r in sac})
    rng = random.Random(2026)
    trials = 10000
    le = sum(len(set(rng.sample(qs, len(sac)))) <= obs for _ in range(trials))
    print(f"E2 クワイア: R5 の頁は {obs} 個のクワイアに分散（{dict(Counter(info[r['頁']]['Q'] for r in sac))}）、"
          f"無作為なら平均 {sum(len(set(rng.sample(qs, len(sac)))) for _ in range(2000)) / 2000:.1f} 個、"
          f"p = {(le + 1) / (trials + 1):.3f}（少ない側）")

    # E3 書き手（記述のみ）
    hs = Counter(info[r["頁"]]["H"] for r in sac)
    ht = Counter(info[r["頁"]]["H"] for r in rows)
    print("E3 書き手（$H, 未確認の情報）: " + "、".join(
        f"{h}: R5 {hs.get(h, 0)}/{ht[h]} 頁" for h in sorted(ht, key=str)))


if __name__ == "__main__":
    main()

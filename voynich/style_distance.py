#!/usr/bin/env python3
"""ヴォイニッチの植物の絵が、LJS 419 の慣習の様式（A）と写実の様式（B）のどちらに近いか。

盲検の多数決の結果（根の型 R1〜R8, 不一致 M1〜M4）だけを使う。手順は
notes/器官らしい根の手本探し.md の第 4 段階（事前の記録）のとおり。

    python3 voynich/style_distance.py
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

NOTES = Path(__file__).resolve().parent / "notes"
TYPES = [f"R{i}" for i in range(1, 9)]
ITEMS = ["M1", "M2", "M3", "M4"]
GRID = [i / 100 for i in range(101)]


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["根の型"] in TYPES]


def props(rows: list[dict], smooth: float = 0.0) -> list[float]:
    c = Counter(r["根の型"] for r in rows)
    tot = len(rows) + smooth * len(TYPES)
    return [(c[t] + smooth) / tot for t in TYPES]


def tv(p: list[float], q: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(p, q)) / 2


def mix_w_types(v: list[dict], a: list[dict], b: list[dict]) -> float:
    """ヴォイニッチの根の型 = w·A + (1 − w)·B の w を最尤法で（0.5 を足してならす）。"""
    pa, pb = props(a, 0.5), props(b, 0.5)
    c = Counter(r["根の型"] for r in v)
    best = max(GRID, key=lambda w: sum(c[t] * math.log(w * x + (1 - w) * y)
                                       for t, x, y in zip(TYPES, pa, pb)))
    return best


def rates(rows: list[dict]) -> list[float]:
    return [sum(int(r[it]) for r in rows) / len(rows) for it in ITEMS]


def mix_w_items(v: list[dict], a: list[dict], b: list[dict]) -> float:
    rv, ra, rb = rates(v), rates(a), rates(b)
    return min(GRID, key=lambda w: sum((x - (w * y + (1 - w) * z)) ** 2
                                       for x, y, z in zip(rv, ra, rb)))


def ci(xs: list[float]) -> tuple[float, float]:
    xs = sorted(xs)
    return xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]


def main() -> None:
    v = load(NOTES / "rater_consensus.csv") + load(NOTES / "rater_consensus_rep.csv")
    ljs = load(NOTES / "rater_consensus_ljs419.csv")
    sample = json.loads((NOTES / "ljs419_sample.json").read_text(encoding="utf-8"))
    a = [r for r in ljs if r["頁"] in set(sample["A"])]
    b = [r for r in ljs if r["頁"] in set(sample["B"])]
    print(f"ヴォイニッチ {len(v)} 頁 / LJS 419 慣習（A）{len(a)} 頁 / 写実（B）{len(b)} 頁\n")

    print("根の型の割合")
    print("       " + "".join(f"{t:>7}" for t in TYPES))
    for name, rows in (("ヴォイ", v), ("A 慣習", a), ("B 写実", b)):
        print(f"{name:<6}" + "".join(f"{x:>7.0%}" for x in props(rows)))
    print("\n不一致の項目の「あり」の割合")
    print("       " + "".join(f"{t:>7}" for t in ITEMS))
    for name, rows in (("ヴォイ", v), ("A 慣習", a), ("B 写実", b)):
        print(f"{name:<6}" + "".join(f"{x:>7.0%}" for x in rates(rows)))
    print()

    tva, tvb = tv(props(v), props(a)), tv(props(v), props(b))
    w2, w3 = mix_w_types(v, a, b), mix_w_items(v, a, b)

    rng = random.Random(2026)
    boots = {"diff": [], "w2": [], "w3": []}
    for _ in range(10000):
        bv = [rng.choice(v) for _ in v]
        ba = [rng.choice(a) for _ in a]
        bb = [rng.choice(b) for _ in b]
        boots["diff"].append(tv(props(bv), props(ba)) - tv(props(bv), props(bb)))
        boots["w2"].append(mix_w_types(bv, ba, bb))
        boots["w3"].append(mix_w_items(bv, ba, bb))

    lo, hi = ci(boots["diff"])
    print(f"D1 全変動距離: ヴォイニッチ–A {tva:.2f}、ヴォイニッチ–B {tvb:.2f}、"
          f"差 {tva - tvb:+.2f}（95% 区間 {lo:+.2f}〜{hi:+.2f}; 負なら A に近い）")
    lo, hi = ci(boots["w2"])
    print(f"D2 混合の割合 w（根の型, A の割合）: {w2:.2f}（95% 区間 {lo:.2f}〜{hi:.2f}）")
    lo, hi = ci(boots["w3"])
    print(f"D3 混合の割合 w（不一致 M1〜M4）: {w3:.2f}（95% 区間 {lo:.2f}〜{hi:.2f}）\n")

    pv, pa, pb = props(v), props(a, 0.5), props(b, 0.5)
    print(f"残差（w = {w2:.2f} の混合と比べたヴォイニッチの多い・少ない）")
    for t, x, y, z in zip(TYPES, pv, pa, pb):
        m = w2 * y + (1 - w2) * z
        exp = m * len(v)
        print(f"  {t}: ヴォイニッチ {x:.0%}（{round(x * len(v))} 頁）、混合の予想 {m:.0%}（{exp:.1f} 頁）、"
              f"比 {x / m:.1f}")


if __name__ == "__main__":
    main()

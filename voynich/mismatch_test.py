#!/usr/bin/env python3
"""地上部と根の不一致（合成図仮説）の検定。手順は notes/地上部と根の不一致の調査案.md で事前に決めたもの。

notes/mismatch_classification.csv の M1〜M4（0/1）から不一致の点数（0〜4）を求め、次を並べ替え検定で調べる。
  Q1: 言語 A と B で不一致の頁（点数 2 以上）の割合が違うか（両側）
  Q2: 同じ二つ折り・同じクワイアの頁どうしは点数が似ているか（組の点数の差の平均が小さいか）
  Q3: 器官のように見える根の型（R1, R3, R5, R6, R8）の頁は、植物らしい根の型（R2, R4, R7）より点数が高いか

    python3 voynich/mismatch_test.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

NOTES = Path(__file__).resolve().parent / "notes"
ORGAN_LIKE = {"R1", "R3", "R5", "R6", "R8"}
PLANT_LIKE = {"R2", "R4", "R7"}


def load():
    with open(NOTES / "mismatch_classification.csv", encoding="utf-8") as f:
        mism = {r["頁"]: sum(int(r[k]) for k in ("M1様式", "M2接合", "M3大きさ", "M4向き")) for r in csv.DictReader(f)}
    with open(NOTES / "anatomy_classification.csv", encoding="utf-8") as f:
        roots = {r["頁"]: r["根"] for r in csv.DictReader(f)}
    sample = json.loads((NOTES / "anatomy_sample.json").read_text(encoding="utf-8"))
    lang = {p: "A" for p in sample["A"]} | {p: "B" for p in sample["B"]}
    return mism, roots, lang


def perm_p(observed: float, stat, labels: list, trials: int, rng: random.Random, greater: bool = True) -> float:
    hits = 0
    shuffled = labels[:]
    for _ in range(trials):
        rng.shuffle(shuffled)
        v = stat(shuffled)
        if (v >= observed) if greater else (v <= observed):
            hits += 1
    return (hits + 1) / (trials + 1)


def main(argv=None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="地上部と根の不一致の検定")
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)
    mism, roots, lang = load()
    pages = [p for p in mism if roots.get(p, "R0") != "R0"]
    score = [mism[p] for p in pages]
    flag = [s >= 2 for s in score]

    meta = {}
    for ln in ivtff.parse_file(corpus.ensure_data(corpus.DEFAULT_FILE)):
        meta.setdefault(ln.page.name, ln.page)

    n = len(pages)
    print(f"対象 {n} 頁（根の型 R0 を除く）。不一致の頁（点数 2 以上）: {sum(flag)} 頁\n")
    print("点数の分布: " + ", ".join(f"{k}点 {score.count(k)}" for k in range(5)) + "\n")

    # Q1
    langs = [lang[p] for p in pages]

    def diff_rate(ls):
        a = [f for f, l in zip(flag, ls) if l == "A"]
        b = [f for f, l in zip(flag, ls) if l == "B"]
        return abs(sum(a) / len(a) - sum(b) / len(b))

    a = [f for f, l in zip(flag, langs) if l == "A"]
    b = [f for f, l in zip(flag, langs) if l == "B"]
    obs = diff_rate(langs)
    p1 = perm_p(obs, diff_rate, langs, args.trials, rng)
    print("--- Q1: 言語 A と B で不一致の割合は違うか ---")
    print(f"言語 A {sum(a)}/{len(a)} ({sum(a) / len(a):.0%})、言語 B {sum(b)}/{len(b)} ({sum(b) / len(b):.0%})、"
          f"差 {obs:.0%}、p = {p1:.4f}（両側）\n")

    # Q2
    print("--- Q2: 同じ紙・同じクワイアの頁どうしは点数が似ているか ---")
    for name, key in (("同じ二つ折り", lambda p: (meta[p].get("Q"), meta[p].get("B"))),
                      ("同じクワイア", lambda p: meta[p].get("Q"))):
        groups = [key(p) for p in pages]
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if groups[i] == groups[j]]
        if not pairs:
            print(f"{name}: 組なし")
            continue

        def mean_gap(sc):
            return sum(abs(sc[i] - sc[j]) for i, j in pairs) / len(pairs)

        obs = mean_gap(score)
        allpairs = sum(abs(score[i] - score[j]) for i in range(n) for j in range(i + 1, n)) / (n * (n - 1) / 2)
        p2 = perm_p(obs, mean_gap, score, args.trials, rng, greater=False)
        print(f"{name}: {len(pairs)} 組、点数の差の平均 {obs:.2f}（全ての組 {allpairs:.2f}）、p = {p2:.4f}")
    print()

    # Q3
    kinds = ["organ" if roots[p] in ORGAN_LIKE else "plant" if roots[p] in PLANT_LIKE else "other" for p in pages]

    def mean_diff(ks):
        o = [s for s, k in zip(score, ks) if k == "organ"]
        q = [s for s, k in zip(score, ks) if k == "plant"]
        return sum(o) / len(o) - sum(q) / len(q)

    o = [s for s, k in zip(score, kinds) if k == "organ"]
    q = [s for s, k in zip(score, kinds) if k == "plant"]
    obs = mean_diff(kinds)
    p3 = perm_p(obs, mean_diff, kinds, args.trials, rng)
    print("--- Q3: 器官のように見える根の頁は、不一致の点数が高いか ---")
    print(f"器官らしい根（R1, R3, R5, R6, R8）{len(o)} 頁: 平均 {sum(o) / len(o):.2f}、"
          f"植物らしい根（R2, R4, R7）{len(q)} 頁: 平均 {sum(q) / len(q):.2f}、差 {obs:.2f}、p = {p3:.4f}（片側）\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""複数の判定者（盲検）による根の型・不一致の判定を集計する。

入力（判定者の出力と、記号 → 頁の対応表）:
  <dir>/out/root1.csv … root3.csv   列: code,root,note
  <dir>/out/mis1.csv  … mis3.csv    列: code,M1,M2,M3,M4,M5,note
  <dir>/key.json                     {記号: 頁}
出力:
  - 項目ごとの判定者間の一致度（Fleiss の κ）
  - 多数決の結果 notes/rater_consensus.csv（頁, 根の型, M1〜M5, 不一致の点数, 割れ方）
  - 多数決の判定での Q1〜Q3（mismatch_test.py と同じ検定）と M5 の集計

    python3 voynich/rater_aggregate.py <dir>
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import mismatch_test  # noqa: E402

NOTES = Path(__file__).resolve().parent / "notes"
ITEMS = ["M1", "M2", "M3", "M4", "M5"]


def fleiss_kappa(ratings: list[list[str]]) -> float:
    """ratings[i] = 項目 i への各判定者のカテゴリ（判定者数は同じ）。"""
    n = len(ratings[0])
    cats = sorted({c for r in ratings for c in r})
    N = len(ratings)
    p_j = {c: sum(r.count(c) for r in ratings) / (N * n) for c in cats}
    P_i = [(sum(r.count(c) ** 2 for c in cats) - n) / (n * (n - 1)) for r in ratings]
    P_bar = sum(P_i) / N
    P_e = sum(v * v for v in p_j.values())
    return (P_bar - P_e) / (1 - P_e) if P_e < 1 else 1.0


def read(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return {r["code"].strip(): r for r in csv.DictReader(f)}


def main(argv=None) -> None:
    d = Path((argv or sys.argv[1:])[0])
    key = json.loads((d / "key.json").read_text())
    roots = [read(d / "out" / f"root{i}.csv") for i in (1, 2, 3)]
    mis = [read(d / "out" / f"mis{i}.csv") for i in (1, 2, 3)]
    codes = sorted(key)
    for name, rs in (("root", roots), ("mis", mis)):
        for i, r in enumerate(rs, 1):
            missing = set(codes) - set(r)
            if missing:
                print(f"注意: {name}{i} に {len(missing)} 件の欠け: {sorted(missing)[:5]}")
    codes = [c for c in codes if all(c in r for r in roots + mis)]

    print(f"=== 判定者間の一致度（Fleiss の κ, {len(codes)} 頁, 判定者 3 体）===")
    print("目安: 0.2 未満 わずか / 0.2〜0.4 まずまず / 0.4〜0.6 中程度 / 0.6 以上 かなり一致")
    print(f"  根の型（R0〜R8）: κ = {fleiss_kappa([[r[c]['root'].strip() for r in roots] for c in codes]):.2f}")
    for it in ITEMS:
        print(f"  {it}: κ = {fleiss_kappa([[r[c][it].strip() for r in mis] for c in codes]):.2f}"
              f"（「あり」の割合 {sum(int(r[c][it]) for r in mis for c in codes) / (3 * len(codes)):.0%}）")
    print()

    rows = []
    for c in codes:
        votes = Counter(r[c]["root"].strip() for r in roots)
        top, cnt = votes.most_common(1)[0]
        root = top if cnt >= 2 else "不定"
        m = {it: int(sum(int(r[c][it]) for r in mis) >= 2) for it in ITEMS}
        split = sum(1 for it in ITEMS if 0 < sum(int(r[c][it]) for r in mis) < 3)
        rows.append({"頁": key[c], "根の型": root, "根の票": " ".join(r[c]["root"].strip() for r in roots),
                     **m, "不一致の点数": sum(m[it] for it in ITEMS[:4]), "割れた項目数": split})
    rows.sort(key=lambda r: r["頁"])
    out = NOTES / "rater_consensus.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"多数決の結果: {out}")
    print(f"根の型の分布: {dict(sorted(Counter(r['根の型'] for r in rows).items()))}")
    print(f"不一致の点数の分布: {dict(sorted(Counter(r['不一致の点数'] for r in rows).items()))}")
    print(f"M5（異質な部分）あり: {sum(r['M5'] for r in rows)} 頁\n")

    # 事前に決めた Q1〜Q3 を、多数決の判定でやり直す
    _, _, lang = mismatch_test.load()
    use = [r for r in rows if r["根の型"] not in ("R0", "不定")]
    score = [r["不一致の点数"] for r in use]
    flag = [s >= 2 for s in score]
    rng = random.Random(1)
    trials = 10000
    meta = {}
    for ln in ivtff.parse_file(corpus.ensure_data(corpus.DEFAULT_FILE)):
        meta.setdefault(ln.page.name, ln.page)
    print(f"=== 多数決の判定での検定（根の型が R0・不定の頁を除く {len(use)} 頁）===")

    langs = [lang[r["頁"]] for r in use]

    def diff_rate(ls):
        a = [f for f, l in zip(flag, ls) if l == "A"]
        b = [f for f, l in zip(flag, ls) if l == "B"]
        return abs(sum(a) / len(a) - sum(b) / len(b))

    a = [f for f, l in zip(flag, langs) if l == "A"]
    b = [f for f, l in zip(flag, langs) if l == "B"]
    p1 = mismatch_test.perm_p(diff_rate(langs), diff_rate, langs, trials, rng)
    print(f"Q1 言語差: A {sum(a)}/{len(a)}、B {sum(b)}/{len(b)}、p = {p1:.4f}（両側）")

    n = len(use)
    for name, keyf in (("同じ二つ折り", lambda p: (meta[p].get("Q"), meta[p].get("B"))),
                       ("同じクワイア", lambda p: meta[p].get("Q"))):
        g = [keyf(r["頁"]) for r in use]
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if g[i] == g[j]]

        def gap(sc, pairs=pairs):
            return sum(abs(sc[i] - sc[j]) for i, j in pairs) / len(pairs)

        p2 = mismatch_test.perm_p(gap(score), gap, score, trials, rng, greater=False)
        print(f"Q2 {name}: {len(pairs)} 組、差の平均 {gap(score):.2f}、p = {p2:.4f}")

    kinds = ["organ" if r["根の型"] in mismatch_test.ORGAN_LIKE else "plant" for r in use]

    def mdiff(ks):
        o = [s for s, k in zip(score, ks) if k == "organ"]
        q = [s for s, k in zip(score, ks) if k == "plant"]
        return (sum(o) / len(o) - sum(q) / len(q)) if o and q else 0.0

    o = [s for s, k in zip(score, kinds) if k == "organ"]
    q = [s for s, k in zip(score, kinds) if k == "plant"]
    if o and q:
        p3 = mismatch_test.perm_p(mdiff(kinds), mdiff, kinds, trials, rng)
        print(f"Q3 器官らしい根: {len(o)} 頁 平均 {sum(o) / len(o):.2f}、植物らしい根: {len(q)} 頁 平均 "
              f"{sum(q) / len(q):.2f}、p = {p3:.4f}（片側。根の型と不一致は別の判定者）")
    print()
    split = sorted(rows, key=lambda r: (-(r["根の型"] == "不定") - 0, -r["割れた項目数"]))[:12]
    print("判定が割れた頁（研究者に確認してもらう候補）:")
    for r in split:
        print(f"  {r['頁']:<6} 根 {r['根の型']}（{r['根の票']}）  割れた M 項目 {r['割れた項目数']}")


if __name__ == "__main__":
    main()

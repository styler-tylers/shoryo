#!/usr/bin/env python3
"""聖人暦の名前の一覧と、黄道のラベルの並び方の型を比べる（第 13 回 第 2 段階）。

聖人暦: 『The Roman Martyrology』（1916 年英訳, Internet Archive romanmartyrology00cathuoft）の巻末の索引から
(名前, 月, 日) を取り出し、各日から 1 人を無作為に選んで 12 の月の一覧を作る（200 回選び直す）。

N1 2 つ以上の月に出る名前の割合 / N2 月の中で隣り合う名前の編集距離（入れ替えとの比較）

    python3 voynich/saints_calendar.py <romanmartyrology00cathuoft_djvu.txt>
"""

from __future__ import annotations

import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

MONTHS = ["Jan", "Feb", "March", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
ORDER = {"Jan": 1, "Feb": 2, "March": 3, "Mar": 3, "Apr": 4, "May": 5, "June": 6, "July": 7, "Aug": 8,
         "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def parse_index(path: Path):
    t = re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="replace"))
    idx = t[int(len(t) * 0.80):]
    pat = re.compile(r"([A-Z][a-z]+), (?:Sts?|Bl)\.,[^.]{0,60}?\b(" + "|".join(MONTHS) + r")\.? (\d{1,2})\b")
    by_day = defaultdict(set)
    for name, m, d in pat.findall(idx):
        d = int(d)
        if 1 <= d <= 31:
            by_day[(ORDER[m], d)].add(name.lower())
    return by_day


def lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1]


def n1(months: dict[int, list[str]]) -> float:
    where = defaultdict(set)
    for m, ns in months.items():
        for n in ns:
            where[n].add(m)
    return sum(len(v) >= 2 for v in where.values()) / len(where)


def adj(months) -> float:
    v = [lev(a, b) for ns in months.values() for a, b in zip(ns, ns[1:])]
    return sum(v) / len(v)


def main() -> None:
    by_day = parse_index(Path(sys.argv[1]))
    per_month = defaultdict(int)
    for (m, _d) in by_day:
        per_month[m] += 1
    print(f"索引から取り出した日: {len(by_day)}（月ごと: {dict(sorted(per_month.items()))}）")
    print(f"1 日あたりの聖人の数: 平均 {statistics.mean(len(v) for v in by_day.values()):.1f}\n")
    rng = random.Random(2026)
    n1s, obs_adj, null_adj, ps = [], [], [], []
    for _ in range(200):
        months = defaultdict(list)
        for (m, d) in sorted(by_day):
            months[m].append(rng.choice(sorted(by_day[(m, d)])))
        n1s.append(n1(months))
        o = adj(months)
        nulls = [adj({m: rng.sample(ns, len(ns)) for m, ns in months.items()}) for _ in range(200)]
        obs_adj.append(o)
        null_adj.append(statistics.mean(nulls))
        ps.append((sum(x <= o for x in nulls) + 1) / 201)
    print(f"N1 2 つ以上の月に出る名前の割合: 平均 {statistics.mean(n1s):.0%}"
          f"（200 回の範囲 {min(n1s):.0%}〜{max(n1s):.0%}）。ヴォイニッチの黄道のラベルは 9%")
    print(f"N2 隣り合う名前の編集距離 {statistics.mean(obs_adj):.2f}、入れ替えた場合 {statistics.mean(null_adj):.2f}、"
          f"p の中央値 {statistics.median(ps):.3f}（p < 0.05 の回 {sum(p < 0.05 for p in ps)}/200）")
    print("   ヴォイニッチ: 4.93 対 5.20, p = 0.0002")
    months = defaultdict(list)
    for (m, d) in sorted(by_day):
        months[m].append(sorted(by_day[(m, d)])[0])
    print("例（1 月の最初の 12 日, 各日アルファベット順の最初の名前）: " + " / ".join(months[1][:12]))


if __name__ == "__main__":
    main()

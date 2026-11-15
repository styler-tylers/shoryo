#!/usr/bin/env python3
"""黄道のラベルは日付（数）か名前か（第 13 回）。

D1 月をまたぐ繰り返し / D2 同じ順番の位置のラベルどうしの似かた / D3 頁の中で隣り合うラベルの似かた。
ZL の行の順番を円の上の並び順とみなす。

    python3 voynich/zodiac_days.py
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import self_citation as sc  # noqa: E402


def lev(a: str, b: str) -> int:
    x, y = tuple(ivtff.glyphs(a)), tuple(ivtff.glyphs(b))
    prev = list(range(len(y) + 1))
    for i, gx in enumerate(x, 1):
        cur = [i] + [0] * len(y)
        for j, gy in enumerate(y, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (gx != gy))
        prev = cur
    return prev[-1]


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = None
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    lab = defaultdict(list)
    order = []
    for ln in lines:
        if ln.page.get("I") == "Z" and ln.locus_class == "L":
            ws = ivtff.words(ln.raw, opts)
            if ws:
                if ln.page.name not in order:
                    order.append(ln.page.name)
                lab[ln.page.name].append(" ".join(ws))  # 1 つのラベル = 1 行
    pages = order
    print("頁ごとのラベルの数: " + ", ".join(f"{p} {len(lab[p])}" for p in pages))
    allv = [w for p in pages for w in lab[p]]
    print(f"ラベル 計 {len(allv)}、1 頁あたり平均 {len(allv) / len(pages):.1f}\n")

    # D1
    where = defaultdict(set)
    for p in pages:
        for w in lab[p]:
            where[w].add(p)
    dist = Counter(len(v) for v in where.values())
    print(f"D1 異なるラベル {len(where)}。出る頁の数ごとの異なり数: {dict(sorted(dist.items()))}")
    print(f"   10 頁以上に出るラベル: {sum(1 for v in where.values() if len(v) >= 10)}"
          f"（日付説なら、約 30 の語が 12 頁ほぼ全てに出るはず）\n")

    cache = {}

    def d(a, b):
        k = (a, b) if a <= b else (b, a)
        if k not in cache:
            cache[k] = lev(a, b)
        return cache[k]

    # D2
    def d2(lists):
        same, diff = [], []
        for i, p in enumerate(pages):
            for q in pages[i + 1:]:
                A, B = lists[p], lists[q]
                for ia, a in enumerate(A):
                    xa = ia / max(1, len(A) - 1)
                    for ib, b in enumerate(B):
                        xb = ib / max(1, len(B) - 1)
                        (same if abs(xa - xb) <= 0.05 else diff).append(d(a, b))
        return sum(same) / len(same) - sum(diff) / len(diff), len(same)

    obs2, n_same = d2(lab)
    ge = 0
    trials = 1000
    for _ in range(trials):
        sh = {p: rng.sample(lab[p], len(lab[p])) for p in pages}
        ge += d2(sh)[0] <= obs2
    print(f"D2 同じ位置のラベルどうし − 違う位置の組 の編集距離の差 {obs2:+.3f}（同じ位置の組 {n_same}）、"
          f"p = {(ge + 1) / (trials + 1):.4f}（片側, {trials} 回）")
    print("   負で p が小さければ、同じ位置（同じ日付）のラベルが似ている\n")

    # D3
    def d3(lists):
        v = [d(a, b) for p in pages for a, b in zip(lists[p], lists[p][1:])]
        return sum(v) / len(v)

    obs3 = d3(lab)
    ge = 0
    null = []
    for _ in range(5000):
        sh = {p: rng.sample(lab[p], len(lab[p])) for p in pages}
        x = d3(sh)
        null.append(x)
        ge += x <= obs3
    print(f"D3 隣り合うラベルの編集距離の平均 {obs3:.2f}、順番を入れ替えた場合 {sum(null) / len(null):.2f}、"
          f"p = {(ge + 1) / 5001:.4f}（片側）")
    print("   例（最初の頁の並び）: " + " / ".join(lab[pages[0]][:12]))


if __name__ == "__main__":
    main()

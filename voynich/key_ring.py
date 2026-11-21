#!/usr/bin/env python3
"""暗号の研究 実験 8: f57v の円（f57v.3）の 1 周分を鍵 K とし、f66r の列・f57v の他の輪と比べる。

    python3 voynich/key_ring.py
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import glyph_roles  # noqa: E402
import ivtff  # noqa: E402


def lcs(a, b) -> int:
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def lcs_test(K, seq, rng, n=10000):
    obs = lcs(K, seq)
    s = list(seq)
    ge = 0
    tot = 0
    for _ in range(n):
        rng.shuffle(s)
        v = lcs(K, s)
        tot += v
        ge += v >= obs
    return obs, tot / n, (ge + 1) / (n + 1)


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(2026)
    ring = {ln.id: [g for w in ivtff.words(ln.raw, opts) for g in ivtff.glyphs(w)] for ln in lines if ln.page.name == "f57v"}
    full = ring["f57v.3"]
    # 1 周の長さ: 最初の字形が次に現れるまで
    period = full.index(full[0], 1)
    K = full[:period]
    print(f"鍵 K（f57v.3 の 1 周, {len(K)} 字形）: {' '.join(K)}")
    for c in range(len(full) // period):
        cyc = full[c * period:(c + 1) * period]
        diff = [f"{i + 1} 番目 {K[i]}→{x}" for i, x in enumerate(cyc) if i < len(K) and x != K[i]]
        print(f"   {c + 1} 周目: {' '.join(cyc)}   K との違い: {', '.join(diff) or 'なし'}")
    f66 = [ws[0] for ln in lines if ln.page.name == "f66r" and ln.locus_class == "L"
           for ws in [ivtff.words(ln.raw, opts)] if len(ws) == 1 and len(list(ivtff.glyphs(ws[0]))) == 1]
    print(f"\n(a) f66r の列（{len(f66)} 字形）: {' '.join(f66)}")
    for name, seq in (("列そのまま", f66), ("組の前の字形", f66[0::2]), ("組の後の字形", f66[1::2])):
        obs, mean, p = lcs_test(K, seq, rng)
        print(f"   {name}（{len(seq)}）: LCS {obs}（無作為の平均 {mean:.2f}）, p = {p:.3g}{'  ← 有意' if p < 0.05 / 3 else ''}")
    print("\n(b) f57v の他の輪")
    P = Counter(g for ln in lines if ln.locus_class == "P" for w in ivtff.words(ln.raw, opts) for g in ivtff.glyphs(w))
    kset = set(K)
    pk, pn = sum(P[g] for g in kset), sum(P.values())
    for lid, gs in ring.items():
        if lid == "f57v.3" or not gs:
            continue
        a = sum(g in kset for g in gs)
        p = glyph_roles.fisher(a, len(gs) - a, pk, pn - pk)
        obs, mean, pl = lcs_test(K, gs, rng, 2000)
        ln = next(x for x in lines if x.id == lid)
        print(f"   {lid}（{ln.locus_type}, {len(gs)} 字形）: K の字形 {a / len(gs):.0%}（段落 {pk / pn:.0%}, p = {glyph_roles.fmt_p(p)}）; "
              f"LCS {obs}（無作為 {mean:.2f}, p = {pl:.3g}）")
        print(f"      {' '.join(gs[:60])}{' …' if len(gs) > 60 else ''}")


if __name__ == "__main__":
    main()

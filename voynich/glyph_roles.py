#!/usr/bin/env python3
"""暗号の研究 実験 4（稀な字形の出る場所）と実験 5（変化形の役割）。

    python3 voynich/glyph_roles.py
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import word_families  # noqa: E402

PAIRS = [("ch", "sh"), ("k", "ckh"), ("t", "cth"), ("p", "cph"), ("f", "cfh")]


def chi2_sf(x: float, k: int) -> float:
    """カイ二乗分布の上側確率（正則化不完全ガンマ関数。x が大きいときは連分数）。"""
    a, xx = k / 2, x / 2
    if xx <= 0:
        return 1.0
    lead = math.exp(-xx + a * math.log(xx) - math.lgamma(a))
    if xx < a + 1:
        s, term, n = 0.0, 1.0 / a, 0
        while term > 1e-15 * s and n < 10000:
            s += term
            n += 1
            term *= xx / (a + n)
        return max(0.0, 1 - lead * s)
    b, c, d = xx + 1 - a, 1e300, 1 / (xx + 1 - a)
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1 / d if abs(d) > 1e-300 else 1e300
        c = b + an / c if abs(c) > 1e-300 else 1e300
        h *= d * c
        if abs(d * c - 1) < 1e-15:
            break
    return lead * h


def _lhyp(x, r1, c1, n):
    lc = lambda a, b: math.lgamma(a + 1) - math.lgamma(b + 1) - math.lgamma(a - b + 1)  # noqa: E731
    return lc(c1, x) + lc(n - c1, r1 - x) - lc(n, r1)


def fisher(a: int, b: int, c: int, d: int) -> float:
    r1, c1, n = a + b, a + c, a + b + c + d
    obs = _lhyp(a, r1, c1, n)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(math.exp(lp) for x in range(lo, hi + 1) if (lp := _lhyp(x, r1, c1, n)) <= obs + 1e-9))


def tokens(lines, opts):
    """(字形, ロカスの種類, 段落の 1 行目か, 行の中の位置, 語の中の位置, 語, 言語) を順に返す。"""
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        for i, w in enumerate(ws):
            lp = "最初の語" if i == 0 else "最後の語" if i == len(ws) - 1 else "その他"
            gs = list(ivtff.glyphs(w))
            for j, g in enumerate(gs):
                wp = "1 字の語" if len(gs) == 1 else "語頭" if j == 0 else "語末" if j == len(gs) - 1 else "語中"
                yield g, ln.locus_class, ln.position == "@", lp, wp, gs, ln.page.get("L")


def fmt_p(p):
    return "< 1e-12" if p < 1e-12 else f"{p:.2g}"


def exp4(toks):
    print("=== 実験 4: 稀な字形の出る場所 ===")
    total = Counter(t[0] for t in toks)
    rare = {g for g, n in total.items() if n < 30}
    at = {g for g in rare if g.startswith("@")}
    print(f"稀な字形 {len(rare)} 種類・{sum(total[g] for g in rare)} 回（うち @nnn; は {len(at)} 種類・{sum(total[g] for g in at)} 回）。"
          f"全ての字形 {sum(total.values())} 回")
    dims = [("ロカスの種類", lambda t: t[1], None),
            ("段落の 1 行目か", lambda t: "1 行目" if t[2] else "その他の行", "P"),
            ("行の中の位置", lambda t: t[3], "P"),
            ("語の中の位置", lambda t: t[4], None)]
    for label, sel in (("稀な字形（30 回未満）", rare), ("@nnn; だけ", at)):
        print(f"\n-- {label} --")
        for name, key, only in dims:
            ts = [t for t in toks if only is None or t[1] == only]
            r = Counter(key(t) for t in ts if t[0] in sel)
            o = Counter(key(t) for t in ts if t[0] not in sel)
            keys = sorted(set(r) | set(o), key=lambda k: -o[k])
            g, _ = word_families.g_test([[r[k] for k in keys], [o[k] for k in keys]])
            p = chi2_sf(g, len(keys) - 1)
            nr, no = sum(r.values()), sum(o.values())
            cells = "  ".join(f"{k} {r[k] / nr:.0%}（基準 {o[k] / no:.0%}, 比 {(r[k] / nr) / (o[k] / no):.1f}）" for k in keys)
            print(f"{name:<10} n={nr:<4} {cells}  G = {g:.1f}, p = {fmt_p(p)}{'  ← 有意' if p < 0.05 / 4 else ''}")
    # 稀な字形の語の中身
    words = Counter("".join(t[5]) for t in toks if t[0] in at)
    print("\n@nnn; を含む語（多い順）:", ", ".join(f"{w}({n})" for w, n in words.most_common(12)))


def exp5(toks):
    print("\n=== 実験 5: 変化形の役割 ===")
    P = [t for t in toks if t[1] == "P"]
    print("(a) 変化形の割合（元の形＋変化形のうち、変化形の割合）。α = 0.05/20")
    conds = [("語頭", lambda t: t[4] in ("語頭", "1 字の語")),
             ("行の最初の語", lambda t: t[3] == "最初の語"),
             ("段落の 1 行目", lambda t: t[2]),
             ("言語 B", lambda t: t[6] == "B")]
    for base, var in PAIRS:
        out = []
        for name, f in conds:
            a = sum(1 for t in P if t[0] == var and f(t))
            b = sum(1 for t in P if t[0] == base and f(t))
            c = sum(1 for t in P if t[0] == var and not f(t))
            d = sum(1 for t in P if t[0] == base and not f(t))
            p = fisher(a, b, c, d)
            orr = (a + .5) * (d + .5) / ((b + .5) * (c + .5))
            out.append(f"{name} {a / max(1, a + b):.0%} 対 {c / max(1, c + d):.0%}（OR {orr:.2f}, p {fmt_p(p)}{' *' if p < 0.05 / 20 else ''}）")
        print(f"  {base}/{var}: " + "；".join(out))
    print("\n(b) 入れ替わる相手: 元の形を含む語（3 回以上）の最初の元の形を Y に置き換えた語が実在する割合")
    freq = Counter(tuple(t[5]) for t in P if t[4] in ("語頭", "1 字の語"))  # 語ごとに 1 回数える
    glyph_n = Counter(t[0] for t in P)
    cands = [g for g, n in glyph_n.items() if n >= 300]
    ranks = {}
    for base, var in PAIRS:
        src = [w for w, n in freq.items() if n >= 3 and base in w]
        rate = {}
        for y in set(cands) | {var}:  # 変化形は 300 回未満でも必ず候補に入れる（事前の記録からの変更）
            if y == base:
                continue
            hit = 0
            for w in src:
                i = w.index(base)
                if freq.get(w[:i] + (y,) + w[i + 1:], 0) >= 1:
                    hit += 1
            rate[y] = hit / len(src)
        order = sorted(rate, key=lambda y: -rate[y])
        ranks[base] = order.index(var) + 1
        print(f"  {base}（{len(src)} 語）: 変化形 {var} は {ranks[base]} 位（{rate[var]:.0%}）。上位: "
              + ", ".join(f"{y} {rate[y]:.0%}" for y in order[:6]))
    print("\n(c) 探索（事前の記録に無い）: 逆向き。変化形を含む語の、変化形を Y に置き換えた語が実在する割合")
    for base, var in PAIRS:
        src = [w for w, n in freq.items() if n >= 3 and var in w]
        if not src:
            continue
        rate = {}
        for y in set(cands) | {base}:
            if y == var:
                continue
            hit = sum(1 for w in src if freq.get(w[:w.index(var)] + (y,) + w[w.index(var) + 1:], 0) >= 1)
            rate[y] = hit / len(src)
        order = sorted(rate, key=lambda y: -rate[y])
        print(f"  {var}（{len(src)} 語）: 元の形 {base} は {order.index(base) + 1} 位（{rate[base]:.0%}）。上位: "
              + ", ".join(f"{y} {rate[y]:.0%}" for y in order[:6]))
    k = sum(1 for r in ranks.values() if r <= 3)
    print(f"  変化形が上位 3 位以内: {k}/5 組（予測: 4 組以上なら「同じ文字に印を足した形」）")


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    toks = list(tokens(lines, corpus.word_options(args)))
    exp4(toks)
    exp5(toks)


if __name__ == "__main__":
    main()

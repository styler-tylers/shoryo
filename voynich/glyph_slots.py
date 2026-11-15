#!/usr/bin/env python3
"""暗号の研究 実験 6（背の高い字形の枠）と実験 7（字形 1 つだけの語と字形の一覧）。

    python3 voynich/glyph_slots.py <ラテン語のテキスト（E4 の参照）>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import glyph_roles  # noqa: E402
import ivtff  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import unit_entropy  # noqa: E402

GALLOWS = {"k": "k", "t": "t", "p": "p", "f": "f", "ckh": "k", "cth": "t", "cph": "p", "cfh": "f"}
VOWELISH = {"o", "a", "e", "y", "i"}


def mi(pairs) -> float:
    n = len(pairs)
    cxy = Counter(pairs)
    cx = Counter(x for x, _ in pairs)
    cy = Counter(y for _, y in pairs)
    return sum(v / n * math.log2(v * n / (cx[x] * cy[y])) for (x, y), v in cxy.items())


def h(xs) -> float:
    c = Counter(xs)
    n = len(xs)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def corrected(xs, ys, rng, k=200) -> float:
    obs = mi(list(zip(xs, ys)))
    xs2 = list(xs)
    null = 0.0
    for _ in range(k):
        rng.shuffle(xs2)
        null += mi(list(zip(xs2, ys)))
    return obs - null / k


def slot_report(name, words_ctx, is_slot, label, rng):
    """words_ctx: [(字形のリスト, 文脈の dict)]。is_slot: 字形 → 枠の中の種類 or None。"""
    G, nxt, prv, ctx = [], [], [], {}
    B, bn, bp = [], [], []
    for gs, c in words_ctx:
        seq = ["#"] + gs + ["#"]
        for i in range(1, len(seq) - 1):
            g = seq[i]
            s = is_slot(g)
            B.append(s is not None)
            bn.append(seq[i + 1])
            bp.append(seq[i - 1])
            if s is not None:
                G.append(s)
                nxt.append(label(seq[i + 1]))
                prv.append(label(seq[i - 1]))
                for k, v in c.items():
                    ctx.setdefault(k, []).append(v if k != "語頭" else i == 1)
    hg = h(G)
    out = [f"後ろ {corrected(G, nxt, rng) / hg:.1%}", f"前 {corrected(G, prv, rng) / hg:.1%}"]
    out += [f"{k} {corrected(G, v, rng) / hg:.1%}" for k, v in ctx.items()]
    hb = h(B)
    print(f"{name}: 枠の字形 {len(G)} 回、H(G) = {hg:.2f} ビット")
    print(f"   Q1 選択の決まり方（H(G) に対する割合）: " + "、".join(out))
    qn, qp = corrected(B, bn, rng, 50) / hb, corrected(B, bp, rng, 50) / hb
    print(f"   Q2 枠になるかどうか: 後ろ {qn:.1%}、前 {qp:.1%}（H(B) = {hb:.2f}）  → {'後ろ > 前' if qn > qp else '前 ≥ 後ろ'}")
    print("   分布: " + ", ".join(f"{g} {n}" for g, n in Counter(G).most_common()))


def exp6(lines, opts, latin, rng):
    print("=== 実験 6: 背の高い字形の枠 ===")
    for lang in ("A", "B"):
        wc = []
        for ln in lines:
            if ln.locus_class != "P" or ln.page.get("L") != lang:
                continue
            ws = ivtff.words(ln.raw, opts)
            for i, w in enumerate(ws):
                wc.append((list(ivtff.glyphs(w)), {"段落の 1 行目": ln.position == "@", "行の最初の語": i == 0, "語頭": None}))
        slot_report(f"ヴォイニッチ {lang}", wc, GALLOWS.get, lambda g: GALLOWS.get(g, g), rng)
    for p in latin:
        lw = ["".join(w) for w in unit_entropy.latin_words(p)][:30000]
        wc = [(scmp.syllable_code_e4(w), {"語頭": None}) for w in lw]
        slot_report(f"参照 E4 {p.stem}（頭の記号 A〜D）", wc, lambda g: g if g in "ABCD" else None, lambda g: g, rng)


def exp7(lines, opts):
    print("\n=== 実験 7: 字形の一覧 ===")
    lists = {}
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        if ln.page.name in ("f49v", "f66r") and ln.locus_class == "L" and len(ws) == 1 and len(list(ivtff.glyphs(ws[0]))) == 1:
            lists.setdefault(ln.page.name, []).append(ws[0])
        if ln.id == "f57v.3":
            lists["f57v 円"] = [g for w in ws for g in ivtff.glyphs(w)]
    ptok = Counter(g for ln in lines if ln.locus_class == "P" for w in ivtff.words(ln.raw, opts) for g in ivtff.glyphs(w))
    common = {g for g, n in ptok.most_common(25)}
    pv, pn = sum(ptok[g] for g in VOWELISH), sum(ptok.values())
    for name, xs in lists.items():
        a = sum(1 for g in xs if g in VOWELISH)
        p = glyph_roles.fisher(a, len(xs) - a, pv, pn - pv)
        types = list(dict.fromkeys(xs))
        print(f"{name}（{len(xs)} 字形・{len(types)} 種類）: {' '.join(xs)}")
        print(f"   母音らしい字形 {a}/{len(xs)} = {a / len(xs):.0%}（段落テキスト {pv / pn:.0%}, p = {p:.2g}）")
        print(f"   よく使う 25 種類のうち含むもの {len(common & set(types))}: {' '.join(sorted(common & set(types)))}")
        print(f"   よく使うのに含まないもの: {' '.join(g for g, _ in ptok.most_common(25) if g not in types)}")
        print(f"   背の高い字形: {' '.join(sorted({GALLOWS[g] for g in types if g in GALLOWS}))}")


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(2026)
    exp6(lines, opts, [Path(x) for x in sys.argv[1:]], rng)
    exp7(lines, opts)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""黄道のラベルを月（頁）ごとに見る（第 11 回 第 2 段階）。

Z1 ラベルの繰り返し / Z2 同じ頁の円形の文章との共有（頁の入れ替え） / Z3 語頭の分布 / Z4 頁ごとの語の候補。

    python3 voynich/zodiac_labels.py            # 第 2 段階
    python3 voynich/zodiac_labels.py --stage3   # 第 3 段階（頁の並び順）
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = None
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    lab, circ = defaultdict(list), defaultdict(list)
    para = []
    order = []
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        if ln.page.get("I") == "Z":
            if ln.page.name not in order:
                order.append(ln.page.name)
            if ln.locus_class == "L":
                lab[ln.page.name] += [w for w in ws if len(ivtff.glyphs(w)) >= 3]
            elif ln.locus_class == "C":
                circ[ln.page.name] += ws
        elif ln.locus_class == "P":
            para += ws
    pages = [p for p in order if lab[p] and circ[p]]
    print(f"黄道の頁 {len(pages)}: " + ", ".join(pages) + "\n")

    # Z1
    where = defaultdict(set)
    for p in pages:
        for w in set(lab[p]):
            where[w].add(p)
    types = len(where)
    multi = sum(len(v) >= 2 for v in where.values())
    tok = sum(len(lab[p]) for p in pages)
    print(f"Z1 ラベル {tok} 語・異なり {types} 語。2 頁以上に出る異なり語 {multi}（{multi / types:.0%}）")
    print("   よく繰り返すラベル: " + ", ".join(f"{w}({len(v)} 頁)" for w, v in
                                         sorted(where.items(), key=lambda x: -len(x[1]))[:12]))
    same_page_rep = sum(c - 1 for p in pages for c in Counter(lab[p]).values() if c > 1)
    print(f"   同じ頁の中での繰り返し: {same_page_rep} 語\n")

    # Z2
    def rate(assign):
        h = t = 0
        for p in pages:
            vocab = set(circ[assign[p]])
            for w in lab[p]:
                t += 1
                h += w in vocab
        return h / t

    obs = rate({p: p for p in pages})
    ge = 0
    null = []
    for _ in range(5000):
        sh = pages[:]
        rng.shuffle(sh)
        r = rate(dict(zip(pages, sh)))
        null.append(r)
        ge += r >= obs
    print(f"Z2 ラベルの語が同じ頁の円形の文章に出る割合 {obs:.1%}、別の頁と入れ替えた平均 {sum(null) / len(null):.1%}、"
          f"p = {(ge + 1) / 5001:.4f}")
    for p in pages:
        v = set(circ[p])
        others = [sum(w in set(circ[q]) for w in lab[p]) / len(lab[p]) for q in pages if q != p]
        print(f"   {p:<6} ラベル {len(lab[p]):>2} 語  同じ頁 {sum(w in v for w in lab[p]) / len(lab[p]):.0%}"
              f"  他の頁の平均 {sum(others) / len(others):.0%}")
    print()

    # Z3
    def heads(ws):
        c = Counter("".join(ivtff.glyphs(w)[:2]) for w in ws)
        n = sum(c.values())
        return {k: v / n for k, v in c.items()}

    hl = heads([w for p in pages for w in lab[p]])
    hc = heads([w for p in pages for w in circ[p]])
    hp = heads(para)
    print("Z3 語頭の 2 字形の割合（ラベル / 円形の文章 / 全体の段落）")
    for k in sorted(hl, key=lambda k: -hl[k])[:10]:
        print(f"   {k:<6} {hl[k]:>6.1%} {hc.get(k, 0):>7.1%} {hp.get(k, 0):>7.1%}")
    print()

    # Z4
    allw = defaultdict(Counter)
    for p in pages:
        allw[p].update(lab[p])
        allw[p].update(circ[p])
    seen = defaultdict(set)
    for p in pages:
        for w in allw[p]:
            seen[w].add(p)
    print("Z4 その頁だけに出て、その頁で 2 回以上出る語（ラベル＋円形の文章）")
    for p in pages:
        cand = [(w, c) for w, c in allw[p].items() if len(seen[w]) == 1 and c >= 2 and len(ivtff.glyphs(w)) >= 3]
        cand.sort(key=lambda x: -x[1])
        inlab = set(lab[p])
        print(f"   {p:<6} " + (", ".join(f"{w}×{c}{'（ラベル）' if w in inlab else ''}" for w, c in cand) or "なし"))


if __name__ == "__main__" and "--stage3" not in sys.argv:
    main()


# ---------------------------------------------------------------------------
# 第 3 段階: 黄道の頁の並び順とラベル
# ---------------------------------------------------------------------------

SIGN = {"f70v2": "うお座", "f70v1": "おひつじ座（暗）", "f71r": "おひつじ座（明）", "f71v": "おうし座（明）",
        "f72r1": "おうし座（暗）", "f72r2": "ふたご座", "f72r3": "かに座", "f72v3": "しし座", "f72v2": "おとめ座",
        "f72v1": "てんびん座", "f73r": "さそり座", "f73v": "いて座"}
ORDER = list(SIGN)


def stage3() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = None
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    lab, allw = defaultdict(list), defaultdict(set)
    for ln in lines:
        if ln.page.name in SIGN:
            ws = ivtff.words(ln.raw, opts)
            if ln.locus_class == "L":
                lab[ln.page.name] += [w for w in ws if len(ivtff.glyphs(w)) >= 3]
            allw[ln.page.name].update(ws)
    where = defaultdict(set)
    for p in ORDER:
        for w in set(lab[p]):
            where[w].add(p)
    rep = {w: ps for w, ps in where.items() if len(ps) >= 2}

    def zo1(order):
        idx = {p: i for i, p in enumerate(order)}
        d = [abs(idx[a] - idx[b]) for ps in rep.values() for a in ps for b in ps if a < b]
        return sum(d) / len(d)

    def jac(a, b):
        return len(allw[a] & allw[b]) / len(allw[a] | allw[b])

    def zo2(order):
        adj = [jac(a, b) for a, b in zip(order, order[1:])]
        non = [jac(order[i], order[j]) for i in range(len(order)) for j in range(i + 2, len(order))]
        return sum(adj) / len(adj) - sum(non) / len(non)

    o1, o2 = zo1(ORDER), zo2(ORDER)
    g1 = g2 = 0
    n1, n2 = [], []
    for _ in range(5000):
        sh = ORDER[:]
        rng.shuffle(sh)
        a, b = zo1(sh), zo2(sh)
        n1.append(a)
        n2.append(b)
        g1 += a <= o1
        g2 += b >= o2
    print(f"ZO1 繰り返すラベル {len(rep)} 語: 出る頁どうしの並び順の差の平均 {o1:.2f}、入れ替えた場合 {sum(n1) / 5000:.2f}、"
          f"p = {(g1 + 1) / 5001:.4f}")
    for w, ps in sorted(rep.items(), key=lambda x: -len(x[1])):
        print(f"   {w:<10} " + ", ".join(f"{SIGN[p]}" for p in ORDER if p in ps))
    print(f"ZO2 隣り合う月の Jaccard − 隣り合わない組 = {o2:+.4f}、入れ替えた場合 {sum(n2) / 5000:+.4f}、"
          f"p = {(g2 + 1) / 5001:.4f}")
    pairs = sorted(((jac(a, b), a, b) for i, a in enumerate(ORDER) for b in ORDER[i + 1:]), reverse=True)
    rank = {(a, b): r + 1 for r, (_, a, b) in enumerate(pairs)}
    for a, b in (("f70v1", "f71r"), ("f71v", "f72r1")):
        print(f"ZO3 {SIGN[a]}–{SIGN[b]}: Jaccard {jac(a, b):.3f}、66 組中 {rank[(a, b)]} 番目")
    print("   似ている組の上位 5: " + ", ".join(f"{SIGN[a]}–{SIGN[b]} {j:.3f}" for j, a, b in pairs[:5]))


if __name__ == "__main__" and "--stage3" in sys.argv:
    stage3()

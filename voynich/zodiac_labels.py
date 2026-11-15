#!/usr/bin/env python3
"""黄道のラベルを月（頁）ごとに見る（第 11 回 第 2 段階）。

Z1 ラベルの繰り返し / Z2 同じ頁の円形の文章との共有（頁の入れ替え） / Z3 語頭の分布 / Z4 頁ごとの語の候補。

    python3 voynich/zodiac_labels.py
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


if __name__ == "__main__":
    main()

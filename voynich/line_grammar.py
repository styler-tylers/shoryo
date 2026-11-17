#!/usr/bin/env python3
"""行の中の文法（第 17 回）。

G1 位置ごとの語頭・語末の分布 / G2 行の 1 語目と最後の語の結び付き / G3 行の中での語末の移り変わり

    python3 voynich/line_grammar.py <ラテン語のテキスト …>
    python3 voynich/line_grammar.py --stage2   # 行頭・行末の型は普通の語＋印か
    python3 voynich/line_grammar.py --stage3   # 行の中ほどの語だけでやり直す
    python3 voynich/line_grammar.py --stage4   # 行頭にしか出ない語
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import function_words  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
import word_grammar  # noqa: E402


def bin_of(n: int) -> int:
    return 0 if n <= 5 else 1 if n <= 7 else 2 if n <= 9 else 3


def g2(lines_, first_fn, last_fn, rng, trials=2000):
    ls = [l for l in lines_ if len(l) >= 4]
    firsts = [first_fn(l[0]) for l in ls]
    lasts = [last_fn(l[-1]) for l in ls]
    bins = [bin_of(len(l)) for l in ls]
    obs = line_unit.mi(list(zip(firsts, lasts)))
    idx = defaultdict(list)
    for i, b in enumerate(bins):
        idx[b].append(i)
    ge = 0
    null = []
    for _ in range(trials):
        sh = lasts[:]
        for ids in idx.values():
            vals = [lasts[i] for i in ids]
            rng.shuffle(vals)
            for i, v in zip(ids, vals):
                sh[i] = v
        m = line_unit.mi(list(zip(firsts, sh)))
        null.append(m)
        ge += m >= obs
    return obs, statistics.mean(null), (ge + 1) / (trials + 1), len(ls)


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    first2 = lambda w: "".join(ivtff.glyphs(w)[:2])  # noqa: E731
    endc = lambda w: word_grammar.parse(w)[2]  # noqa: E731
    headc = lambda w: word_grammar.parse(w)[0]  # noqa: E731
    for lang in ("A", "B"):
        ls = [ivtff.words(ln.raw, opts) for ln in lines if ln.page.get("L") == lang]
        ls = [l for l in ls if len(l) >= 4]
        print(f"=== 言語 {lang}（4 語以上の行 {len(ls)}）===")
        # G1
        pos = {"1語目": [l[0] for l in ls], "2語目": [l[1] for l in ls],
               "中ほど": [w for l in ls for w in l[2:-1]], "最後": [l[-1] for l in ls]}
        for name, fn in (("語頭", headc), ("語末", endc)):
            mid = Counter(fn(w) for w in pos["中ほど"])
            nm = sum(mid.values())
            print(f"G1 {name}（中ほどと比べて 2 倍以上 ↑ / 半分以下 ↓）")
            for p in ("1語目", "2語目", "最後"):
                c = Counter(fn(w) for w in pos[p])
                n = sum(c.values())
                ups = [f"{k} {c[k] / n:.0%}↑" for k in c if c[k] / n >= 2 * mid[k] / nm and c[k] >= 10]
                downs = [f"{k} {c[k] / n:.0%}↓" for k in mid if mid[k] / nm >= 0.03 and c[k] / n <= 0.5 * mid[k] / nm]
                print(f"   {p}: " + ", ".join(ups + downs))
        # G2
        obs, null, p, n = g2(ls, first2, endc, rng)
        print(f"G2 1 語目の始めの 2 字形 × 最後の語の語末: 相互情報量 {obs:.3f}、入れ替え {null:.3f}、"
              f"差 {obs - null:+.3f}、p = {p:.4f}（{n} 行）")
        # G3
        print("G3 行の中の相対位置（5 つに分ける）ごとの語末の割合 と 順位相関")
        for e in ("dy", "y", "l", "r", "aiin"):
            shares = []
            for b in range(5):
                ws = [w for l in ls for i, w in enumerate(l) if min(4, int(5 * i / len(l))) == b]
                shares.append(sum(endc(w) == e for w in ws) / len(ws))
            rho = function_words.spearman(list(range(5)), shares)
            print(f"   -{e:<5} " + " ".join(f"{x:.0%}" for x in shares) + f"   相関 {rho:+.1f}")
        print()

    width = 37
    for p in map(Path, sys.argv[1:]):
        words = ["".join(w) for w in unit_entropy.latin_words(p)]
        wr = [l for _, ls in line_unit.wrap(words, width) for l in ls]
        se = [l for _, ls in line_unit.sentences(p) for l in ls]
        for name, L in (("紙の幅で折り返し", wr), ("1 行に 1 文", se)):
            obs, null, pv, n = g2(L, lambda w: w[:2], lambda w: w[-2:], rng, trials=500)
            print(f"参照 {p.stem}（{name}）G2: 相互情報量 {obs:.3f}、入れ替え {null:.3f}、差 {obs - null:+.3f}、"
                  f"p = {pv:.4f}（{n} 行）")


if __name__ == "__main__" and not ({"--stage2", "--stage3", "--stage4"} & set(sys.argv)):
    main()


# ---------------------------------------------------------------------------
# 第 2 段階: 行頭・行末の型は「普通の語＋印」か / 第 3 段階: 行の中ほどの語だけでやり直す
# ---------------------------------------------------------------------------

GALLOWS = {"k", "t", "p", "f", "ckh", "cth", "cph", "cfh"}


def fisher(a, b, c, d):
    import sac_roots
    return sac_roots.fisher_two_sided(a, b, c, d)


def stage2() -> None:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        ls = [ivtff.words(ln.raw, opts) for ln in lines if ln.page.get("L") == lang]
        ls = [l for l in ls if len(l) >= 3]
        mid = set(w for l in ls for w in l[1:-1])

        def m_has(w):
            g = list(ivtff.glyphs(w))
            stem = "".join(g[:-1])
            return any(stem + e in mid for e in ("n", "r", "l", "s", "y", "dy"))

        def g_has(w):
            g = list(ivtff.glyphs(w))
            rest = "".join(g[1:])
            return len(g) >= 2 and (rest in mid or any(h + rest in mid for h in ("ch", "sh", "o", "qo")))

        fin_m = [l[-1] for l in ls if ivtff.glyphs(l[-1])[-1:] == ["m"]]
        mid_m = [w for l in ls for w in l[1:-1] if ivtff.glyphs(w)[-1:] == ["m"]]
        a, c = sum(map(m_has, fin_m)), sum(map(m_has, mid_m))
        print(f"=== 言語 {lang} ===")
        print(f"M1 -m の語で、語末を n/r/l/s/y/dy にした形が中ほどにある割合: 行末 {a}/{len(fin_m)}（{a / max(1, len(fin_m)):.0%}）、"
              f"中ほど {c}/{len(mid_m)}（{c / max(1, len(mid_m)):.0%}）、p = {fisher(a, len(fin_m) - a, c, len(mid_m) - c):.3g}")
        ini_g = [l[0] for l in ls if ivtff.glyphs(l[0])[:1] and ivtff.glyphs(l[0])[0] in GALLOWS]
        mid_g = [w for l in ls for w in l[1:-1] if ivtff.glyphs(w)[:1] and ivtff.glyphs(w)[0] in GALLOWS]
        a, c = sum(map(g_has, ini_g)), sum(map(g_has, mid_g))
        print(f"M2 背の高い字形で始まる語で、最初の字形を除いた・置き換えた形が中ほどにある割合: 行頭 {a}/{len(ini_g)}（{a / max(1, len(ini_g)):.0%}）、"
              f"中ほど {c}/{len(mid_g)}（{c / max(1, len(mid_g)):.0%}）、p = {fisher(a, len(ini_g) - a, c, len(mid_g) - c):.3g}")
        ex = [w for w in ini_g if g_has(w)][:8]
        print("   行頭の例: " + ", ".join(f"{w}→{''.join(ivtff.glyphs(w)[1:])}" for w in ex))
        ex = [w for w in fin_m if m_has(w)][:8]
        print("   行末の例: " + ", ".join(ex))
        print()


def stage3(paths) -> None:
    import function_words as fw
    import null_generator as ng
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        ls = [ivtff.words(ln.raw, opts) for ln in lines if ln.page.get("L") == lang]
        full = [w for l in ls for w in l]
        inner = [w for l in ls if len(l) >= 3 for w in l[1:-1]]
        print(f"=== 言語 {lang}: 全ての語 {len(full)} → 中ほどの語 {len(inner)} ===")
        for name, toks in (("全て", full), ("中ほど", inner)):
            e = unit_entropy.entropies([list(ivtff.glyphs(w)) for w in toks])
            v = ng.vocab_stats(toks)
            rows = fw.profile(toks)
            nf = sum(1 for r in rows if r[3] >= 0.95 and r[4] >= 0.80)
            print(f"  {name:<5} h1 {e['h1']:.2f}  h2 {e['h2']:.2f}  h2/h1 {e['h2/h1']:.2f}  "
                  + "  ".join(f"{k} {x:.3f}" for k, x in v.items()) + f"  機能語らしい語 {nf}")
    print("  自然言語の範囲: h2 3.09〜3.37, h2/h1 0.78〜0.83, V1 1511〜4793, V2 0.491〜0.681, V3 −0.869〜−0.572, "
          "V4 0.597〜0.783, 機能語らしい語 2〜29")


if __name__ == "__main__" and "--stage2" in sys.argv:
    stage2()
if __name__ == "__main__" and "--stage3" in sys.argv:
    stage3([])


# ---------------------------------------------------------------------------
# 第 4 段階: 行頭にしか出ない語
# ---------------------------------------------------------------------------


def stage4() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        L = [(ln, ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == lang]
        L = [(ln, ws) for ln, ws in L if len(ws) >= 3]
        not_first = set(w for _, ws in L for w in ws[1:])
        only = set(ws[0] for _, ws in L) - not_first
        print(f"=== 言語 {lang}: 行頭だけの語 {len(only)} 種類 ===")
        # I1
        a = sum(ws[0] in only for ln, ws in L if ln.position == "@")
        n1 = sum(1 for ln, _ in L if ln.position == "@")
        c = sum(ws[0] in only for ln, ws in L if ln.position != "@")
        n2 = len(L) - n1
        print(f"I1 行頭の語のうち行頭だけの語: 段落の 1 行目 {a}/{n1}（{a / max(1, n1):.0%}）、それ以外 {c}/{n2}（{c / n2:.0%}）、"
              f"p = {fisher(a, n1 - a, c, n2 - c):.3g}")
        # I2
        pages_of = defaultdict(set)
        count = Counter()
        for ln, ws in L:
            for w in ws:
                pages_of[w].add(ln.page.name)
                count[w] += 1
        multi = [w for w in only if count[w] >= 2]
        obs = sum(len(pages_of[w]) == 1 for w in multi) / max(1, len(multi))
        mids_by_n = defaultdict(list)
        for w in set(w for _, ws in L for w in ws[1:-1]):
            if w not in only:
                mids_by_n[count[w]].append(w)
        vals = []
        for _ in range(200):
            pick = []
            for w in multi:
                pool = mids_by_n.get(count[w]) or mids_by_n[2]
                pick.append(rng.choice(pool))
            vals.append(sum(len(pages_of[w]) == 1 for w in pick) / max(1, len(pick)))
        print(f"I2 2 回以上出る行頭だけの語 {len(multi)} 種類のうち、1 つの頁だけに出る割合 {obs:.0%}、"
              f"同じ回数の中ほどの語 {statistics.mean(vals):.0%}（200 回の平均）、"
              f"中ほどの方が同じか高い回 {sum(v >= obs for v in vals)}/200")
        # I3
        mids_page = defaultdict(set)
        for ln, ws in L:
            mids_page[ln.page.name].update(ws[1:-1])
        items = [(ln.page.name, "".join(ivtff.glyphs(ws[0])[1:])) for ln, ws in L if ws[0] in only and len(ivtff.glyphs(ws[0])) >= 3]
        pages = list(mids_page)

        def rate(assign):
            return sum(rest in mids_page[assign[p]] for p, rest in items) / len(items)

        obs3 = rate({p: p for p in pages})
        ge = 0
        null = []
        for _ in range(2000):
            sh = pages[:]
            rng.shuffle(sh)
            r = rate(dict(zip(pages, sh)))
            null.append(r)
            ge += r >= obs3
        print(f"I3 最初の字形を除いた形が同じ頁の中ほどに出る割合 {obs3:.1%}、頁を入れ替えた場合 {statistics.mean(null):.1%}、"
              f"p = {(ge + 1) / 2001:.4f}（{len(items)} 語）")
        print("   例: " + ", ".join(sorted(only, key=lambda w: -count[w])[:12]))
        print()


if __name__ == "__main__" and "--stage4" in sys.argv:
    stage4()

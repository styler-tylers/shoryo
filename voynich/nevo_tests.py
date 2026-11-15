#!/usr/bin/env python3
"""nēvo Research Method による解析: N1 縦に読む / N2 尺度を変える（A と B）/ N3 関係軸を変える（語彙の軸）。

    python3 voynich/nevo_tests.py <Caesar> <Descartes> <Dante>
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import unit_entropy  # noqa: E402
from e5_cipher import syllable_code_e5  # noqa: E402
from e6_rotation import rotate  # noqa: E402

# ---------------------------------------------------------------------------
# データ: 頁 → 行（語は単位のタプル）
# ---------------------------------------------------------------------------


def voynich_pages(lines, opts, lang, section=None):
    pages = {}
    for ln in lines:
        if ln.locus_class != "P" or ln.page.get("L") != lang or (section and ln.page.get("I") != section):
            continue
        ws = [tuple(ivtff.glyphs(w)) for w in ivtff.words(ln.raw, opts)]
        if ws:
            pages.setdefault(ln.page.name, []).append(ws)
    return pages


def latin_pages(words, width=37):
    return {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in line_unit.wrap(words, width)}


def column_transposed(words, rows=25, cols=6):
    pages, per = {}, rows * cols
    for b in range(0, len(words) - per + 1, per):
        block = words[b:b + per]
        grid = [[block[c * rows + r] for c in range(cols)] for r in range(rows)]
        pages[f"p{b // per}"] = [[tuple(w) for w in row] for row in grid]
    return pages


end2 = lambda w: "".join(w[-2:])  # noqa: E731
head2 = lambda w: "".join(w[:2])  # noqa: E731

# ---------------------------------------------------------------------------
# N1 縦に読む
# ---------------------------------------------------------------------------


def n1(name, pages, rng, runs=50):
    horiz = [(end2(a), head2(b)) for ls in pages.values() for l in ls for a, b in zip(l, l[1:])]
    vert, vk = [], []
    for pg, ls in pages.items():
        for up, lo in zip(ls, ls[1:]):
            for k in range(min(len(up), len(lo))):
                vert.append((end2(up[k]), head2(lo[k])))
                vk.append((pg, k, end2(up[k])))
    by_k = {}
    for pg, ls in pages.items():
        for l in ls:
            for k, w in enumerate(l):
                by_k.setdefault(k, []).append((pg, head2(w)))
    n = min(len(horiz), len(vert))
    mv = line_unit.mi(vert)
    mh, mn = [], []
    for _ in range(runs):
        mh.append(line_unit.mi(rng.sample(horiz, n)))
        null = []
        for pg, k, e in vk:
            cand = by_k[k]
            while True:
                q, h = rng.choice(cand)
                if q != pg:
                    break
            null.append((e, h))
        mn.append(line_unit.mi(null))
    h, z = statistics.mean(mh), statistics.mean(mn)
    v = (mv - z) / (h - z) if h > z else float("nan")
    print(f"  {name:<28} 組 横 {len(horiz)}・縦 {len(vert)}  横 {h:.3f}  縦 {mv:.3f}  無関係 {z:.3f}  V = {v:.2f}")


# ---------------------------------------------------------------------------
# N2 尺度を変える
# ---------------------------------------------------------------------------


def sample_lines(ls, n, rng):
    ls = list(ls)
    rng.shuffle(ls)
    out, k = [], 0
    for l in ls:
        if k >= n:
            break
        out.append(l)
        k += len(l)
    return out


def jsd(c1: Counter, c2: Counter) -> float:
    n1_, n2_ = sum(c1.values()), sum(c2.values())
    d = 0.0
    for k in set(c1) | set(c2):
        p, q = c1[k] / n1_, c2[k] / n2_
        m = (p + q) / 2
        if p:
            d += 0.5 * p * math.log2(p / m)
        if q:
            d += 0.5 * q * math.log2(q / m)
    return d


def bigrams(ls):
    c = Counter()
    for l in ls:
        seq = ["#"]
        for w in l:
            seq += list(w) + ["#"]
        c.update(zip(seq, seq[1:]))
    return c


def word_dist(ls1, ls2):
    c1 = Counter(w for l in ls1 for w in l)
    c2 = Counter(w for l in ls2 for w in l)
    keep = {w for w in set(c1) | set(c2) if c1[w] >= 5 or c2[w] >= 5}
    return jsd(Counter({w: c1[w] for w in keep}), Counter({w: c2[w] for w in keep}))


WIDTH = {**{k: hi - lo for k, (lo, hi) in scmp.FULL_RANGE.items()}, **{k: hi - lo for k, (lo, hi) in scmp.V_NAT.items()}}


def type_profile(ls):
    words = [w for l in ls for w in l]
    e = unit_entropy.entropies([list(w) for w in words])
    v = null_generator.vocab_stats(["".join(w) for w in words])
    return {**{k: e[k] for k in scmp.FULL_RANGE}, **v}


def far(ls1, ls2):
    a, b = type_profile(ls1), type_profile(ls2)
    return statistics.mean(abs(a[k] - b[k]) / WIDTH[k] for k in WIDTH)


def distances(X, Y, n, rng, draws=10):
    out = {"近景 字形の 2 つ組": [], "中景 語": [], "遠景 文章の型": []}
    for _ in range(draws):
        x, y = sample_lines(X, n, rng), sample_lines(Y, n, rng)
        out["近景 字形の 2 つ組"].append(jsd(bigrams(x), bigrams(y)))
        out["中景 語"].append(word_dist(x, y))
        try:
            out["遠景 文章の型"].append(far(x, y))
        except ZeroDivisionError:  # 標本が小さく Heaps の指数が計算できない（事前の記録からの変更）
            out["遠景 文章の型"].append(float("nan"))
    return {k: statistics.mean(v) for k, v in out.items()}


def split_alt(pages):
    ks = sorted(pages)
    return [l for k in ks[0::2] for l in pages[k]], [l for k in ks[1::2] for l in pages[k]]


def n2(lines, opts, lat, rng):
    print("\n=== N2 尺度を変える: 言語 A と B ===")
    A, B = voynich_pages(lines, opts, "A"), voynich_pages(lines, opts, "B")
    AH, BH = voynich_pages(lines, opts, "A", "H"), voynich_pages(lines, opts, "B", "H")
    allA = [l for ls in A.values() for l in ls]
    allB = [l for ls in B.values() for l in ls]
    c1, c2 = (latin_pages(["".join(w) for w in unit_entropy.latin_words(p)][:40000]) for p in lat[:2])
    dn = latin_pages(["".join(w) for w in unit_entropy.latin_words(lat[2])][:40000])
    flat = lambda P: [l for ls in P.values() for l in ls]  # noqa: E731
    cs1, cs2 = split_alt(c1)
    for N, rows in ((5000, [("A 対 B（全体）", allA, allB), ("A₁ 対 A₂（同じ言語の中）", *split_alt(A)),
                             ("B₁ 対 B₂（同じ言語の中）", *split_alt(B)),
                             ("Caesar₁ 対 Caesar₂（同じ文章の中）", cs1, cs2),
                             ("Caesar 対 Descartes（同じ言語・別の書き手）", flat(c1), flat(c2)),
                             ("Caesar 対 Dante（別の言語）", flat(c1), flat(dn))]),
                    (1500, [("植物の頁だけ: A 対 B", flat(AH), flat(BH)), ("植物の頁だけ: A₁ 対 A₂", *split_alt(AH)),
                            ("植物の頁だけ: B₁ 対 B₂", *split_alt(BH)),
                            ("Caesar₁ 対 Caesar₂", cs1, cs2),
                            ("Caesar 対 Descartes", flat(c1), flat(c2)), ("Caesar 対 Dante", flat(c1), flat(dn))])):
        print(f"-- 1 回の標本 {N} 語、10 回の平均 --")
        for name, X, Y in rows:
            d = distances(X, Y, N, rng)
            print(f"  {name:<36} " + "  ".join(f"{k} {v:.3f}" for k, v in d.items()))


# ---------------------------------------------------------------------------
# N3 関係軸を変える
# ---------------------------------------------------------------------------


def jacc(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def gdiff(pages, d1=1, d2=10):
    j1 = [jacc(ls[i], ls[i + d1]) for ls in pages.values() for i in range(len(ls) - d1)]
    j2 = [jacc(ls[i], ls[i + d2]) for ls in pages.values() for i in range(len(ls) - d2)]
    return statistics.mean(j1) - statistics.mean(j2)


def n3(name, pages, rng, perms=1000):
    pages = {k: v for k, v in pages.items() if len(v) >= 11}
    keys = list(pages)
    base = []
    for _ in range(20000):
        p, q = rng.sample(keys, 2)
        base.append(jacc(rng.choice(pages[p]), rng.choice(pages[q])))
    b = statistics.mean(base)
    g = {d: statistics.mean(jacc(ls[i], ls[i + d]) for ls in pages.values() for i in range(len(ls) - d)) / b
         for d in (1, 2, 3, 5, 10)}
    obs = gdiff(pages)
    ge = 0
    for _ in range(perms):
        sh = {}
        for k, ls in pages.items():
            x = list(ls)
            rng.shuffle(x)
            sh[k] = x
        ge += gdiff(sh) >= obs
    p = (ge + 1) / (perms + 1)
    print(f"  {name:<28} 頁 {len(pages)}  基準 {b:.4f}  " + "  ".join(f"G({d}) {v:.2f}" for d, v in g.items())
          + f"  G(1)−G(10) の p = {p:.3g}")


def main() -> None:
    lat = [Path(x) for x in sys.argv[1:4]]
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(2026)
    caesar = ["".join(w) for w in unit_entropy.latin_words(lat[0])][:30000]
    e5 = ["".join(syllable_code_e5(w)) for w in caesar]
    para = {}
    for lang in ("A", "B"):
        for i, (pg, ls) in enumerate(line_unit.voynich_paragraphs(lines, lang, opts)):
            para[f"{lang}{i}"] = (lang, [[tuple(ivtff.glyphs(w)) for w in l] for l in ls])
    print("=== N1 観測点を動かす: 縦に読む ===")
    for lang in ("A", "B"):
        n1(f"ヴォイニッチ {lang}（段落）", {k: ls for k, (lg, ls) in para.items() if lg == lang}, rng)
    n1("参照 (a) E5 折り返し", latin_pages(e5), rng)
    n1("参照 (b) E5 列の転置", column_transposed(e5), rng)
    n2(lines, opts, lat, rng)
    print("\n=== N3 関係軸を変える: 語彙の軸 ===")
    for lang in ("A", "B"):
        n3(f"ヴォイニッチ {lang}（頁）", voynich_pages(lines, opts, lang), rng)
    n3("参照 E5 ＋ 回転", dict(rotate(list(latin_pages(e5).items()), random.Random(7))), rng)
    n3("参照 ラテン語（文字）", latin_pages(caesar), rng)


if __name__ == "__main__":
    main()

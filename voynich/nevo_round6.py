#!/usr/bin/env python3
"""nēvo による解析 第 6 巡: N15（綱引きを解く）・N16（工夫した無意味な生成）・N17（言語 B の段落の始まり）。

    python3 voynich/nevo_round6.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402
from e5_cipher import syllable_code_e5  # noqa: E402
from nevo_round2 import CLASSES, distance_test, similar_words  # noqa: E402
from nevo_round3 import edges, interior  # noqa: E402
from nevo_round5 import fresh_source, share_first_only  # noqa: E402


def pick(inner, rng, short):
    recent = inner[-10:]
    ws = [(1 / (len(recent) - i), l) for i, l in enumerate(recent) if l]
    if not ws:
        return None
    r = rng.random() * sum(x for x, _ in ws)
    line = ws[-1][1]
    for x, l in ws:
        r -= x
        if r <= 0:
            line = l
            break
    if short:
        return rng.choices(line, [1 / len(w) ** 2 for w in line])[0]
    return rng.choice(line)


def group_of(ch):
    if ch in scmp.ONSET:
        i = scmp.ONSET.index(ch) // 4
        return scmp.ONSET[i * 4:i * 4 + 4]
    if ch in scmp.NUCLEUS:
        i = scmp.NUCLEUS.index(ch) // 2
        return scmp.NUCLEUS[i * 2:i * 2 + 2]
    return next(c for c in CLASSES if ch in c)


def mutate(w, rng, in_group):
    i = rng.randrange(len(w) - 1) if len(w) > 1 else 0  # 最後以外
    pool = group_of(w[i]) if in_group else next(c for c in CLASSES if w[i] in c)
    cand = [x for x in pool if x != w[i]] or [w[i]]
    return w[:i] + rng.choice(cand) + w[i + 1:]


def build(inner_src, edge_src, c, rng, q, short=False, in_group=False, cap=30000, width=37, lpp=25):
    lines, inner, cur, cur_len, total = [], [], [], 0, 0

    def close(line):
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        a, b = edge_src(), edge_src()
        if a is None or b is None:
            return False
        if rng.random() < q:
            a = rng.choice("XYW") + a
        inner.append(list(line))
        lines.append([a] + line + [b])
        return True

    while total < cap:
        w = None
        if rng.random() < c:
            w = pick(inner, rng, short)
            if w is not None and rng.random() < 0.5:
                w = mutate(w, rng, in_group)
        if w is None:
            w = inner_src()
            if w is None:
                break
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > width - 12:
            if not close(cur):
                cur = []
                break
            total += len(cur) + 2
            cur, cur_len, add = [], 0, len(w)
        cur.append(w)
        cur_len += add
    if cur:
        close(cur)
    return [(f"p{i // lpp}", lines[i:i + lpp]) for i in range(0, len(lines), lpp)]


def sources(caesar, mode, rng):
    half = len(caesar) // 2
    if mode == "無意味な語彙":
        word, _ = fresh_source(random.Random(3))
        lex = list(dict.fromkeys(word() for _ in range(20000)))[:8000]
        wts = [1 / r for r in range(1, len(lex) + 1)]
        f = lambda: rng.choices(lex, wts)[0]  # noqa: E731
        return f, f
    inner = ["".join(syllable_code_e5(w)) for w in caesar[:half]]
    if mode == "語順を崩した平文":
        random.Random(9).shuffle(inner)
    edge = ["".join(syllable_code_e5(w)) for w in caesar[half:]]
    random.Random(5).shuffle(edge)
    it, et = iter(inner), iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None))


def row(name, pages, rng, perms=300):
    words = [w for _, ls in pages for l in ls for w in l]
    e = unit_entropy.entropies([list(w) for w in words])
    v = null_generator.vocab_stats(words)
    k, n = scmp.judge(e, v)
    r = line_unit.l1(pages, lambda w: w[-2:], lambda w: w[:2], rng)
    print(f"-- {name}: 8 つの量 {k}/{n}（h2 {e['h2']:.2f} 語長 {e['語の長さ']:.2f} V4 {v['V4 Heaps']:.3f} V3 {v['V3 Zipf']:.3f}）")
    print(f"   またぐ−基準 {r['行をまたぐ'] - r['無関係']:+.3f}  行の中−基準 {r['行の中'] - r['無関係']:+.3f}  行頭だけの語 {share_first_only(pages):.0%}")
    sc.CHAR_MODE = True
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    sct.measure("   T1〜T4", dict(pages), tuple, rng)
    tp = {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in pages}
    distance_test("   端 似た語", edges(tp), similar_words, rng, perms=perms)
    distance_test("   内側 似た語", interior(tp), similar_words, rng, perms=perms)


def n17(rng, runs=200):
    print("\n=== N17 段落の中と段落の境目（ZL, 段落テキスト）===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    g = lambda w: list(ivtff.glyphs(w))  # noqa: E731
    for lang in ("A", "B"):
        L = [(ln.page.name, ln.position == "@", ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == lang]
        L = [x for x in L if x[2]]
        pairs = {"段落の中": [], "段落の境目": []}
        heads = {"段落の中": [], "段落の境目": []}
        for (p1, _, w1), (p2, at2, w2) in zip(L, L[1:]):
            if p1 != p2:
                continue
            kind = "段落の境目" if at2 else "段落の中"
            pairs[kind].append((p2, "".join(g(w1[-1])[-2:]), "".join(g(w2[0])[:2])))
        for p, at, ws in L:
            heads["段落の境目" if at else "段落の中"].append((p, "".join(g(ws[0])[:2])))
        for kind, ps in pairs.items():
            obs = line_unit.mi([(a, b) for _, a, b in ps])
            nulls = []
            for _ in range(runs):
                null = []
                for page, a, _ in ps:
                    while True:
                        q, h = rng.choice(heads[kind])
                        if q != page:
                            break
                    null.append((a, h))
                nulls.append(line_unit.mi(null))
            m = statistics.mean(nulls)
            p = (sum(x >= obs for x in nulls) + 1) / (runs + 1)
            print(f"  言語 {lang} {kind:<6} 組 {len(ps):>5}  観測 {obs:.3f}  基準 {m:.3f}  差 {obs - m:+.3f}  p = {p:.3g}")


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    print("=== N15 綱引きを解く（型 B, c 0.4, q 0.25）===")
    for name, short, grp in (("元（N12）", False, False), ("S 短い語", True, False), ("G 群の中", False, True), ("S＋G", True, True)):
        i, e = sources(caesar, "平文", rng)
        row(name, build(i, e, 0.4, random.Random(11), 0.25, short, grp), rng)
    print("\n=== N16 新しい語の出どころ（型 B, c 0.2, q 0.25）===")
    for mode in ("平文", "語順を崩した平文", "無意味な語彙"):
        i, e = sources(caesar, mode, random.Random(13))
        row(mode, build(i, e, 0.2, random.Random(11), 0.25, cap=20000), rng)
    n17(rng)


if __name__ == "__main__":
    main()

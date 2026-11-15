#!/usr/bin/env python3
"""nēvo による解析 第 5 巡: N14（行頭だけの語）・N12（全部を合わせたモデル）・N13（平文なし）。

    python3 voynich/nevo_round5.py <Caesar>
"""

from __future__ import annotations

import random
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
from nevo_round2 import distance_test, similar_words  # noqa: E402
from nevo_round3 import edges, interior  # noqa: E402
from nevo_round4 import mutate_at, pick_p10  # noqa: E402


def build(inner_src, edge_src, c, rng, where, q, cap=30000, width=37, lpp=25):
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
            w = pick_p10(inner, rng)
            if w is not None and rng.random() < 0.5:
                w = mutate_at(w, rng, where)
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


def plain_sources(caesar):
    half = len(caesar) // 2
    it = iter(["".join(syllable_code_e5(w)) for w in caesar[:half]])
    edge = ["".join(syllable_code_e5(w)) for w in caesar[half:]]
    random.Random(5).shuffle(edge)
    et = iter(edge)
    return (lambda: next(it, None)), (lambda: next(et, None))


def fresh_source(rng):
    nw = [1 / r for r in range(1, 7)]
    ow = [1 / r for r in range(1, 5)]

    def word():
        k = rng.choices([1, 2, 3, 4], [0.35, 0.40, 0.20, 0.05])[0]
        nuc = [rng.choices(range(6), nw)[0] for _ in range(k)]
        out, prev_g = "", 0
        for n in nuc:
            g = (n // 2 + prev_g) % 3
            out += scmp.ONSET[g * 4 + rng.choices(range(4), ow)[0]] + scmp.NUCLEUS[n]
            prev_g = n // 2
        if rng.random() < 0.5:
            out += rng.choice(scmp.CODA)
        return out

    return word, word


def share_first_only(pages):
    not_first = set(w for _, ls in pages for l in ls for w in l[1:])
    firsts = [l[0] for _, ls in pages for l in ls]
    return sum(w not in not_first for w in firsts) / len(firsts)


def row(name, pages, units, rng, perms=300, char_mode=True):
    """pages: [(頁, [[語(文字列)…]…])]。units: 語 → 単位のタプル。"""
    words = [w for _, ls in pages for l in ls for w in l]
    e = unit_entropy.entropies([list(units(w)) for w in words])
    v = null_generator.vocab_stats(words)
    k, n = scmp.judge(e, v)
    r = line_unit.l1(pages, lambda w: "".join(units(w)[-2:]), lambda w: "".join(units(w)[:2]), rng)
    print(f"-- {name}: 8 つの量 {k}/{n}（h1 {e['h1']:.2f} h2 {e['h2']:.2f} h2/h1 {e['h2/h1']:.2f} 語長 {e['語の長さ']:.2f}, "
          + ", ".join(f"{a} {b:.3f}" for a, b in v.items()) + f"）")
    print(f"   R {r['R']:.2f}, またぐ−基準 {r['行をまたぐ'] - r['無関係']:+.3f}, 行頭だけの語 {share_first_only(pages):.0%}")
    sc.CHAR_MODE = char_mode
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    sct.measure("   T1〜T4", dict(pages), units, rng)
    tp = {pg: [[tuple(units(w)) for w in l] for l in ls] for pg, ls in pages}
    distance_test("   全て 似た語", tp, similar_words, rng, perms=perms)
    distance_test("   端 似た語", edges(tp), similar_words, rng, perms=perms)
    distance_test("   内側 似た語", interior(tp), similar_words, rng, perms=perms)


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    print("=== 参照: ヴォイニッチ（ZL, 段落テキスト, 頁ごと）===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        pages = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        row(f"ヴォイニッチ {lang}", list(pages.items()), lambda w: tuple(ivtff.glyphs(w)), rng, char_mode=False)
    print("\n=== N14 行頭だけの語（平文, 最後以外, c 0.2）===")
    for q in (0.15, 0.25, 0.35):
        i, e = plain_sources(caesar)
        row(f"q = {q}", build(i, e, 0.2, random.Random(11), "最後以外", q), tuple, rng)
    print("\n=== N12 全部を合わせたモデル（平文, q 0.25）===")
    for where, label in (("最後以外", "型 B"), ("前半", "型 A")):
        for c in (0.2, 0.4):
            i, e = plain_sources(caesar)
            row(f"{label}（{where}）c = {c}", build(i, e, c, random.Random(11), where, 0.25), tuple, rng)
    print("\n=== N13 平文なし（音節の型だけ, q 0.25, 最後以外）===")
    for c in (0.6, 0.8):
        i, e = fresh_source(random.Random(3))
        row(f"c = {c}", build(i, e, c, random.Random(11), "最後以外", 0.25, cap=20000), tuple, rng)


if __name__ == "__main__":
    main()

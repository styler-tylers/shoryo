#!/usr/bin/env python3
"""nēvo による解析 第 3 巡: N6（行の端と内側）・N7（2 層のモデル）・N8（字形の区切り方）。

    python3 voynich/nevo_round3.py <Caesar> <Descartes> <Dante>
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import glyph_slots  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402
from e5_cipher import syllable_code_e5  # noqa: E402
from nevo_round2 import distance_test, mutate, same_words, similar_words  # noqa: E402
from nevo_tests import distances, latin_pages, split_alt, voynich_pages  # noqa: E402


def edges(pages):
    return {k: [[l[0], l[-1]] for l in ls if len(l) >= 3] for k, ls in pages.items()}


def interior(pages):
    return {k: [l[1:-1] for l in ls if len(l) >= 3] for k, ls in pages.items()}


def n6(name, pages, rng):
    for layer, f in (("端", edges), ("内側", interior)):
        P = f(pages)
        distance_test(f"{name} {layer} 似た語", P, similar_words, rng)
        distance_test(f"{name} {layer} 同じ語", P, same_words, rng)


# ---------------------------------------------------------------------------
# N7 2 層のモデル
# ---------------------------------------------------------------------------


def two_layer(plain, c, pool, rng, width=37, lpp=25):
    lines, cur, cur_len, it = [], [], 0, iter(plain)
    inner = []  # 各行の内側の語（写す元）

    def pick():
        if pool == "P3":
            cand = [w for l in inner[-3:] for w in l]
            return rng.choice(cand) if cand else None
        recent = inner[-10:]
        ws = [(1 / (len(recent) - i), l) for i, l in enumerate(recent) if l]
        if not ws:
            return None
        tot = sum(x for x, _ in ws)
        r = rng.random() * tot
        for x, l in ws:
            r -= x
            if r <= 0:
                return rng.choice(l)
        return rng.choice(ws[-1][1])

    def close(line):
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        if len(line) >= 2:
            line = [rng.choice("XYW") + line[0]] + line[1:-1] + [line[-1] + rng.choice("UV")]
        else:
            line = [rng.choice("XYW") + line[0] + rng.choice("UV")]
        lines.append(line)
        inner.append(line[1:-1])

    while True:
        w = None
        if rng.random() < c:
            w = pick()
            if w is not None and rng.random() < 0.5:
                w = mutate(w, rng)
        if w is None:
            try:
                w = "".join(syllable_code_e5(next(it)))
            except StopIteration:
                break
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > width:
            close(cur)
            cur, cur_len, add = [], 0, len(w)
        cur.append(w)
        cur_len += add
    if cur:
        close(cur)
    return [(f"p{i // lpp}", lines[i:i + lpp]) for i in range(0, len(lines), lpp)]


def n7(caesar, rng):
    print("\n=== N7 2 層のモデル ===")
    for c in (0.2, 0.4):
        for pool in ("P3", "P10"):
            pages = two_layer(caesar, c, pool, random.Random(11))
            words = [w for _, ls in pages for l in ls for w in l]
            e = unit_entropy.entropies([list(w) for w in words])
            v = null_generator.vocab_stats(words)
            k, n = scmp.judge(e, v)
            r = line_unit.l1(pages, lambda w: w[-2:], lambda w: w[:2], rng)
            not_first = set(w for _, ls in pages for l in ls for w in l[1:])
            firsts = [l[0] for _, ls in pages for l in ls]
            share = sum(w not in not_first for w in firsts) / len(firsts)
            print(f"-- c = {c}, {pool}: 8 つの量 {k}/{n}, R {r['R']:.2f}, またぐ−基準 {r['行をまたぐ'] - r['無関係']:+.3f}, "
                  f"行頭だけの語 {share:.0%}")
            sc.CHAR_MODE = True
            sc.glyph_tuple.cache_clear()
            sc.distance.cache_clear()
            sct.measure("   T1〜T4", dict(pages), lambda w: tuple(w), rng)
            tp = {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in pages}
            distance_test("   全て 似た語", tp, similar_words, rng, perms=300)
            distance_test("   全て 同じ語", tp, same_words, rng, perms=300)
            distance_test("   端 似た語", edges(tp), similar_words, rng, perms=300)
            distance_test("   内側 似た語", interior(tp), similar_words, rng, perms=300)


# ---------------------------------------------------------------------------
# N8 字形の区切り方
# ---------------------------------------------------------------------------

SPLIT = {"ch": ("c", "h"), "sh": ("s", "h"), "ckh": ("c", "k", "h"), "cth": ("c", "t", "h"),
         "cph": ("c", "p", "h"), "cfh": ("c", "f", "h")}


def split_word(w):
    out = []
    for g in w:
        out += SPLIT.get(g, (g,))
    return tuple(out)


def n8(lines, opts, lat, rng):
    print("\n=== N8 字形の区切り方（ch → c h など）===")
    P = {lang: voynich_pages(lines, opts, lang) for lang in ("A", "B")}
    S = {lang: {k: [[split_word(w) for w in l] for l in ls] for k, ls in P[lang].items()} for lang in P}
    caesar = [list(w) for w in unit_entropy.latin_words(lat[0])]
    ec = unit_entropy.entropies(caesar)
    print(f"参照 Caesar（文字）: h1 {ec['h1']:.2f} h2 {ec['h2']:.2f} h2/h1 {ec['h2/h1']:.2f}")
    for lang in ("A", "B"):
        for name, pages in (("元の区切り", P[lang]), ("分けた区切り", S[lang])):
            e = unit_entropy.entropies([list(w) for ls in pages.values() for l in ls for w in l])
            print(f"ヴォイニッチ {lang} {name}: 種類 {e['種類'] - 1} h1 {e['h1']:.2f} h2 {e['h2']:.2f} h2/h1 {e['h2/h1']:.2f}")
    G = {"k": "k", "t": "t", "p": "p", "f": "f"}
    for lang in ("A", "B"):
        wc = []
        for ln in lines:
            if ln.locus_class != "P" or ln.page.get("L") != lang:
                continue
            ws = ivtff.words(ln.raw, opts)
            for i, w in enumerate(ws):
                wc.append((list(split_word(tuple(ivtff.glyphs(w)))),
                           {"段落の 1 行目": ln.position == "@", "行の最初の語": i == 0, "語頭": None}))
        glyph_slots.slot_report(f"実験 6（分けた区切り）{lang}", wc, G.get, lambda g: g, rng)
    flat = lambda D: [l for ls in D.values() for l in ls]  # noqa: E731
    c1, c2, dn = (latin_pages(["".join(w) for w in unit_entropy.latin_words(p)][:40000]) for p in lat)
    print("N2 近景（分けた区切り, 5,000 語 × 10 回）:")
    for name, X, Y in (("A 対 B", flat(S["A"]), flat(S["B"])), ("A₁ 対 A₂", *split_alt(S["A"])),
                       ("Caesar 対 Descartes", flat(c1), flat(c2)), ("Caesar 対 Dante", flat(c1), flat(dn))):
        d = distances(X, Y, 5000, rng)
        print(f"  {name:<22} 近景 {d['近景 字形の 2 つ組']:.3f}")
    for lang in ("A", "B"):
        distance_test(f"N5 似た語（分けた区切り）{lang}", S[lang], similar_words, rng)


def main() -> None:
    lat = [Path(x) for x in sys.argv[1:4]]
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    print("=== N6 行の端と内側（ZL）===")
    for lang in ("A", "B"):
        n6(f"ヴォイニッチ {lang}", voynich_pages(lines, opts, lang), rng)
    caesar = ["".join(w) for w in unit_entropy.latin_words(lat[0])]
    n7(caesar, rng)
    n8(lines, opts, lat, rng)


if __name__ == "__main__":
    main()

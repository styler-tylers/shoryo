#!/usr/bin/env python3
"""nēvo による解析 第 4 巡: N9（端を直した 2 層のモデル）・N10（手本は話題か書いた順か）・N11（語末の変わりにくさ）。

    python3 voynich/nevo_round4.py <Caesar>
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
from nevo_round2 import CLASSES, distance_test, same_words, similar_words  # noqa: E402
from nevo_round3 import edges, interior  # noqa: E402


def mutate_at(w: str, rng, where: str) -> str:
    n = len(w)
    if where == "どこでも" or n == 1:
        i = rng.randrange(n)
    elif where == "最後以外":
        i = rng.randrange(n - 1)
    else:  # 前半
        i = rng.randrange(max(1, n // 2))
    cls = next(c for c in CLASSES if w[i] in c)
    return w[:i] + rng.choice([x for x in cls if x != w[i]]) + w[i + 1:]


def pick_p10(inner, rng):
    recent = inner[-10:]
    ws = [(1 / (len(recent) - i), l) for i, l in enumerate(recent) if l]
    if not ws:
        return None
    r = rng.random() * sum(x for x, _ in ws)
    for x, l in ws:
        r -= x
        if r <= 0:
            return rng.choice(l)
    return rng.choice(ws[-1][1])


def build(plain_inner, edge_words, c, rng, where="どこでも", two_layer=True, width=37, lpp=25):
    """two_layer: 端を平文の別の列から取り、写しに加えない。False なら N4 と同じ（端の区別なし）。"""
    lines, inner, cur, cur_len = [], [], [], 0
    it, et = iter(plain_inner), iter(edge_words)
    reserve = 0

    def close(line):
        k = rng.randrange(len(line))
        line = line[k:] + line[:k]
        if two_layer:
            try:
                a, b = next(et), next(et)
            except StopIteration:
                return False
            line = [a] + line + [b]
            inner.append(line[1:-1])
        else:
            inner.append(line)
        lines.append(line)
        return True

    if two_layer:
        reserve = 12  # 端の 2 語ぶんの幅をおおよそ空ける
    while True:
        w = None
        if rng.random() < c:
            w = pick_p10(inner, rng)
            if w is not None and rng.random() < 0.5:
                w = mutate_at(w, rng, where)
        if w is None:
            try:
                w = "".join(syllable_code_e5(next(it)))
            except StopIteration:
                break
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > width - reserve:
            if not close(cur):
                cur = []
                break
            cur, cur_len, add = [], 0, len(w)
        cur.append(w)
        cur_len += add
    if cur:
        close(cur)
    return [(f"p{i // lpp}", lines[i:i + lpp]) for i in range(0, len(lines), lpp)]


def report(name, pages, rng, perms=300, layers=True):
    words = [w for _, ls in pages for l in ls for w in l]
    e = unit_entropy.entropies([list(w) for w in words])
    v = null_generator.vocab_stats(words)
    k, n = scmp.judge(e, v)
    r = line_unit.l1(pages, lambda w: w[-2:], lambda w: w[:2], rng)
    not_first = set(w for _, ls in pages for l in ls for w in l[1:])
    firsts = [l[0] for _, ls in pages for l in ls]
    share = sum(w not in not_first for w in firsts) / len(firsts)
    print(f"-- {name}: 8 つの量 {k}/{n}, R {r['R']:.2f}, またぐ−基準 {r['行をまたぐ'] - r['無関係']:+.3f}, 行頭だけの語 {share:.0%}")
    sc.CHAR_MODE = True
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    sct.measure("   T1〜T4", dict(pages), lambda w: tuple(w), rng)
    tp = {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in pages}
    distance_test("   全て 似た語", tp, similar_words, rng, perms=perms)
    if layers:
        distance_test("   端 似た語", edges(tp), similar_words, rng, perms=perms)
        distance_test("   内側 似た語", interior(tp), similar_words, rng, perms=perms)


def n9(caesar, rng):
    print("=== N9 端を直した 2 層のモデル ===")
    half = len(caesar) // 2
    inner_plain = caesar[:half]
    edge = ["".join(syllable_code_e5(w)) for w in caesar[half:]]
    random.Random(5).shuffle(edge)
    for c in (0.2, 0.4):
        report(f"c = {c}", build(inner_plain, edge, c, random.Random(11)), rng)


def n11(caesar, rng):
    print("\n=== N11 写すときに変える位置（c 0.4, P10, 端の区別なし）===")
    for where in ("どこでも", "最後以外", "前半"):
        report(f"変える位置: {where}", build(caesar, [], 0.4, random.Random(11), where, two_layer=False), rng, layers=False)


# ---------------------------------------------------------------------------
# N10 話題か書いた順か
# ---------------------------------------------------------------------------


def n10(rng, perms=1000):
    print("\n=== N10 手本は話題か、書いた順の近さか（内側の語・似た語）===")
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        pages, sect = {}, {}
        for ln in lines:
            if ln.locus_class != "P" or ln.page.get("L") != lang:
                continue
            ws = [tuple(ivtff.glyphs(w)) for w in ivtff.words(ln.raw, opts)]
            if len(ws) >= 3:
                pages.setdefault(ln.page.name, []).append(ws[1:-1])
                sect[ln.page.name] = ln.page.get("I")
        order = list(pages)
        idx = {p: i for i, p in enumerate(order)}
        w1 = [similar_words(ls[i], ls[i + 1]) for ls in pages.values() for i in range(len(ls) - 1)]
        w10 = [similar_words(ls[i], ls[i + 10]) for ls in pages.values() for i in range(len(ls) - 10)]

        def page_sim(p, q, k=30):
            return statistics.mean(similar_words(rng.choice(pages[p]), rng.choice(pages[q])) for _ in range(k))

        same = [(p, q) for p in order for q in order if p < q and sect[p] == sect[q]]
        M = {(p, q): page_sim(p, q) for p, q in same}
        M.update({(q, p): v for (p, q), v in M.items()})
        diff = [similar_words(rng.choice(pages[p]), rng.choice(pages[q]))
                for p, q in ((rng.choice(order), rng.choice(order)) for _ in range(20000)) if sect[p] != sect[q]]

        def p1_pf(ix):
            by = {}
            for p in order:
                by.setdefault(sect[p], []).append(p)
            a, b = [], []
            for s, ps in by.items():
                ps = sorted(ps, key=lambda x: ix[x])
                for i, p in enumerate(ps):
                    for q in ps[i + 1:]:
                        d = abs(ix[p] - ix[q])
                        if d == 1:
                            a.append(M[(p, q)])
                        elif d >= 10:
                            b.append(M[(p, q)])
            return (statistics.mean(a) if a else float("nan")), (statistics.mean(b) if b else float("nan")), len(a), len(b)

        P1, PF, na, nb = p1_pf(idx)
        obs = P1 - PF
        ge = 0
        by = {}
        for p in order:
            by.setdefault(sect[p], []).append(p)
        for _ in range(perms):
            ix = {}
            for s, ps in by.items():
                pos = sorted(idx[p] for p in ps)
                sh = list(ps)
                rng.shuffle(sh)
                ix.update(dict(zip(sh, pos)))
            a, b, _, _ = p1_pf(ix)
            ge += (a - b) >= obs
        p = (ge + 1) / (perms + 1)
        print(f"  言語 {lang}: W1 {statistics.mean(w1):.3f}  W10 {statistics.mean(w10):.3f}  P1 {P1:.3f}（{na} 組の頁）  "
              f"PF {PF:.3f}（{nb}）  X {statistics.mean(diff):.3f}   P1 > PF の p = {p:.3g}{'  ← 有意' if p < 0.025 else ''}")


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    n9(caesar, rng)
    n10(rng)
    n11(caesar, rng)
    print("\n参照 ヴォイニッチの T1:")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    sc.CHAR_MODE = False
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    for lang in ("A", "B"):
        pages = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        sct.measure(f"ヴォイニッチ {lang}", pages, lambda w: tuple(ivtff.glyphs(w)), rng)


if __name__ == "__main__":
    main()

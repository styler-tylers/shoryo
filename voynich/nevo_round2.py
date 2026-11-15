#!/usr/bin/env python3
"""nēvo による解析 第 2 巡: N4（自己引用 ＋ 音節の表記のモデル）と N5（N3 の再現: 似た語・IT 転写）。

    python3 voynich/nevo_round2.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402
from e5_cipher import syllable_code_e5  # noqa: E402
from e6_rotation import rotate  # noqa: E402
from nevo_tests import latin_pages, voynich_pages  # noqa: E402

CLASSES = [scmp.ONSET, scmp.NUCLEUS, scmp.CODA]


def mutate(w: str, rng) -> str:
    i = rng.randrange(len(w))
    cls = next(c for c in CLASSES if w[i] in c)
    return w[:i] + rng.choice([x for x in cls if x != w[i]]) + w[i + 1:]


def self_citing(plain, c, rng, width=37, n_words=30000, lpp=25):
    n_words = min(n_words, len(plain))
    lines, cur, cur_len, placed, it = [], [], 0, 0, iter(plain)
    while placed < n_words:
        pool = [w for l in lines[-3:] for w in l]
        if pool and rng.random() < c:
            w = rng.choice(pool)
            if rng.random() < 0.5:
                w = mutate(w, rng)
        else:
            w = "".join(syllable_code_e5(next(it)))
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > width:
            lines.append(cur)
            cur, cur_len, add = [], 0, len(w)
        cur.append(w)
        cur_len += add
        placed += 1
    lines.append(cur)
    return [(f"p{i // lpp}", lines[i:i + lpp]) for i in range(0, len(lines), lpp)]


# ---------------------------------------------------------------------------
# 行どうしの近さ（同じ語・似た語）と、距離 d の効果の並べ替え検定
# ---------------------------------------------------------------------------


def ed1(a, b) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) > len(b):
        a, b = b, a
    for i in range(len(b)):
        if b[:i] + b[i + 1:] == a:
            return True
    return False


def same_words(u, l):
    a, b = set(u), set(l)
    return len(a & b) / len(a | b) if a | b else 0.0


def similar_words(u, l):
    if not u:
        return 0.0
    ls = set(l)
    return sum(any(ed1(w, v) for v in ls) for w in u) / len(u)


def distance_test(name, pages, sim, rng, perms=1000, ds=(1, 2, 3, 5, 10)):
    pages = {k: v for k, v in pages.items() if len(v) >= 11}
    keys = list(pages)
    base = []
    for _ in range(5000):
        p, q = rng.sample(keys, 2)
        base.append(sim(rng.choice(pages[p]), rng.choice(pages[q])))
    b = statistics.mean(base)
    mats = {k: [[sim(x, y) if i != j else 0.0 for j, y in enumerate(ls)] for i, x in enumerate(ls)] for k, ls in pages.items()}

    def mean_d(order, d):
        vals = [mats[k][o[i]][o[i + d]] for k, o in order.items() for i in range(len(o) - d)]
        return statistics.mean(vals)

    ident = {k: list(range(len(ls))) for k, ls in pages.items()}
    g = {d: mean_d(ident, d) / b for d in ds}
    obs = mean_d(ident, 1) - mean_d(ident, 10)
    ge = 0
    for _ in range(perms):
        order = {}
        for k, o in ident.items():
            x = list(o)
            rng.shuffle(x)
            order[k] = x
        ge += mean_d(order, 1) - mean_d(order, 10) >= obs
    p = (ge + 1) / (perms + 1)
    print(f"  {name:<34} 頁 {len(pages):>3}  基準 {b:.4f}  " + "  ".join(f"G({d}) {v:.2f}" for d, v in g.items())
          + f"  p = {p:.3g}{'  ← 有意' if p < 0.05 else ''}{'（補正後も）' if p < 0.0083 else ''}")
    return g, p


def n4(caesar, rng):
    print("=== N4 自己引用 ＋ 音節の表記 ＋ 行ごとの回転 ===")
    for c in (0, 0.2, 0.4):
        pages = rotate(self_citing(caesar, c, random.Random(11)), random.Random(7))
        words = [w for _, ls in pages for l in ls for w in l]
        e = unit_entropy.entropies([list(w) for w in words])
        v = null_generator.vocab_stats(words)
        k, n = scmp.judge(e, v)
        r = line_unit.l1(pages, lambda w: w[-2:], lambda w: w[:2], rng)
        print(f"-- c = {c}: 8 つの量 {k}/{n}（V2 {v['V2 1回だけ']:.3f}）, R {r['R']:.2f}, またぐ−基準 {r['行をまたぐ'] - r['無関係']:+.3f}")
        sc.CHAR_MODE = True
        sc.glyph_tuple.cache_clear()
        sc.distance.cache_clear()
        sct.measure("   T1〜T4", dict(pages), lambda w: tuple(w), rng)
        distance_test("   N3 同じ語", {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in pages}, same_words, rng)


def n5(caesar_words, rng):
    print("\n=== N5 N3 の再現 ===")
    for f in ("ZL3b-n.txt", "IT2a-n.txt"):
        args = corpus.make_parser("").parse_args(["--file", f])
        _, lines = corpus.load_lines(args)
        opts = corpus.word_options(args)
        for lang in ("A", "B"):
            pages = voynich_pages(lines, opts, lang)
            distance_test(f"{f[:2]} {lang} 同じ語", pages, same_words, rng)
            distance_test(f"{f[:2]} {lang} 似た語（1 字形違い）", pages, similar_words, rng)
    distance_test("参照 ラテン語 似た語（1 文字違い）", latin_pages(caesar_words), similar_words, rng)


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    n4(caesar, rng)
    n5(caesar[:30000], rng)


if __name__ == "__main__":
    main()

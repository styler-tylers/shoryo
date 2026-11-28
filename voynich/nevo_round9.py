#!/usr/bin/env python3
"""nēvo による解析 第 9 巡: N24（合わせていない量）・N25（言語 A・B を設定の違いで）。

    python3 voynich/nevo_round9.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import nevo_round6  # noqa: E402
import self_citation as sc  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402
from e5_cipher import syllable_code_e5  # noqa: E402
from nevo_round2 import CLASSES, ed1, similar_words  # noqa: E402
from nevo_round5 import share_first_only  # noqa: E402
from nevo_round8 import apply_rule  # noqa: E402

# ---------------------------------------------------------------------------
# 量
# ---------------------------------------------------------------------------


def skew(xs):
    m, s = statistics.mean(xs), statistics.pstdev(xs)
    return sum((x - m) ** 3 for x in xs) / len(xs) / s ** 3


def m_measures(lines_, last_of_block):
    """lines_: [[単位のタプル…]…]。last_of_block: 行がまとまりの最後か（m2 で除く）。"""
    lens = [len(w) for l in lines_ for w in l]
    m1 = (statistics.pstdev(lens) / statistics.mean(lens), skew(lens))
    ll = [sum(len(w) for w in l) + len(l) - 1 for l, last in zip(lines_, last_of_block) if not last and l]
    m2 = statistics.pstdev(ll) / statistics.mean(ll)
    first = [len(l[0]) for l in lines_ if len(l) >= 3]
    lastw = [len(l[-1]) for l in lines_ if len(l) >= 3]
    mid = [len(w) for l in lines_ if len(l) >= 3 for w in l[1:-1]]
    mm = statistics.mean(mid)
    m3 = (statistics.mean(first) / mm, statistics.mean(lastw) / mm)
    pairs = [(a, b) for l in lines_ for a, b in zip(l, l[1:])]
    m4 = (sum(a == b for a, b in pairs) / len(pairs), sum(ed1(a, b) for a, b in pairs) / len(pairs))
    return {"m1 CV": m1[0], "m1 歪度": m1[1], "m2 行長 CV": m2, "m3 最初/内側": m3[0], "m3 最後/内側": m3[1],
            "m4 同じ語": m4[0], "m4 1 単位違い": m4[1]}


def t1(pages_str, char_mode):
    sc.CHAR_MODE = char_mode
    sc.glyph_tuple.cache_clear()
    sc.distance.cache_clear()
    same, _ = word_families.pairs(pages_str)
    c = Counter(p for p, _, _ in same)
    n = max(1, len(same))
    return c["語頭"] / n, c["語中"] / n, c["語末"] / n


def adj_diff(lines_, rng, runs=20):
    inner = [l[1:-1] for l in lines_ if len(l) >= 4]
    f = lambda a, b: ("".join(a[-2:]), "".join(b[:2]))  # noqa: E731
    obs = line_unit.mi([f(a, b) for l in inner for a, b in zip(l, l[1:])])
    nulls = []
    for _ in range(runs):
        ps = []
        for l in inner:
            x = list(l)
            rng.shuffle(x)
            ps += [f(a, b) for a, b in zip(x, x[1:])]
        nulls.append(line_unit.mi(ps))
    return obs - statistics.mean(nulls)


def g1_g10(pages_t, rng):
    P = {k: [l[1:-1] for l in ls if len(l) >= 3] for k, ls in pages_t.items()}
    P = {k: v for k, v in P.items() if len(v) >= 11}
    keys = list(P)
    base = statistics.mean(similar_words(rng.choice(P[a]), rng.choice(P[b]))
                           for a, b in (rng.sample(keys, 2) for _ in range(3000)))
    d = lambda k: statistics.mean(similar_words(ls[i], ls[i + k]) for ls in P.values() for i in range(len(ls) - k))  # noqa: E731
    return d(1) / base, d(10) / base


def profile(pages_t, pages_str, char_mode, rng):
    words = [w for ls in pages_t.values() for l in ls for w in l]
    e = unit_entropy.entropies([list(w) for w in words])
    lines_ = [l for ls in pages_t.values() for l in ls]
    return {"h2": e["h2"], "T1": t1(pages_str, char_mode), "隣どうし": adj_diff(lines_, rng),
            "G": g1_g10(pages_t, rng), "行頭だけ": share_first_only(list(pages_str.items()))}


# ---------------------------------------------------------------------------
# モデル
# ---------------------------------------------------------------------------


def mutate_front(w, rng, in_group):
    i = rng.randrange(max(1, len(w) // 2))
    cls = next(c for c in CLASSES if w[i] in c)
    return w[:i] + rng.choice([x for x in cls if x != w[i]]) + w[i + 1:]


ORIG_MUTATE = nevo_round6.mutate


def model(caesar, c, beta, where, rng):
    nevo_round6.mutate = ORIG_MUTATE if where == "最後以外" else mutate_front
    i, e = nevo_round6.sources(caesar, "平文", rng)
    pages = nevo_round6.build(i, e, c, random.Random(11), 0.25, short=True)
    nevo_round6.mutate = ORIG_MUTATE
    return apply_rule(pages, beta, random.Random(17))


def voynich():
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    out = {}
    for lang in ("A", "B"):
        L = [ln for ln in lines if ln.page.get("L") == lang]
        pages_str = {}
        last = []
        for i, ln in enumerate(L):
            ws = ivtff.words(ln.raw, opts)
            if not ws:
                continue
            pages_str.setdefault(ln.page.name, []).append(ws)
            nxt = L[i + 1] if i + 1 < len(L) else None
            last.append("<$>" in ln.raw or nxt is None or nxt.page.name != ln.page.name or "<%>" in nxt.raw)
        pages_t = {k: [[tuple(ivtff.glyphs(w)) for w in l] for l in ls] for k, ls in pages_str.items()}
        out[lang] = (pages_t, pages_str, last)
    return out


def main() -> None:
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    rng = random.Random(2026)
    V = voynich()
    print("=== N24 合わせていない量 ===")
    rows = {}
    for lang in ("A", "B"):
        pt, _, last = V[lang]
        rows[f"ヴォイニッチ {lang}"] = m_measures([l for ls in pt.values() for l in ls], last)
    mp = model(caesar, 0.4, 0.5, "最後以外", rng)
    ml = [[tuple(w) for w in l] for _, ls in mp for l in ls]
    mlast = [i == len(ls) - 1 for _, ls in mp for i in range(len(ls))]
    rows["モデル β 0.5"] = m_measures(ml, mlast)
    raw = line_unit.wrap(["".join(syllable_code_e5(w)) for w in caesar], 37)
    rl = [[tuple(w) for w in l] for _, ls in raw for l in ls]
    rows["参照 E5 そのまま"] = m_measures(rl, [i == len(ls) - 1 for _, ls in raw for i in range(len(ls))])
    keys = list(rows["モデル β 0.5"])
    print(f"  {'':<16}" + "".join(f"{k:>14}" for k in keys))
    for name, r in rows.items():
        print(f"  {name:<16}" + "".join(f"{r[k]:>14.3f}" for k in keys))
    a, b, m = rows["ヴォイニッチ A"], rows["ヴォイニッチ B"], rows["モデル β 0.5"]
    for k in keys:
        lo, hi = min(a[k], b[k]), max(a[k], b[k])
        tol = max(hi - lo, 0.25 * abs((a[k] + b[k]) / 2))
        off = 0 if lo <= m[k] <= hi else min(abs(m[k] - lo), abs(m[k] - hi))
        print(f"  {k:<12} モデル {m[k]:.3f}  ヴォイニッチ {lo:.3f}〜{hi:.3f}  → {'外れ' if off > tol else '合う'}")

    print("\n=== N25 言語 A・B を設定の違いで ===")
    T = {}
    for lang in ("A", "B"):
        pt, ps, _ = V[lang]
        T[lang] = profile(pt, ps, False, rng)
        t = T[lang]
        print(f"  目標 {lang}: h2 {t['h2']:.2f} T1 {t['T1'][0]:.0%}/{t['T1'][1]:.0%}/{t['T1'][2]:.0%} 隣 {t['隣どうし']:+.3f} "
              f"G {t['G'][0]:.2f}/{t['G'][1]:.2f} 行頭だけ {t['行頭だけ']:.0%}")

    def dist(p, t):
        return (abs(p["h2"] - t["h2"]) / 0.15 + sum(abs(x - y) for x, y in zip(p["T1"], t["T1"])) / 0.24
                + abs(p["隣どうし"] - t["隣どうし"]) / 0.05 + sum(abs(x - y) for x, y in zip(p["G"], t["G"])) / 0.3
                + abs(p["行頭だけ"] - t["行頭だけ"]) / 0.08)

    res = []
    for where in ("最後以外", "前半"):
        for c in (0.3, 0.4, 0.5):
            for beta in (0.3, 0.5, 0.7):
                mp = model(caesar, c, beta, where, rng)
                pt = {pg: [[tuple(w) for w in l] for l in ls] for pg, ls in mp}
                ps = {pg: ls for pg, ls in mp}
                p = profile(pt, ps, True, rng)
                res.append(((where, c, beta), p))
                print(f"  {where} c {c} β {beta}: h2 {p['h2']:.2f} T1 {p['T1'][0]:.0%}/{p['T1'][1]:.0%}/{p['T1'][2]:.0%} "
                      f"隣 {p['隣どうし']:+.3f} G {p['G'][0]:.2f}/{p['G'][1]:.2f} 行頭だけ {p['行頭だけ']:.0%}  "
                      f"距離 A {dist(p, T['A']):.1f} B {dist(p, T['B']):.1f}")
    for lang in ("A", "B"):
        t = T[lang]
        (setting, p) = min(res, key=lambda x: dist(x[1], t))
        ok = {"h2": abs(p["h2"] - t["h2"]) <= 0.15, "T1": all(abs(x - y) <= 0.08 for x, y in zip(p["T1"], t["T1"])),
              "隣どうし": abs(p["隣どうし"] - t["隣どうし"]) <= 0.05,
              "G": all(abs(x - y) <= 0.3 for x, y in zip(p["G"], t["G"])), "行頭だけ": abs(p["行頭だけ"] - t["行頭だけ"]) <= 0.08}
        print(f"  {lang} に最も近い設定: {setting}  距離 {dist(p, t):.1f}  判定: "
              + ", ".join(f"{k} {'○' if v else '×'}" for k, v in ok.items()))


if __name__ == "__main__":
    main()

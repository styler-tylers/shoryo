#!/usr/bin/env python3
"""nēvo による解析 第 54 巡: N160（略しの設定を Caesar で決め Descartes で確かめる）・N161（ほかの量）・N162（略しの跡）。

    python3 voynich/nevo_round54.py <texts の場所>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import scripts_compare  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34, lastf  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import crossing, family  # noqa: E402
from nevo_round52 import REF, three  # noqa: E402
from nevo_round53 import equalize  # noqa: E402

TOLV = 0.15


def e4_of(path):
    return [tuple(scripts_compare.syllable_code_e4("".join(w))) for w in unit_entropy.latin_words(path)]


def clip(ws, K):
    return equalize(ws, "L2", random.Random(3), hi=K)[0]


def lines_of(ws):
    return [l for _, ls in line_unit.wrap(ws, 37) for l in ls]


def dist(h2, sk, sp, lang):
    h, k = REF[lang]
    return max(abs(h2 - h), abs(sk - k)) / TOLV if sp >= 0.65 else float("inf")


def js(p, q):
    keys = set(p) | set(q)
    np_, nq = sum(p.values()), sum(q.values())
    P = {k: p[k] / np_ for k in keys}
    Q = {k: q[k] / nq for k in keys}
    M = {k: (P[k] + Q[k]) / 2 for k in keys}
    kl = lambda A: sum(A[k] * math.log2(A[k] / M[k]) for k in keys if A[k])  # noqa: E731
    return (kl(P) + kl(Q)) / 2


def trace(name, ws, endf):
    n = len(ws)
    long9 = sum(len(w) >= 9 for w in ws) / n
    lo = Counter(endf(w) for w in ws if 4 <= len(w) <= 6)
    hi = Counter(endf(w) for w in ws if len(w) >= 7)
    print(f"  {name:<28} 9 記号以上 {long9:.1%}  語末の差（7 以上 対 4〜6）{js(hi, lo):.3f} ビット", flush=True)


def main(tdir):
    T = Path(tdir)
    V = voynich()
    cae, des = e4_of(T / "pg218.txt"), e4_of(T / "pg23306.txt")
    print("=== N160 設定を Caesar で選ぶ ===", flush=True)
    res = {}
    for K in (6, 7, 8):
        res[K] = three(f"E4・略し K={K}（Caesar）", lines_of(clip(cae, K)[:30000]))
    pick = {}
    for lang in ("A", "B"):
        d = {K: dist(*res[K], lang) for K in res}
        pick[lang] = min(d, key=d.get)
        print(f"  {lang}: 差（許容幅の何倍か）" + "  ".join(f"K={K} {v:.2f}" for K, v in d.items()) + f"  → 選ぶ K={pick[lang]}", flush=True)
    print("=== N160 Descartes で確かめる ===", flush=True)
    three("E4・そのまま（Descartes）", lines_of(des[:30000]))
    for K in sorted(set(pick.values())):
        r = three(f"E4・略し K={K}（Descartes）", lines_of(clip(des, K)[:30000]))
        for lang in ("A", "B"):
            if pick[lang] == K:
                print(f"    {lang} 向けの設定: 差 {dist(*r, lang):.2f}（1 以下なら 3 つとも範囲内）", flush=True)

    print("=== N161 ほかの量 ===", flush=True)
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）", flush=True)
        report("Caesar（ラテン語）", dict(line_unit.wrap([tuple(w) for w in words_any(T / 'pg218.txt')][:cap], 37)), ref, rng)
        report("E4・そのまま", dict(line_unit.wrap(cae[:cap], 37)), ref, rng)
        P = dict(line_unit.wrap(clip(cae, pick[lang])[:cap], 37))
        report(f"E4・略し K={pick[lang]}", P, ref, rng)
        kw = dict(c=0.4, mark=0.25) if lang == "A" else dict(c=0.6, mark=0.12, live=True)
        LG = LengthGrammar(pt)
        M = build34(LG, Compat(LG, pt), pt, random.Random(1), cap=cap, **kw)
        report("平文なしの最良のモデル", M, ref, rng)
        for name, pages in ((f"ヴォイニッチ {lang}", pt), (f"E4・略し K={pick[lang]}", P), ("平文なしのモデル", M)):
            ws = [w for ls in pages.values() for l in ls for w in l]
            f = family(ws)
            c, n = crossing(pages, random.Random(5))
            print(f"    {name:<22} 家族の場所 頭 {f[0]:.2f} 中 {f[1]:.2f} 末 {f[2]:.2f}  行の切れ目のつながり {c:+.3f}（{n} 組）", flush=True)

    print("=== N162 略しの跡 ===", flush=True)
    for lang in ("A", "B"):
        ws = [w for ls in V[lang][0].values() for l in ls for w in l]
        trace(f"ヴォイニッチ {lang}（語末の欄）", ws, lambda w: "".join(split(w)[2]))
        trace(f"ヴォイニッチ {lang}（最後の字形）", ws, lambda w: w[-1])
    trace("Caesar（最後の字）", [tuple(w) for w in words_any(T / "pg218.txt")], lambda w: w[-1])
    trace("E4・そのまま（最後の記号）", cae, lambda w: w[-1])
    for K in sorted(set(pick.values())):
        trace(f"E4・略し K={K}（最後の記号）", clip(cae, K), lambda w: w[-1])


if __name__ == "__main__":
    main(sys.argv[1])

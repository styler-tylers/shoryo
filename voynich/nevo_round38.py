#!/usr/bin/env python3
"""nēvo による解析 第 38 巡: N112（言語ごとの最良の組み合わせ）・N113（写しと前の語とのつながり）。

    python3 voynich/nevo_round38.py n112|n113 [A|B]
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round25 import score  # noqa: E402
from nevo_round34 import C_LANG, build34, lastf  # noqa: E402
from nevo_round35 import MARK  # noqa: E402
from nevo_round36 import gt_p, near  # noqa: E402
from nevo_round37 import NovelGrammar4  # noqa: E402


def scored(name, builder, ref, rng):
    runs = []
    for seed in (1, 2):
        P = builder(random.Random(seed))
        runs.append(with_strength(measure(P, lastf(P), rng), P))
    summarize(name, runs)
    for r in runs:
        for k, v in r.items():
            if isinstance(v, float) and v != v:
                r[k] = -9.0
    hit = score(name, runs, ref)
    m = lambda k: statistics.mean(r[k] for r in runs)  # noqa: E731
    print(f"  {name}: 隣 {m('隣'):.3f}  G1 {m('G1'):.2f}  またぐ {m('またぐ'):.3f}  V2 {m('V2'):.3f}  V3 {m('V3'):.2f}", flush=True)
    return hit


def novel(pt):
    p = gt_p(pt)
    probe = NovelGrammar4(pt, 1.0)
    r = random.Random(7)
    for _ in range(20000):
        probe.word(r)
    return NovelGrammar4(pt, min(1.0, p / (probe.made / probe.tried)))


def n112(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語、写し {c}）########", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        NG = novel(pt)
        NC = Compat(NG, pt)
        kw = dict(mark=0.25, t2=True, headfit=True) if lang == "A" else dict(mark=MARK["B"], live=True)
        scored("言語ごとの最良の組み合わせ", lambda r: build34(NG, NC, pt, r, c=c, cap=cap, **kw), ref, rng)


def share(pages, far):
    """隣り合う行（far=False）または同じ頁の 10 行以上先（far=True）で、(同じ語を共有する割合, 同じ語は無いが 1 字形違いがある割合)。前の行の語ごとに数える。"""
    same = nearc = n = 0
    for ls in pages.values():
        L = [l[1:-1] for l in ls if len(l) >= 3]
        for i, a in enumerate(L):
            js = [j for j in range(len(L)) if (abs(j - i) >= 10 if far else j == i + 1)]
            for j in js:
                bs = set(L[j])
                for w in a:
                    n += 1
                    if w in bs:
                        same += 1
                    elif any(near(w, x) for x in bs):
                        nearc += 1
    return same / n, nearc / n


def n113(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        a, b = share(pt, False), share(pt, True)
        print(f"  (1) ヴォイニッチ 隣の行: 同じ語 {a[0]:.3f}  1 字形違い {a[1]:.3f} ／ 10 行以上先: 同じ語 {b[0]:.3f}  1 字形違い {b[1]:.3f} ／ 比: 同じ語 {a[0] / b[0]:.2f}  1 字形違い {a[1] / b[1]:.2f}", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        print(f"  基準（ヴォイニッチ）: 隣 {ref['隣']:.3f}  G1 {ref['G1']:.2f}", flush=True)
        for c in (0.0, 0.2, 0.4, 0.6):
            scored(f"2 字形の表・写し {c}", lambda r, c=c: build34(LG, LC, pt, r, c=c, cap=cap, t2=True), ref, rng)
        c = C_LANG[lang]
        P = build34(LG, LC, pt, random.Random(1), c=c, cap=cap, t2=True, widepick=True)
        a, b = share(P, False), share(P, True)
        print(f"  広い写しのモデル 隣の行: 同じ語 {a[0]:.3f}  1 字形違い {a[1]:.3f} ／ 比: 同じ語 {a[0] / b[0]:.2f}  1 字形違い {a[1] / b[1]:.2f}", flush=True)
        scored(f"広い写し（写し {c}, 2 字形の表）", lambda r: build34(LG, LC, pt, r, c=c, cap=cap, t2=True, widepick=True), ref, rng)


if __name__ == "__main__":
    V = voynich()
    rng = random.Random(2026)
    langs = sys.argv[2:] or ["A", "B"]
    {"n112": n112, "n113": n113}[sys.argv[1]](V, rng, langs)

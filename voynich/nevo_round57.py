#!/usr/bin/env python3
"""nēvo による解析 第 57 巡: N169（段落の長さと語の長さ）・N170（続けた文章でほかの量）・N171（モデルの語尾の幅）。

    python3 voynich/nevo_round57.py
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import crossing, family  # noqa: E402
from nevo_round51 import space_guess  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo, perm_p, sk  # noqa: E402


def H(c):
    t = sum(c.values())
    return -sum(v / t * math.log2(v / t) for v in c.values() if v)


def paragraphs(V, lang, keep=lambda pg: True):
    pt, _, last = V[lang]
    out, cur, i = [], [], 0
    for pg, ls in pt.items():
        for l in ls:
            if keep(pg):
                cur.append(l)
            if last[i]:
                if cur:
                    out.append(cur)
                cur = []
            i += 1
    return out


def measures(pages):
    lines_ = [l for ls in pages.values() for l in ls]
    ws = [w for l in lines_ for w in l]
    return {"歪度": sk(lines_), "h2": unit_entropy.entropies([list(w) for w in ws])["h2"], "空白": space_guess(lines_),
            "語末H": H(Counter("".join(split(w)[2]) for w in ws)), "切れ目": crossing(pages, random.Random(5), runs=5)[0]}


def narrow(P, q, rng):
    ws = [w for ls in P.values() for l in ls for w in l]
    by = defaultdict(Counter)
    for w in ws:
        h, m, e = split(w)
        by[(h, m)][e] += 1
    top = {k: c.most_common(1)[0][0] for k, c in by.items()}
    out = {}
    for pg, ls in P.items():
        nl = []
        for l in ls:
            r = []
            for w in l:
                h, m, e = split(w)
                t = top[(h, m)]
                r.append((h + m + t) if e != t and rng.random() < q and (h + m + t) else w)
            nl.append(r)
        out[pg] = nl
    return out


def main():
    V = voynich()
    a = corpus.make_parser("").parse_args([])
    a.locus = "P"
    _, L = corpus.load_lines(a)
    ill = {ln.page.name: ln.page.get("I") for ln in L}
    rng = random.Random(2026)
    print("=== N169 段落の長さと語の長さ ===", flush=True)
    for lang, keep in (("A", lambda pg: True), ("B", lambda pg: ill[pg] != "T")):
        ps = paragraphs(V, lang, keep)
        short = [l for p in ps if len(p) <= 4 for l in p]
        long_ = [l for p in ps if len(p) >= 9 for l in p]
        o, base, p = perm_p(long_, short, rng)
        print(f"  言語 {lang}{'（図のある頁）' if lang == 'B' else ''}: 長い段落 {o:+.2f}（{sum(len(p_) >= 9 for p_ in ps)} 段落, {sum(map(len, long_))} 語）  "
              f"短い段落 {base:+.2f}（{sum(len(p_) <= 4 for p_ in ps)} 段落, {sum(map(len, short))} 語）  p {p:.3f}", flush=True)

    print("=== N170 続けた文章でほかの量 ===", flush=True)
    pt = V["B"][0]
    T = {pg: ls for pg, ls in pt.items() if ill[pg] == "T"}
    pics = [pg for pg in pt if ill[pg] != "T"]
    n = sum(len(l) for ls in T.values() for l in ls)
    obs = measures(T)
    samp = []
    r = random.Random(11)
    for _ in range(500):
        pick, c = {}, 0
        for pg in r.sample(pics, len(pics)):
            if c >= n:
                break
            pick[pg] = pt[pg]
            c += sum(map(len, pt[pg]))
        samp.append(measures(pick))
    for k, v in obs.items():
        xs = sorted(s_[k] for s_ in samp)
        lo, hi = xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]
        print(f"  {k:<4} 文字だけの頁 {v:+.3f}  図のある頁の組 {lo:+.3f}〜{hi:+.3f}  {'範囲の中' if lo <= v <= hi else '範囲の外'}", flush=True)

    print("=== N171 モデルの語尾の幅 ===", flush=True)
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        p_ = V[lang][0]
        vw = [w for ls in p_.values() for l in ls for w in l]
        cap = len(vw)
        ref = measure(p_, V[lang][2], random.Random(2026))
        LG = LengthGrammar(p_)
        M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=cap, **kw)
        print(f"  ---- 言語 {lang}: ヴォイニッチの語尾の幅 {endinfo(vw)[2]:.2f}", flush=True)
        for q in (0.0, 0.3, 0.6):
            P = M if q == 0 else narrow(M, q, random.Random(3))
            ws = [w for ls in P.values() for l in ls for w in l]
            f = family(ws)
            print(f"  q={q}: 語尾の幅 {endinfo(ws)[2]:.2f}  家族の場所 頭 {f[0]:.2f} 中 {f[1]:.2f} 末 {f[2]:.2f}", flush=True)
            three(f"  q={q}", [l for ls in P.values() for l in ls])
            report(f"q={q}", P, ref, random.Random(2026))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 58 巡: N172（文字だけの頁の行のつながり）・N173（語の種類を生む場所）。

    python3 voynich/nevo_round58.py <texts の場所> <タガログ語などの場所>
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round47 import crossing  # noqa: E402


def table(pages):
    cab, ca = defaultdict(Counter), Counter()
    for ls in pages.values():
        for l in ls:
            for x, y in zip(l, l[1:]):
                cab[x[-1]][y[0]] += 1
            for w in l:
                ca[w[0]] += 1
    return cab, ca


def carry(pages, tab, rng, runs=20):
    cab, ca = tab
    na = sum(ca.values())
    K = len(ca) + 1

    def g(a, b):
        row = cab.get(a, Counter())
        pb = (ca.get(b, 0) + 1) / (na + K)
        pba = (row.get(b, 0) + pb * 5) / (sum(row.values()) + 5)
        return math.log2(pba / pb)
    obs, nul = [], [[] for _ in range(runs)]
    for ls in pages.values():
        ls = [l for l in ls if l]
        for i in range(len(ls) - 1):
            obs.append(g(ls[i][-1][-1], ls[i + 1][0][0]))
            others = [k for k in range(len(ls)) if k != i + 1]
            for r in range(runs):
                nul[r].append(g(ls[i][-1][-1], ls[rng.choice(others)][0][0]))
    return statistics.mean(obs) - statistics.mean(statistics.mean(x) for x in nul)


def H(c):
    t = sum(c.values())
    return -sum(v / t * math.log2(v / t) for v in c.values() if v)


def chain(parts):
    """parts: [(a, b, c)] → (H(a), H(b|a), H(c|a,b)) の割合"""
    h1 = H(Counter(p[0] for p in parts))
    h12 = H(Counter(p[:2] for p in parts))
    h = H(Counter(parts))
    tot = h
    return h1 / tot, (h12 - h1) / tot, (h - h12) / tot, tot


def pos3(ws):
    return [(w[0], tuple(w[1:-1]), w[-1]) for w in ws if len(w) >= 3]


def main(tdir, pdir):
    T, P = Path(tdir), Path(pdir)
    V = voynich()
    a = corpus.make_parser("").parse_args([])
    a.locus = "P"
    _, L = corpus.load_lines(a)
    ill = {ln.page.name: ln.page.get("I") for ln in L}
    pt = V["B"][0]
    TP = {pg: ls for pg, ls in pt.items() if ill[pg] == "T"}
    pics = [pg for pg in pt if ill[pg] != "T"]
    PP = {pg: pt[pg] for pg in pics}
    tab = table(PP)
    print("=== N172 文字だけの頁の行のつながり ===", flush=True)
    n = sum(len(l) for ls in TP.values() for l in ls)
    oc = crossing(TP, random.Random(5), runs=20)[0]
    ok = carry(TP, tab, random.Random(5))
    r = random.Random(11)
    sc, sk_ = [], []
    for _ in range(200):
        pick, c = {}, 0
        for pg in r.sample(pics, len(pics)):
            if c >= n:
                break
            pick[pg] = pt[pg]
            c += sum(map(len, pt[pg]))
        sc.append(crossing(pick, random.Random(5), runs=20)[0])
        sk_.append(carry(pick, tab, random.Random(5)))
    for name, v, xs in (("(1) 行の切れ目のつながり", oc, sc), ("(2) 境目の規則の持ち越し", ok, sk_)):
        xs = sorted(xs)
        hi = xs[int(0.975 * len(xs)) - 1]
        print(f"  {name}  文字だけの頁 {v:+.4f}  図のある頁の組 中央 {statistics.median(xs):+.4f}・97.5% {hi:+.4f}  {'超える' if v > hi else '超えない'}"
              f"（組のうち文字だけの頁以上 {sum(x >= v for x in xs) / len(xs):.3f}）", flush=True)
    print(f"  (3) 図のある頁全体の持ち越し {carry(PP, tab, random.Random(5)):+.4f} ビット", flush=True)

    print("=== N173 語の種類を生む場所 ===", flush=True)
    rows = []
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        p_ = V[lang][0]
        vw = [w for ls in p_.values() for l in ls for w in l]
        LG = LengthGrammar(p_)
        M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=len(vw), **kw)
        mw = [w for ls in M.values() for l in ls for w in l]
        rows += [(f"ヴォイニッチ {lang}", vw, True), (f"モデル {lang}", mw, True)]
    w = lambda n_: [tuple(x) for x in words_any(P / f"pg{n_}.txt")]  # noqa: E731
    rows += [("タガログ語（13773）", w(13773)[:20000], False), ("セブアノ語（20820）", w(20820)[:20000], False),
             ("Caesar", [tuple(x) for x in words_any(T / "pg218.txt")][:20000], False)]
    for name, ws, slot in rows:
        f, m, l, tot = chain(pos3(ws))
        extra = ""
        if slot:
            sf, sm, sl, st = chain([split(x) for x in ws])
            extra = f"   欄で分けて: 語頭 {sf:.2f}  芯 {sm:.2f}  語末 {sl:.2f}（{st:.2f} ビット）"
        print(f"  {name:<18} 最初の字 {f:.2f}  中ほど {m:.2f}  最後の字 {l:.2f}（{tot:.2f} ビット）{extra}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])

#!/usr/bin/env python3
"""nēvo による解析 第 35 巡: N103（頁のまとまりが消えた原因）・N104（最良をまとめて確かめる）・N105（1 回だけの語と型の広さ）。

    python3 voynich/nevo_round35.py n103|n104|n105
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round25 import score  # noqa: E402
from nevo_round29 import build_fav  # noqa: E402
from nevo_round30 import ratio  # noqa: E402
from nevo_round34 import C_LANG, REF_SIM, build34, lastf  # noqa: E402

MARK = {"A": 0.25, "B": 0.12}


def scored(name, builder, ref, rng, sim=None):
    runs, sims = [], []
    for seed in (1, 2):
        P = builder(random.Random(seed))
        sims.append(ratio(P))
        runs.append(with_strength(measure(P, lastf(P), rng), P))
    summarize(name, runs)
    for r in runs:
        for k, v in r.items():
            if isinstance(v, float) and v != v:
                r[k] = -9.0
    hit = score(name, runs, ref)
    s = statistics.mean(sims)
    print(f"  {name}: まとまり {s:.2f}（{sims[0]:.2f}・{sims[1]:.2f}）" + (f"  基準 {sim:.2f} → {'入る' if abs(s - sim) <= 0.10 else '外れ'}" if sim else ""), flush=True)
    return hit


def n103(V, rng):
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ph = (0.5, 0.0)
        steps = [("S0 第 29 巡のモデル・30000 語", lambda r: build_fav(LG, LC, pt, r, 0.5)),
                 ("S1 同じ・ヴォイニッチの語の数", lambda r: build_fav(LG, LC, pt, r, 0.5, cap=cap)),
                 ("S2 位置で語を選ぶ（写し 0.4）", lambda r: build34(LG, LC, pt, r, c=0.4, cap=cap, phis=ph)),
                 ("S3 ＋頭の印 0.25", lambda r: build34(LG, LC, pt, r, c=0.4, cap=cap, phis=ph, mark=0.25))]
        if c != 0.4:
            steps.append((f"S4 ＋写し {c}", lambda r: build34(LG, LC, pt, r, c=c, cap=cap, phis=ph, mark=0.25)))
        steps.append(("S5 ＋位置の語の言い回し 0.3", lambda r: build34(LG, LC, pt, r, c=c, cap=cap, phis=ph, mark=0.25, mu2=0.3)))
        for name, f in steps:
            rs = [ratio(f(random.Random(seed))) for seed in (1, 2)]
            print(f"  {name}: まとまり {statistics.mean(rs):.2f}（{rs[0]:.2f}・{rs[1]:.2f}）", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        scored("S6 位置で選ぶときも好みの語から", lambda r: build34(LG, LC, pt, r, c=c, cap=cap, phis=ph, mark=MARK[lang], favpos=True), ref, rng, REF_SIM[lang])


def n104(V, rng):
    for lang in ("A", "B"):
        pt, last = V[lang][0], V[lang][2]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語、写し {c}、頭の印 {MARK[lang]}）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, last, rng), pt)
        scored("(1) 頭の印＋毎回型から作る・全体", lambda r: build34(LG, LC, pt, r, c=c, cap=cap, mark=MARK[lang], live=True), ref, rng)
        names = list(pt)
        lastp, i = {}, 0
        for k in names:
            lastp[k] = last[i:i + len(pt[k])]
            i += len(pt[k])
        half = {s: {k: pt[k] for j, k in enumerate(names) if j % 2 == s} for s in (0, 1)}
        ref0 = with_strength(measure(half[0], [x for k in half[0] for x in lastp[k]], rng), half[0])
        cap0 = sum(len(l) for ls in half[0].values() for l in ls)
        summarize("基準（偶数番目の頁）", [ref0])
        for cond, s in (("内", 0), ("外", 1)):
            src = half[s]
            G = LengthGrammar(src)
            C = Compat(G, src)
            scored(f"(2) {cond}（{'偶' if s == 0 else '奇'}数番目の頁から作る, {cap0} 語）",
                   lambda r: build34(G, C, src, r, c=c, cap=cap0, mark=MARK[lang], live=True), ref0, rng)


def v2(words):
    c = Counter(words)
    return sum(1 for k in c.values() if k == 1) / len(c)


class NovelGrammar(LengthGrammar):
    """確率 p で、語の芯を、まだ見えていない芯（芯の種類から数えた字形の 2 つ並びの鎖で作る）に替える。"""

    def __init__(self, pages_t, p):
        super().__init__(pages_t)
        self.p = p
        self.known = {m for d in self.mh.values() for m in d}
        self.chain = defaultdict(Counter)
        for m in self.known:
            for a, b in zip(("^",) + m, m + ("$",)):
                self.chain[a][b] += 1
        self.tried = self.made = 0

    def _core(self, rng):
        out, x = [], "^"
        while len(out) < 12:
            k, v = zip(*self.chain[x].items())
            x = rng.choices(k, v)[0]
            if x == "$":
                break
            out.append(x)
        return tuple(out)

    def word(self, rng):
        w = super().word(rng)
        if rng.random() >= self.p:
            return w
        self.tried += 1
        h, m, e = split(w)
        if len(m) < 2:
            return w
        for _ in range(200):
            m2 = self._core(rng)
            if len(m2) == len(m) and m2[-1] == m[-1] and m2 not in self.known and split(h + m2 + e) == (h, m2, e):
                self.made += 1
                return h + m2 + e
        return w


def n105(V, rng):
    for lang in ("A", "B"):
        pt = V[lang][0]
        words = [w for ls in pt.values() for l in ls for w in l]
        cap = len(words)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        LG = LengthGrammar(pt)
        pairs = Counter((split(w)[0], split(w)[1]) for w in words)
        p = sum(1 for k in pairs.values() if k == 1) / cap
        NG = NovelGrammar(pt, p)
        r = random.Random(7)
        m = lambda f: statistics.mean(f() for _ in range(5))  # noqa: E731
        print(f"  (1) 1 回だけの語の割合: ヴォイニッチ {v2(words):.3f}  引き直し {m(lambda: v2(r.choices(words, k=cap))):.3f}  "
              f"型から独立に {m(lambda: v2([LG.word(r) for _ in range(cap)])):.3f}", flush=True)
        vn = m(lambda: v2([NG.word(r) for _ in range(cap)]))
        print(f"  (2) 新しい芯の割合 p {p:.3f}（1 回だけの（頭, 芯）{int(p * cap)} 組）  実際に替わった割合 {NG.made / max(1, NG.tried) * p:.3f}  "
              f"型＋新しい芯から独立に {vn:.3f}", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        LC = Compat(LG, pt)
        scored("(3) 土台＋位置（もとの型）", lambda rr: build34(LG, LC, pt, rr, c=c, cap=cap), ref, rng)
        NC = Compat(NG, pt)
        scored("(3) 土台＋位置（型＋新しい芯）", lambda rr: build34(NG, NC, pt, rr, c=c, cap=cap), ref, rng)


if __name__ == "__main__":
    V = voynich()
    rng = random.Random(2026)
    {"n103": n103, "n104": n104, "n105": n105}[sys.argv[1]](V, rng)

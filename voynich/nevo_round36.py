#!/usr/bin/env python3
"""nēvo による解析 第 36 巡: N106（全部を 1 つに）・N107（まだ見えていない芯を見積もりどおりに）・N108（隣どうしのつながりの原因）。

    python3 voynich/nevo_round36.py n106|n107|n108 [A|B]
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import null_generator  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round25 import score  # noqa: E402
from nevo_round30 import ratio  # noqa: E402
from nevo_round34 import C_LANG, REF_SIM, build34, lastf, sim_ret  # noqa: E402
from nevo_round35 import MARK, NovelGrammar, v2  # noqa: E402


def scored(name, builder, ref, rng, lang=None):
    runs, sims = [], []
    for seed in (1, 2):
        P = builder(random.Random(seed))
        sims.append(sim_ret(P) if lang else (ratio(P), float("nan")))
        runs.append(with_strength(measure(P, lastf(P), rng), P))
    summarize(name, runs)
    for r in runs:
        for k, v in r.items():
            if isinstance(v, float) and v != v:
                r[k] = -9.0
    hit = score(name, runs, ref)
    print(f"  {name}: V2 {statistics.mean(r['V2'] for r in runs):.3f}  V3 {statistics.mean(r['V3'] for r in runs):.2f}  "
          f"隣 {statistics.mean(r['隣'] for r in runs):.3f}  境目%語 {statistics.mean(r['境目%語'] for r in runs):.2f}  "
          f"またぐ {statistics.mean(r['またぐ'] for r in runs):.3f}", flush=True)
    s = statistics.mean(x for x, _ in sims)
    print(f"  {name}: まとまり {s:.2f}（{sims[0][0]:.2f}・{sims[1][0]:.2f}）", flush=True)
    if lang:
        ok1 = abs(s - REF_SIM[lang]) <= 0.10
        rets = [y for _, y in sims if y == y]
        ret = statistics.mean(rets) if rets else float("nan")
        if lang == "A":
            ok2 = ret == ret and abs(ret - 0.71) <= 0.15
            print(f"  {name}: 芯を保つ置き換えで残る {ret:.0%}  24 の量で {hit + ok1 + ok2}/24（まとまり {'入る' if ok1 else '外れ'}・残る割合 {'入る' if ok2 else '外れ'}）", flush=True)
        else:
            print(f"  {name}: 23 の量で {hit + ok1}/23（まとまり {'入る' if ok1 else '外れ'}）", flush=True)
    return hit


def gt_p(pt):
    words = [w for ls in pt.values() for l in ls for w in l]
    pairs = Counter((split(w)[0], split(w)[1]) for w in words)
    return sum(1 for k in pairs.values() if k == 1) / len(words)


def n106(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        NG = NovelGrammar(pt, gt_p(pt))
        NC = Compat(NG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        b = lambda phi, rho: (lambda r: build34(NG, NC, pt, r, c=c, cap=cap, mark=MARK[lang], live=True, phis=(phi, 0.0), rho=rho, favpos=True))  # noqa: E731
        grid = []
        for phi in (0.2, 0.3, 0.5):
            for rho in (0.05, 0.1):
                P = b(phi, rho)(random.Random(1))
                s = ratio(P)
                v3 = null_generator.vocab_stats(["".join(w) for ls in P.values() for l in ls for w in l])["V3 Zipf"]
                grid.append((phi, rho, s, v3))
                print(f"  φ {phi} ρ {rho}: まとまり {s:.2f}  V3 {v3:.2f}（基準 {ref['V3']:.2f}）", flush=True)
        inside = [g for g in grid if abs(g[2] - REF_SIM[lang]) <= 0.10]
        best = min(inside, key=lambda g: abs(g[3] - ref["V3"])) if inside else min(grid, key=lambda g: abs(g[2] - REF_SIM[lang]))
        print(f"  選んだ設定: φ {best[0]} ρ {best[1]}（許容の幅に入った設定 {len(inside)}）", flush=True)
        scored(f"全部を 1 つに（φ {best[0]} ρ {best[1]}）", b(best[0], best[1]), ref, rng, lang)


class NovelGrammar2(NovelGrammar):
    """N107: 条件をゆるめた新しい芯（長さ ±1、最後の字形は語末の欄と一緒に見えたことがあれば可）。"""

    def word(self, rng):
        w = LengthGrammar.word(self, rng)
        if rng.random() >= self.p:
            return w
        self.tried += 1
        h, m, e = split(w)
        if not m:
            return w
        for _ in range(200):
            m2 = self._core(rng)
            if m2 and abs(len(m2) - len(m)) <= 1 and m2 not in self.known and self.em[m2[-1]][e] > 0 and split(h + m2 + e) == (h, m2, e):
                self.made += 1
                return h + m2 + e
        return w


def n107(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        words = [w for ls in pt.values() for l in ls for w in l]
        cap = len(words)
        c = C_LANG[lang]
        p = gt_p(pt)
        print(f"######## 言語 {lang}（{cap} 語、見積もり p {p:.3f}）########", flush=True)
        r = random.Random(7)
        probe = NovelGrammar2(pt, 1.0)
        for _ in range(20000):
            probe.word(r)
        succ = probe.made / probe.tried
        att = min(1.0, p / succ)
        NG = NovelGrammar2(pt, att)
        vn = statistics.mean(v2([NG.word(r) for _ in range(cap)]) for _ in range(5))
        print(f"  成功の割合 {succ:.3f}  試す割合 {att:.3f}  実際に替わった割合 {NG.made / (5 * cap):.3f}", flush=True)
        print(f"  (1) 1 回だけの語の割合: ヴォイニッチ {v2(words):.3f}  型＋新しい芯（ゆるめた条件）から独立に {vn:.3f}", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        NC = Compat(NG, pt)
        scored("(2) 土台＋位置（型＋新しい芯, 見積もりどおり）", lambda rr: build34(NG, NC, pt, rr, c=c, cap=cap), ref, rng)


def adj(pairs_of, lines_, rng, f, runs=20):
    inner = [l[1:-1] for l in lines_ if len(l) >= 4]
    obs = line_unit.mi([f(a, b) for l in inner for a, b in pairs_of(l)])
    nulls = []
    for _ in range(runs):
        ps = []
        for l in inner:
            x = list(l)
            rng.shuffle(x)
            ps += [f(a, b) for a, b in pairs_of(x)]
        nulls.append(line_unit.mi(ps))
    return obs - statistics.mean(nulls)


def near(a, b):
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    s, t = (a, b) if len(a) < len(b) else (b, a)
    return any(t[:i] + t[i + 1:] == s for i in range(len(t)))


def n108(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語、写し {c}）########", flush=True)
        lines_ = [l for ls in pt.values() for l in ls]
        g2 = lambda a, b: ("".join(a[-2:]), "".join(b[:2]))  # noqa: E731
        ww = lambda a, b: (a, b)  # noqa: E731
        n_all = sum(len(l) - 3 for l in lines_ if len(l) >= 4)
        for name, keep in (("全ての組", lambda a, b: True), ("同じ語の並びを除く", lambda a, b: a != b), ("1 字形違いの組も除く", lambda a, b: not near(a, b))):
            po = lambda l, keep=keep: [(a, b) for a, b in zip(l, l[1:]) if keep(a, b)]  # noqa: E731
            n = sum(len(po(l[1:-1])) for l in lines_ if len(l) >= 4)
            print(f"  (1) ヴォイニッチ・{name}: 組 {n}（{n / n_all:.1%}）  隣どうし {adj(po, lines_, rng, g2):+.3f}  語×語 {adj(po, lines_, rng, ww):+.3f}", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        b = lambda **kw: (lambda r: build34(LG, LC, pt, r, c=c, cap=cap, **kw))  # noqa: E731
        for name, kw in (("基準", {}), ("(a) 回さない", dict(rot=False)), ("(b) 写した語を替えない", dict(mut=0.0)), ("(c) γ 4", dict(gamma=4.0)),
                         ("(d) 2 字形の表", dict(t2=True)), ("(e) 2 字形の表＋頭を付け替えない", dict(t2=True, headmut=False))):
            scored(name, b(**kw), ref, rng)


if __name__ == "__main__":
    V = voynich()
    rng = random.Random(2026)
    langs = sys.argv[2:] or ["A", "B"]
    {"n106": n106, "n107": n107, "n108": n108}[sys.argv[1]](V, rng, langs)

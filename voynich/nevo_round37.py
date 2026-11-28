#!/usr/bin/env python3
"""nēvo による解析 第 37 巡: N109（写した語の頭を前の語に合わせる）・N110（好みの語と語の回数の傾き）・N111（新しい芯の作り方）。

    python3 voynich/nevo_round37.py n109|n110|n111 [A|B]
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import null_generator  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round16 import with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round30 import ratio  # noqa: E402
from nevo_round34 import C_LANG, REF_SIM, build34  # noqa: E402
from nevo_round35 import MARK, NovelGrammar, v2  # noqa: E402
from nevo_round36 import NovelGrammar2, adj, gt_p, scored  # noqa: E402


def n109(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語、写し {c}）########", flush=True)
        lines_ = [l for ls in pt.values() for l in ls]
        po = lambda l: list(zip(l, l[1:]))  # noqa: E731
        core1 = lambda b: (split(b)[1] or split(b)[2] or ("-",))[0]  # noqa: E731
        for name, f in (("後ろの語の最初の字形", lambda a, b: (a[-1], b[0])), ("後ろの語の頭の欄", lambda a, b: (a[-1], split(b)[0])),
                        ("後ろの語の芯の最初の字形", lambda a, b: (a[-1], core1(b))),
                        ("頭の欄＋芯の最初の字形", lambda a, b: (a[-1], (split(b)[0], core1(b))))):
            print(f"  (1) ヴォイニッチ: 前の語の最後の字形 × {name}: {adj(po, lines_, rng, f):+.3f}", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        b = lambda **kw: (lambda r: build34(LG, LC, pt, r, c=c, cap=cap, **kw))  # noqa: E731
        for name, kw in (("基準", {}), ("(f) 頭を選び直す", dict(headfit=True)), ("(g) 頭を選び直す＋2 字形の表", dict(headfit=True, t2=True))):
            scored(name, b(**kw), ref, rng)


def shares(words):
    c = Counter(words[:10000])
    v = [k for _, k in c.most_common(100)]
    return sum(v[:10]) / 10000, sum(v[10:50]) / 10000, sum(v[50:]) / 10000


def n110(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        words = [w for ls in pt.values() for l in ls for w in l]
        cap = len(words)
        c = C_LANG[lang]
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        b = lambda phi, fc: (lambda r: build34(LG, LC, pt, r, c=c, cap=cap, mark=MARK[lang], phis=(phi, 0.0), favpos=True, favcontent=fc))  # noqa: E731
        fl = lambda P: [w for ls in P.values() for l in ls for w in l]  # noqa: E731
        sh = lambda t: "上位 10 語 {:.1%}  11〜50 語 {:.1%}  51〜100 語 {:.1%}".format(*t)  # noqa: E731
        print(f"  (1) ヴォイニッチ: {sh(shares(words))}", flush=True)
        for name, f in (("好みなし", b(0.0, False)), ("S6（φ 0.5）", b(0.5, False))):
            print(f"  (1) {name}: {sh(shares(fl(f(random.Random(1)))))}", flush=True)
        grid = []
        for phi in (0.5, 0.7, 0.9):
            P = b(phi, True)(random.Random(1))
            s = ratio(P)
            v3 = null_generator.vocab_stats(["".join(w) for w in fl(P)])["V3 Zipf"]
            grid.append((phi, s, v3))
            print(f"  (2) 上位の語は替えない φ {phi}: まとまり {s:.2f}  V3 {v3:.2f}（基準 {ref['V3']:.2f}）  {sh(shares(fl(P)))}", flush=True)
        inside = [g for g in grid if abs(g[1] - REF_SIM[lang]) <= 0.10]
        best = min(inside, key=lambda g: abs(g[2] - ref["V3"])) if inside else min(grid, key=lambda g: abs(g[1] - REF_SIM[lang]))
        print(f"  選んだ設定: φ {best[0]}（許容の幅に入った設定 {len(inside)}）", flush=True)
        scored(f"上位の語は替えない（φ {best[0]}）", b(best[0], True), ref, rng, lang)


class NovelGrammar3(NovelGrammar2):
    """N111 (a): 字形の 3 つ並びの鎖で新しい芯を作る。"""

    def __init__(self, pages_t, p):
        super().__init__(pages_t, p)
        self.tri = defaultdict(Counter)
        for m in self.known:
            seq = ("^", "^") + m + ("$",)
            for a, b, x in zip(seq, seq[1:], seq[2:]):
                self.tri[(a, b)][x] += 1

    def _core(self, rng):
        out, ctx = [], ("^", "^")
        while len(out) < 12:
            k, v = zip(*self.tri[ctx].items())
            x = rng.choices(k, v)[0]
            if x == "$":
                break
            out.append(x)
            ctx = (ctx[1], x)
        return tuple(out)


class NovelGrammar4(NovelGrammar):
    """N111 (b): 既にある芯の 1 字形だけを替える。"""

    def word(self, rng):
        w = LengthGrammar.word(self, rng)
        if rng.random() >= self.p:
            return w
        self.tried += 1
        h, m, e = split(w)
        if not m:
            return w
        for _ in range(50):
            i = rng.randrange(len(m))
            a = m[i - 1] if i else "^"
            z = m[i + 1] if i + 1 < len(m) else "$"
            cands = [g for g in self.chain[a] if g != m[i] and g != "$" and self.chain[g][z]]
            if not cands:
                continue
            g = rng.choices(cands, [self.chain[a][x] for x in cands])[0]
            m2 = m[:i] + (g,) + m[i + 1:]
            if m2 not in self.known and self.em[m2[-1]][e] > 0 and split(h + m2 + e) == (h, m2, e):
                self.made += 1
                return h + m2 + e
        return w


def n111(V, rng, langs):
    for lang in langs:
        pt = V[lang][0]
        words = [w for ls in pt.values() for l in ls for w in l]
        cap = len(words)
        c = C_LANG[lang]
        p = gt_p(pt)
        h2 = lambda ws: unit_entropy.entropies([list(w) for w in ws])["h2"]  # noqa: E731
        print(f"######## 言語 {lang}（{cap} 語、見積もり p {p:.3f}）########", flush=True)
        r = random.Random(7)
        LG = LengthGrammar(pt)
        print(f"  (1) ヴォイニッチ: 1 回だけの語 {v2(words):.3f}  h2 {h2(words):.3f}", flush=True)
        ws = [LG.word(r) for _ in range(cap)]
        print(f"  (1) もとの型: 1 回だけの語 {v2(ws):.3f}  h2 {h2(ws):.3f}", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        for name, cls in (("2 つ並びの鎖（N107）", NovelGrammar2), ("(a) 3 つ並びの鎖", NovelGrammar3), ("(b) 1 字形だけ替える", NovelGrammar4)):
            probe = cls(pt, 1.0)
            for _ in range(20000):
                probe.word(r)
            succ = probe.made / probe.tried
            NG = cls(pt, min(1.0, p / succ))
            ws = [NG.word(r) for _ in range(cap)]
            print(f"  (1) {name}: 成功の割合 {succ:.3f}  実際に替わった割合 {NG.made / cap:.3f}  1 回だけの語 {v2(ws):.3f}  h2 {h2(ws):.3f}", flush=True)
            if cls is not NovelGrammar2:
                NC = Compat(NG, pt)
                scored(f"(2) 土台＋位置・{name}", lambda rr: build34(NG, NC, pt, rr, c=c, cap=cap), ref, rng)


if __name__ == "__main__":
    V = voynich()
    rng = random.Random(2026)
    langs = sys.argv[2:] or ["A", "B"]
    {"n109": n109, "n110": n110, "n111": n111}[sys.argv[1]](V, rng, langs)

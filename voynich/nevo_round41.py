#!/usr/bin/env python3
"""nēvo による解析 第 41 巡: N121（語の順番に固有の 1 つ飛び）・N122（隣り合う語のつながりの足りない所）・
N123（少し替えて写すの中身）・N124（芯で綴じの中の並びを推定する）。

    python3 voynich/reproduce.py fetch     # 先に比べる文章を取ってくる
    python3 voynich/nevo_round41.py check|n121|n122|n123|n124
"""

from __future__ import annotations

import itertools
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import reorder  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round40 import coded_lines, excess, natural, top_k  # noqa: E402

TEXTS = Path(__file__).resolve().parent / "data" / "texts"
C_LANG = {"A": 0.4, "B": 0.6}
KW = {"A": dict(mark=0.25), "B": dict(mark=0.12, live=True)}


# ---------------------------------------------------------------- N121
def order_skip(lines, K, rng, S=50, runs=20):
    """順番に固有の余り ＝ E(実際) − E(行の中でかき混ぜ) の平均。z ＝ ÷ その標準偏差。"""
    e0 = excess(lines, K, rng, runs=runs)[2]
    es = [excess([rng.sample(l, len(l)) for l in lines], K, rng, runs=runs)[2] for _ in range(S)]
    m, sd = statistics.mean(es), statistics.pstdev(es)
    return e0 - m, (e0 - m) / sd if sd > 0 else float("nan"), e0, m


def synthetic(rng, skip=0.0, K=20, topics=5, n=2500, L=8):
    T = [[[rng.random() ** 4 for _ in range(K)] for _ in range(K)] for _ in range(topics)]
    lines = []
    for _ in range(n):
        t = T[rng.randrange(topics)]
        x = rng.randrange(K)
        l = []
        for i in range(L):
            x = rng.choices(range(K), t[x])[0]
            if i >= 2 and rng.random() < skip:
                x = l[i - 2]
            l.append(x)
        lines.append(l)
    return lines


def check():
    rng = random.Random(7)
    for name, sk, ok in (("(a) 話題ごとの鎖（1 つ飛びは鎖だけ）", 0.0, lambda z: abs(z) < 2),
                         ("(b) ＋ 2 つ前の語を 2 割写す", 0.2, lambda z: z > 5)):
        for rep in (1, 2):
            v, z, e0, m = order_skip(synthetic(random.Random(rep), sk), 20, rng)
            print(f"  {name} 試し {rep}: E(実際) {e0:+.4f}  E(かき混ぜ) {m:+.4f}  順番に固有 {v:+.4f}  z {z:+.1f}  → {'通る' if ok(z) else '通らない'}", flush=True)


def groups_for(lang, V):
    pt = V[lang][0]
    cap = sum(len(l) for ls in pt.values() for l in ls)
    LG = LengthGrammar(pt)
    LC = Compat(LG, pt)
    g = {"平文あり": [], "平文なし": []}
    for name, ws in natural(TEXTS, TEXTS, cap).items():
        g["平文あり"].append((name, dict(line_unit.wrap(ws, 37))))
    caesar = ["".join(w) for w in natural(TEXTS, TEXTS, 30000)["Caesar（ラテン語）"]]
    _, _, coded = matched_source(caesar, LG, random.Random(1))
    g["平文あり"].append(("符号表だけ（Caesar）", dict(line_unit.wrap(coded[:cap], 37))))
    it = iter(coded)
    src = lambda: next(it, None)  # noqa: E731
    g["平文あり"].append(("平文ありのモデル", build12(src, src, LG, LC, random.Random(11), c=0.4, beta=0.0, compat=True, wfun=gram_prob(LG), cap=cap)))
    for seed in (1, 2):
        g["平文なし"].append((f"最良のモデル 種 {seed}", build34(LG, LC, pt, random.Random(seed), c=C_LANG[lang], cap=cap, **KW[lang])))
    return pt, g


def n121():
    V = voynich()
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt, g = groups_for(lang, V)
        print(f"######## 言語 {lang} ########", flush=True)
        vals = {}
        for grp, ps in g.items():
            vals[grp] = []
            for name, P in ps:
                words = [w for ls in P.values() for l in ls for w in l]
                inner, K = coded_lines(P, top_k(words, 30))
                v, z, e0, m = order_skip(inner, K, rng)
                vals[grp].append(z)
                print(f"  {grp}・{name:<24} E(実際) {e0:+.4f}  E(かき混ぜ) {m:+.4f}  順番に固有 {v:+.4f}  z {z:+.1f}", flush=True)
        words = [w for ls in pt.values() for l in ls for w in l]
        inner, K = coded_lines(pt, top_k(words, 30))
        v, z, e0, m = order_skip(inner, K, rng)
        print(f"  ヴォイニッチ {lang:<28} E(実際) {e0:+.4f}  E(かき混ぜ) {m:+.4f}  順番に固有 {v:+.4f}  z {z:+.1f}", flush=True)
        a, b = vals["平文あり"], vals["平文なし"]
        gap = max(min(a) - max(b), min(b) - max(a))
        spread = max(max(a) - min(a), max(b) - min(b))
        print(f"  → z: 平文あり {min(a):+.1f}〜{max(a):+.1f}  平文なし {min(b):+.1f}〜{max(b):+.1f}  {'分かれた' if gap > 0 and gap > spread else '分かれない'}", flush=True)


# ---------------------------------------------------------------- N122
def cell_contrib(lines, rng, shuf=5):
    f = lambda a, b: ("".join(a[-2:]), "".join(b[:2]))  # noqa: E731
    inner = [l[1:-1] for l in lines if len(l) >= 4]

    def contrib(pairs):
        n = len(pairs)
        cxy = Counter(pairs)
        cx, cy = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
        return {k: c / n * math.log2(c * n / (cx[k[0]] * cy[k[1]])) for k, c in cxy.items()}

    obs = contrib([f(a, b) for l in inner for a, b in zip(l, l[1:])])
    base = defaultdict(float)
    for _ in range(shuf):
        ps = []
        for l in inner:
            x = rng.sample(l, len(l))
            ps += [f(a, b) for a, b in zip(x, x[1:])]
        for k, v in contrib(ps).items():
            base[k] += v / shuf
    keys = set(obs) | set(base)
    return {k: obs.get(k, 0.0) - base.get(k, 0.0) for k in keys}


def n122():
    V = voynich()
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        lines_ = [l for ls in pt.values() for l in ls]
        cv = cell_contrib(lines_, rng)
        cms = []
        for seed in (1, 2):
            P = build34(LG, LC, pt, random.Random(seed), c=C_LANG[lang], cap=cap, **KW[lang])
            cms.append(cell_contrib([l for ls in P.values() for l in ls], rng))
        keys = set(cv) | set(cms[0]) | set(cms[1])
        cm = {k: (cms[0].get(k, 0) + cms[1].get(k, 0)) / 2 for k in keys}
        d = {k: cv.get(k, 0) - cm[k] for k in keys}
        pos = sum(x for x in d.values() if x > 0)
        print(f"######## 言語 {lang}: 隣どうし ヴォイニッチ {sum(cv.values()):.3f}  モデル {sum(cm.values()):.3f}  差 {sum(d.values()):+.3f}（正の差の合計 {pos:.3f}）########", flush=True)
        top = sorted(d.items(), key=lambda kv: -kv[1])[:15]
        acc = 0.0
        for i, ((x, y), v) in enumerate(top, 1):
            acc += v
            print(f"  {i:>2}. -{x} → {y}-  ヴォイニッチ {cv.get((x, y), 0):+.4f}  モデル {cm[(x, y)]:+.4f}  差 {v:+.4f}  累積 {acc / pos:.0%}", flush=True)
        for label, idx in (("前の語の最後の 1 字形", 0), ("後ろの語の最初の 1 字形", 1)):
            agg = defaultdict(float)
            for (x, y), v in d.items():
                agg[(x, y)[idx][-1] if idx == 0 else (x, y)[idx][0]] += v
            print(f"  {label}ごと: " + "  ".join(f"{k} {v:+.3f}" for k, v in sorted(agg.items(), key=lambda kv: -kv[1])[:8]), flush=True)
        # 確かめ: 寄与の和 ＝ 結び付き − かき混ぜ
        print(f"  （確かめ: 寄与の和 {sum(cv.values()):.4f}）", flush=True)


# ---------------------------------------------------------------- N123
def edit_kind(a, b):
    """1 字形違いの a → b の種類（欄 × 置き換え／足す・削る）。"""
    ha, ma, ea = split(a)
    hb, mb, eb = split(b)
    op = "置き換え" if len(a) == len(b) else "足す・削る"
    if ha != hb and ma == mb and ea == eb:
        return f"語頭の欄・{op}"
    if ea != eb and ha == hb and ma == mb:
        return f"語末の欄・{op}"
    if ma != mb and ha == hb and ea == eb:
        return f"芯・{op}"
    return f"欄の境目が動く・{op}"


def near1(a, b):
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, t = (a, b) if len(a) < len(b) else (b, a)
    return any(t[:i] + t[i + 1:] == s for i in range(len(t)))


def edits(P, far):
    cnt, n = Counter(), 0
    for ls in P.values():
        L = [l[1:-1] for l in ls if len(l) >= 3]
        for i in range(len(L)):
            js = [j for j in range(len(L)) if abs(j - i) >= 10] if far else ([i - 1] if i else [])
            for j in js:
                for w in L[i]:
                    n += 1
                    if w in L[j]:
                        continue
                    ks = {edit_kind(x, w) for x in L[j] if near1(x, w)}
                    for k in ks:
                        cnt[k] += 1 / len(ks)
    return cnt, n


def n123():
    V = voynich()
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        texts = [(f"ヴォイニッチ {lang}", pt)] + [(f"最良のモデル 種 {s}", build34(LG, LC, pt, random.Random(s), c=C_LANG[lang], cap=cap, **KW[lang])) for s in (1, 2)]
        print(f"######## 言語 {lang} ########", flush=True)
        for name, P in texts:
            (ca, na), (cf, nf) = edits(P, False), edits(P, True)
            kinds = sorted(set(ca) | set(cf), key=lambda k: -ca[k])
            print(f"  {name}: 隣の行で 1 字形違いがある割合 {sum(ca.values()) / na:.3f}（離れた行 {sum(cf.values()) / nf:.3f}）", flush=True)
            for k in kinds:
                ra, rf = ca[k] / na, cf[k] / nf
                print(f"     {k:<14} 隣 {ra:.4f}  離れた {rf:.4f}  増え方 {ra / rf if rf else float('nan'):.2f}", flush=True)


# ---------------------------------------------------------------- N124
def n124():
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    core = lambda w: "".join(split(tuple(ivtff.glyphs(w)))[1]) or "·"  # noqa: E731
    for q in "ABCDEFGMT":
        L = [ln for ln in lines if ln.page.get("Q") == q]
        sheets, skipped = reorder.build_sheets(L, opts)
        n = len(sheets)
        if n < 3 or n > 8:
            print(f"=== クワイア {q}: 二つ折り {n} 枚（対象外）", flush=True)
            continue
        out = {}
        for feat in ("語", "芯"):
            if feat == "芯":
                for sh in sheets:
                    sh.page_words = {p: Counter({core(w): k for w, k in c.items()}) for p, c in sh.page_words.items()} if not hasattr(sh, "_c") else sh.page_words
                    sh._c = True
            trans = reorder.transition_matrix(sheets, "tfidf")
            scored = sorted(((reorder.sequence_score(p, trans), p) for p in itertools.permutations(range(n))), reverse=True)
            cur = reorder.sequence_score(list(range(n)), trans)
            rank = 1 + sum(1 for sc, _ in scored if sc > cur + 1e-12)
            out[feat] = (scored[0][1], rank, len(scored))
        keys = [sh.key for sh in sheets]
        fmt = lambda o: ", ".join(keys[i] for i in o)  # noqa: E731
        same = out["語"][0] == out["芯"][0]
        print(f"=== クワイア {q}（{n} 枚, {out['語'][2]} 通り）: 語の 1 位 {fmt(out['語'][0])} ／ 芯の 1 位 {fmt(out['芯'][0])}  {'同じ' if same else '違う'}  "
              f"（現在の並びの順位 語 {out['語'][1]}・芯 {out['芯'][1]}）", flush=True)


if __name__ == "__main__":
    {"check": check, "n121": n121, "n122": n122, "n123": n123, "n124": n124}[sys.argv[1]]()

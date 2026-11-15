#!/usr/bin/env python3
"""書き手（ZL の $H）ごとの文章の違い（第 9 回）。

notes/2026-11-15 ヴォイニッチ手稿 書き手ごとの違い.md の事前の記録のとおり。
頁ごとの文体の特徴（語頭・語末の字形の分布、語の長さ、よく出る語 30 語の頻度）を標準化し、
1 頁ずつ抜いて、残りの頁の重心に最も近い書き手を当てる。

    python3 voynich/scribes.py
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402


def load(locus: str | None = "P"):
    args = corpus.make_parser("").parse_args([])
    args.locus = locus
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    words: dict[str, list[str]] = defaultdict(list)
    meta = {}
    for ln in lines:
        meta.setdefault(ln.page.name, ln.page)
        words[ln.page.name] += ivtff.words(ln.raw, opts)
    return words, meta


class Features:
    """特徴の定義（語頭・語末の字形、よく出る語）は、基準にする頁の集まりから決める。"""

    def __init__(self, pages: list[list[str]], top_words: int = 30, top_glyphs: int = 12):
        init, fin, wc = Counter(), Counter(), Counter()
        for ws in pages:
            for w in ws:
                g = ivtff.glyphs(w)
                if g:
                    init[g[0]] += 1
                    fin[g[-1]] += 1
                wc[w] += 1
        self.init = [g for g, _ in init.most_common(top_glyphs)]
        self.fin = [g for g, _ in fin.most_common(top_glyphs)]
        self.words = [w for w, _ in wc.most_common(top_words)]

    def vector(self, ws: list[str]) -> list[float]:
        n = max(1, len(ws))
        gs = [ivtff.glyphs(w) for w in ws]
        init = Counter(g[0] for g in gs if g)
        fin = Counter(g[-1] for g in gs if g)
        wc = Counter(ws)
        return ([init[g] / n for g in self.init] + [fin[g] / n for g in self.fin]
                + [sum(len(g) for g in gs) / n] + [wc[w] / n for w in self.words])


def standardize(vecs: list[list[float]]) -> list[list[float]]:
    m = len(vecs[0])
    mu = [sum(v[j] for v in vecs) / len(vecs) for j in range(m)]
    sd = [math.sqrt(sum((v[j] - mu[j]) ** 2 for v in vecs) / len(vecs)) or 1.0 for j in range(m)]
    return [[(v[j] - mu[j]) / sd[j] for j in range(m)] for v in vecs]


def loo_balanced_accuracy(vecs, labels) -> float:
    """1 頁ずつ抜いて、残りの頁の各ラベルの重心に最も近いラベルを当てる。ラベルごとの正答率の平均。"""
    hit, tot = Counter(), Counter()
    for i, v in enumerate(vecs):
        cent = defaultdict(list)
        for j, (u, l) in enumerate(zip(vecs, labels)):
            if j != i:
                cent[l].append(u)
        best, bd = None, float("inf")
        for l, us in cent.items():
            c = [sum(x) / len(us) for x in zip(*us)]
            d = sum((a - b) ** 2 for a, b in zip(v, c))
            if d < bd:
                best, bd = l, d
        tot[labels[i]] += 1
        hit[labels[i]] += best == labels[i]
    return sum(hit[l] / tot[l] for l in tot) / len(tot)


def perm_test(vecs, labels, trials: int, rng) -> tuple[float, float]:
    obs = loo_balanced_accuracy(vecs, labels)
    ge = 0
    for _ in range(trials):
        sh = labels[:]
        rng.shuffle(sh)
        ge += loo_balanced_accuracy(vecs, sh) >= obs
    return obs, (ge + 1) / (trials + 1)


def centroid(vs):
    return [sum(x) / len(vs) for x in zip(*vs)]


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main() -> None:
    rng = random.Random(2026)
    words, meta = load("P")
    hb = sorted(p for p, m in meta.items() if m.get("I") == "H" and m.get("L") == "B" and words.get(p))
    feat = Features([words[p] for p in hb])
    X = standardize([feat.vector(words[p]) for p in hb])
    H = [meta[p].get("H") for p in hb]
    Q = [meta[p].get("Q") for p in hb]
    print(f"言語 B の植物の頁: {len(hb)} 頁 書き手 {dict(Counter(H))}\n")

    acc, p = perm_test(X, H, 5000, rng)
    print(f"W1 書き手 2・3・5 を当てる: 当たる割合（書き手ごとの平均）{acc:.2f}（偶然なら約 0.33）、p = {p:.4f}")
    idx = [i for i, h in enumerate(H) if h in ("2", "5")]
    acc_b, p_b = perm_test([X[i] for i in idx], [H[i] for i in idx], 5000, rng)
    print(f"W1b 書き手 2 と 5 だけ（{len(idx)} 頁）: {acc_b:.2f}（偶然なら約 0.50）、p = {p_b:.4f}")
    idx = [i for i in range(len(hb)) if Q[i] == "F"]
    acc_c, p_c = perm_test([X[i] for i in idx], [H[i] for i in idx], 2000, rng)
    print(f"W1c クワイア F の中だけ（{len(idx)} 頁, 書き手 {dict(Counter(H[i] for i in idx))}）: {acc_c:.2f}、p = {p_c:.3f}（記述）")
    idx = [i for i, h in enumerate(H) if h == "2"]
    acc_q, p_q = perm_test([X[i] for i in idx], [Q[i] for i in idx], 2000, rng)
    print(f"W2 対照: 書き手 2 の頁（{len(idx)} 頁）でクワイア {dict(Counter(Q[i] for i in idx))} を当てる: "
          f"{acc_q:.2f}（偶然なら約 0.25）、p = {p_q:.3f}（記述）\n")

    # W3・W4: 言語をまたぐ比較。特徴は全体（段落テキスト）で決める
    words_all, meta_all = load(None)
    allp = [p for p in words_all if words_all[p]]
    feat2 = Features([words_all[p] for p in allp])
    Xa = dict(zip(allp, standardize([feat2.vector(words_all[p]) for p in allp])))

    def grp(cond):
        return [Xa[p] for p in allp if cond(meta_all[p])]

    c1A = centroid(grp(lambda m: m.get("H") == "1" and m.get("L") == "A"))
    cB = centroid(grp(lambda m: m.get("H") in ("2", "3") and m.get("L") == "B"))
    c3B = centroid(grp(lambda m: m.get("H") == "3" and m.get("L") == "B"))
    h4 = [p for p in allp if meta_all[p].get("H") == "4"]
    print(f"W3 書き手 4（{len(h4)} 頁, 全てのテキスト）の重心までの距離: 言語 A（書き手 1）"
          f"{dist(centroid([Xa[p] for p in h4]), c1A):.2f}、言語 B（書き手 2・3）{dist(centroid([Xa[p] for p in h4]), cB):.2f}")
    nearer = Counter("A" if dist(Xa[p], c1A) < dist(Xa[p], cB) else "B" for p in h4)
    print(f"   頁ごとに近い方: {dict(nearer)}")
    h3a = [p for p in allp if meta_all[p].get("H") == "3" and meta_all[p].get("L") == "A"]
    for p in h3a:
        print(f"W4 書き手 3 の言語 A の頁 {p}: 書き手 1 の A まで {dist(Xa[p], c1A):.2f}、書き手 3 の B まで {dist(Xa[p], c3B):.2f}")


if __name__ == "__main__":
    main()

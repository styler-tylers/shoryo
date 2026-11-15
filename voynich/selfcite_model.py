#!/usr/bin/env python3
"""自己引用の手順で人工のテキストを作り、ヴォイニッチ言語 A と同じ量を測って比べる（第 8 回）。

モデル（Timm & Schinner の手順を単純化したもの。原典と同じではない）:
  - 頁・行・語数の形はヴォイニッチ言語 A の段落テキストと同じ
  - 各語は、確率 p_new で語彙から頻度に比例して新しく選ぶ。残りは「写し」:
    元の語を、確率 p_above で上の行（1 行上 60%, 2 行上 25%, 3 行上 15%）から、相対位置が近いほど
    選ばれやすく（重み exp(-|差|/σ)）、それ以外は同じ行の前の語から選ぶ。
    頁の 1 行目は前の頁の最後の行を「上の行」とする。
    選んだ語は確率 p_mut で、字形 1 つ違いの語彙の語（頻度に比例）に変える

測る量（self_citation.py と同じ関数）:
  S1 検証 1「どちらか」の倍率 / S2 検証 1「同じ語」の割合（合わせる量）
  P1 検証 3（行頭・行末を除く）の実際 ÷ 入れ替え / P2 検証 2 の k=1 倍率 ÷ k=8 倍率（予測する量）

    python3 voynich/selfcite_model.py                 # 格子の全 72 通り
    python3 voynich/selfcite_model.py --quick         # 動作確認（2 通り）
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import self_citation as sc  # noqa: E402

NOTES = Path(__file__).resolve().parent / "notes"
DEPTH = [(1, 0.60), (2, 0.25), (3, 0.15)]
GRID = {"p_new": [0.3, 0.5, 0.7, 0.85], "p_above": [0.5, 0.8], "sigma": [0.1, 0.3, 1.0],
        "p_mut": [0.5, 0.8, 1.0]}


def voynich_pages(language: str = "A") -> dict[str, list[list[str]]]:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    return sc.page_lines([ln for ln in lines if ln.page.get("L") == language], opts)


class Lexicon:
    def __init__(self, pages):
        self.freq = Counter(w for ls in pages.values() for l in ls for w in l)
        self.words = list(self.freq)
        self.weights = [self.freq[w] for w in self.words]
        self._nb: dict[str, tuple[list[str], list[int]]] = {}
        # 字形 1 つ違いの近傍を、長さの近い語の中から探す
        self.by_len = defaultdict(list)
        for w in self.words:
            self.by_len[len(sc.glyph_tuple(w))].append(w)

    def draw(self, rng) -> str:
        return rng.choices(self.words, self.weights)[0]

    def neighbours(self, w: str):
        if w not in self._nb:
            n = len(sc.glyph_tuple(w))
            cand = [v for L in (n - 1, n, n + 1) for v in self.by_len.get(L, []) if v != w and sc.distance(w, v) == 1]
            self._nb[w] = (cand, [self.freq[v] for v in cand])
        return self._nb[w]

    def mutate(self, w: str, rng) -> str:
        cand, wt = self.neighbours(w)
        return rng.choices(cand, wt)[0] if cand else w


def generate(shape: dict[str, list[int]], lex: Lexicon, p_new, p_above, sigma, p_mut, rng):
    out: dict[str, list[list[str]]] = {}
    prev_page_last: list[list[str]] = []
    for page, lens in shape.items():
        lines: list[list[str]] = []
        for li, n in enumerate(lens):
            line: list[str] = []
            for wi in range(n):
                above_pool = (prev_page_last + lines)  # 上の行の候補（新しいほど後ろ）
                if rng.random() < p_new or (not line and not above_pool):
                    line.append(lex.draw(rng))
                    continue
                use_above = above_pool and (rng.random() < p_above or not line)
                if use_above:
                    ks = [k for k, _ in DEPTH if k <= len(above_pool)]
                    k = rng.choices(ks, [p for kk, p in DEPTH if kk in ks])[0]
                    src = above_pool[-k]
                    x = wi / (n - 1) if n > 1 else 0.5
                    pos = [(j / (len(src) - 1) if len(src) > 1 else 0.5) for j in range(len(src))]
                    wts = [math.exp(-abs(x - q) / sigma) for q in pos]
                    w = rng.choices(src, wts)[0]
                else:
                    w = rng.choice(line)
                if rng.random() < p_mut:
                    w = lex.mutate(w, rng)
                line.append(w)
            lines.append(line)
        out[page] = lines
        prev_page_last = lines[-1:]
    return out


def measure(pages, rng, null_runs=4, trials=200) -> dict[str, float]:
    def own(page, li):
        return pages[page][li], pages[page][li - 1]

    e, n, t = sc.copy_rates(pages, own)
    ne = nn = nt = 0
    for _ in range(null_runs):
        a, b, c = sc.copy_rates(pages, sc.null_source(pages, rng))
        ne, nn, nt = ne + a, nn + b, nt + c
    s1 = ((e + n) / t) / ((ne + nn) / nt)
    s2 = e / t
    obs, null, p, npairs = sc.vertical_alignment(pages, rng, trials, inner=True)
    rows = sc.decay(pages, 8, rng, max(1, null_runs // 2))
    r1 = rows[0][1] / rows[0][2]
    r8 = rows[-1][1] / rows[-1][2]
    return {"S1": s1, "S2": s2, "P1": obs / null, "P1_p": p, "P2": r1 / r8, "k1": r1, "k8": r8}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="自己引用の生成モデルとの比較")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=NOTES / "selfcite_model_grid.csv")
    args = ap.parse_args(argv)
    rng = random.Random(1)
    real = voynich_pages("A")
    shape = {p: [len(l) for l in ls] for p, ls in real.items()}
    lex = Lexicon(real)
    v = measure(real, rng)
    print(f"ヴォイニッチ言語 A（{len(real)} 頁, {sum(map(sum, shape.values()))} 語）: "
          + ", ".join(f"{k} {x:.3f}" for k, x in v.items()))
    combos = list(itertools.product(*GRID.values()))
    if args.quick:
        combos = combos[:2]
    rows = []
    for c in combos:
        prm = dict(zip(GRID, c))
        g = generate(shape, lex, rng=random.Random(1), **prm)
        m = measure(g, rng)
        fit = abs(m["S1"] - v["S1"]) <= 0.05 and abs(m["S2"] - v["S2"]) <= 0.2 * v["S2"]
        pred = abs(m["P1"] - v["P1"]) <= 0.02 and abs(m["P2"] - v["P2"]) <= 0.10
        rows.append({**prm, **{k: round(x, 4) for k, x in m.items()}, "合う": int(fit), "予測も当たる": int(fit and pred)})
        print(f"{prm}  " + ", ".join(f"{k} {x:.3f}" for k, x in m.items())
              + ("  ← 合う" if fit else "") + ("・予測も当たる" if fit and pred else ""), flush=True)
    if not args.quick:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n結果: {args.out}")
        fits = [r for r in rows if r["合う"]]
        print(f"合うパラメータ: {len(fits)} 通り、予測も当たる: {sum(r['予測も当たる'] for r in rows)} 通り")
        print(f"ヴォイニッチ: S1 {v['S1']:.3f}, S2 {v['S2']:.3f}, P1 {v['P1']:.3f}, P2 {v['P2']:.3f}")
        for r in fits:
            print(f"  {r['p_new']}, {r['p_above']}, {r['sigma']}, {r['p_mut']}: "
                  f"S1 {r['S1']}, S2 {r['S2']}, P1 {r['P1']}, P2 {r['P2']}")


if __name__ == "__main__":
    main()

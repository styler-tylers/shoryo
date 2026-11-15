#!/usr/bin/env python3
"""行末の daiin・dar の前の語（第 15 回 第 4 段階）と、行頭の y（第 5 段階）。

    python3 voynich/function_words3.py <カエサルのテキスト pg218.txt>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import function_words2 as fw2  # noqa: E402
import ivtff  # noqa: E402
import unit_entropy  # noqa: E402
import word_families  # noqa: E402
import word_grammar  # noqa: E402


def end_of(w: str) -> str:
    return word_grammar.parse(w)[2]


def prev_kl_rank(tokens, end_fn, targets, top=100):
    rev = tokens[::-1]
    return fw2.next_kl_rank(rev, end_fn, targets, top)


def js(p: Counter, q: Counter) -> float:
    keys = set(p) | set(q)
    n, m = sum(p.values()), sum(q.values())
    P = {k: p[k] / n for k in keys}
    Q = {k: q[k] / m for k in keys}
    M = {k: (P[k] + Q[k]) / 2 for k in keys}

    def kl(a):
        return sum(a[k] * math.log2(a[k] / M[k]) for k in keys if a[k] > 0)
    return math.sqrt((kl(P) + kl(Q)) / 2)


def head2(w: str) -> str:
    return "".join(ivtff.glyphs(w)[:2])


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    # 第 4 段階（言語 A）
    A = [(ln, ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == "A"]
    A = [(ln, ws) for ln, ws in A if ws]
    print("=== 第 4 段階: 行末の daiin・dar の前の語（言語 A）===")
    fin, mid = Counter(), Counter()
    fin_words = Counter()
    for _, ws in A:
        for i in range(1, len(ws)):
            if ws[i] in ("daiin", "dar"):
                if i == len(ws) - 1:
                    fin[end_of(ws[i - 1])] += 1
                    fin_words[ws[i - 1]] += 1
                else:
                    mid[end_of(ws[i - 1])] += 1
    keys = sorted(set(fin) | set(mid))
    g, df = word_families.g_test([[fin[k] for k in keys], [mid[k] for k in keys]])[0], len(keys) - 1
    # 自由度が 2 でないので、p はカイ二乗分布の上側確率を級数で求める
    from math import exp, lgamma, log

    def chi2_sf(x, k):
        # 正則化不完全ガンマ関数 Q(k/2, x/2) を級数で
        a, xx = k / 2, x / 2
        s, term, n = 0.0, 1.0 / a, 0
        while term > 1e-12 and n < 1000:
            s += term
            n += 1
            term *= xx / (a + n)
        return max(0.0, 1 - exp(-xx + a * log(xx) - lgamma(a)) * s) if xx > 0 else 1.0

    print(f"E1 直前の語の語末: 行末の daiin/dar {sum(fin.values())} 回、行の中ほど {sum(mid.values())} 回、"
          f"G = {g:.1f}（自由度 {df}）、p = {chi2_sf(g, df):.3g}")
    print("   行末: " + ", ".join(f"{k} {fin[k] / sum(fin.values()):.0%}" for k in sorted(keys, key=lambda k: -fin[k])[:6]))
    print("   中ほど: " + ", ".join(f"{k} {mid[k] / sum(mid.values()):.0%}" for k in sorted(keys, key=lambda k: -mid[k])[:6]))
    toks = [w for _, ws in A for w in ws]
    res, n = prev_kl_rank(toks, end_of, ["daiin", "dar"])
    print("E2 前の語の語末の偏り（上位 100 語中の順位）: " + ", ".join(f"{t} {v:.2f} ビット（{r}/{n} 位）" for t, (v, r) in res.items()))
    if len(sys.argv) > 1:
        lat = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
        res, n = prev_kl_rank(lat, lambda w: w[-2:], ["est", "sunt", "erat"])
        print("   参照 ラテン語: " + ", ".join(f"{t} {v:.2f}（{r}/{n} 位）" for t, (v, r) in res.items()))
    print("E3 行末の daiin/dar の直前に多い語: " + ", ".join(f"{w}({c})" for w, c in fin_words.most_common(10)))

    # 第 5 段階（言語 B）
    print("\n=== 第 5 段階: 行頭の y（言語 B）===")
    B = [(ln, ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == "B"]
    B = [(ln, ws) for ln, ws in B if len(ws) >= 2]
    is_y = [ws[0] == "y" for _, ws in B]
    print(f"y 行 {sum(is_y)} / {len(B)} 行")

    def stat(flags):
        w2y = Counter(head2(ws[1]) for (_, ws), f in zip(B, flags) if f)
        w1n = Counter(head2(ws[0]) for (_, ws), f in zip(B, flags) if not f)
        w2n = Counter(head2(ws[1]) for (_, ws), f in zip(B, flags) if not f)
        return js(w2y, w1n) - js(w2y, w2n), js(w2y, w1n), js(w2y, w2n)

    obs, ja, jb = stat(is_y)
    rng = random.Random(2026)
    le = 0
    for _ in range(2000):
        sh = is_y[:]
        rng.shuffle(sh)
        le += stat(sh)[0] <= obs
    print(f"Y1 y 行の 2 語目と (a) 他の行の 1 語目の距離 {ja:.3f}、(b) 他の行の 2 語目の距離 {jb:.3f}、"
          f"差 {obs:+.3f}、p = {(le + 1) / 2001:.4f}（小さい側）")
    w2 = Counter(ws[1] for (_, ws), f in zip(B, is_y) if f)
    print("   y 行の 2 語目に多い語: " + ", ".join(f"{w}({c})" for w, c in w2.most_common(10)))
    first = sum(ln.position == "@" for (ln, _), f in zip(B, is_y) if f)
    allfirst = sum(ln.position == "@" for ln, _ in B)
    print(f"Y2 段落の 1 行目の割合: y 行 {first / max(1, sum(is_y)):.1%}、全ての行 {allfirst / len(B):.1%}")
    prev_end = Counter()
    all_end = Counter()
    for i in range(1, len(B)):
        (ln0, w0), (ln1, w1) = B[i - 1], B[i]
        if ln0.page.name != ln1.page.name:
            continue
        all_end[end_of(w0[-1])] += 1
        if w1[0] == "y":
            prev_end[end_of(w0[-1])] += 1
    tp, ta = sum(prev_end.values()), sum(all_end.values())
    print("Y3 上の行の最後の語の語末（y 行の上 / 全ての行の上）: " + ", ".join(
        f"{k} {prev_end[k] / tp:.0%}/{all_end[k] / ta:.0%}" for k in sorted(all_end, key=lambda k: -all_end[k])[:7]))


if __name__ == "__main__":
    main()

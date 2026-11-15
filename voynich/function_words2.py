#!/usr/bin/env python3
"""機能語の候補の位置と前後（第 15 回 第 2 段階）と、語の区切りの見直し（第 3 段階）。

    python3 voynich/function_words2.py <カエサルのテキスト pg218.txt>
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import null_generator  # noqa: E402
import unit_entropy  # noqa: E402
import word_grammar  # noqa: E402

CAND = {"A": ["daiin", "s", "dar"], "B": ["chedy", "ol", "y"]}
SEG = {"A": ["daiin", "dar"], "B": ["chedy", "ol"]}


def binom_two_sided(k: int, n: int, p: float) -> float:
    """正規近似（n が大きい）。"""
    if n == 0:
        return 1.0
    mu, sd = n * p, math.sqrt(n * p * (1 - p))
    if sd == 0:
        return 1.0
    z = abs(k - mu) / sd
    return math.erfc(z / math.sqrt(2))


def kl(p: Counter, q: Counter) -> float:
    n, m = sum(p.values()), sum(q.values())
    keys = set(p) | set(q)
    eps = 0.5
    tot_p = n + eps * len(keys)
    tot_q = m + eps * len(keys)
    return sum(((p[k] + eps) / tot_p) * math.log2(((p[k] + eps) / tot_p) / ((q[k] + eps) / tot_q)) for k in keys)


def next_kl_rank(tokens, end_of, targets, top=100):
    base = Counter(end_of(b) for b in tokens[1:])
    nxt = {}
    for a, b in zip(tokens, tokens[1:]):
        nxt.setdefault(a, Counter())[end_of(b)] += 1
    tops = [w for w, _ in Counter(tokens).most_common(top)]
    vals = {w: kl(nxt[w], base) for w in tops if w in nxt}
    order = sorted(vals, key=lambda w: -vals[w])
    return {t: (vals.get(t, float("nan")), order.index(t) + 1 if t in order else None) for t in targets}, len(order)


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        L = [ln for ln in lines if ln.page.get("L") == lang]
        pos = Counter()
        cand_pos = {c: Counter() for c in CAND[lang]}
        first_all = first_c = None
        para = Counter()
        cand_para = {c: Counter() for c in CAND[lang]}
        tokens = []
        for ln in L:
            ws = ivtff.words(ln.raw, opts)
            if not ws:
                continue
            tokens += ws
            first = ln.position == "@"
            for i, w in enumerate(ws):
                where = "行頭" if i == 0 else "行末" if i == len(ws) - 1 else "中"
                pos[where] += 1
                para["1行目" if first else "他"] += 1
                if w in cand_pos:
                    cand_pos[w][where] += 1
                    cand_para[w]["1行目" if first else "他"] += 1
        n_all = sum(pos.values())
        print(f"=== 言語 {lang} ===")
        print(f"全ての語: 行頭 {pos['行頭'] / n_all:.1%}, 行末 {pos['行末'] / n_all:.1%}, 段落の 1 行目 {para['1行目'] / n_all:.1%}")
        for c in CAND[lang]:
            cp, n = cand_pos[c], sum(cand_pos[c].values())
            ph = binom_two_sided(cp["行頭"], n, pos["行頭"] / n_all)
            pe = binom_two_sided(cp["行末"], n, pos["行末"] / n_all)
            pp = binom_two_sided(cand_para[c]["1行目"], n, para["1行目"] / n_all)
            m = lambda p, t: "*" if p < t else ""  # noqa: E731
            print(f"  {c:<6} {n:>4} 回  行頭 {cp['行頭'] / n:.1%}（p {ph:.3g}{m(ph, 0.0042)}）  行末 {cp['行末'] / n:.1%}"
                  f"（p {pe:.3g}{m(pe, 0.0042)}）  段落の 1 行目 {cand_para[c]['1行目'] / n:.1%}（p {pp:.3g}{m(pp, 0.0083)}）")
        res, n_top = next_kl_rank(tokens, lambda w: word_grammar.parse(w)[2], CAND[lang])
        print("  P3 後ろの語の語末の偏り（KL, 上位 100 語の中の順位）: "
              + ", ".join(f"{c} {v:.2f} ビット（{r}/{n_top} 位）" for c, (v, r) in res.items()))
        print()

    if len(sys.argv) > 1:
        lat = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
        res, n_top = next_kl_rank(lat, lambda w: w[-2:], ["in", "et", "cum", "ad", "de"])
        print("参照 ラテン語（カエサル）P3: " + ", ".join(f"{c} {v:.2f}（{r}/{n_top} 位）" for c, (v, r) in res.items()))
        print()

    # 第 3 段階: 語の区切りの見直し
    print("=== 第 3 段階: 語の区切りの見直し ===")
    for lang in ("A", "B"):
        toks = [w for ln in lines if ln.page.get("L") == lang for w in ivtff.words(ln.raw, opts)]
        print(f"言語 {lang}: 区切り直す前 " + ", ".join(f"{k} {v:.3f}" for k, v in null_generator.vocab_stats(toks).items()))
        new = toks
        for c in SEG[lang]:
            cg = len(ivtff.glyphs(c))
            alone = sum(w == c for w in toks)
            end = sum(w.endswith(c) and len(ivtff.glyphs(w)) >= cg + 2 for w in toks)
            start = sum(w.startswith(c) and len(ivtff.glyphs(w)) >= cg + 2 for w in toks)
            print(f"  S1 {c}: 単独 {alone}、語末に含む {end}、語頭に含む {start}")
            out = []
            for w in new:
                g = len(ivtff.glyphs(w))
                if w != c and w.endswith(c) and g >= cg + 2:
                    out += [w[:-len(c)], c]
                elif w != c and w.startswith(c) and g >= cg + 2:
                    out += [c, w[len(c):]]
                else:
                    out.append(w)
            new = out
        print(f"  区切り直した後（延べ {len(toks)} → {len(new)} 語）: "
              + ", ".join(f"{k} {v:.3f}" for k, v in null_generator.vocab_stats(new).items()))
        print("  自然言語の範囲: V1 1511〜4793, V2 0.491〜0.681, V3 −0.869〜−0.572, V4 0.597〜0.783\n")


if __name__ == "__main__":
    main()

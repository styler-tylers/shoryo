#!/usr/bin/env python3
"""語頭の入れ替えの並び方（第 10 回 第 2 段階）。

語頭の部品（qo, q, o, ch, sh, y, なし）だけが違い、本体が同じ語の組が、
隣り合って書かれやすいか（O1）、どちらが先に来るか（O2）、上の行との移り変わり（O3）。

    python3 voynich/prefix_order.py            # 第 2 段階
    python3 voynich/prefix_order.py --stage3   # 第 3 段階（語頭の群と本体）
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
import self_citation as sc  # noqa: E402

HEADS = [("q", "o"), ("q",), ("o",), ("ch",), ("sh",), ("y",)]


def split(word: str):
    g = tuple(ivtff.glyphs(word))
    for h in HEADS:
        if g[:len(h)] == h and len(g) - len(h) >= 2:
            return "".join(h), g[len(h):]
    if len(g) >= 2:
        return "なし", g
    return None


def adjacent_pairs(pages):
    """隣り合う「語頭だけ違う組」: [(先の語頭, 後の語頭)]"""
    out = []
    for ls in pages.values():
        for l in ls:
            sp = [split(w) for w in l]
            for a, b in zip(sp, sp[1:]):
                if a and b and a[1] == b[1] and a[0] != b[0]:
                    out.append((a[0], b[0]))
    return out


def binom_two_sided(k: int, n: int) -> float:
    pk = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, sum(p for p in pk if p <= pk[k] * (1 + 1e-9)))


def run(title, pages, rng, trials=2000):
    print(f"=== {title}（{len(pages)} 頁）===")
    obs = adjacent_pairs(pages)
    ge = 0
    null = []
    for _ in range(trials):
        sh = {p: [rng.sample(l, len(l)) for l in ls] for p, ls in pages.items()}
        n = len(adjacent_pairs(sh))
        null.append(n)
        ge += n >= len(obs)
    print(f"O1 隣り合う「語頭だけ違う組」: {len(obs)} 組、行の中で語順を入れ替えた場合の平均 {sum(null) / trials:.1f}、"
          f"倍率 {len(obs) / (sum(null) / trials):.2f}、p = {(ge + 1) / (trials + 1):.4f}")

    cnt = Counter(obs)
    combos = sorted({tuple(sorted(k)) for k in cnt if cnt[k] + cnt[(k[1], k[0])] >= 10})
    print(f"O2 向き（10 回以上の組 {len(combos)} 個, ボンフェローニ補正 p < {0.05 / max(1, len(combos)):.4f}）:")
    for a, b in sorted(combos, key=lambda c: -(cnt[c] + cnt[(c[1], c[0])])):
        n = cnt[(a, b)] + cnt[(b, a)]
        p = binom_two_sided(cnt[(a, b)], n)
        mark = "  ← 補正後も有意" if p < 0.05 / len(combos) else ""
        print(f"   {a:>4} → {b:<4} {cnt[(a, b)]:>3}  /  {b:>4} → {a:<4} {cnt[(b, a)]:>3}   p = {p:.4f}{mark}")

    # O3: 上の行の真上あたりにある「語頭だけ違う語」との移り変わり
    trans = Counter()
    for ls in pages.values():
        for li in range(1, len(ls)):
            line, above = ls[li], ls[li - 1]
            if len(line) < 2 or len(above) < 2:
                continue
            sa = [split(w) for w in above]
            for wi, w in enumerate(line):
                s = split(w)
                if not s:
                    continue
                x = wi / (len(line) - 1)
                for aj, t in enumerate(sa):
                    if t and t[1] == s[1] and abs(x - aj / (len(above) - 1)) <= 0.2:
                        trans[(t[0], s[0])] += 1
    heads = ["qo", "q", "o", "ch", "sh", "y", "なし"]
    tot = sum(trans.values())
    same = sum(trans[(h, h)] for h in heads)
    up = Counter()
    down = Counter()
    for (a, b), n in trans.items():
        up[a] += n
        down[b] += n
    exp_same = sum(up[h] * down[h] for h in heads) / tot ** 2 if tot else 0
    print(f"O3 真上あたりの同じ本体の語 {tot} 組: 同じ語頭 {same / tot:.0%}（語頭の頻度から期待 {exp_same:.0%}）")
    print("    上 → 下（行: 上の語頭, 列: 下の語頭）")
    print("        " + "".join(f"{h:>6}" for h in heads))
    for a in heads:
        print(f"   {a:>4} " + "".join(f"{trans[(a, b)]:>6}" for b in heads))
    print()


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        pages = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        run(f"言語 {lang}", pages, rng)


if __name__ == "__main__" and "--stage3" not in sys.argv:
    main()


# ---------------------------------------------------------------------------
# 第 3 段階: 語頭の群と本体の組み合わせ
# ---------------------------------------------------------------------------

GROUP = {"qo": "QO", "o": "QO", "ch": "CH", "sh": "CH"}


def combos(pages, rng, trials=1000):
    toks = []  # (群, 本体)
    for ls in pages.values():
        for l in ls:
            for w in l:
                s = split(w)
                if s and s[0] in GROUP:
                    toks.append((GROUP[s[0]], s[1]))

    def skewed(ts):
        c = defaultdict(Counter)
        for g, b in ts:
            c[b][g] += 1
        big = [b for b, x in c.items() if sum(x.values()) >= 10]
        return sum(max(c[b].values()) / sum(c[b].values()) >= 0.8 for b in big), len(big), c

    k, n, c = skewed(toks)
    groups = [g for g, _ in toks]
    bodies = [b for _, b in toks]
    ge = 0
    vals = []
    for _ in range(trials):
        sh = groups[:]
        rng.shuffle(sh)
        kk, nn, _ = skewed(list(zip(sh, bodies)))
        vals.append(kk / nn if nn else 0)
        ge += (kk / nn if nn else 0) >= k / n
    print(f"C1 群の語が 10 語以上の本体 {n} 個のうち、片方の群に 80% 以上偏る本体 {k}（{k / n:.0%}）。"
          f"入れ替えた場合の平均 {sum(vals) / trials:.0%}、p = {(ge + 1) / (trials + 1):.4f}")
    first = defaultdict(Counter)
    for g, b in toks:
        first[b[0]][g] += 1
    tot = Counter(g for g, _ in toks)
    print(f"C2 本体の 1 つ目の字形ごとの QO 群の割合（全体では {tot['QO'] / sum(tot.values()):.0%}）:")
    rows = sorted(first.items(), key=lambda x: -sum(x[1].values()))[:12]
    print("   " + ", ".join(f"{f}: {x['QO'] / sum(x.values()):.0%}（{sum(x.values())}）" for f, x in rows))
    both = [(b, x) for b, x in c.items() if x["QO"] >= 3 and x["CH"] >= 3]
    both.sort(key=lambda bx: -sum(bx[1].values()))
    print("C3 両方の群と組む本体: " + ", ".join(
        f"-{''.join(b)}（QO {x['QO']}・CH {x['CH']}）" for b, x in both[:10]))
    only = sorted(((b, x) for b, x in c.items() if sum(x.values()) >= 10 and max(x.values()) / sum(x.values()) >= 0.8),
                  key=lambda bx: -sum(bx[1].values()))
    print("   片方に偏る本体の例: " + ", ".join(
        f"-{''.join(b)}（{max(x, key=x.get)} {max(x.values())}/{sum(x.values())}）" for b, x in only[:10]))


def stage3() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        pages = sc.page_lines([ln for ln in lines if ln.page.get("L") == lang], opts)
        print(f"=== 言語 {lang} ===")
        combos(pages, rng)
        print()


if __name__ == "__main__" and "--stage3" in sys.argv:
    stage3()

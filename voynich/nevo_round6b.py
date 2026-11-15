#!/usr/bin/env python3
"""第 6 巡の補い: N17 を ZL の段落の印（<%> 段落の始まり・<$> 段落の終わり）で数え直す。
N16 の行の中の隣どうしのつながりを、行の中で語の順を並べ替えた基準で測り直す（事後の変更）。

    python3 voynich/nevo_round6b.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round6 import build, sources  # noqa: E402


def n17(rng, runs=200):
    print("=== N17（直し）段落の中と段落の境目: <%> と <$> で段落を決める ===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    g = lambda w: list(ivtff.glyphs(w))  # noqa: E731
    for lang in ("A", "B"):
        L = [(ln.page.name, ln.raw, ln.position, ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == lang]
        L = [x for x in L if x[3]]
        starts = [("<%>" in raw) or pos == "@" for _, raw, pos, _ in L]
        pairs = {"段落の中": [], "段落の境目": []}
        heads = {"段落の中": [], "段落の境目": []}
        for i in range(1, len(L)):
            (p1, raw1, _, w1), (p2, _, _, w2) = L[i - 1], L[i]
            if p1 != p2:
                continue
            kind = "段落の境目" if (starts[i] or "<$>" in raw1) else "段落の中"
            pairs[kind].append((p2, "".join(g(w1[-1])[-2:]), "".join(g(w2[0])[:2])))
        for i, (p, _, _, ws) in enumerate(L):
            heads["段落の境目" if starts[i] else "段落の中"].append((p, "".join(g(ws[0])[:2])))
        print(f"  言語 {lang}: 段落の始まりの行 {sum(starts)}")
        for kind, ps in pairs.items():
            n = len(ps)
            obs = line_unit.mi([(a, b) for _, a, b in ps])
            nulls = []
            for _ in range(runs):
                null = []
                for page, a, _ in ps:
                    while True:
                        q, h = rng.choice(heads[kind])
                        if q != page:
                            break
                    null.append((a, h))
                nulls.append(line_unit.mi(null))
            m = statistics.mean(nulls)
            p = (sum(x >= obs for x in nulls) + 1) / (runs + 1)
            print(f"  言語 {lang} {kind:<6} 組 {n:>5}  観測 {obs:.3f}  基準 {m:.3f}  差 {obs - m:+.3f}  p = {p:.3g}")


def adjacency(name, lines_, rng, runs=50):
    """行の内側（端を除く）の隣どうしの語末 2 × 語頭 2 の相互情報量と、行の中で語の順を並べ替えた基準。"""
    inner = [l[1:-1] for l in lines_ if len(l) >= 4]
    u = lambda w: tuple(w)  # noqa: E731
    obs_pairs = [("".join(u(a)[-2:]), "".join(u(b)[:2])) for l in inner for a, b in zip(l, l[1:])]
    obs = line_unit.mi(obs_pairs)
    nulls = []
    for _ in range(runs):
        ps = []
        for l in inner:
            x = list(l)
            rng.shuffle(x)
            ps += [("".join(u(a)[-2:]), "".join(u(b)[:2])) for a, b in zip(x, x[1:])]
        nulls.append(line_unit.mi(ps))
    m = statistics.mean(nulls)
    p = (sum(x >= obs for x in nulls) + 1) / (runs + 1)
    print(f"  {name:<22} 組 {len(obs_pairs):>6}  隣どうし {obs:.3f}  並べ替え {m:.3f}  差 {obs - m:+.3f}  p = {p:.3g}")


def main() -> None:
    rng = random.Random(2026)
    n17(rng)
    print("\n=== N16（事後の変更）行の内側の隣どうしのつながり: 行の中で語の順を並べ替えた基準 ===")
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(sys.argv[1]))]
    for mode in ("平文", "語順を崩した平文", "無意味な語彙"):
        i, e = sources(caesar, mode, random.Random(13))
        pages = build(i, e, 0.2, random.Random(11), 0.25, cap=20000)
        adjacency(mode, [l for _, ls in pages for l in ls], rng)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        ls = [[tuple(ivtff.glyphs(w)) for w in ivtff.words(ln.raw, opts)] for ln in lines if ln.page.get("L") == lang]
        adjacency(f"ヴォイニッチ {lang}", ls, rng)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""機能語らしい語（第 15 回）。上位 100 語の「散らばり」と「後ろの語の多様さ」を自然言語と比べる。

    python3 voynich/function_words.py <自然言語のテキスト …>
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import unit_entropy  # noqa: E402

CHUNK = 250
N_TOKENS = 20000


def profile(tokens: list[str]):
    toks = tokens[:N_TOKENS]
    K = len(toks) // CHUNK
    toks = toks[:K * CHUNK]
    freq = Counter(toks)
    chunks = defaultdict(set)
    nxt = defaultdict(list)
    for i, w in enumerate(toks):
        chunks[w].add(i // CHUNK)
        if i + 1 < len(toks) and len(nxt[w]) < 50:
            nxt[w].append(toks[i + 1])
    rows = []
    for rank, (w, n) in enumerate(freq.most_common(100), 1):
        exp = K * (1 - (1 - 1 / K) ** n)
        disp = len(chunks[w]) / exp
        div = len(set(nxt[w])) / len(nxt[w]) if nxt[w] else 0
        rows.append((rank, w, n, disp, div))
    return rows


def spearman(xs, ys) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for k, i in enumerate(order):
            r[i] = k
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return cov / (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5


def report(name, rows, show: int = 15) -> int:
    fn = [r for r in rows if r[3] >= 0.95 and r[4] >= 0.80]
    rho = spearman([r[0] for r in rows], [r[3] for r in rows])
    print(f"{name:<16} 機能語らしい語 {len(fn):>3}/100  順位と散らばりの相関 {rho:+.2f}  "
          f"散らばりの中央値 {sorted(r[3] for r in rows)[50]:.2f}")
    print("   " + ", ".join(f"{w}({n})" for _, w, n, _, _ in fn[:show]))
    return len(fn)


def main() -> None:
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    vrows = {}
    for lang in ("A", "B"):
        toks = [w for ln in lines if ln.page.get("L") == lang for w in ivtff.words(ln.raw, opts)]
        vrows[lang] = profile(toks)
        report(f"ヴォイニッチ {lang}", vrows[lang], show=30)
    nat = []
    for p in map(Path, sys.argv[1:]):
        nat.append(report(p.stem, profile(["".join(w) for w in unit_entropy.latin_words(p)])))
    if nat:
        print(f"\n自然言語の機能語らしい語の数: {min(nat)}〜{max(nat)}")
    for lang, rows in vrows.items():
        fn = [r for r in rows if r[3] >= 0.95 and r[4] >= 0.80]
        if fn:
            L = [len(ivtff.glyphs(w)) for _, w, _, _, _ in fn]
            other = [len(ivtff.glyphs(w)) for _, w, _, d, v in rows if not (d >= 0.95 and v >= 0.80)]
            print(f"ヴォイニッチ {lang}: 機能語らしい語の平均の長さ {sum(L) / len(L):.2f} 字形、それ以外の上位語 {sum(other) / len(other):.2f}")
        bursty = sorted(rows, key=lambda r: r[3])[:10]
        print(f"   最も固まる上位語: " + ", ".join(f"{w}({d:.2f})" for _, w, _, d, _ in bursty))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""段落の始まりの語（頁の見出し語）と植物の絵の対応（第 18 回）。

H1 色の特徴の距離 × 見出しの本体の編集距離 の相関 / H2 根の型が同じ組と違う組の見出しの距離
同じクワイアの頁の組は除く。

    python3 voynich/heading_image.py
"""

from __future__ import annotations

import csv
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import image_text  # noqa: E402
import ivtff  # noqa: E402
import page_images  # noqa: E402
import zodiac_days  # noqa: E402

GALLOWS = {"k", "t", "p", "f", "ckh", "cth", "cph", "cfh"}
NOTES = Path(__file__).resolve().parent / "notes"


def heading(words: list[str]) -> str:
    g = ivtff.glyphs(words[0])
    return "".join(g[1:]) if len(g) >= 3 and g[0] in GALLOWS else words[0]


def norm_dist(a: str, b: str) -> float:
    return zodiac_days.lev(a, b) / max(len(ivtff.glyphs(a)), len(ivtff.glyphs(b)), 1)


def pearson(xs, ys) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    head, meta = {}, {}
    for ln in lines:
        if ln.page.get("I") != "H" or ln.position != "@" or ln.page.name in head:
            continue
        ws = ivtff.words(ln.raw, opts)
        if ws:
            head[ln.page.name] = heading(ws)
            meta[ln.page.name] = ln.page
    roots = {}
    for name in ("rater_consensus.csv", "rater_consensus_rep.csv"):
        with open(NOTES / name, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["根の型"].startswith("R") and r["根の型"] != "R0":
                    roots[r["頁"]] = r["根の型"]
    for lang in ("A", "B"):
        pages = [p for p in head if meta[p].get("L") == lang and page_images.image_path(p, 500).exists()]
        feats = {p: image_text.color_features(page_images.image_path(p, 500)) for p in pages}
        keys = sorted(next(iter(feats.values())))
        mu = {k: sum(feats[p][k] for p in pages) / len(pages) for k in keys}
        sd = {k: math.sqrt(sum((feats[p][k] - mu[k]) ** 2 for p in pages) / len(pages)) or 1 for k in keys}
        vec = {p: [(feats[p][k] - mu[k]) / sd[k] for k in keys] for p in pages}
        pairs = [(a, b) for i, a in enumerate(pages) for b in pages[i + 1:] if meta[a].get("Q") != meta[b].get("Q")]
        img = [math.dist(vec[a], vec[b]) for a, b in pairs]

        def word_d(assign):
            return [norm_dist(assign[a], assign[b]) for a, b in pairs]

        obs = pearson(img, word_d(head))
        ge = 0
        for _ in range(5000):
            sh = [head[p] for p in pages]
            rng.shuffle(sh)
            ge += pearson(img, word_d(dict(zip(pages, sh)))) >= obs
        print(f"=== 言語 {lang}（植物の頁 {len(pages)}, 違うクワイアの組 {len(pairs)}）===")
        print(f"H1 色の距離 × 見出しの本体の距離 の相関 {obs:+.3f}、p = {(ge + 1) / 5001:.4f}（片側, 正の相関）")

        rp = [p for p in pages if p in roots]
        rpairs = [(a, b) for i, a in enumerate(rp) for b in rp[i + 1:] if meta[a].get("Q") != meta[b].get("Q")]

        def h2(labels):
            same = [norm_dist(head[a], head[b]) for a, b in rpairs if labels[a] == labels[b]]
            diff = [norm_dist(head[a], head[b]) for a, b in rpairs if labels[a] != labels[b]]
            return sum(diff) / len(diff) - sum(same) / len(same), len(same)

        o2, ns = h2(roots)
        ge = 0
        for _ in range(5000):
            sh = [roots[p] for p in rp]
            rng.shuffle(sh)
            ge += h2(dict(zip(rp, sh)))[0] >= o2
        print(f"H2 根の型が同じ組（{ns} 組）は違う組より見出しが近いか: 差 {o2:+.3f}、p = {(ge + 1) / 5001:.4f}（{len(rp)} 頁）")
        print("   見出しの例: " + ", ".join(f"{p} {head[p]}" for p in pages[:10]))
        print()


if __name__ == "__main__":
    main()

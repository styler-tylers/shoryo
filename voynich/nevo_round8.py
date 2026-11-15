#!/usr/bin/env python3
"""nēvo による解析 第 8 巡: N21（境目の 1 字形どうし）・N22（写しらしい語のつながり）・N23（境目の規則を入れたモデル）。

    python3 voynich/nevo_round8.py <Caesar> <Descartes>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import line_unit  # noqa: E402
import nevo_round6  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round2 import ed1  # noqa: E402
from nevo_round6b import adjacency  # noqa: E402
from nevo_tests import voynich_pages  # noqa: E402

e2 = lambda w: "".join(w[-2:])  # noqa: E731
h2 = lambda w: "".join(w[:2])  # noqa: E731


def inner_lines(lines_):
    return [l[1:-1] for l in lines_ if len(l) >= 4]


def n21_one(name, lines_, rng, runs=50):
    inner = inner_lines(lines_)
    pairs = [(a, b) for l in inner for a, b in zip(l, l[1:])]
    out = {}
    for label, fa, fb in (("語末2×語頭2", e2, h2), ("語×語", lambda w: w, lambda w: w)):
        obs = line_unit.mi([(fa(a), fb(b)) for a, b in pairs])
        n1 = []
        for _ in range(runs):
            ps = []
            for l in inner:
                x = list(l)
                rng.shuffle(x)
                ps += [(fa(a), fb(b)) for a, b in zip(x, x[1:])]
            n1.append(line_unit.mi(ps))
        groups = defaultdict(list)
        for i, (a, b) in enumerate(pairs):
            groups[(a[-1], b[0])].append(i)
        n2 = []
        for _ in range(runs):
            bs = [b for _, b in pairs]
            for idx in groups.values():
                sh = [pairs[i][1] for i in idx]
                rng.shuffle(sh)
                for i, b in zip(idx, sh):
                    bs[i] = b
            n2.append(line_unit.mi([(fa(a), fb(b)) for (a, _), b in zip(pairs, bs)]))
        b1, b2 = statistics.mean(n1), statistics.mean(n2)
        frac = (b2 - b1) / (obs - b1) if obs > b1 else float("nan")
        out[label] = (obs, b1, b2, frac)
    print(f"  {name:<18} 組 {len(pairs):>6}  " + "  ".join(
        f"{k}: 観測 {o:.3f} 基準1 {a:.3f} 基準2 {b:.3f} → 境目の 1 字形で説明 {f:.0%}" for k, (o, a, b, f) in out.items()))


def n22(rng, runs=50):
    print("\n=== N22 写しらしい語でも隣どうしのつながりは出るか（ZL）===")
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        P = voynich_pages(lines, opts, lang)
        groups = {"写しらしい語": [], "それ以外": []}
        for ls in P.values():
            inner = [l[1:-1] if len(l) >= 4 else [] for l in ls]
            for i, l in enumerate(inner):
                prev = set(w for x in inner[max(0, i - 3):i] for w in x)
                if i < 3:
                    continue
                for a, b in zip(l, l[1:]):
                    kind = "写しらしい語" if (b in prev or any(ed1(b, v) for v in prev)) else "それ以外"
                    groups[kind].append((e2(a), h2(b)))
        n = min(len(v) for v in groups.values())
        res = {}
        for kind, ps in groups.items():
            diffs = []
            for _ in range(runs):
                sub = rng.sample(ps, n)
                bs = [b for _, b in sub]
                rng.shuffle(bs)
                diffs.append(line_unit.mi(sub) - line_unit.mi([(a, b) for (a, _), b in zip(sub, bs)]))
            res[kind] = statistics.mean(diffs)
        print(f"  言語 {lang}: 写しらしい語 {len(groups['写しらしい語'])} 組・それ以外 {len(groups['それ以外'])} 組（{n} 組に揃える）  "
              f"差: 写しらしい語 {res['写しらしい語']:+.3f}、それ以外 {res['それ以外']:+.3f}、比 {res['写しらしい語'] / res['それ以外']:.2f}")


def apply_rule(pages, beta, rng):
    out = []
    for pg, ls in pages:
        new = []
        for l in ls:
            l = list(l)
            for i in range(2, len(l) - 1):
                w, prev = l[i], l[i - 1]
                if w and w[0] in scmp.ONSET and rng.random() < beta:
                    g = scmp.ONSET.index(w[0]) // 4
                    l[i] = scmp.ONSET[g * 4 + scmp._h("b" + prev[-1], 4)] + w[1:]
            new.append(l)
        out.append((pg, new))
    return out


def n23(caesar, rng):
    print("\n=== N23 境目の規則を入れたモデル（S のモデル, E5, c 0.4）===")
    for beta in (0.0, 0.5, 1.0):
        i, e = nevo_round6.sources(caesar, "平文", rng)
        pages = nevo_round6.build(i, e, 0.4, random.Random(11), 0.25, short=True)
        pages = apply_rule(pages, beta, random.Random(17))
        nevo_round6.row(f"β = {beta}", pages, rng)
        adjacency("   隣どうし", [l for _, ls in pages for l in ls], rng)


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:3]]
    rng = random.Random(2026)
    print("=== N21 境目の 1 字形どうし ===")
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        P = voynich_pages(lines, opts, lang)
        n21_one(f"ヴォイニッチ {lang}", [l for ls in P.values() for l in ls], rng)
    for p in paths:
        ws = ["".join(w) for w in unit_entropy.latin_words(p)][:20000]
        n21_one(f"{p.stem} 文字", [[tuple(w) for w in l] for _, ls in line_unit.wrap(ws, 37) for l in ls], rng)
    n22(rng)
    caesar = ["".join(w) for w in unit_entropy.latin_words(paths[0])]
    n23(caesar, rng)


if __name__ == "__main__":
    main()

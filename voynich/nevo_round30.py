#!/usr/bin/env python3
"""nēvo による解析 第 30 巡: N88（まとまりの中身）・N89（好みの語と組の記憶）・N90（頁の長さをそろえた N87）。

    python3 voynich/nevo_round30.py <Caesar>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round25 import score  # noqa: E402
from nevo_round27 import BINS, page_sim  # noqa: E402
from nevo_round29 import build_fav  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
jac = lambda a, b: len(a & b) / len(a | b)  # noqa: E731


def ratio(P):
    pages = list(P.values())
    allw = Counter(w for ls in pages for l in ls for w in l)
    top = {w for w, _ in allw.most_common(50)}
    sets = [s for s in (set(w for l in ls for w in l) - top for ls in pages) if s]
    num, den, n1, n2 = 0.0, 0.0, 0, 0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            d = j - i
            if 2 <= d <= 5:
                num += jac(sets[i], sets[j]); n1 += 1
            elif d >= 21:
                den += jac(sets[i], sets[j]); n2 += 1
    return (num / n1) / (den / n2)


def surrogate(P, key, rng):
    pool = defaultdict(list)
    for ls in P.values():
        for l in ls:
            for w in l:
                pool[key(w)].append(w)
    return {k: [[rng.choice(pool[key(w)]) for w in l] for l in ls] for k, ls in P.items()}


HE = lambda w: (split(w)[0], split(w)[2])  # noqa: E731
MID = lambda w: split(w)[1]  # noqa: E731


def n88(name, P):
    r0 = ratio(P)
    out = [f"  {name:<26} 元 {r0:.2f}"]
    for label, key in (("HE", HE), ("M", MID)):
        rs = [ratio(surrogate(P, key, random.Random(s))) for s in range(5)]
        m = statistics.mean(rs)
        out.append(f"置き換え {label} {m:.2f}[{min(rs):.2f}〜{max(rs):.2f}] 残る割合 {(m - 1) / (r0 - 1):.0%}")
    print("   ".join(out), flush=True)


def n90(V):
    print("\n=== N90 頁の長さをそろえた N87（各頁 60 語, 20 通りの平均）===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    meta = {ln.page.name: (ln.page.get("Q"), ln.page.get("B"), ln.page.get("I"), ln.page.get("F")) for ln in lines}
    for lang in ("A", "B"):
        pt = V[lang][0]
        allw = Counter(w for ls in pt.values() for l in ls for w in l)
        top = {w for w, _ in allw.most_common(50)}
        pg = [(k, [w for l in ls for w in l]) for k, ls in pt.items()]
        idx = [i for i, (k, ws) in enumerate(pg) if len(ws) >= 60]
        print(f"\n--- 言語 {lang}（頁 {len(pg)} のうち 60 語以上 {len(idx)}）---")
        acc = defaultdict(float)
        R = 20
        for r in range(R):
            rng = random.Random(r)
            sets = {i: set(rng.sample(pg[i][1], 60)) - top for i in idx}
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    i, j = idx[a], idx[b]
                    acc[(i, j)] += jac(sets[i], sets[j]) / R
        pairs = [(j - i, v, meta[pg[i][0]], meta[pg[j][0]]) for (i, j), v in acc.items()]
        base = statistics.mean(p[1] for p in pairs)

        def row(name, sel):
            out = []
            for label, lo, hi in BINS:
                v = [p[1] for p in pairs if lo <= p[0] <= hi and sel(p)]
                out.append((label, statistics.mean(v) / base if len(v) >= 20 else None, len(v)))
            s = "  ".join(f"S({k}) {'—' if x is None else format(x, '.2f')}（{n}）" for k, x, n in out)
            d = {k: x for k, x, _ in out}
            r = f"{d['2〜5'] / d['21〜']:.2f}" if d["2〜5"] and d["21〜"] else "—"
            print(f"  {name:<20} {s}   S(2〜5)÷S(21〜) {r}")

        row("全ての頁の組", lambda p: True)
        row("同じ挿絵の種類", lambda p: p[2][2] == p[3][2])
        row("違う挿絵の種類", lambda p: p[2][2] != p[3][2])
        row("挿絵 H どうし", lambda p: p[2][2] == p[3][2] == "H")
        row("同じ挿絵・同じ綴じ", lambda p: p[2][2] == p[3][2] and p[2][0] == p[3][0])
        row("同じ挿絵・違う綴じ", lambda p: p[2][2] == p[3][2] and p[2][0] != p[3][0])
        sq = lambda p: p[2][0] == p[3][0] and p[2][2] == p[3][2]  # noqa: E731
        for name, sel in (("同じ綴じ・同じ挿絵・同じ紙（別の葉）", lambda p: sq(p) and p[2][1] == p[3][1] and p[2][3] != p[3][3]),
                          ("同じ綴じ・同じ挿絵・違う紙", lambda p: sq(p) and p[2][1] != p[3][1])):
            v = [p[1] for p in pairs if sel(p)]
            dm = statistics.mean(p[0] for p in pairs if sel(p)) if v else 0
            print(f"  {name:<20} 重なり ÷ 全体 {statistics.mean(v) / base if len(v) >= 20 else float('nan'):.2f}（組 {len(v)}、平均の距離 {dm:.1f}）")
            if lang == "B":
                for kind in ("H", "B", "S"):
                    v2 = [p[1] for p in pairs if sel(p) and p[2][2] == kind]
                    if len(v2) >= 20:
                        print(f"      挿絵 {kind}: {statistics.mean(v2) / base:.2f}（組 {len(v2)}）")


def main() -> None:
    caesar = words_any(Path(sys.argv[1]))[:30000]
    rng = random.Random(2026)
    V = voynich()
    n90(V)
    models = {}
    print("\n=== N88 まとまりの中身（置き換え）===", flush=True)
    for lang in ("A", "B"):
        pt = V[lang][0]
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        models[lang] = (LG, LC)
        n88(f"ヴォイニッチ {lang}", pt)
        for seed in (1, 2):
            _, _, coded = matched_source(caesar, LG, random.Random(seed))
            it = iter(coded)
            src = lambda: next(it, None)  # noqa: E731
            P = build12(src, src, LG, LC, random.Random(seed + 10), c=0.4, beta=0.0, compat=True, wfun=gram_prob(LG))
            n88(f"平文あり（段 2）{lang} 種 {seed}", P)
            P = build_fav(LG, LC, pt, random.Random(seed), 0.5)
            n88(f"平文なし（好みの語）{lang} 種 {seed}", P)
    print("\n=== N89 好みの語に組の記憶 ===", flush=True)
    for lang in ("A", "B"):
        pt = V[lang][0]
        LG, LC = models[lang]
        print(f"######## 言語 {lang} ########", flush=True)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        for name, kw in (("(i) μ 0.2", dict(mu=0.2)), ("(ii) κ 5", dict(kappa=5.0))):
            runs = []
            for seed in (1, 2):
                P = build_fav(LG, LC, pt, random.Random(seed), 0.5, **kw)
                page_sim(f"{name} 種 {seed}", P)
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(name, runs)
            score(name, runs, ref)
            sys.stdout.flush()


if __name__ == "__main__":
    main()

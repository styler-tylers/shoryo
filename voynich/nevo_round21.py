#!/usr/bin/env python3
"""nēvo による解析 第 21 巡: N62（書き換えの痕跡）・N63（語頭の変異がある言語）・N61（連声型の書き換えの規則）。

    python3 voynich/nevo_round21.py <Caesar> --ref <ラテン語など …> --mut <ウェールズ語・アイルランド語 …>
"""

from __future__ import annotations

import argparse
import random
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import adj_diff, voynich  # noqa: E402
from nevo_round10 import measure, n21_fracs  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731


def words_any(path: Path):
    t = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*\* ?START.*?\*\*\*(.*)\*\*\* ?END", t, re.S)
    t = (m.group(1) if m else t).lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))
    return re.findall(r"[a-z]+", t)


def families_test(name, lines_, rng, runs=200):
    inner = [l[1:-1] for l in lines_ if len(l) >= 4]
    cnt = Counter(w for l in inner for w in l)
    fam = defaultdict(set)
    for w, n in cnt.items():
        if n >= 5 and len(w) >= 2:
            fam[tuple(w[1:])].add(w)
    fam = {k: v for k, v in fam.items() if len(v) >= 2}
    member = {w: k for k, v in fam.items() for w in v}
    obs_rows = defaultdict(list)
    for l in inner:
        for a, b in zip(l, l[1:]):
            if b in member:
                obs_rows[member[b]].append((b, a[-1]))
    N = sum(len(v) for v in obs_rows.values())

    def score(rows):
        return sum(len(v) / N * line_unit.mi(v) for v in rows.values() if len(v) >= 2)

    obs = score(obs_rows)
    nulls = []
    for _ in range(runs):
        sh = {}
        for k, v in obs_rows.items():
            prev = [p for _, p in v]
            rng.shuffle(prev)
            sh[k] = [(b, p) for (b, _), p in zip(v, prev)]
        nulls.append(score(sh))
    m = statistics.mean(nulls)
    p = (sum(x >= obs for x in nulls) + 1) / (runs + 1)
    ex = sorted(fam.items(), key=lambda kv: -sum(cnt[w] for w in kv[1]))[:3]
    exs = "; ".join("/".join("".join(w) for w in sorted(v, key=lambda w: -cnt[w])[:4]) for _, v in ex)
    print(f"  {name:<22} 家族 {len(fam):>4}・語 {N:>5}  観測 {obs:.4f}  基準 {m:.4f}  超過 {obs - m:+.4f}  比 {obs / m if m else float('nan'):.2f}  p = {p:.3g}   例: {exs}")


def first_table(pt):
    T = defaultdict(Counter)
    for ls in pt.values():
        for l in ls:
            if len(l) >= 4:
                for a, b in zip(l[1:-1], l[2:-1]):
                    T[a[-1]][b[0]] += 1
    return T


def apply_sandhi(P, T, sigma, rng):
    for ls in P.values():
        for li, l in enumerate(ls):
            if len(l) < 4:
                continue
            new = [l[0]]
            for i in range(1, len(l)):
                w = l[i]
                d = T.get(new[-1][-1])
                if d and rng.random() < sigma:
                    k, v = zip(*d.items())
                    w = (rng.choices(k, v)[0],) + w[1:]
                new.append(w)
            ls[li] = new
    return P


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("caesar")
    ap.add_argument("--ref", nargs="*", default=[])
    ap.add_argument("--mut", nargs="*", default=[])
    a = ap.parse_args()
    rng = random.Random(2026)
    V = voynich()
    print("=== N62 頭だけが違う語の家族 × 前の語の最後 ===")
    for lang in ("A", "B"):
        families_test(f"ヴォイニッチ {lang}", [l for ls in V[lang][0].values() for l in ls], rng)
    texts = [(Path(x), "参照") for x in [a.caesar] + a.ref] + [(Path(x), "語頭の変異") for x in a.mut]
    lines_of = {}
    for p, kind in texts:
        ws = words_any(p)[:30000]
        lines_of[p] = [[tuple(w) for w in l] for _, ls in line_unit.wrap(ws, 37) for l in ls]
        families_test(f"{p.stem}（{kind}）", lines_of[p], rng)
    print("\n=== N63 隣どうしのつながりと境目の 1 字形で説明される割合 ===")
    for lang in ("A", "B"):
        ls = [l for x in V[lang][0].values() for l in x]
        fr = n21_fracs(ls, rng)
        print(f"  ヴォイニッチ {lang:<12} 隣どうし {adj_diff(ls, rng):+.3f}  境目で説明: 語末2×語頭2 {fr[0]:.0%}  語×語 {fr[1]:.0%}")
    for p, kind in texts:
        fr = n21_fracs(lines_of[p], rng)
        print(f"  {p.stem + '（' + kind + '）':<24} 隣どうし {adj_diff(lines_of[p], rng):+.3f}  境目で説明: 語末2×語頭2 {fr[0]:.0%}  語×語 {fr[1]:.0%}")
    sys.stdout.flush()
    caesar = ["".join(w) for w in unit_entropy.latin_words(Path(a.caesar))]
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang}: N61 連声型の書き換え ########", flush=True)
        summarize(f"ヴォイニッチ {lang}", [with_strength(measure(pt, V[lang][2], rng), pt)])
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        T = first_table(pt)
        for sigma in (0.3, 0.6):
            runs = []
            for seed in (1, 2, 3):
                i, e, _ = matched_source(caesar, LG, random.Random(seed))
                P = build12(i, e, LG, LC, random.Random(seed + 10), beta=0.0, compat=True, wfun=gram_prob(LG))
                P = apply_sandhi(P, T, sigma, random.Random(seed + 20))
                runs.append(with_strength(measure(P, lastf(P), rng), P))
            summarize(f"σ = {sigma}", runs)
            sys.stdout.flush()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 39 巡（第 4 段の 1 巡目）: N115（1 つ飛びの語のつながり）・N116（隣の行の少し違う語、1 回だけの芯の近さ）・N117（ラベルと本文）。

    python3 voynich/nevo_round39.py texts <Caesar> <Dante> <Culpeper>     # N115・N116
    python3 voynich/nevo_round39.py labels                                # N117
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round36 import near  # noqa: E402
from nevo_round38 import share  # noqa: E402


def mi_joint(J):
    n = sum(J.values())
    cx, cy = Counter(), Counter()
    for (a, b), v in J.items():
        cx[a] += v
        cy[b] += v
    return sum(v / n * math.log2(v * n / (cx[a] * cy[b])) for (a, b), v in J.items() if v > 0)


def skip_stats(inner, cls):
    tri = [(cls(a), cls(b), cls(c)) for l in inner for a, b, c in zip(l, l[1:], l[2:])]
    adj = mi_joint(Counter((a, b) for a, b, _ in tri))
    skp = mi_joint(Counter((a, c) for a, _, c in tri))
    ab, bc, pa = defaultdict(Counter), defaultdict(Counter), Counter()
    for a, b, c in tri:
        ab[a][b] += 1
        bc[b][c] += 1
        pa[a] += 1
    J = Counter()
    for a, na in pa.items():
        for b, nb in ab[a].items():
            tb = sum(bc[b].values())
            for c, nc in bc[b].items():
                J[(a, c)] += nb * nc / tb
    return adj, skp, mi_joint(J)


def n115(name, P, rng, runs=20):
    lines_ = [l for ls in P.values() for l in ls]
    inner = [l[1:-1] for l in lines_ if len(l) >= 5]
    top = {w: i for i, (w, _) in enumerate(Counter(w for l in lines_ for w in l).most_common(30))}
    cls = lambda w: top.get(w, -1)  # noqa: E731
    obs = skip_stats(inner, cls)
    nul = []
    for _ in range(runs):
        sh = []
        for l in inner:
            x = list(l)
            rng.shuffle(x)
            sh.append(x)
        nul.append(skip_stats(sh, cls))
    adj, skp, ch = (o - statistics.mean(n[i] for n in nul) for i, o in enumerate(obs))
    v = (skp - ch) / adj if adj > 0 else float("nan")
    print(f"  N115 {name:<34} 隣どうし {adj:+.4f}  1 つ飛び {skp:+.4f}  鎖で説明 {ch:+.4f}  余り {skp - ch:+.4f}  余り÷隣どうし {v:+.3f}", flush=True)
    return v


def n116a(name, P):
    a, b = share(P, False), share(P, True)
    rs, rn = a[0] / b[0], a[1] / b[1]
    v = (rn - 1) / (rs - 1) if abs(rs - 1) > 0.02 else float("nan")
    print(f"  N116a {name:<33} 同じ語の比 {rs:.2f}  1 字形違いの比 {rn:.2f}  指標 {v:+.2f}", flush=True)
    return v


def n116b(name, words, unit, rng):
    cnt = Counter(unit(w) for w in words)
    hap = [u for u, k in cnt.items() if k == 1 and len(u) >= 3]
    freq = [u for u, k in cnt.items() if k >= 5 and len(u) >= 2]
    bylen = defaultdict(list)
    for u in freq:
        bylen[len(u)].append(u)
    hit = lambda u: any(near(u, f) for L in (len(u) - 1, len(u), len(u) + 1) for f in bylen[L] if f != u)  # noqa: E731
    chain = defaultdict(Counter)
    for u in cnt:
        for a, b in zip(("^",) + tuple(u), tuple(u) + ("$",)):
            chain[a][b] += 1

    def rand(L):
        for _ in range(500):
            out, x = [], "^"
            while len(out) <= L:
                k, v = zip(*chain[x].items())
                x = rng.choices(k, v)[0]
                if x == "$":
                    break
                out.append(x)
            if len(out) == L and tuple(out) not in cnt and "".join(out) not in cnt:
                return tuple(out)
        return None

    obs = sum(hit(tuple(u)) for u in hap) / len(hap)
    rs = [r for r in (rand(len(u)) for u in hap) if r]
    nul = sum(hit(r) for r in rs) / len(rs)
    print(f"  N116b {name:<33} 1 回だけの芯 {len(hap)}  よく出る芯 {len(freq)}  近くにある割合 {obs:.3f}  基準 {nul:.3f}  実際÷基準 {obs / nul:.2f}", flush=True)
    return obs / nul


def texts(paths):
    V = voynich()
    rng = random.Random(2026)
    nat = {"Caesar（ラテン語）": words_any(Path(paths[0])), "Dante（イタリア語）": words_any(Path(paths[1])), "Culpeper（英語）": words_any(Path(paths[2]))}
    stem = lambda w: tuple(w[:-2]) if len(w) > 4 else tuple(w)  # noqa: E731
    core = lambda w: split(w)[1]  # noqa: E731
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        c = {"A": 0.4, "B": 0.6}[lang]
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        groups = {"平文あり": [], "平文なし": []}
        for name, ws in nat.items():
            groups["平文あり"].append((name, dict(line_unit.wrap([tuple(w) for w in ws[:cap]], 37))))
        caesar = nat["Caesar（ラテン語）"][:30000]
        _, _, coded = matched_source(caesar, LG, random.Random(1))
        groups["平文あり"].append(("符号表だけ（Caesar）", dict(line_unit.wrap(coded[:cap], 37))))
        it = iter(coded)
        src = lambda: next(it, None)  # noqa: E731
        groups["平文あり"].append(("平文ありのモデル（符号表＋写し）", build12(src, src, LG, LC, random.Random(11), c=0.4, beta=0.0, compat=True, wfun=gram_prob(LG), cap=cap)))
        kw = dict(mark=0.25) if lang == "A" else dict(mark=0.12, live=True)
        for seed in (1, 2):
            groups["平文なし"].append((f"最良のモデル 種 {seed}", build34(LG, LC, pt, random.Random(seed), c=c, cap=cap, **kw)))
        if lang == "A":
            for seed in (1, 2):
                groups["平文なし"].append((f"広い写し＋2 字形の表 種 {seed}", build34(LG, LC, pt, random.Random(seed), c=c, cap=cap, t2=True, widepick=True)))
        for label, f in (("N115 余り÷隣どうし", lambda n, P: n115(n, P, rng)), ("N116a 指標", n116a)):
            vals = {g: [f(f"{g}・{n}", P) for n, P in ps] for g, ps in groups.items()}
            v = f(f"ヴォイニッチ {lang}", pt)
            a, b = [x for x in vals["平文あり"] if x == x], [x for x in vals["平文なし"] if x == x]
            gap = max(min(a) - max(b), min(b) - max(a))
            spread = max(max(a) - min(a), max(b) - min(b))
            sep = gap > 0 and gap > spread
            print(f"  → {label}: 平文あり {min(a):+.3f}〜{max(a):+.3f}  平文なし {min(b):+.3f}〜{max(b):+.3f}  すき間 {gap:+.3f}  広がり {spread:.3f}  "
                  f"{'分かれた' if sep else '分かれない'}  ヴォイニッチ {v:+.3f}", flush=True)
        for name, ws in nat.items():
            n116b(name, ws[:cap], stem, rng)
        n116b(f"ヴォイニッチ {lang}", [w for ls in pt.values() for l in ls for w in l], core, rng)


BANDS = (1, 3, 9, 29)
band = lambda f: sum(f > b for b in BANDS)  # noqa: E731


def labels():
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(2026)
    for lang in ("A", "B"):
        text, lab = defaultdict(list), defaultdict(list)
        for ln in lines:
            if ln.page.get("L") != lang:
                continue
            ws = ivtff.words(ln.raw, opts)
            if ln.locus_class == "P":
                text[ln.page.name] += ws
            elif ln.locus_class == "L":
                lab[ln.page.name] += ws
        freq = Counter(w for ws in text.values() for w in ws)
        sets = {p: set(ws) for p, ws in text.items()}
        pages = [p for p in lab if p in text]
        other = lambda w, p: statistics.mean(w in sets[q] for q in sets if q != p)  # noqa: E731
        print(f"######## 言語 {lang}: ラベルと本文の両方がある頁 {len(pages)}、ラベルの語 {sum(len(lab[p]) for p in pages)}、本文のある頁 {len(text)} ########", flush=True)
        for title, keep in (("全てのラベル", lambda f: True), ("本文で 2 回以上出る語のラベル", lambda f: f >= 2)):
            own, oth, pown, poth, n = [], [], [], [], 0
            for p in pages:
                cnt = Counter(text[p])
                byband = defaultdict(list)
                for w in text[p]:
                    byband[band(freq[w])].append(w)
                for w in lab[p]:
                    if not keep(freq[w]) or not byband[band(freq[w])]:
                        continue
                    n += 1
                    own.append(w in sets[p])
                    oth.append(other(w, p))
                    ps = [rng.choice(byband[band(freq[w])]) for _ in range(200)]
                    pown.append(statistics.mean(cnt[x] >= 2 for x in ps))
                    poth.append(statistics.mean(other(x, p) for x in set(ps)))
            m = statistics.mean
            print(f"  {title}（{n} 語）: ラベル 同じ頁 {m(own):.3f}  他の頁 {m(oth):.3f}  比 {m(own) / m(oth):.2f} ／ にせのラベル 同じ頁 {m(pown):.3f}  他の頁 {m(poth):.3f}  比 {m(pown) / m(poth):.2f}", flush=True)
        seen = Counter(w for p in pages for w in lab[p])
        print(f"  ラベルの語の種類 {len(seen)}、うち本文に 1 度も出ない {sum(freq[w] == 0 for w in seen)}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "texts":
        texts(sys.argv[2:])
    else:
        labels()

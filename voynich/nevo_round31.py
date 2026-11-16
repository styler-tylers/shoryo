#!/usr/bin/env python3
"""nēvo による解析 第 31 巡: N91（自然言語での置き換え）・N92（好みの芯）・N93（芯への語頭・語末の付き方）。

    python3 voynich/nevo_round31.py <Caesar> <名前=文章 …>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat, build12  # noqa: E402
from nevo_round13 import gram_prob, matched_source  # noqa: E402
from nevo_round16 import summarize, with_strength  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round25 import score  # noqa: E402
from nevo_round27 import page_sim  # noqa: E402
from nevo_round29 import build_fav  # noqa: E402
from nevo_round30 import ratio  # noqa: E402

lastf = lambda P: [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))]  # noqa: E731
V_CORE = lambda w: split(w)[1]  # noqa: E731
V_AFF = lambda w: (split(w)[0], split(w)[2])  # noqa: E731


def cut(k):
    def end(w):
        return w[-k:] if len(w) >= 5 else (w[-1:] if len(w) >= 3 else "")
    return (lambda w: w[:len(w) - len(end(w))]), end


def surrogate(P, key, rng):
    pool = defaultdict(list)
    for ls in P.values():
        for l in ls:
            for w in l:
                pool[key(w)].append(w)
    n = ch = 0
    out = {}
    for k, ls in P.items():
        out[k] = []
        for l in ls:
            new = [rng.choice(pool[key(w)]) for w in l]
            n += len(l)
            ch += sum(a != b for a, b in zip(l, new))
            out[k].append(new)
    return out, ch / n


def retain(name, P, core, aff):
    r0 = ratio(P)
    out = [f"  {name:<28} 元 {r0:.2f}"]
    for label, key in (("語頭・語末（語尾）を保つ", aff), ("芯（語幹）を保つ", core)):
        rs, cs = zip(*[(ratio(Q), c) for Q, c in (surrogate(P, key, random.Random(s)) for s in range(5))])
        m = statistics.mean(rs)
        out.append(f"{label} {m:.2f} 残る {(m - 1) / (r0 - 1):.0%}（語が変わった割合 {statistics.mean(cs):.0%}）")
    print("   ".join(out), flush=True)


def n93(name, units, core, aff, rng, runs=200):
    pool = defaultdict(list)
    for u in units:
        for w in u:
            pool[core(w)].append(aff(w))
    num = den = wsum = 0.0
    ncore = 0
    for u in units:
        by = defaultdict(list)
        for w in u:
            by[core(w)].append(aff(w))
        for m, affs in by.items():
            n = len(affs)
            if n < 5 or len(pool[m]) == n:
                continue
            exp = statistics.mean(len(set(rng.sample(pool[m], n))) for _ in range(runs))
            num += len(set(affs)) / exp * n
            den += n
            ncore += 1
    print(f"  {name:<28} 実際 ÷ 期待 {num / den:.3f}（芯と単位の組 {ncore}、語 {int(den)}）", flush=True)


def blocks(P, size=8):
    pages = list(P.values())
    return [[w for ls in pages[i:i + size] for l in ls for w in l] for i in range(0, len(pages), size)]


def main() -> None:
    cae = Path(sys.argv[1])
    texts = {"Caesar（ラテン語）": cae}
    for a in sys.argv[2:]:
        k, v = a.split("=")
        texts[k] = Path(v)
    rng = random.Random(2026)
    V = voynich()
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    quire = {ln.page.name: ln.page.get("Q") for ln in lines}
    nat = {}
    print("=== N91 自然言語での置き換え ===", flush=True)
    for name, p in texts.items():
        ws = words_any(p)[:30000]
        P = dict(line_unit.wrap(ws, 37))
        nat[name] = P
        for k in (2, 3):
            st, en = cut(k)
            retain(f"{name} 語尾 {k} 字", P, st, en)
    res = {}
    caesar = words_any(cae)[:30000]
    for lang in ("A", "B"):
        pt = V[lang][0]
        print(f"\n######## 言語 {lang} ########", flush=True)
        retain(f"ヴォイニッチ {lang}", pt, V_CORE, V_AFF)
        LG = LengthGrammar(pt)
        LC = Compat(LG, pt)
        ref = with_strength(measure(pt, V[lang][2], rng), pt)
        _, _, coded = matched_source(caesar, LG, random.Random(1))
        it = iter(coded)
        src = lambda: next(it, None)  # noqa: E731
        Pp = build12(src, src, LG, LC, random.Random(11), c=0.4, beta=0.0, compat=True, wfun=gram_prob(LG))
        retain(f"平文あり（段 2）{lang}", Pp, V_CORE, V_AFF)
        Pf = build_fav(LG, LC, pt, random.Random(1), 0.5)
        retain(f"平文なし（好みの語）{lang}", Pf, V_CORE, V_AFF)
        print("=== N92 好みの芯 ===", flush=True)
        runs, Pc1 = [], None
        for seed in (1, 2):
            P = build_fav(LG, LC, pt, random.Random(seed), 0.5, size=60, core=True)
            Pc1 = Pc1 or P
            page_sim(f"好みの芯 種 {seed}", P)
            retain(f"好みの芯 {lang} 種 {seed}", P, V_CORE, V_AFF)
            runs.append(with_strength(measure(P, lastf(P), rng), P))
        summarize("好みの芯", runs)
        score("好みの芯", runs, ref)
        res[lang] = (pt, Pp, Pf, Pc1)
    print("\n=== N93 芯への語頭・語末の付き方（実際の種類の数 ÷ 期待）===", flush=True)
    for lang in ("A", "B"):
        pt, Pp, Pf, Pc = res[lang]
        byq = defaultdict(list)
        for k, ls in pt.items():
            byq[quire[k]].extend(w for l in ls for w in l)
        n93(f"ヴォイニッチ {lang}（綴じの単位 {len(byq)}）", list(byq.values()), V_CORE, V_AFF, rng)
        n93(f"平文あり（段 2）{lang}", blocks(Pp), V_CORE, V_AFF, rng)
        n93(f"平文なし（好みの語）{lang}", blocks(Pf), V_CORE, V_AFF, rng)
        n93(f"平文なし（好みの芯）{lang}", blocks(Pc), V_CORE, V_AFF, rng)
    for name, P in nat.items():
        st, en = cut(2)
        n93(f"{name} 語尾 2 字", blocks(P), st, en, rng)


if __name__ == "__main__":
    main()

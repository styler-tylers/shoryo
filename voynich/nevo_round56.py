#!/usr/bin/env python3
"""nēvo による解析 第 56 巡: N166（言語 B の文字だけの頁）・N167（モデルの二面の仕組み）・N168（語頭の字形の入れ替わり）。

    python3 voynich/nevo_round56.py <texts の場所> <タガログ語などの場所>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import skew, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round47 import edit_pos  # noqa: E402
from nevo_round52 import three  # noqa: E402


def sk(lines_):
    return skew([len(w) for l in lines_ for w in l])


def perm_p(target, pool, rng, runs=1000):
    obs = sk(target)
    n = sum(len(l) for l in target)
    hit = 0
    for _ in range(runs):
        pick, c = [], 0
        for l in rng.sample(pool, len(pool)):
            if c >= n:
                break
            pick.append(l)
            c += len(l)
        hit += sk(pick) >= obs
    return obs, sk(pool), hit / runs


def H(c):
    t = sum(c.values())
    return -sum(v / t * math.log2(v / t) for v in c.values() if v)


def endinfo(ws):
    ends = Counter("".join(split(w)[2]) for w in ws)
    by = defaultdict(set)
    for w in set(ws):
        h, m, e = split(w)
        by[(h, m)].add(e)
    return len(ends), H(ends), sum(len(v) for v in by.values()) / len(by)


def perturb_end(lines_, rng):
    core = Counter(g for l in lines_ for w in l for g in split(w)[1])
    gk, gv = zip(*core.items())
    out = []
    for l in lines_:
        nl = []
        for w in l:
            h, m, e = split(w)
            if e:
                e = tuple(rng.choices(gk, gv, k=len(e)))
            nl.append((h + m + e) or w)
        out.append(nl)
    return out


def head_changes(ws):
    types = sorted({tuple(w) for w in ws if len(w) >= 3})
    by_len = defaultdict(list)
    for w in types:
        by_len[len(w)].append(w)
    c = Counter()
    for w in types:
        for L in (len(w), len(w) + 1):
            for v in by_len.get(L, []):
                if L == len(w) and v <= w:
                    continue
                if edit_pos(w, v) != "頭":
                    continue
                if len(v) == len(w):
                    if w[0] != v[0]:
                        c["/".join(sorted(("".join(w[:1]), "".join(v[:1]))))] += 1
                    else:
                        c["（最初以外）"] += 1
                elif v[1:] == w:
                    c["+" + v[0]] += 1
                else:
                    c["（最初以外）"] += 1
    c.pop("（最初以外）", None)
    return c


def main(tdir, pdir):
    T, P = Path(tdir), Path(pdir)
    V = voynich()
    a = corpus.make_parser("").parse_args([])
    a.locus = "P"
    _, L = corpus.load_lines(a)
    meta = {ln.page.name: (ln.page.get("I"), ln.page.get("H"), ln.page.get("Q")) for ln in L}
    pt = V["B"][0]
    rng = random.Random(2026)
    print("=== N166 言語 B の文字だけの頁 ===", flush=True)
    tl = [l for pg, ls in pt.items() if meta[pg][0] == "T" for l in ls]
    print(f"  文字だけの頁: {sorted(pg for pg in pt if meta[pg][0] == 'T')}  行 {len(tl)}  語 {sum(map(len, tl))}  行あたり {sum(map(len, tl)) / len(tl):.1f} 語  歪度 {sk(tl):+.2f}", flush=True)
    for label, cond in (("(i) 同じ書き手 2 の図のある頁", lambda m: m[1] == "2"),
                        ("(ii) 同じ綴じ N の図のある頁", lambda m: m[2] == "N"),
                        ("（参考）同じ綴じ M の図のある頁", lambda m: m[2] == "M"),
                        ("（参考）言語 B の図のある頁すべて", lambda m: True)):
        pool = [l for pg, ls in pt.items() if meta[pg][0] != "T" and cond(meta[pg]) for l in ls]
        tgt = [l for pg, ls in pt.items() if meta[pg][0] == "T" and (cond(meta[pg]) or label.startswith("（参考）言語"))
               for l in ls] if not label.startswith("（参考）同じ綴じ M") else [l for pg, ls in pt.items() if meta[pg][0] == "T" and meta[pg][2] == "M" for l in ls]
        o, base, p = perm_p(tgt, pool, rng)
        print(f"  {label:<26} 文字だけ {o:+.2f}（{sum(map(len, tgt))} 語） 比べる相手 {base:+.2f}（{len(pool)} 行, 行あたり {sum(map(len, pool)) / max(1, len(pool)):.1f} 語）  p {p:.3f}", flush=True)
    pics = [l for pg, ls in pt.items() if meta[pg][0] != "T" for l in ls]
    lo, hi = [l for l in pics if len(l) <= 9], [l for l in pics if len(l) >= 10]
    print(f"  (iii) 図のある頁: 9 語以下の行 {sk(lo):+.2f}（{len(lo)} 行）  10 語以上の行 {sk(hi):+.2f}（{len(hi)} 行）  差 {sk(hi) - sk(lo):+.2f}", flush=True)

    print("=== N167 モデルの二面の仕組み ===", flush=True)
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        p_ = V[lang][0]
        vw = [w for ls in p_.values() for l in ls for w in l]
        cap = len(vw)
        LG = LengthGrammar(p_)
        M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=cap, **kw)
        ml = [l for ls in M.values() for l in ls]
        mw = [w for l in ml for w in l]
        for name, ws in ((f"ヴォイニッチ {lang}", vw), (f"モデル {lang}", mw)):
            n, h, wd = endinfo(ws)
            print(f"  {name:<16} 語末の欄の種類 {n}  エントロピー {h:.2f}  語尾の幅 {wd:.2f}", flush=True)
        three(f"モデル {lang}・もと", ml)
        three(f"モデル {lang}・語末の欄を崩す", perturb_end(ml, random.Random(7)))

    print("=== N168 語頭の字形の入れ替わり ===", flush=True)
    w = lambda n: [tuple(x) for x in words_any(P / f"pg{n}.txt")]  # noqa: E731
    sets = [("ヴォイニッチ A", [w_ for ls in V["A"][0].values() for l in ls for w_ in l]),
            ("ヴォイニッチ B", [w_ for ls in V["B"][0].values() for l in ls for w_ in l]),
            ("タガログ語（13773）", w(13773)[:10000]), ("セブアノ語（20820）", w(20820)[:10000]),
            ("Caesar", [tuple(x) for x in words_any(T / "pg218.txt")][:20000])]
    for name, ws in sets:
        c = head_changes(ws)
        n = sum(c.values())
        top = c.most_common(5)
        print(f"  {name:<18} 組 {n:>5}  上位 5 つの割合 {sum(v for _, v in top) / n:.0%}  種類 {len(c)}  "
              + "、".join(f"{k} {v / n:.0%}" for k, v in c.most_common(8)), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])

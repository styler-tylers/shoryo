#!/usr/bin/env python3
"""nēvo による解析 第 71 巡: N213（目印の位置の一覧）・N214（薬学の容器と植物のラベル）・N215（VTN の語の長さ）。

    python3 voynich/nevo_round71.py <texts の場所>
"""

from __future__ import annotations

import csv
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round61 import G_PAR  # noqa: E402
from nevo_round69 import synth_words  # noqa: E402
from nevo_round70 import set_uni  # noqa: E402

HERE = Path(__file__).resolve().parent


def stats(ws):
    sp = [split(w) for w in ws]
    return (statistics.mean(len(m) for _, m, _ in sp), statistics.mean(any(g in G_PAR for g in m) for _, m, _ in sp),
            statistics.mean("".join(h) == "o" for h, _, _ in sp), statistics.mean(len(e) for _, _, e in sp), len(ws))


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def sim(a, b):
    return 1 - lev(a, b) / max(len(a), len(b))


def main(tdir):
    T = Path(tdir)
    V = voynich()
    print("=== N213 目印の位置の一覧 ===", flush=True)
    pos = defaultdict(list)
    for lang in ("A", "B"):
        for v in flagged(V, lang).values():
            for j, (l, st) in enumerate(v):
                if not l:
                    continue
                if st:
                    pos["P4 頁の最初の語" if j == 0 else "P3 頁の途中の段落の最初の語"].append(l[0])
                    pos["P5 段落の最初の行の 2 語目以降"].extend(l[1:])
                else:
                    pos["P2 ふつうの行の最初の語"].append(l[0])
                    if len(l) >= 2:
                        pos["P6 ふつうの行の最後の語"].append(l[-1])
                    pos["P1 ふつうの行の中ほど"].extend(l[1:-1])
    a = corpus.make_parser("").parse_args([])
    a.locus = "L"
    _, L = corpus.load_lines(a)
    opts = corpus.word_options(a)
    pos["P7 ラベル"] = [tuple(ivtff.glyphs(w)) for ln in L for w in ivtff.words(ln.raw, opts)]
    res = {}
    for k in sorted(pos):
        res[k] = stats(pos[k])
        c, pf, o, e, n = res[k]
        print(f"  {k:<26} 語 {n:>6}  芯 {c:.2f}  芯に p/f {pf:.1%}  語頭 o {o:.1%}  語末 {e:.2f}", flush=True)
    P1, P2 = res["P1 ふつうの行の中ほど"], res["P2 ふつうの行の最初の語"]
    others = [v[2] for k, v in res.items() if not k.startswith("P7")]
    print(f"  (a) P2 − P1 の芯 {P2[0] - P1[0]:+.2f}  (b) P7 の語頭 o − 他の最大 {res['P7 ラベル'][2] - max(others):+.1%}"
          f"  (c) P4 の p/f {res['P4 頁の最初の語'][1]:.1%} 対 P3 {res['P3 頁の途中の段落の最初の語'][1]:.1%}"
          f"  (d) P6 − P1 の語末 {res['P6 ふつうの行の最後の語'][3] - P1[3]:+.2f}", flush=True)

    print("=== N214 薬学の容器と植物のラベル ===", flush=True)
    rows = list(csv.DictReader(open(HERE / "notes" / "薬学ラベル対応表.csv", encoding="utf-8-sig")))
    groups = defaultdict(lambda: {"jar": None, "plants": []})
    for r in rows:
        key = (r["頁"], r["段"])
        g = tuple(x for w in r["ラベル"].split() for x in ivtff.glyphs(w))
        if not g:
            continue
        if r["種類"] == "薬壺":
            groups[key]["jar"] = g
        else:
            groups[key]["plants"].append(g)
    bypage = defaultdict(list)
    for (pg, dan), g in groups.items():
        if g["jar"] and g["plants"]:
            bypage[pg].append(g)
    pages = {pg: gs for pg, gs in bypage.items() if len(gs) >= 2}
    print(f"  使う頁 {len(pages)}、段 {sum(map(len, pages.values()))}、薬草のラベル {sum(len(g['plants']) for gs in pages.values() for g in gs)}", flush=True)

    def score(pg_groups):
        jp, pp = [], []
        for gs in pg_groups.values():
            for g in gs:
                jp += [sim(g["jar"], p) for p in g["plants"]]
                pl = g["plants"]
                pp += [sim(pl[i], pl[j]) for i in range(len(pl)) for j in range(i + 1, len(pl))]
        return statistics.mean(jp), statistics.mean(pp)
    o_jp, o_pp = score(pages)
    rng = random.Random(2026)
    hj = hp = 0
    R = 5000
    for _ in range(R):
        sh = {}
        for pg, gs in pages.items():
            allp = [p for g in gs for p in g["plants"]]
            rng.shuffle(allp)
            ng, i = [], 0
            for g in gs:
                n = len(g["plants"])
                ng.append({"jar": g["jar"], "plants": allp[i:i + n]})
                i += n
            sh[pg] = ng
        j, p = score(sh)
        hj += j >= o_jp
        hp += p >= o_pp
    print(f"  (i) 薬壺 × 同じ段の薬草 {o_jp:.3f}  p {hj / R:.4f}   (ii) 同じ段の薬草どうし {o_pp:.3f}  p {hp / R:.4f}", flush=True)

    print("=== N215 VTN の語の長さを合わせる（偶数番目の頁と比べる）===", flush=True)
    p_ = V["B"][0]
    pages_ = list(p_)
    odd = {k: p_[k] for k in pages_[0::2]}
    even = {k: p_[k] for k in pages_[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))
    three("ヴォイニッチ B・偶数番目の頁", [l for ls in even.values() for l in ls])
    syn = synth_words(ow, 600000, random.Random(5))
    target = Counter(len(w) for w in ow)
    bylen = defaultdict(list)
    for w in syn:
        bylen[len(w)].append(w)
    r = random.Random(6)
    fitted = []
    tot = sum(target.values())
    for n, c in target.items():
        want = round(300000 * c / tot)
        pool = bylen.get(n, [])
        if pool:
            fitted += r.choices(pool, k=want)
    r.shuffle(fitted)
    print(f"  長さを合わせた作った語 {len(fitted)}", flush=True)
    set_uni(0.75)
    cae = r68.letters_any(T / "pg218.txt")
    r68.show("VTN・長さを合わせた在庫・1 文字 0.75", r68.make_text(r68.VTN, fitted, cae, r68.para_lengths(Fo), len(ew)), ref_e)


if __name__ == "__main__":
    main(sys.argv[1])

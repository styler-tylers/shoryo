#!/usr/bin/env python3
"""nēvo による解析 第 69 巡: N207（字形の型から在庫を作った VTN）・N208（単独の語の割合を増やす）。

    python3 voynich/nevo_round69.py <texts の場所>
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round67 import growth  # noqa: E402

S, E = "^", "$"


def synth_words(words, n, rng):
    nxt = defaultdict(Counter)
    ends = defaultdict(Counter)
    for w in words:
        h, m, e = split(w)
        k = tuple(h) + tuple(m)
        if not k:
            continue
        seq = (S,) + k + (E,)
        for a, b in zip(seq, seq[1:]):
            nxt[a][b] += 1
        ends[k[-1]][tuple(e)] += 1
    table = {a: (list(c), list(c.values())) for a, c in nxt.items()}
    etab = {a: (list(c), list(c.values())) for a, c in ends.items()}
    out = []
    while len(out) < n:
        k, a = [], S
        while True:
            xs, ws = table[a]
            b = rng.choices(xs, ws)[0]
            if b == E or len(k) >= 12:
                break
            k.append(b)
            a = b
        if not k:
            continue
        xs, ws = etab.get(k[-1], ([()], [1]))
        out.append(tuple(k) + rng.choices(xs, ws)[0])
    return out


def main(tdir):
    T = Path(tdir)
    V = voynich()
    p_ = V["B"][0]
    vw = [w for ls in p_.values() for l in ls for w in l]
    cap = len(vw)
    ref = measure(p_, V["B"][2], random.Random(2026))
    cae = r68.letters_any(T / "pg218.txt")
    pages = list(p_)
    odd = {k: p_[k] for k in pages[0::2]}
    even = {k: p_[k] for k in pages[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))
    print("=== N207 字形の型から在庫を作った VTN（奇数番目の頁で作り、偶数番目の頁と比べる）===", flush=True)
    three("ヴォイニッチ B・偶数番目の頁", [l for ls in even.values() for l in ls])
    _, sle = growth([[w for l in ls for w in l] for ls in even.values()], random.Random(11))
    print(f"    V3 {ref_e['V3']:.2f}  語尾の幅 {endinfo(ew)[2]:.2f}  在庫の増え方 {sle:.3f}", flush=True)
    syn = synth_words(ow, 300000, random.Random(5))
    print(f"  作った語 {len(syn)}、語の種類 {len(set(syn))}（奇数番目の頁の語 {len(ow)}・種類 {len(set(ow))}）", flush=True)
    r68.show("VTN・作った在庫", r68.make_text(r68.VTN, syn, cae, r68.para_lengths(Fo), len(ew)), ref_e)
    r68.show("VTN・奇数番目の頁の語の在庫（参考）", r68.make_text(r68.VTN, ow, cae, r68.para_lengths(Fo), len(ew)), ref_e)

    print("=== N208 単独の語の割合を増やす（VTN, 全ての頁の在庫, 言語 B と比べる）===", flush=True)
    import nevo_round63 as r63
    import nevo_round64 as r64
    plens = r68.para_lengths(flagged(V, "B"))
    for uni in (0.45, 0.60, 0.75):
        r63.P_BIGRAM = 1 - uni
        r64.P_BIGRAM = 1 - uni
        r68.show(f"VTN・1 文字の単位 {uni}", r68.make_text(r68.VTN, vw, cae, plens, cap), ref)


if __name__ == "__main__":
    main(sys.argv[1])

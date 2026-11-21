#!/usr/bin/env python3
"""nēvo による解析 第 68 巡: N204（VT ＋ Naibbe の単独の語）・N205（平文の言語を替える）・N206（半分の頁で表を作る）。

    python3 voynich/nevo_round68.py <texts の場所> <lang2 の場所> <lang3 の場所>
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round61 import G_PAR  # noqa: E402
from nevo_round62 import ADD, SWAP  # noqa: E402
from nevo_round64 import units_of  # noqa: E402
from nevo_round67 import P_NEW, SIM, VT, growth  # noqa: E402


def letters_any(path):
    return [c for w in words_any(path) for c in w]


class VTN(VT):
    def __init__(self, vwords, unit_rank, rng):
        letters = [u for u in unit_rank if len(u) == 1]
        top = [w for w, _ in Counter(vwords).most_common() if not any(x in G_PAR for x in w)]
        uw = top[:6 * len(letters)]
        self.uni_hc = {tuple(split(w)[0]) + tuple(split(w)[1]) for w in uw}
        super().__init__([w for w in vwords if (tuple(split(w)[0]) + tuple(split(w)[1])) not in self.uni_hc], unit_rank, rng)
        self.uni = {}
        self.uowner = {}
        for r, c in enumerate(letters):
            lst = [uw[min(r * 6 + t, len(uw) - 1)] for t in range(6)]
            self.uni[c] = Counter({w: x for w, x in zip(lst, [40, 15, 15, 10, 10, 10])})
            for w in lst:
                self.uowner.setdefault(w, c)

    def word(self, u):
        if len(u) == 2:
            k = self.key(u)
            return k + self.end(k)
        H = self.uni[u]
        if self.rng.random() < P_NEW:
            base = list(self.rng.choices(list(H), list(H.values()))[0])
            pos = [i for i, x in enumerate(base) if x in SIM]
            if pos:
                i = self.rng.choice(pos)
                base[i] = SIM[base[i]]
                nw = tuple(base)
                if self.uowner.get(nw, u) == u:
                    self.uowner[nw] = u
                    H[nw] += 1
                    return nw
        w = self.rng.choices(list(H), list(H.values()))[0]
        H[w] += 1
        return w


def para_lengths(F):
    out = []
    for v in F.values():
        c = 0
        for _, st in v:
            if st and c:
                out.append(c)
                c = 0
            c += 1
        if c:
            out.append(c)
    return out


def make_text(cls, vw, letters, plens, cap, seed=3):
    cu = units_of(letters, random.Random(1))
    rank_ = [u for u, _ in Counter(cu).most_common()]
    vt = cls(vw, rank_, random.Random(seed))
    if cls is VT:
        words = [k + vt.end(k) for k in (vt.key(u) for u in cu[:cap])]
    else:
        words = [vt.word(u) for u in cu[:cap]]
    P = dict(line_unit.wrap(words, 37))
    keys = list(P)
    lines_ = [l for k in keys for l in P[k]]
    r = random.Random(9)
    flags = []
    while len(flags) < len(lines_):
        L = r.choice(plens)
        flags += [True] + [False] * (L - 1)
    flags = flags[:len(lines_)]

    def firstline(w):
        h, m, e = split(w)
        m = [SWAP[x] if x in SWAP and r.random() < 0.9 else x for x in m]
        h = [SWAP[x] if x in SWAP and r.random() < 0.9 else x for x in h]
        if r.random() < 0.4:
            m.insert(r.randint(0, len(m)), r.choice(ADD))
        return tuple(h) + tuple(m) + tuple(e)
    new_lines = [[firstline(w) for w in l] if f else l for l, f in zip(lines_, flags)]
    P1, j = {}, 0
    for k in keys:
        P1[k] = new_lines[j:j + len(P[k])]
        j += len(P[k])
    return P1


def show(name, P, ref):
    lines_ = [l for ls in P.values() for l in ls]
    ws = [w for l in lines_ for w in l]
    h2 = three(name, lines_)[0]
    report(name, P, ref, random.Random(2026))
    _, sl = growth([[w for l in ls for w in l] for ls in P.values()], random.Random(11))
    print(f"    語尾の幅 {endinfo(ws)[2]:.2f}  在庫の増え方の傾き {sl:.3f}  語の種類 {len(set(ws))}", flush=True)
    return h2


def main(tdir, l2, l3):
    T, L2, L3 = Path(tdir), Path(l2), Path(l3)
    V = voynich()
    p_ = V["B"][0]
    vw = [w for ls in p_.values() for l in ls for w in l]
    cap = len(vw)
    ref = measure(p_, V["B"][2], random.Random(2026))
    plens = para_lengths(flagged(V, "B"))
    cae = letters_any(T / "pg218.txt")
    print("=== N204 VT ＋ Naibbe の単独の語（VTN, 言語 B と比べる）===", flush=True)
    _, slv = growth([[w for l in ls for w in l] for ls in p_.values()], random.Random(11))
    print(f"  ヴォイニッチ B: V3 {ref['V3']:.2f}  語尾の幅 {endinfo(vw)[2]:.2f}  在庫の増え方の傾き {slv:.3f}", flush=True)
    show("VT（第 67 巡の形）", make_text(VT, vw, cae, plens, cap), ref)
    show("VTN", make_text(VTN, vw, cae, plens, cap), ref)

    print("=== N205 平文の言語を替える（VT）===", flush=True)
    h2s = {}
    for name, path in (("ラテン語 Caesar", T / "pg218.txt"), ("イタリア語 Dante", T / "pg1012.txt"), ("英語 Culpeper", T / "pg49513.txt"),
                       ("フィンランド語", L2 / "pg8451.txt"), ("タガログ語", L3 / "pg13773.txt")):
        h2s[name] = show(f"VT・{name}", make_text(VT, vw, letters_any(path), plens, cap), ref)
    print(f"  → h2 の幅 {max(h2s.values()) - min(h2s.values()):.2f}  B の範囲に入った言語 {[k for k, v in h2s.items() if abs(v - 2.10) <= 0.15]}", flush=True)

    print("=== N206 半分の頁で表を作る ===", flush=True)
    pages = list(p_)
    odd = {k: p_[k] for k in pages[0::2]}
    even = {k: p_[k] for k in pages[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))
    _, sle = growth([[w for l in ls for w in l] for ls in even.values()], random.Random(11))
    three("ヴォイニッチ B・偶数番目の頁", [l for ls in even.values() for l in ls])
    print(f"    語尾の幅 {endinfo(ew)[2]:.2f}  在庫の増え方の傾き {sle:.3f}  語 {len(ew)}", flush=True)
    show("VT・奇数番目の頁で作った表", make_text(VT, ow, cae, para_lengths(Fo), len(ew)), ref_e)
    show("VT・全ての頁で作った表（同じ語の数）", make_text(VT, vw, cae, plens, len(ew)), ref_e)


if __name__ == "__main__":
    main(*sys.argv[1:4])

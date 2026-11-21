#!/usr/bin/env python3
"""nēvo による解析 第 66 巡: N197（語尾の幅で Naibbe 暗号を直す）・N198（Naibbe 暗号に段落の最初の行の規則）。

    python3 voynich/nevo_round66.py <texts の場所> <tables.json>
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import nevo_round65 as r65  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round61 import G_PAR, core_len, gstart, share  # noqa: E402
from nevo_round62 import SWAP  # noqa: E402


class Variant(r65.Naibbe):
    def __init__(self, T, same_table=False, p_uni=r65.P_UNI):
        super().__init__(T)
        self.same, self.p_uni = same_table, p_uni

    def encrypt(self, letters, rng, with_units=False):
        out, units, i = [], [], 0
        while i < len(letters):
            if i + 1 < len(letters) and rng.random() >= self.p_uni:
                a = rng.choices(r65.TABLES, r65.CARDS)[0]
                b = a if self.same else rng.choices(r65.TABLES, r65.CARDS)[0]
                out.append(self.ps[f"{a}_{letters[i]}_prefix"] + self.ps[f"{b}_{letters[i + 1]}_suffix"])
                units.append(letters[i] + letters[i + 1])
                i += 2
            else:
                out.append(self.uni[f"unigram_{rng.choices(r65.TABLES, r65.CARDS)[0]}_{letters[i]}"])
                units.append(letters[i])
                i += 1
        return (out, units) if with_units else out


def summary(name, nb, letters, cap, ref):
    ws, us = nb.encrypt(letters, random.Random(1), with_units=True)
    ws, us = ws[:cap], us[:cap]
    gw = [r65.g(w) for w in ws]
    P = dict(line_unit.wrap(gw, 37))
    three(name, [l for ls in P.values() for l in ls])
    report(name, P, ref, random.Random(2026))
    rd = [nb.readings(w) for w in ws]
    uniq = sum(len(r) == 1 and u in r for r, u in zip(rd, us)) / len(ws)
    n, h, wd = endinfo(gw)
    print(f"    語尾の幅 {wd:.2f}  語の種類 {len(set(gw))}  1 語で読みが決まる {uniq:.1%}", flush=True)
    return P


def main(tdir, tables):
    T = Path(tdir)
    V = voynich()
    TB = json.load(open(tables))
    cae = r65.naibbe_letters(T / "pg218.txt")
    p_ = V["B"][0]
    cap = sum(len(l) for ls in p_.values() for l in ls)
    ref = measure(p_, V["B"][2], random.Random(2026))
    print("=== N197 語尾の幅で Naibbe 暗号を直す（言語 B と比べる）===", flush=True)
    P0 = summary("元の使い方", Variant(TB), cae, cap, ref)
    summary("V1 語尾側も同じ表", Variant(TB, same_table=True), cae, cap, ref)
    summary("V2 1 文字の単位 0.70", Variant(TB, p_uni=0.70), cae, cap, ref)

    print("=== N198 Naibbe 暗号に段落の最初の行の規則 ===", flush=True)
    F = flagged(V, "B")
    plens = []
    for v in F.values():
        c = 0
        for _, st in v:
            if st and c:
                plens.append(c)
                c = 0
            c += 1
        if c:
            plens.append(c)
    rng = random.Random(9)
    lines_ = [l for ls in P0.values() for l in ls]
    flags, i = [], 0
    while i < len(lines_):
        L = rng.choice(plens)
        flags += [True] + [False] * (L - 1)
        i += L
    flags = flags[:len(lines_)]

    def sw(w):
        return tuple(SWAP[x] if x in SWAP and rng.random() < 0.9 else x for x in w)
    new_lines = [[sw(w) for w in l] if f else l for l, f in zip(lines_, flags)]
    keys = list(P0.keys())
    sizes = [len(P0[k]) for k in keys]
    P1, j = {}, 0
    for k, n in zip(keys, sizes):
        P1[k] = new_lines[j:j + n]
        j += n
    for name, ls in (("規則なし", lines_), ("規則あり", new_lines)):
        first = [l for l, f in zip(ls, flags) if f]
        other = [l for l, f in zip(ls, flags) if not f]
        print(f"  {name}: 段落の頭の絞首台 {share(first, G_PAR) / max(1e-9, share(other, G_PAR)):.1f} 倍  芯の長さの差 {core_len(first) - core_len(other):+.3f}"
              f"  絞首台で始まる語 {gstart(first) / gstart(other):.2f} 倍", flush=True)
    three("規則あり", new_lines)
    report("規則あり", P1, ref, random.Random(2026))


if __name__ == "__main__":
    main(*sys.argv[1:3])

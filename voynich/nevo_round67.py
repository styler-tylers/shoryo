#!/usr/bin/env python3
"""nēvo による解析 第 67 巡: N201（ヴォイニッチ型の冗長な暗号 VT）・N202（字形の在庫の増え方）。

    python3 voynich/nevo_round67.py <texts の場所> <tables.json>
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import nevo_round65 as r65  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import family  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round61 import G_PAR, core_len, gstart, share  # noqa: E402
from nevo_round62 import ADD, SWAP  # noqa: E402
from nevo_round63 import WEIGHTS, letters_of  # noqa: E402
from nevo_round64 import units_of  # noqa: E402

SIM = {"ch": "sh", "sh": "ch", "k": "t", "t": "k", "o": "a", "a": "o", "l": "r", "r": "l"}
P_NEW = 0.15


class VT:
    def __init__(self, vwords, unit_rank, rng):
        hc = Counter()
        self.ends = defaultdict(Counter)
        self.ends_last = defaultdict(Counter)
        for w in vwords:
            h, m, e = split(w)
            k = tuple(h) + tuple(m)
            if not k:
                continue
            self.ends[k][tuple(e)] += 1
            self.ends_last[k[-1]][tuple(e)] += 1
            if not any(x in G_PAR for x in k):
                hc[k] += 1
        inv = [k for k, _ in hc.most_common()]
        U = len(unit_rank)
        self.homo = {}
        self.owner = {}
        for r, u in enumerate(unit_rank):
            lst = []
            for t in range(6):
                j = t * U + r
                k = inv[j] if j < len(inv) else inv[r]
                lst.append(k)
                self.owner.setdefault(k, u)
            self.homo[u] = Counter({k: w for k, w in zip(lst, [40, 15, 15, 10, 10, 10])})
        self.rng = rng

    def key(self, u):
        H = self.homo[u]
        if self.rng.random() < P_NEW:
            base = list(self.rng.choices(list(H), list(H.values()))[0])
            pos = [i for i, x in enumerate(base) if x in SIM]
            if pos:
                i = self.rng.choice(pos)
                base[i] = SIM[base[i]]
                nk = tuple(base)
                if self.owner.get(nk, u) == u:
                    self.owner[nk] = u
                    H[nk] += 1
                    return nk
        k = self.rng.choices(list(H), list(H.values()))[0]
        H[k] += 1
        return k

    def end(self, k):
        c = self.ends.get(k) or self.ends_last.get(k[-1]) or Counter({(): 1})
        a, b = zip(*c.items())
        return self.rng.choices(a, b)[0]

    def write(self, units):
        return [(self.key(u), u) for u in units]


def growth(pages_words, rng, runs=10, ns=(1000, 2000, 4000, 8000, 16000, 23000)):
    """pages_words: [[語, …] 頁ごと]。語頭 ＋ 芯の組の種類の数の平均と、n ≥ 2000 の傾き"""
    acc = defaultdict(list)
    total = sum(map(len, pages_words))
    for _ in range(runs):
        order = rng.sample(pages_words, len(pages_words))
        seen, c, j = set(), 0, 0
        flat = [w for p in order for w in p]
        for n in ns:
            if n > total:
                break
            while c < n:
                h, m, e = split(flat[c])
                seen.add(tuple(h) + tuple(m))
                c += 1
            acc[n].append(len(seen))
    pts = [(n, sum(v) / len(v)) for n, v in acc.items()]
    xs = [math.log(n) for n, _ in pts if n >= 2000]
    ys = [math.log(v) for n, v in pts if n >= 2000]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return pts, slope


def main(tdir, tables):
    T = Path(tdir)
    V = voynich()
    p_ = V["B"][0]
    vw = [w for ls in p_.values() for l in ls for w in l]
    cap = len(vw)
    ref = measure(p_, V["B"][2], random.Random(2026))
    cl = letters_of(T / "pg218.txt")
    cu = units_of(cl, random.Random(1))
    rank_ = [u for u, _ in Counter(cu).most_common()]
    vt = VT(vw, rank_, random.Random(3))
    pairs = vt.write(cu[:cap])
    words = [k + vt.end(k) for k, _ in pairs]
    P = dict(line_unit.wrap(words, 37))
    keys = list(P)
    lines_ = [l for k in keys for l in P[k]]
    # 段落
    F = flagged(V, "B")
    plens, c = [], 0
    for v in F.values():
        c = 0
        for _, st in v:
            if st and c:
                plens.append(c)
                c = 0
            c += 1
        if c:
            plens.append(c)
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
        n = len(P[k])
        P1[k] = new_lines[j:j + n]
        j += n
    print("=== N201 ヴォイニッチ型の冗長な暗号 VT（言語 B と比べる）===", flush=True)
    three("ヴォイニッチ B", [l for ls in p_.values() for l in ls])
    three("VT", new_lines)
    report("VT", P1, ref, random.Random(2026))
    ws = [w for l in new_lines for w in l]
    f = family(ws)
    n_, h_, wd = endinfo(ws)
    first = [l for l, fl in zip(new_lines, flags) if fl]
    other = [l for l, fl in zip(new_lines, flags) if not fl]
    print(f"    語尾の幅 {wd:.2f}（ヴォイニッチ B {endinfo(vw)[2]:.2f}）  家族の語頭 {f[0]:.3f}  語の種類 {len(set(ws))}（{len(set(vw))}）", flush=True)
    print(f"    段落の頭の絞首台 {share(first, G_PAR) / max(1e-9, share(other, G_PAR)):.1f} 倍  芯の長さの差 {core_len(first) - core_len(other):+.3f}  絞首台で始まる語 {gstart(first) / gstart(other):.2f} 倍", flush=True)
    # 読み戻し（段落の最初の行以外）
    idx, ok, tot = 0, 0, 0
    for l, fl in zip(lines_, flags):
        for w in l:
            k, u = pairs[idx]
            idx += 1
            if fl:
                continue
            h, m, e = split(w)
            tot += 1
            ok += vt.owner.get(tuple(h) + tuple(m)) == u
    print(f"    読み戻し（段落の最初の行以外, 語を欄に分けて語頭 ＋ 芯を引く）{ok / tot:.1%}", flush=True)

    print("=== N202 字形の在庫の増え方（語頭 ＋ 芯の組の種類）===", flush=True)
    LG = LengthGrammar(p_)
    M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=cap, mark=0.12, live=True, c=0.6)
    nb = r65.Naibbe(json.load(open(tables)))
    nw = [r65.g(w) for w in nb.encrypt(r65.naibbe_letters(T / "pg218.txt"), random.Random(1))[:cap]]
    from nevo_round64 import Code2
    cd = Code2(vw, rank_)
    c2 = cd.encrypt(cu, random.Random(3))[:cap]
    sets = [("ヴォイニッチ B", [[w for l in ls for w in l] for ls in p_.values()]),
            ("平文なしのモデル B", [[w for l in ls for w in l] for ls in M.values()]),
            ("Naibbe 暗号", [[w for l in ls for w in l] for _, ls in line_unit.wrap(nw, 37)]),
            ("表 2（決まった表）", [[w for l in ls for w in l] for _, ls in line_unit.wrap(c2, 37)]),
            ("VT", [[w for l in ls for w in l] for ls in P1.values()])]
    for name, pw in sets:
        pts, sl = growth(pw, random.Random(11))
        print(f"  {name:<18} 傾き {sl:.3f}  " + "  ".join(f"{n}:{v:.0f}" for n, v in pts), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])

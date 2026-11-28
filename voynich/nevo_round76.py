#!/usr/bin/env python3
"""nēvo による解析 第 76 巡: N227（語の長さの形が平文で動く理由）。

    python3 voynich/nevo_round76.py <texts の場所>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import skew  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round64 import units_of  # noqa: E402
from nevo_round70 import set_uni  # noqa: E402
from nevo_round74 import VTNlook  # noqa: E402
from nevo_round75 import stream_from  # noqa: E402


def estimate(vt, units, rng, n=50000):
    cu = Counter(units)
    us, ws = zip(*cu.items())
    out = []
    for u in rng.choices(us, ws, k=n):
        if len(u) == 2 and u in vt.homo:
            H = vt.homo[u]
            k = rng.choices(list(H), list(H.values()))[0]
            out.append(len(k) + len(vt.end(k)))
        elif u in vt.uni:
            H = vt.uni[u]
            out.append(len(rng.choices(list(H), list(H.values()))[0]))
    return skew(out)


def main(tdir):
    T = Path(tdir)
    V = voynich()
    p_ = V["B"][0]
    kb = list(p_)
    odd = {k: p_[k] for k in kb[0::2]}
    even = {k: p_[k] for k in kb[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    st = stream_from(ow)
    set_uni(0.75)
    VTNlook.q = 0.3
    print("=== N227 語の長さの形が平文で動く理由 ===", flush=True)
    res = {}
    for name, f in (("Caesar", "pg218.txt"), ("Descartes", "pg23306.txt"), ("Dante", "pg1012.txt")):
        letters = r68.letters_any(T / f)
        cu = units_of(letters, random.Random(1))
        rank_ = [u for u, _ in Counter(cu).most_common()]
        obs, est = [], []
        for seed in (3, 4, 5):
            vt0 = VTNlook(st, rank_, random.Random(seed))
            est.append(estimate(vt0, cu, random.Random(seed)))
            P = r68.make_text(VTNlook, st, letters, r68.para_lengths(Fo), len(ew), seed=seed)
            obs.append(skew([len(w) for ls in P.values() for l in ls for w in l]))
        top = Counter(cu)
        uni_share = sum(v for u, v in top.items() if len(u) == 1) / len(cu)
        res[name] = (statistics.mean(obs), statistics.mean(est))
        print(f"  {name:<10} 実際の歪度 {statistics.mean(obs):+.3f}（{', '.join(f'{x:+.2f}' for x in obs)}）  見積もり {statistics.mean(est):+.3f}（{', '.join(f'{x:+.2f}' for x in est)}）"
              f"  差 {statistics.mean(obs) - statistics.mean(est):+.3f}  単位の種類 {len(top)}  1 文字の単位の割合 {uni_share:.2f}", flush=True)
    oo = sorted(res, key=lambda k: res[k][0])
    eo = sorted(res, key=lambda k: res[k][1])
    print(f"  大小の順: 実際 {oo}  見積もり {eo}  {'同じ' if oo == eo else '違う'}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

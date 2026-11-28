#!/usr/bin/env python3
"""第 60 巡 N180 の事後の点検: 直した「またぐ」の対照が 0 を含まなかった理由を探る。
基準から (i) 前の行そのもの（k = i）も除く、(ii) さらに同じ段落の行だけに限る、の 2 通りで対照を測る。

    python3 voynich/nevo_round60_n180_posthoc.py
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from line_unit import mi  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round59 import flagged, shuffled  # noqa: E402


def matagu2(F, rng, own=True, runs=50):
    e2, h2 = (lambda w: "".join(w[-2:])), (lambda w: "".join(w[:2]))
    obs, pools = [], []
    for v in F.values():
        v = [(l, st) for l, st in v if l]
        cand = [k for k in range(len(v)) if not v[k][1]]
        for i in range(len(v) - 1):
            if v[i + 1][1]:
                continue
            o = [k for k in cand if k != i + 1 and (own or k != i)]
            if not o:
                continue
            obs.append((e2(v[i][0][-1]), h2(v[i + 1][0][0])))
            pools.append([h2(v[k][0][0]) for k in o])
    m = mi(obs)
    return m - statistics.mean(mi([(a, rng.choice(p)) for (a, _), p in zip(obs, pools)]) for _ in range(runs))


def main():
    V = voynich()
    for lang in ("A", "B"):
        F = flagged(V, lang)
        for own in (True, False):
            ctrl = sorted(matagu2(shuffled(F, s), random.Random(5), own) for s in range(20))
            v = matagu2(F, random.Random(5), own)
            print(f"  {lang} 前の行を基準に{'含む' if own else '含めない'}: 対照 {ctrl[1]:+.4f}〜{ctrl[18]:+.4f} 中央 {statistics.median(ctrl):+.4f}  値 {v:+.4f}", flush=True)
        # 頁の大きさによる偏りの確かめ: 頁ごとに候補の数が違う。候補が 1 つしか無い組を除く
    print("  （参考）MI の標本の偏り: 独立に作った組で、同じ数の組の MI の差を測る", flush=True)
    r = random.Random(1)
    F = flagged(V, "A")
    heads = [("".join(l[0][:2])) for v in F.values() for l, st in v if l]
    ends = [("".join(l[-1][-2:])) for v in F.values() for l, st in v if l]
    xs = [mi([(r.choice(ends), r.choice(heads)) for _ in range(1300)]) for _ in range(20)]
    print(f"  独立な 1300 組の MI: 平均 {statistics.mean(xs):.4f}  標準偏差 {statistics.pstdev(xs):.4f}", flush=True)


if __name__ == "__main__":
    main()

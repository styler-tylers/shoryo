#!/usr/bin/env python3
"""nēvo による解析 第 23 巡: N67（語の端の字形の組の表）・N68（母音・子音の交代との比較）。

    python3 voynich/nevo_round23.py <文章 …>
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round21 import words_any  # noqa: E402

VV = {"o", "a", "e", "y", "i"}
VN = set("aeiouy")


def pairs_of(lines_):
    return [(a[-1], b[0]) for l in lines_ if len(l) >= 4 for a, b in zip(l[1:-1], l[2:-1])]


def n67(name, pairs, top=10):
    c = Counter(pairs)
    ea, sb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    n = len(pairs)
    rows = []
    for (a, b), o in c.items():
        e = ea[a] * sb[b] / n
        z = (o - e) / math.sqrt(e * (1 - ea[a] / n) * (1 - sb[b] / n)) if e > 0 else 0
        rows.append((z, a, b, o, e))
    for a, b in {(a, b) for a in list(ea)[:0] for b in sb}:
        pass
    # 期待 20 以上で観測 0 の組も「避ける」に入れる
    for a in ea:
        for b in sb:
            if (a, b) not in c:
                e = ea[a] * sb[b] / n
                if e >= 20:
                    z = -e / math.sqrt(e * (1 - ea[a] / n) * (1 - sb[b] / n))
                    rows.append((z, a, b, 0, e))
    pref = sorted([r for r in rows if r[0] > 4], reverse=True)[:top]
    avoid = sorted([r for r in rows if r[0] < -4])[:top]
    topend = ", ".join(f"{g} {v / n:.0%}" for g, v in ea.most_common(6))
    topst = ", ".join(f"{g} {v / n:.0%}" for g, v in sb.most_common(6))
    print(f"  {name}: 組 {n}、語の終わりの字形 {len(ea)} 種類（{topend}）、始まりの字形 {len(sb)} 種類（{topst}）")
    print("    好む組: " + ", ".join(f"-{a}→{b}- {o}/{e:.0f}（z {z:+.0f}）" for z, a, b, o, e in pref))
    print("    避ける組: " + ", ".join(f"-{a}→{b}- {o}/{e:.0f}（z {z:+.0f}）" for z, a, b, o, e in avoid))


def n68(name, pairs, vowels):
    t = Counter((a in vowels, b in vowels) for a, b in pairs)
    vv, vc, cv, cc = t[(True, True)] + .5, t[(True, False)] + .5, t[(False, True)] + .5, t[(False, False)] + .5
    lor = math.log((vv * cc) / (vc * cv))
    full = line_unit.mi(pairs)
    cls = line_unit.mi([(a in vowels, b in vowels) for a, b in pairs])
    pv_end = (vv + vc) / (vv + vc + cv + cc)
    pv_start = (vv + cv) / (vv + vc + cv + cc)
    print(f"  {name:<22} 母音らしい語末 {pv_end:.0%}・語頭 {pv_start:.0%}  対数オッズ比 {lor:+.2f}  "
          f"境目の結び付き {full:.3f} のうち母音・子音で説明 {cls / full:.0%}")


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:]]
    V = voynich()
    nat = {}
    for p in paths:
        ws = words_any(p)[:30000]
        nat[p.stem] = pairs_of([[tuple(w) for w in l] for _, ls in line_unit.wrap(ws, 37) for l in ls])
    print("=== N67 語の端の字形の組（|z| > 4）===")
    for lang in ("A", "B"):
        n67(f"ヴォイニッチ {lang}", pairs_of([l for ls in V[lang][0].values() for l in ls]))
    for name in list(nat)[:2]:
        n67(f"{name}（参照）", nat[name], top=6)
    print("\n=== N68 母音・子音の交代 ===")
    for lang in ("A", "B"):
        n68(f"ヴォイニッチ {lang}", pairs_of([l for ls in V[lang][0].values() for l in ls]), VV)
    for name, pr in nat.items():
        n68(name, pr, VN)


if __name__ == "__main__":
    main()

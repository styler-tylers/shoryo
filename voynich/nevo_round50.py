#!/usr/bin/env python3
"""nēvo による解析 第 50 巡: N148（語頭・語中で語形を変える言語を増やす）・N149（タガログ語をこれまでの量で）。

    python3 voynich/nevo_round50.py <texts の場所> <フィリピンの言語の場所>
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round30 import ratio as page_ratio  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import crossing, family  # noqa: E402
from nevo_round48 import end_entropy, shuffled_end  # noqa: E402


def main(tdir, pdir):
    rng = random.Random(2026)
    T, P = Path(tdir), Path(pdir)
    w = lambda *ns: [tuple(x) for n in ns for x in words_any(P / f"pg{n}.txt")]  # noqa: E731
    sets = [("タガログ語 2（13773）", w(13773)[:10000]), ("タガログ語 3（14215・14270・14271）", w(14215, 14270, 14271)[:10000]),
            ("セブアノ語（20820）", w(20820)[:10000]), ("イロカノ語（15548・15624）", w(15548, 15624)[:10000])]
    print("=== N148 語頭・語中で語形を変える言語 ===", flush=True)
    for name, ws in sets:
        h, m, e, n = family(ws)
        se = shuffled_end(ws, rng, runs=50)
        ok = e <= 0.25 and h + m >= 0.75 and e / se < 1.05
        print(f"  {name:<32} 語 {len(ws):>5}  組 {n:>5}  語頭 {h:.2f}  語中 {m:.2f}  語末 {e:.2f}  比 {e / se:.2f}  H末 {end_entropy(ws):.2f}  → {'予測どおり' if ok else '予測と違う'}", flush=True)

    print("=== N149 タガログ語をこれまでの量で ===", flush=True)
    V = voynich()
    tg = [tuple(x) for x in words_any(P / "pg13773.txt")]
    cae = [tuple(x) for x in words_any(T / "pg218.txt")]
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        c = report("Caesar（ラテン語）", dict(line_unit.wrap(cae[:cap], 37)), ref, rng)
        t = report("タガログ語（13773）", dict(line_unit.wrap(tg[:cap], 37)), ref, rng)
        print(f"  → Caesar {c}、タガログ語 {t}", flush=True)
    for name, Pg in (("ヴォイニッチ A", V["A"][0]), ("ヴォイニッチ B", V["B"][0]),
                     ("Caesar", dict(line_unit.wrap(cae[:23000], 37))), ("タガログ語", dict(line_unit.wrap(tg[:23000], 37)))):
        x, n = crossing(Pg, rng)
        print(f"  {name:<14} 行をまたぐつながり（同じ頁の別の行と比べる）{x:+.4f}  頁のまとまり {page_ratio(Pg):.2f}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])

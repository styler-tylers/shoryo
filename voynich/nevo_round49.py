#!/usr/bin/env python3
"""nēvo による解析 第 49 巡: N145（語幹と語尾の結び付きの比の正式な検定）・N146（語末の字形の少なさの整理）。

    python3 voynich/nevo_round49.py <texts の場所> <ポリグラフィア III の表 CSV> <意味のない文章の場所> <マザーグース pg10607> <新しい言語の場所>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scripts_compare  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round46 import gibberish, p3_cipher, p3_table  # noqa: E402
from nevo_round47 import family  # noqa: E402
from nevo_round48 import end_entropy, shuffled_end  # noqa: E402


def ratio(ws, rng):
    h, m, e, n = family(ws)
    se = shuffled_end(ws, rng, runs=50)
    return e, se, (e / se if se else float("nan")), n


def inventory(ws):
    c = Counter(w[-1] for w in ws if w)
    n = sum(c.values())
    acc, k = 0, 0
    for _, v in c.most_common():
        acc += v
        k += 1
        if acc >= 0.9 * n:
            break
    top, tv = c.most_common(1)[0]
    return end_entropy(ws), k, "".join(top) if isinstance(top, tuple) else top, tv / n


def main(tdir, csv, gdir, goose, ldir):
    rng = random.Random(2026)
    V = voynich()
    T = Path(tdir)
    L = Path(ldir)
    cae = words_any(T / "pg218.txt")
    head, table = p3_table(csv)
    letters = [c for c in "".join(cae).replace("j", "i").replace("v", "u") if c in head]
    p2 = [w for ls in p3_cipher(letters[:120000], table, "P2", random.Random(1)).values() for l in ls for w in l]
    vw = lambda lang: [w for ls in V[lang][0].values() for l in ls for w in l]  # noqa: E731
    tup = lambda ws: [tuple(w) for w in ws]  # noqa: E731
    second = lambda ws: ws[10000:20000]  # noqa: E731
    test = [
        ("ヴォイニッチ B（2 つ目の 1 万語）", "非", second(vw("B"))),
        ("マザーグース（2 つ目）", "非", second(tup(words_any(Path(goose))))),
        ("暗号 P2（2 つ目）", "非", second(p2)),
        ("Caesar（2 つ目）", "自", second(tup(cae))),
        ("Dante（2 つ目）", "自", second(tup(words_any(T / "pg1012.txt")))),
        ("Culpeper（2 つ目）", "自", second(tup(words_any(T / "pg49513.txt")))),
        ("フィンランド語", "自", tup(words_any(L / "pg8451.txt"))[:10000]),
        ("ハンガリー語", "自", tup(words_any(L / "pg19744.txt"))[:10000]),
        ("エスペラント", "自", tup(words_any(L / "pg11511.txt"))[3000:13000]),
        ("タガログ語", "自", tup(words_any(L / "pg13156.txt") + words_any(L / "pg13320.txt"))[:10000]),
    ]
    ref = [("ヴォイニッチ A（最初の 1 万語, 参考）", "参", vw("A")[:10000]),
           ("ヴォイニッチ B（最初の 1 万語, 参考）", "参", vw("B")[:10000]),
           ("意味のない文章（参考）", "参", [w for ls in gibberish(gdir).values() for l in ls for w in l][:10000])]
    print("=== N145 語幹と語尾の結び付きの比（実際の語末の割合 ÷ 最後の字を入れ替えたとき）===", flush=True)
    res = {"自": [], "非": []}
    for name, g, ws in test + ref:
        e, se, r, n = ratio(ws, rng)
        if g in res:
            res[g].append(r)
        print(f"  [{g}] {name:<30} 語 {len(ws):>5}  組 {n:>5}  語末 {e:.2f}  入れ替え {se:.2f}  比 {r:.2f}", flush=True)
    a, b = res["自"], res["非"]
    print(f"  → 自然言語 {min(a):.2f}〜{max(a):.2f}、言語でないもの {min(b):.2f}〜{max(b):.2f}：{'分かれた' if min(a) > max(b) else '分かれない'}", flush=True)
    print("=== N146 語末の字形の少なさ ===", flush=True)
    e4 = [tuple(scripts_compare.syllable_code_e4("".join(w))) for w in unit_entropy.latin_words(T / "pg218.txt")][:10000]
    rows = [("ヴォイニッチ A", vw("A")[:10000]), ("ヴォイニッチ B", vw("B")[:10000])] + [(n, ws) for n, _, ws in test[1:]] + \
           [("意味のない文章", ref[2][2]), ("音節の暗号 E4（Caesar）", e4)]
    out = []
    for name, ws in rows:
        H, k, top, share = inventory(ws)
        out.append((H, name, k, top, share))
    for H, name, k, top, share in sorted(out):
        print(f"  {name:<24} H末 {H:.2f}  9 割を覆う語末の字 {k:>2} 種類  最も多い語末「{top}」{share:.0%}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:6])

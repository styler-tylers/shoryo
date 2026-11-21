#!/usr/bin/env python3
"""nēvo による解析 第 51 巡: N151（空白の位置と語末形）・N152（境目の字形の規則, 欧州以外）・N153（バイバインの形のタガログ語）。

    python3 voynich/nevo_round51.py <texts の場所> <セム語・ギリシア語の場所> <フィリピンの言語の場所> <新しい言語の場所>
"""

from __future__ import annotations

import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import scripts_compare as scx  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, skew  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round22 import H  # noqa: E402
from nevo_round23 import pairs_of  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import family  # noqa: E402


def space_guess(lines_):
    sp = Counter()
    for l in lines_:
        for wi, w in enumerate(l):
            for a, b in zip(w, w[1:]):
                sp[(a, b, 0)] += 1
            if wi + 1 < len(l):
                sp[(w[-1], l[wi + 1][0], 1)] += 1
    tot = Counter()
    byxy = defaultdict(Counter)
    for (a, b, s), v in sp.items():
        tot[s] += v
        byxy[(a, b)][s] += v
    n = sum(tot.values())
    return 1 - sum(sum(c.values()) / n * H(c) for c in byxy.values()) / H(tot)


def lines(words, width=37):
    return [l for _, ls in line_unit.wrap([tuple(w) for w in words], width) for l in ls]


VOW = {"a": "A", "e": "I", "i": "I", "o": "U", "u": "U"}


def baybayin(word):
    w = word.lower().replace("qu", "k").replace("c", "k").replace("f", "p").replace("v", "b").replace("z", "s").replace("j", "h")
    units, i = [], 0
    while i < len(w):
        if w[i] in VOW:
            units.append(("", VOW[w[i]]))
            i += 1
            continue
        c = "ng" if w[i:i + 2] == "ng" else w[i]
        j = i + len(c)
        if j < len(w) and w[j] in VOW:
            units.append((c, VOW[w[j]]))
            i = j + 1
        else:
            i = j  # 音節末の子音は書かない
    return tuple(c + v for c, v in units)


def main(tdir, sdir, pdir, ldir):
    rng = random.Random(2026)
    T, S, P, L = Path(tdir), Path(sdir), Path(pdir), Path(ldir)
    V = voynich()
    greek = re.findall(r"[α-ωάέήίόύώϊϋΐΰς]+", (S / "pg27073.txt").read_text(encoding="utf-8").lower())
    heb = ["".join(w) for p in ("pg4778.txt", "pg5139.txt", "pg18291.txt") for w in scx.hebrew_words(S / p)]
    ara = ["".join(w) for w in scx.arabic_words(S / "arabic1.txt")]
    texts = [("ヘブライ語", heb), ("ギリシア語", greek), ("アラビア語", ara),
             ("タガログ語（13773）", words_any(P / "pg13773.txt")), ("セブアノ語（20820）", words_any(P / "pg20820.txt")),
             ("フィンランド語（8451）", words_any(L / "pg8451.txt")), ("ハンガリー語（19744）", words_any(L / "pg19744.txt")),
             ("Caesar（ラテン語）", words_any(T / "pg218.txt")), ("ウェールズ語（67424）", words_any(T / "pg67424.txt"))]
    print("=== N151 空白の当てやすさ・N152 境目の結び付き ===", flush=True)
    for lang in ("A", "B"):
        ls = [l for p in V[lang][0].values() for l in p]
        print(f"  ヴォイニッチ {lang:<18} 空白の当てやすさ {space_guess(ls):.0%}  境目の結び付き {line_unit.mi(pairs_of(ls)):.3f}", flush=True)
    for name, ws in texts:
        ls = lines(ws[:30000])
        print(f"  {name:<24} 語 {min(len(ws), 30000):>5}  空白の当てやすさ {space_guess(ls):.0%}  境目の結び付き {line_unit.mi(pairs_of(ls)):.3f}", flush=True)

    print("=== N153 バイバインの形のタガログ語 ===", flush=True)
    tg = words_any(P / "pg13773.txt")
    bb = [baybayin(w) for w in tg]
    bb = [w for w in bb if w]
    print(f"  例: {' '.join(tg[300:308])} → {' '.join('·'.join(w) for w in bb[300:308])}", flush=True)
    print(f"  字の種類: ローマ字 {len(set(c for w in tg for c in w))}、バイバインの形 {len(set(c for w in bb for c in w))}", flush=True)
    for name, ws in (("タガログ語 ローマ字", [tuple(w) for w in tg]), ("タガログ語 バイバインの形", bb)):
        h, m, e, n = family(ws[:10000])
        print(f"  {name:<22} 語の長さの歪度 {skew([len(w) for w in ws[:23000]]):.2f}  語の家族 語頭 {h:.2f}・語中 {m:.2f}・語末 {e:.2f}（組 {n}）", flush=True)
    cae = [tuple(w) for w in words_any(T / "pg218.txt")]
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        c = report("Caesar（ラテン語）", dict(line_unit.wrap(cae[:cap], 37)), ref, rng)
        r = report("タガログ語 ローマ字", dict(line_unit.wrap([tuple(w) for w in tg[:cap]], 37)), ref, rng)
        b = report("タガログ語 バイバインの形", dict(line_unit.wrap(bb[:cap], 12)), ref, rng)
        print(f"  → Caesar {c}、ローマ字 {r}、バイバインの形 {b}（バイバインの形は 1 字 ＝ 1 音節なので幅 12 字で折る）", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:5])

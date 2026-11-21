#!/usr/bin/env python3
"""nēvo による解析 第 70 巡: N210（字形の型の在庫の VTN と単独の語の割合）・N211（ラベルと冗長な暗号）・N212（ラベルの欄の作り）。

    python3 voynich/nevo_round70.py <texts の場所> <tables.json>
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import nevo_round63 as r63  # noqa: E402
import nevo_round64 as r64  # noqa: E402
import nevo_round65 as r65  # noqa: E402
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round61 import G_PAR  # noqa: E402
from nevo_round67 import growth  # noqa: E402
from nevo_round69 import synth_words  # noqa: E402


def set_uni(u):
    r63.P_BIGRAM = 1 - u
    r64.P_BIGRAM = 1 - u


def describe(name, ws):
    sl = [tuple(len(x) for x in split(w)) for w in ws]
    o = statistics.mean(w[0] == "o" for w in ws)
    pf = statistics.mean(any(g in G_PAR for g in split(w)[1]) for w in ws)
    print(f"  {name:<22} 語 {len(ws):>6}  長さ {statistics.mean(map(len, ws)):.2f}  語頭 {statistics.mean(a for a, _, _ in sl):.2f}  芯 {statistics.mean(b for _, b, _ in sl):.2f}"
          f"  語末 {statistics.mean(c for _, _, c in sl):.2f}  o で始まる {o:.1%}  芯に p/f {pf:.1%}", flush=True)
    return statistics.mean(map(len, ws)), o, [statistics.mean(x[i] for x in sl) for i in range(3)], pf


def main(tdir, tables):
    T = Path(tdir)
    V = voynich()
    p_ = V["B"][0]
    pages = list(p_)
    odd = {k: p_[k] for k in pages[0::2]}
    even = {k: p_[k] for k in pages[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))
    cae = r68.letters_any(T / "pg218.txt")
    print("=== N210 字形の型の在庫の VTN（偶数番目の頁と比べる）===", flush=True)
    three("ヴォイニッチ B・偶数番目の頁", [l for ls in even.values() for l in ls])
    _, sle = growth([[w for l in ls for w in l] for ls in even.values()], random.Random(11))
    print(f"    語尾の幅 {endinfo(ew)[2]:.2f}  在庫の増え方 {sle:.3f}", flush=True)
    syn = synth_words(ow, 300000, random.Random(5))
    for u in (0.60, 0.75):
        set_uni(u)
        r68.show(f"VTN・作った在庫・1 文字 {u}", r68.make_text(r68.VTN, syn, cae, r68.para_lengths(Fo), len(ew)), ref_e)

    print("=== N211・N212 ラベル ===", flush=True)
    a = corpus.make_parser("").parse_args([])
    a.locus = "L"
    _, L = corpus.load_lines(a)
    opts = corpus.word_options(a)
    labels = [tuple(ivtff.glyphs(w)) for ln in L for w in ivtff.words(ln.raw, opts)]
    per = Counter(len(ivtff.words(ln.raw, opts)) for ln in L)
    print(f"  （記述）ラベル 1 つあたりの語の数: {dict(sorted(per.items()))}", flush=True)
    text, first, other = [], [], []
    for lang in ("A", "B"):
        F = flagged(V, lang)
        for v in F.values():
            for l, st in v:
                (first if st else other).extend(l)
                text.extend(l)
    lab = describe("ラベル", labels)
    describe("本文の語（全て）", text)
    fst = describe("本文・段落の最初の行", first)
    oth = describe("本文・それ以外の行", other)
    set_uni(0.60)
    vw = [w for ls in p_.values() for l in ls for w in l]
    vt = r68.make_text(r68.VTN, vw, cae, r68.para_lengths(flagged(V, "B")), len(vw))
    vtw = [w for ls in vt.values() for l in ls for w in l]
    vtn = describe("VTN（1 文字 0.60）", vtw)
    nb = r65.Naibbe(json.load(open(tables)))
    nbw = [r65.g(w) for w in nb.encrypt(r65.naibbe_letters(T / "pg218.txt"), random.Random(1))[:len(vw)]]
    nbd = describe("Naibbe 暗号", nbw)
    print(f"  N211: o で始まる VTN {vtn[1]:.1%}・Naibbe {nbd[1]:.1%}（ラベル {lab[1]:.1%}）  長さの差 ラベル − VTN {lab[0] - vtn[0]:+.2f}・ラベル − Naibbe {lab[0] - nbd[0]:+.2f}", flush=True)
    d = [x - y for x, y in zip(lab[2], oth[2])]
    print(f"  N212: ラベル − それ以外の行: 語頭 {d[0]:+.2f}  芯 {d[1]:+.2f}  語末 {d[2]:+.2f}（長さ {lab[0] - oth[0]:+.2f}）  芯に p/f の比 {lab[3] / oth[3]:.2f}", flush=True)
    heads = Counter("".join(split(w)[0]) or "（なし）" for w in labels)
    theads = Counter("".join(split(w)[0]) or "（なし）" for w in other)
    print("  語頭の欄の上位（ラベル）: " + "、".join(f"{k} {v / len(labels):.0%}" for k, v in heads.most_common(6))
          + "  ／（それ以外の行）: " + "、".join(f"{k} {v / len(other):.0%}" for k, v in theads.most_common(6)), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])

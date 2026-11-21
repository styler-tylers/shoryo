#!/usr/bin/env python3
"""nēvo による解析 第 55 巡: N163（題材ごとの語の長さの対称）・N164（語頭の欄の変わり方）。

    python3 voynich/nevo_round55.py <texts の場所> <タガログ語などの場所> <ポリグラフィア III の表 CSV>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import skew, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round46 import p3_cipher, p3_table  # noqa: E402
from nevo_round47 import family  # noqa: E402
from nevo_round54 import clip, e4_of  # noqa: E402

CH = 1500
NAMES = {"H": "植物", "P": "薬", "S": "星", "B": "生体", "T": "文字だけ", "C": "宇宙", "A": "天文", "Z": "黄道"}


def chunks(ws, n=CH):
    return [ws[i:i + n] for i in range(0, len(ws) - n + 1, n)]


def sk(ws):
    return skew([len(w) for w in ws])


def main(tdir, pdir, csv):
    T, P = Path(tdir), Path(pdir)
    V = voynich()
    a = corpus.make_parser("").parse_args([])
    a.locus = "P"
    _, L = corpus.load_lines(a)
    ill = {ln.page.name: ln.page.get("I") for ln in L}
    print("=== N163 題材ごとの語の長さの歪度 ===", flush=True)
    vsd = {}
    for lang in ("A", "B"):
        pt = V[lang][0]
        allw = [w for ls in pt.values() for l in ls for w in l]
        base = sk(allw)
        groups = defaultdict(list)
        for pg, ls in pt.items():
            groups[ill.get(pg)].extend(w for l in ls for w in l)
        print(f"  ヴォイニッチ {lang} 全体 {base:+.2f}（{len(allw)} 語）", flush=True)
        cs = []
        for g, ws in sorted(groups.items(), key=lambda x: -len(x[1])):
            if len(ws) < CH:
                print(f"    {NAMES.get(g, g)}（{len(ws)} 語, 少ないので使わない）{sk(ws):+.2f}", flush=True)
                continue
            v = sk(ws)
            cs += [sk(c) for c in chunks(ws)]
            print(f"    {NAMES.get(g, g)}（{len(ws)} 語）{v:+.2f}  全体との差 {v - base:+.2f}  {'±0.15 以内' if abs(v - base) <= 0.15 else '±0.15 の外'}", flush=True)
        vsd[lang] = statistics.pstdev(cs)
        print(f"    1500 語の塊 {len(cs)} 個の歪度: 標準偏差 {vsd[lang]:.3f}（{min(cs):+.2f}〜{max(cs):+.2f}）", flush=True)
    sds = []
    for name, f in (("Caesar", "pg218.txt"), ("Descartes", "pg23306.txt"), ("Dante", "pg1012.txt"), ("Culpeper", "pg49513.txt")):
        ws = words_any(T / f)
        cs = [sk(c) for c in chunks(ws)]
        sds.append(statistics.pstdev(cs))
        print(f"  {name:<10} 全体 {sk(ws):+.2f}  塊 {len(cs)} 個  標準偏差 {sds[-1]:.3f}（{min(cs):+.2f}〜{max(cs):+.2f}）", flush=True)
    med = statistics.median(sds)
    for lang, v in vsd.items():
        print(f"  → ヴォイニッチ {lang} {v:.3f}、ふつうの文章の中央値 {med:.3f}: {'以下' if v <= med else 'より大きい'}", flush=True)

    print("=== N164 語頭の欄の変わり方 ===", flush=True)
    rows = []
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        pt = V[lang][0]
        ws = [w for ls in pt.values() for l in ls for w in l]
        rows.append((f"ヴォイニッチ {lang}", ws))
        cap = len(ws)
        LG = LengthGrammar(pt)
        M = build34(LG, Compat(LG, pt), pt, random.Random(1), cap=cap, **kw)
        rows.append((f"平文なしのモデル {lang}", [w for ls in M.values() for l in ls for w in l]))
    w = lambda *ns: [tuple(x) for n in ns for x in words_any(P / f"pg{n}.txt")]  # noqa: E731
    rows += [("タガログ語（13773）", w(13773)[:10000]), ("セブアノ語（20820）", w(20820)[:10000])]
    cae = e4_of(T / "pg218.txt")
    rows += [("E4・そのまま", cae[:20000]), ("E4・略し K=8", clip(cae, 8)[:20000])]
    head, table = p3_table(csv)
    letters = [c for c in "".join(words_any(T / "pg218.txt")).replace("j", "i").replace("v", "u") if c in head]
    rows.append(("トリテミウスの暗号 P2", [w for ls in p3_cipher(letters[:60000], table, "P2", random.Random(1)).values() for l in ls for w in l]))
    rows.append(("Caesar", [tuple(x) for x in words_any(T / "pg218.txt")][:20000]))
    for name, ws in rows:
        h, m, e, n = family(ws)
        print(f"  {name:<22} 組 {n:>6}  語頭 {h:.2f}  語中 {m:.2f}  語末 {e:.2f}", flush=True)
    for lang in ("A", "B"):
        ws = set(w for ls in V[lang][0].values() for l in ls for w in l)
        byce = defaultdict(set)
        for x in ws:
            h, c, e = split(x)
            byce[(c, e)].add(h)
        print(f"  ヴォイニッチ {lang}: 語頭の幅（芯と語末が同じ語の種類あたり）{sum(len(v) for v in byce.values()) / len(byce):.2f}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])

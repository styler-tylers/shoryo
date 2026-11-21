#!/usr/bin/env python3
"""nēvo による解析 第 72 巡: N216（ラベルと本文の語の家族）・N217（黄道のラベルの輪と位置）・N218（VTN の長さと出る数）。

    python3 voynich/nevo_round72.py <texts の場所>
"""

from __future__ import annotations

import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round47 import edit_pos  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round69 import synth_words  # noqa: E402
from nevo_round70 import set_uni  # noqa: E402
from nevo_round71 import sim  # noqa: E402

HERE = Path(__file__).resolve().parent
GL = None


def neighbors(w, vocab_by_len):
    out = []
    for L in (len(w) - 1, len(w), len(w) + 1):
        for v in vocab_by_len.get(L, ()):
            if v != w:
                p = edit_pos(w, v)
                if p:
                    out.append((v, p))
    return out


def zodiac(opts):
    cur, zod = None, False
    grp = defaultdict(int)
    out = []
    for line in open(HERE / "data" / "ZL3b-n.txt", encoding="utf-8", errors="replace"):
        m = re.match(r"<(f\d+[rv]\d*)>\s+<!(.*)>", line)
        if m:
            cur, zod = m.group(1), "$I=Z" in m.group(2)
            continue
        m = re.match(r"<(f\d+[rv]\d*)\.(\d+),(.)(\w\w)>\s+(?:<!([0-9:]+)>)?(.*)", line)
        if not m or not cur or not zod:
            continue
        pg, n, _, typ, clk, txt = m.groups()
        if typ[0] in "CR":
            grp[pg] += 1
        if typ == "Lz" and grp[pg] in (1, 2):
            ws = [tuple(ivtff.glyphs(w)) for w in ivtff.words(txt, opts)]
            ws = [w for w in ws if w]
            if ws:
                h, mm = map(int, clk.split(":")) if clk else (None, None)
                out.append(dict(page=pg, ring=grp[pg], num=int(n), clock=(h % 12) * 60 + mm if clk else None, word=ws[0], words=ws))
    return out


def main(tdir):
    T = Path(tdir)
    V = voynich()
    a = corpus.make_parser("").parse_args([])
    a.locus = "L"
    _, L = corpus.load_lines(a)
    opts = corpus.word_options(a)
    print("=== N216 ラベルと本文の語の家族 ===", flush=True)
    labels = {tuple(ivtff.glyphs(w)) for ln in L for w in ivtff.words(ln.raw, opts)}
    labels = {w for w in labels if len(w) >= 3}
    tc = Counter(w for lang in ("A", "B") for ls in V[lang][0].values() for l in ls for w in l)
    vbl = defaultdict(set)
    for w in tc:
        vbl[len(w)].add(w)
    inT = [w for w in labels if w in tc]
    notT = [w for w in labels if w not in tc]
    nb = {w: neighbors(w, vbl) for w in notT}
    has = [w for w in notT if nb[w]]
    pos = Counter(p for w in has for _, p in nb[w])
    hap = [w for w, c in tc.items() if c == 1 and len(w) >= 3]
    base = statistics.mean(bool(neighbors(w, vbl)) for w in hap)
    print(f"  ラベルの種類 {len(labels)}: 本文にある {len(inT)}（{len(inT) / len(labels):.0%}）  本文に無い {len(notT)}: そのうち 1 か所だけ違う本文の語がある {len(has)}（{len(has) / len(notT):.0%}）", flush=True)
    print(f"  基準: 本文で 1 回だけの語（{len(hap)}）で、1 か所だけ違う他の本文の語がある {base:.0%}", flush=True)
    tot = sum(pos.values())
    print(f"  違いの場所（組の数で）: " + "  ".join(f"{k} {v / tot:.0%}" for k, v in pos.most_common()), flush=True)
    ex = [("".join(w), "".join(nb[w][0][0])) for w in has[:8]]
    print("  例: " + "、".join(f"{a_}←{b_}" for a_, b_ in ex), flush=True)

    print("=== N217 黄道のラベルの輪と位置 ===", flush=True)
    Z = zodiac(opts)
    for ring, name in ((1, "外側"), (2, "内側")):
        ws = [z["word"] for z in Z if z["ring"] == ring]
        sp = [split(w) for w in ws]
        print(f"  {name}の輪: ラベル {len(ws)}  芯 {statistics.mean(len(m) for _, m, _ in sp):.2f}  語頭 o {statistics.mean(''.join(h) == 'o' for h, _, _ in sp):.0%}"
              f"  語末 {statistics.mean(len(e) for _, _, e in sp):.2f}  長さ {statistics.mean(map(len, ws)):.2f}", flush=True)
    rings = defaultdict(list)
    for z in Z:
        rings[(z["page"], z["ring"])].append(z)
    for k in rings:
        rings[k].sort(key=lambda z: z["num"])

    def adj_vs(rs):
        adj, non = [], []
        for zs in rs.values():
            w = [z["word"] for z in zs]
            for i in range(len(w)):
                for j in range(i + 1, len(w)):
                    (adj if j == i + 1 else non).append(sim(w[i], w[j]))
        return statistics.mean(adj) - statistics.mean(non)
    o = adj_vs(rings)
    rng = random.Random(2026)
    hit = 0
    R = 5000
    for _ in range(R):
        sh = {}
        for k, zs in rings.items():
            ws = [z["word"] for z in zs]
            rng.shuffle(ws)
            sh[k] = [dict(word=w) for w in ws]
        hit += adj_vs(sh) >= o
    print(f"  (b) 番号が隣り合うラベルの似かた − 隣り合わない組 {o:+.3f}  p {hit / R:.4f}", flush=True)
    pairs, rnd = [], []
    keys = list(rings)
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            if k1[1] != k2[1] or k1[0] == k2[0]:
                continue
            for z in rings[k1]:
                if z["clock"] is None:
                    continue
                cand = [y for y in rings[k2] if y["clock"] is not None]
                if not cand:
                    continue
                d = lambda y: min(abs(y["clock"] - z["clock"]), 720 - abs(y["clock"] - z["clock"]))  # noqa: E731
                best = min(cand, key=d)
                pairs.append(sim(z["word"], best["word"]))
                rnd.append(statistics.mean(sim(z["word"], y["word"]) for y in cand))
    diff = statistics.mean(pairs) - statistics.mean(rnd)
    hit = 0
    for _ in range(R):
        flips = [p if rng.random() < 0.5 else q for p, q in zip(pairs, rnd)]
        other = [q if f == p else p for f, p, q in zip(flips, pairs, rnd)]
        hit += statistics.mean(flips) - statistics.mean(other) >= diff
    print(f"  (c) 別の頁の同じ輪で時計の位置が最も近いラベル − 無作為の組（平均）{diff:+.4f}  組 {len(pairs)}  p {hit / R:.4f}", flush=True)

    print("=== N218 VTN の長さと出る数（偶数番目の頁と比べる）===", flush=True)
    p_ = V["B"][0]
    pages_ = list(p_)
    odd = {k: p_[k] for k in pages_[0::2]}
    even = {k: p_[k] for k in pages_[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))
    three("ヴォイニッチ B・偶数番目の頁", [l for ls in even.values() for l in ls])
    syn = Counter(synth_words(ow, 300000, random.Random(5)))
    bylen = defaultdict(list)
    for w, c in syn.most_common():
        bylen[len(w)].append(w)
    rank_len = [len(w) for w, _ in Counter(ow).most_common()]
    used = defaultdict(int)
    ordered = []
    for L_ in rank_len * 20:
        lst = bylen.get(L_)
        if lst and used[L_] < len(lst):
            ordered.append(lst[used[L_]])
            used[L_] += 1
        if len(ordered) >= 30000:
            break
    # 作った在庫を「順位どおりの出る数」で並べた語の列にする（VTN は出る数の多い順に在庫を作る）
    weights = [max(1, 30000 // (i + 1)) for i in range(len(ordered))]
    stream = [w for w, k in zip(ordered, weights) for _ in range(k)]
    print(f"  並べた在庫 {len(ordered)} 種類、列 {len(stream)} 語", flush=True)
    set_uni(0.75)
    cae = r68.letters_any(T / "pg218.txt")
    r68.show("VTN・長さと出る数を結び付けた在庫・1 文字 0.75", r68.make_text(r68.VTN, stream, cae, r68.para_lengths(Fo), len(ew)), ref_e)


if __name__ == "__main__":
    main(sys.argv[1])

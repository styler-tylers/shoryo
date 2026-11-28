#!/usr/bin/env python3
"""nēvo による解析 第 48 巡: N142（語末の固さと語末の字形の少なさ）・N143（語末が固い書き手）・N144（呪文の名前）。

    python3 voynich/nevo_round48.py <texts の場所> <ポリグラフィア III の表 CSV> <意味のない文章の場所> <マザーグース pg10607> <EEBO-TCP A26563.xml> <Forme of Cury pg8102>
"""

from __future__ import annotations

import math
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round46 import gibberish, p3_cipher, p3_table  # noqa: E402
from nevo_round47 import edit_pos, family  # noqa: E402


def end_entropy(words):
    c = Counter(w[-1] for w in words if w)
    n = sum(c.values())
    return -sum(k / n * math.log2(k / n) for k in c.values())


def shuffled_end(words, rng, runs=20):
    types = sorted({w for w in words if len(w) >= 3})
    lasts = [w[-1] for w in types]
    out = []
    for _ in range(runs):
        rng.shuffle(lasts)
        out.append(family([w[:-1] + (e,) for w, e in zip(types, lasts)])[2])
    return statistics.mean(out)


def examples(words, where, k=4):
    types = sorted({w for w in words if len(w) >= 3})
    ex = []
    for i, a in enumerate(types):
        for b in types[i + 1:]:
            if edit_pos(a, b) == where:
                ex.append(f"{''.join(a)}/{''.join(b)}")
                if len(ex) >= k:
                    return ex
    return ex


def main(tdir, csv, gdir, goose, tcp, cury):
    rng = random.Random(2026)
    V = voynich()
    G = gibberish(gdir)
    cae = words_any(Path(tdir) / "pg218.txt")
    head, table = p3_table(csv)
    letters = [c for c in "".join(cae).replace("j", "i").replace("v", "u") if c in head]
    p2 = p3_cipher(letters[:60000], table, "P2", random.Random(1))
    ref = set(words_any(Path(tdir) / "pg49513.txt")) | set(words_any(Path(cury))) | set(words_any(Path(goose))) | set(cae) | set(words_any(Path(tdir) / "pg23306.txt"))
    t = open(tcp, encoding="utf-8").read()
    body = re.sub(r"&[a-z]+;", " ", re.sub(r"<[^>]+>", " ", t[t.find("<text"):]))
    toks = re.findall(r"[A-Za-z]+", body)
    strange = [tuple(w.lower()) for w in toks if len(w) >= 3 and w.lower() not in ref]
    names = [tuple(w.lower()) for w in toks if len(w) >= 3 and w[0].isupper() and w.lower() not in ref]
    vw = lambda lang: [w for ls in V[lang][0].values() for l in ls for w in l]  # noqa: E731
    texts = [("ヴォイニッチ A", vw("A")), ("ヴォイニッチ B", vw("B")), ("意味のない文章（38 人）", [w for ls in G.values() for l in ls for w in l]),
             ("呪文の語", strange), ("呪文の名前（大文字で始まる）", names),
             ("Caesar（ラテン語）", [tuple(w) for w in cae]), ("Dante（イタリア語）", [tuple(w) for w in words_any(Path(tdir) / "pg1012.txt")]),
             ("Culpeper（英語）", [tuple(w) for w in words_any(Path(tdir) / "pg49513.txt")]),
             ("マザーグース", [tuple(w) for w in words_any(Path(goose))]), ("暗号 P2", [w for ls in p2.values() for l in ls for w in l])]
    print("=== N142・N144 語末の割合と、語末の字形の少なさから予測される割合 ===", flush=True)
    rows = []
    for name, ws in texts:
        ws = ws[:10000]
        h, m, e, n = family(ws)
        se = shuffled_end(ws, rng)
        H = end_entropy(ws)
        rows.append((H, e))
        print(f"  {name:<24} 語 {len(ws):>5}  種類 {len({w for w in ws if len(w) >= 3}):>5}  組 {n:>5}  語頭 {h:.2f}  語末 {e:.2f}  "
              f"H末 {H:.2f}  かき混ぜの語末 {se:.2f}  比 {e / se if se else float('nan'):.2f}", flush=True)
    xs, ys = zip(*rows)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    r = sum((a - mx) * (b - my) for a, b in rows) / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    print(f"  H末 と 語末の割合の相関（10 の文章）: r = {r:+.2f}", flush=True)
    print("=== N143 意味のない文章で語末の割合が低い書き手 ===", flush=True)
    per = []
    for k, ls in G.items():
        ws = [w for l in ls for w in l]
        h, m, e, n = family(ws)
        if n >= 5:
            per.append((e, h, n, k, ws))
    per.sort()
    for e, h, n, k, ws in per[:5]:
        print(f"  {k}: 語 {len(ws)}  組 {n}  語頭 {h:.2f}  語末 {e:.2f}  語頭で違う例 {', '.join(examples(ws, '頭'))}  語末で違う例 {', '.join(examples(ws, '末'))}", flush=True)
        print(f"     書き出し: {' '.join(''.join(w) for w in ws[:24])}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:7])

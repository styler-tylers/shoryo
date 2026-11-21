#!/usr/bin/env python3
"""nēvo による解析 第 46 巡: N137（トリテミウス『ポリグラフィア』第 3 巻の暗号）・N138（人が書いた意味のない文章）。

    python3 voynich/nevo_round46.py <Caesar> <ポリグラフィア III の表 CSV> <意味のない文章の書き起こしの場所>

表: hermesj/R_Voynich_Stats の R code/Historical_ciphers/keys/ciphers_poly_III_in_order.csv
書き起こし: danielgaskell/voynich の data/gibberish_transcriptions.zip を展開したもの
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round42 import report  # noqa: E402


def p3_table(path):
    rows = [l.strip() for l in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    head = [x.strip() for x in rows[0].split(",")]
    table = []
    for r in rows[1:]:
        ws = [x.strip() for x in r.split(",")]
        if len(ws) >= len(head) and all(ws[:len(head)]):
            table.append(dict(zip(head, ws)))
    return head, table


def p3_cipher(letters, table, mode, rng, width=37):
    """mode: P1 全ての行から, P2 最初の 10 行から, P3 行（紙の行）ごとに表の 1 行"""
    lines, cur, n = [], [], 0
    row = rng.randrange(len(table))
    for ch in letters:
        if mode == "P1":
            w = table[rng.randrange(len(table))][ch]
        elif mode == "P2":
            w = table[rng.randrange(10)][ch]
        else:
            w = table[row][ch]
        add = len(w) + (1 if cur else 0)
        if cur and n + add > width:
            lines.append(cur)
            cur, n = [], 0
            add = len(w)
            row = rng.randrange(len(table))
            if mode == "P3":
                w = table[row][ch]
                add = len(w)
        cur.append(w)
        n += add
    if cur:
        lines.append(cur)
    return {f"p{i // 25}": [[tuple(w) for w in l] for l in lines[i:i + 25]] for i in range(0, len(lines), 25)}


def gibberish(folder):
    pages = {}
    for p in sorted(Path(folder).glob("*.txt")):
        ls = []
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            ws = re.findall(r"[a-z]+", raw.lower())
            if ws:
                ls.append([tuple(w) for w in ws])
        if ls:
            pages[p.stem] = ls
    return pages


def t1(name, P, rng):
    m = measure(P, [k == len(ls) - 1 for ls in P.values() for k in range(len(ls))], rng)
    print(f"     {name}: 語の家族の違いの場所 語頭 {m['T1頭']:.2f}・語中 {m['T1中']:.2f}・語末 {m['T1末']:.2f}  行頭だけの語 {m['行頭だけ']:.2f}", flush=True)


def main(caesar, csv, gfolder):
    V = voynich()
    rng = random.Random(2026)
    words = words_any(Path(caesar))
    head, table = p3_table(csv)
    letters = [c for c in "".join(words).replace("j", "i").replace("v", "u") if c in head]
    print(f"表: 文字 {len(head)}、行 {len(table)}。平文の文字 {len(letters)}", flush=True)
    G = gibberish(gfolder)
    gw = sum(len(l) for ls in G.values() for l in ls)
    print(f"意味のない文章: 文書 {len(G)}、行 {sum(len(ls) for ls in G.values())}、語 {gw}", flush=True)
    texts = {m: p3_cipher(letters, table, m, random.Random(1)) for m in ("P1", "P2", "P3")}
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）: T1 語頭 {ref['T1頭']:.2f}・語中 {ref['T1中']:.2f}・語末 {ref['T1末']:.2f}  行頭だけ {ref['行頭だけ']:.2f} ########", flush=True)
        c = report("Caesar（ラテン語）", dict(line_unit.wrap([tuple(w) for w in words[:cap]], 37)), ref, rng)
        res = {}
        for m, label in (("P1", "暗号 P1 全ての行"), ("P2", "暗号 P2 最初の 10 行"), ("P3", "暗号 P3 行ごとに 1 行")):
            P, out, k = texts[m], {}, 0
            for key, ls in P.items():
                if k >= cap:
                    break
                out[key] = ls
                k += sum(len(l) for l in ls)
            res[m] = report(label, out, ref, rng)
            if lang == "A":
                t1(label, out, rng)
        g = report("人が書いた意味のない文章", G, ref, rng)
        if lang == "A":
            t1("人が書いた意味のない文章", G, rng)
            t1("Caesar", dict(line_unit.wrap([tuple(w) for w in words[:cap]], 37)), rng)
        print(f"  → Caesar {c}、暗号 P1 {res['P1']}・P2 {res['P2']}・P3 {res['P3']}、意味のない文章 {g}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])

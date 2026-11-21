#!/usr/bin/env python3
"""nēvo による解析 第 53 巡: N157（暗号に語の長さをそろえる工夫）・N158（語末の欄が担える情報の量）。

    python3 voynich/nevo_round53.py <texts の場所> <ポリグラフィア III の表 CSV>
"""

from __future__ import annotations

import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import scripts_compare  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import split  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round46 import p3_table  # noqa: E402
from nevo_round52 import three  # noqa: E402

NULL = "∅"


def equalize(words, mode, rng, lo=3, hi=7):
    out, added, dropped, total = [], 0, 0, 0
    for w in words:
        w = list(w)
        total += len(w)
        if "L1" in mode or mode == "L3":
            while len(w) < lo:
                pos = rng.randint(1, max(1, len(w) - 1)) if len(w) >= 2 else len(w)
                w.insert(pos, NULL)
                added += 1
        if "L2" in mode or mode == "L3":
            while len(w) > hi:
                del w[rng.randrange(1, len(w) - 1)]
                dropped += 1
        out.append(tuple(w))
    return out, added / total, dropped / total


def H(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


def main(tdir, csv):
    T = Path(tdir)
    rng = random.Random(2026)
    cae = words_any(T / "pg218.txt")
    e4 = [tuple(scripts_compare.syllable_code_e4("".join(w))) for w in unit_entropy.latin_words(T / "pg218.txt")]
    head, table = p3_table(csv)
    letters = [c for c in "".join(cae).replace("j", "i").replace("v", "u") if c in head]
    r = random.Random(1)
    p2 = [tuple(table[r.randrange(10)][ch]) for ch in letters[:60000]]
    print("=== N157 暗号に語の長さをそろえる工夫 ===", flush=True)
    for name, ws in (("音節の暗号 E4", e4), ("トリテミウスの暗号 P2", p2)):
        for mode, label in (("none", "そのまま"), ("L1", "L1 詰め物"), ("L2", "L2 略し"), ("L3", "L3 両方")):
            out, a, d = (ws, 0, 0) if mode == "none" else equalize(ws, mode, random.Random(3))
            three(f"{name}・{label}（詰め {a:.0%}・略し {d:.0%}）", [l for _, ls in line_unit.wrap(out[:30000], 37) for l in ls])

    print("=== N158 語末の欄が担える情報の量 ===", flush=True)
    V = voynich()
    for lang in ("A", "B"):
        ws = [w for ls in V[lang][0].values() for l in ls for w in l]
        ends = Counter("".join(split(w)[2]) or "（なし）" for w in ws)
        bycore = defaultdict(set)
        for w in set(ws):
            h, m, e = split(w)
            bycore[(h, m)].add(e)
        width = sum(len(v) for v in bycore.values()) / len(bycore)
        print(f"  ヴォイニッチ {lang}: 語末の欄の種類 {len(ends)}  エントロピー {H(ends):.2f} ビット  語尾の幅（頭と芯が同じ語の種類あたり）{width:.2f}  "
              f"多いもの: " + ", ".join(f"{k} {v / len(ws):.0%}" for k, v in ends.most_common(6)), flush=True)
    sfx = Counter()
    stems = defaultdict(set)
    for row in table[:10]:
        stem = os.path.commonprefix([row[c] for c in head])
        for c in head:
            stems[stem].add(row[c][len(stem):])
    for w, ch in zip(p2, letters[:60000]):
        pass
    cnt = Counter(letters[:60000])
    print(f"  トリテミウスの暗号 P2: 語尾の種類（1 行あたり）{statistics_mean([len(v) for v in stems.values()]):.1f}  語尾が担う文字のエントロピー {H(cnt):.2f} ビット", flush=True)


def statistics_mean(xs):
    return sum(xs) / len(xs)


if __name__ == "__main__":
    main(*sys.argv[1:3])

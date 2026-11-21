#!/usr/bin/env python3
"""nēvo による解析 第 52 巡: N154（3 つの性質を言語でないもので）・N155（語の端の字形の決まりを崩す）。

    python3 voynich/nevo_round52.py <texts の場所> <ポリグラフィア III の表 CSV> <意味のない文章の場所> <聖歌 gabc の場所>
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import scripts_compare  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import skew, split  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round42 import chant_lines, to_interval  # noqa: E402
from nevo_round46 import gibberish, p3_cipher, p3_table  # noqa: E402
from nevo_round51 import space_guess  # noqa: E402

REF = {"A": (2.30, 0.28), "B": (2.10, 0.11)}


def three(name, lines_):
    ws = [w for l in lines_ for w in l][:30000]
    n, keep = 0, []
    for l in lines_:
        if n >= 30000:
            break
        keep.append(l)
        n += len(l)
    h2 = unit_entropy.entropies([list(w) for w in ws])["h2"]
    sk = skew([len(w) for w in ws])
    sp = space_guess(keep)
    ok = [lang for lang, (h, k) in REF.items() if abs(h2 - h) <= 0.15 and abs(sk - k) <= 0.15 and sp >= 0.65]
    print(f"  {name:<30} h2 {h2:.2f}  歪度 {sk:+.2f}  空白の当てやすさ {sp:.0%}  {'3 つとも ' + '・'.join(ok) + ' の範囲' if ok else ''}", flush=True)
    return h2, sk, sp


def main(tdir, csv, gdir, cdir):
    T = Path(tdir)
    V = voynich()
    print("=== N154 3 つの性質（言語でないもの）===", flush=True)
    for lang in ("A", "B"):
        three(f"ヴォイニッチ {lang}", [l for ls in V[lang][0].values() for l in ls])
    for lang, kw in (("A", dict(c=0.4, mark=0.25)), ("B", dict(c=0.6, mark=0.12, live=True))):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        LG = LengthGrammar(pt)
        P = build34(LG, Compat(LG, pt), pt, random.Random(1), cap=cap, **kw)
        three(f"平文なしの最良のモデル {lang}（循環）", [l for ls in P.values() for l in ls])
    three("人が書いた意味のない文章", [l for ls in gibberish(gdir).values() for l in ls])
    cae = words_any(T / "pg218.txt")
    head, table = p3_table(csv)
    letters = [c for c in "".join(cae).replace("j", "i").replace("v", "u") if c in head]
    for m in ("P1", "P2"):
        three(f"トリテミウスの暗号 {m}", [l for ls in p3_cipher(letters[:150000], table, m, random.Random(1)).values() for l in ls])
    e4 = [tuple(scripts_compare.syllable_code_e4("".join(w))) for w in unit_entropy.latin_words(T / "pg218.txt")]
    three("音節の暗号 E4（Caesar）", [l for _, ls in line_unit.wrap(e4, 37) for l in ls])
    cl = chant_lines(cdir)
    three("聖歌 R1（音の高さ）", [[tuple(w) for w in l] for l in cl])
    three("聖歌 R2（音程）", [[tuple(w) for w in l] for l in to_interval(cl)])
    three("Caesar（参考）", [l for _, ls in line_unit.wrap([tuple(w) for w in cae], 37) for l in ls])

    print("=== N155 語の端の字形の決まりを崩す（ヴォイニッチの語の欄の中身を、芯の字形から無作為に）===", flush=True)
    for lang in ("A", "B"):
        lines_ = [l for ls in V[lang][0].values() for l in ls]
        core = Counter(g for l in lines_ for w in l for g in split(w)[1])
        gk, gv = zip(*core.items())
        rng = random.Random(7)
        rnd = lambda n: tuple(rng.choices(gk, gv, k=n))  # noqa: E731

        def perturb(which):
            out = []
            for l in lines_:
                nl = []
                for w in l:
                    h, m, e = split(w)
                    if "末" in which and e:
                        e = rnd(len(e))
                    if "頭" in which and h:
                        h = rnd(len(h))
                    nl.append((h + m + e) or w)
                out.append(nl)
            return out
        print(f"  ---- 言語 {lang}", flush=True)
        three("もと", lines_)
        for label, which in (("(a) 末の欄を崩す", "末"), ("(b) 頭の欄を崩す", "頭"), ("(c) 両方を崩す", "頭末")):
            three(label, perturb(which))


if __name__ == "__main__":
    main(*sys.argv[1:5])

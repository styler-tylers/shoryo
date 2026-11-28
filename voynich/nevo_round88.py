#!/usr/bin/env python3
"""nēvo による解析 第 88 巡: N253（`-dy` の語と挿絵, 言語 B の生物の頁）。第 287 節の事前の登録どおり。
（N252 は build_retrace_page.py と nevo_round88_retrace.py）

    python3 voynich/nevo_round88.py
"""
import re, sys
from math import comb
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus, ivtff  # noqa: E402
from nevo_round10 import split  # noqa: E402

HERE = Path(__file__).resolve().parent


def fisher_two(a, b, c, d):
    """2×2 表 [[a, b], [c, d]] の正確検定（両側）"""
    n = a + b + c + d; r1 = a + b; c1 = a + c
    def p(x):
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


def isdy(w):
    return "".join(split(tuple(ivtff.glyphs(w)))[2]) == "dy"


def main():
    args = corpus.make_parser("").parse_args([]); args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    meta = {ln.page.name: (ln.page.get("H"), ln.page.get("I")) for ln in lines}
    bio = sorted(p for p, (h, i) in meta.items() if h == "2" and i == "B")
    herb = sorted(p for p, (h, i) in meta.items() if h == "2" and i == "H")
    # 段落の文の行（段落の最後の行の印つき）
    rows = []
    for k, ln in enumerate(lines):
        ws = ivtff.words(ln.raw, opts)
        if not ws:
            continue
        nxt = lines[k + 1] if k + 1 < len(lines) else None
        last = "<$>" in ln.raw or nxt is None or nxt.page.name != ln.page.name or "<%>" in nxt.raw
        rows.append((ln.page.name, ws, last))
    # ラベル（L の行）
    lab = {p: [] for p in bio}
    for line in open(HERE / "data" / "ZL3b-n.txt", encoding="utf-8", errors="replace"):
        m = re.match(r"<(f\d+[rv]\d*)\.(\d+),[@+=]L\w>\s*(.*)", line)
        if m and m.group(1) in lab:
            lab[m.group(1)] += ivtff.words(m.group(3), opts)
    tw = [w for p, ws, _ in rows if p in bio for w in ws]
    lw = [w for p in bio for w in lab[p]]
    a, b = sum(map(isdy, lw)), len(lw) - sum(map(isdy, lw))
    c, d = sum(map(isdy, tw)), len(tw) - sum(map(isdy, tw))
    print(f"=== N253 (a) 生物の頁（{len(bio)} 頁）: ラベル {len(lw)} 語のうち dy {a}（{a / max(1, len(lw)):.1%}）、本文 {len(tw)} 語のうち dy {c}（{c / len(tw):.1%}）  Fisher 両側 p {fisher_two(a, b, c, d):.4g}")
    for name, pages in (("生物", bio), ("本草（対照）", herb)):
        short, full = [], []
        for p in pages:
            ls = [(ws, last) for q, ws, last in rows if q == p]
            med = np.median([len(ws) for ws, _ in ls])
            for ws, last in ls:
                if last:
                    continue
                (short if len(ws) < 0.6 * med else full).extend(ws)
        a, c = sum(map(isdy, short)), sum(map(isdy, full))
        print(f"=== N253 (b) {name}: 短い行 {len(short)} 語の dy {a / max(1, len(short)):.1%}、ふつうの行 {len(full)} 語の dy {c / len(full):.1%}  Fisher 両側 p {fisher_two(a, len(short) - a, c, len(full) - c):.4g}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""nēvo による解析 第 73 巡: N219（続けて書いたものの似かた）・N220（VTN に表の持ち越し）。

    python3 voynich/nevo_round73.py <texts の場所>
"""

from __future__ import annotations

import csv
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round12 import Compat  # noqa: E402
from nevo_round17 import LengthGrammar  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round34 import build34  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round69 import synth_words  # noqa: E402
from nevo_round70 import set_uni  # noqa: E402
from nevo_round71 import sim  # noqa: E402
from nevo_round72 import zodiac  # noqa: E402

HERE = Path(__file__).resolve().parent


def seq_excess(seqs, gap=2, cap=40):
    adj, far = [], []
    for s in seqs:
        for i in range(len(s) - 1):
            adj.append(sim(s[i], s[i + 1]))
        for i in range(len(s)):
            for j in range(i + gap, min(len(s), i + gap + cap)):
                far.append(sim(s[i], s[j]))
    return statistics.mean(adj) - statistics.mean(far) if adj and far else float("nan")


def line_excess(pages, rng, k=3, per=4):
    """pages: {頁: [行]}（段落の最初の行は除いてある）"""
    adj, far = [], []
    for ls in pages.values():
        ls = [l for l in ls if l]
        for i in range(len(ls) - 1):
            a, b = ls[i], ls[i + 1]
            adj += [sim(x, y) for x, y in zip(rng.sample(a, min(per, len(a))), rng.sample(b, min(per, len(b))))]
            for j in range(i + k, len(ls)):
                c = ls[j]
                far += [sim(x, y) for x, y in zip(rng.sample(a, min(2, len(a))), rng.sample(c, min(2, len(c))))]
    return statistics.mean(adj) - statistics.mean(far)


def word_excess(lines_, rng, limit=3000):
    ls = [l for l in lines_ if len(l) >= 4]
    ls = rng.sample(ls, min(limit, len(ls)))
    return seq_excess(ls)


def report_text(name, pages, rng):
    lines_ = [l for ls in pages.values() for l in ls]
    w = word_excess(lines_, random.Random(1))
    wc = sorted(word_excess([random.Random(s).sample(l, len(l)) for l in lines_], random.Random(1)) for s in range(20))
    ln = line_excess(pages, random.Random(2))
    lc = sorted(line_excess({k: random.Random(s).sample(v, len(v)) for k, v in pages.items()}, random.Random(2)) for s in range(20))
    print(f"  {name:<22} (i) 行の中の語 {w:+.4f}（対照 {wc[1]:+.4f}〜{wc[18]:+.4f}）{'超える' if w > wc[18] else ''}"
          f"  (ii) 頁の中の行 {ln:+.4f}（対照 {lc[1]:+.4f}〜{lc[18]:+.4f}）{'超える' if ln > lc[18] else ''}", flush=True)
    return ln


def main(tdir):
    T = Path(tdir)
    V = voynich()
    print("=== N219 続けて書いたものの似かた ===", flush=True)
    rng = random.Random(2026)
    res = {}
    for lang in ("A", "B"):
        F = flagged(V, lang)
        pages = {pg: [l for l, st in v if not st] for pg, v in F.items()}
        res[lang] = report_text(f"ヴォイニッチ {lang}", pages, rng)
    p_ = V["B"][0]
    cap = sum(len(l) for ls in p_.values() for l in ls)
    LG = LengthGrammar(p_)
    M = build34(LG, Compat(LG, p_), p_, random.Random(1), cap=cap, c=0.6, mark=0.12, live=True)
    report_text("平文なしのモデル B", {k: v[1:] for k, v in M.items()}, rng)
    cae_pages = dict(line_unit.wrap([tuple(w) for w in words_any(T / "pg218.txt")][:cap], 37))
    report_text("Caesar", cae_pages, rng)
    pages_ = list(p_)
    odd = {k: p_[k] for k in pages_[0::2]}
    even = {k: p_[k] for k in pages_[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
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
    stream = [w for i, w in enumerate(ordered) for _ in range(max(1, 30000 // (i + 1)))]
    set_uni(0.75)
    cae = r68.letters_any(T / "pg218.txt")
    VT1 = r68.make_text(r68.VTN, stream, cae, r68.para_lengths(Fo), len(ew))
    report_text("VTN（第 223 節の形）", {k: v[1:] for k, v in VT1.items()}, rng)
    a = corpus.make_parser("").parse_args([])
    a.locus = "L"
    opts = corpus.word_options(a)
    Z = zodiac(opts)
    rings = defaultdict(list)
    for z in sorted(Z, key=lambda z: z["num"]):
        rings[(z["page"], z["ring"])].append(z["word"])
    rows = list(csv.DictReader(open(HERE / "notes" / "薬学ラベル対応表.csv", encoding="utf-8-sig")))
    dan = defaultdict(list)
    for r in sorted(rows, key=lambda r: (r["頁"], int(r["段"]), int(r["段内の順"]))):
        if r["種類"] == "薬草":
            g = tuple(x for w in r["ラベル"].split() for x in ivtff.glyphs(w))
            if g:
                dan[(r["頁"], r["段"])].append(g)
    zx = seq_excess(list(rings.values()))
    px = seq_excess(list(dan.values()))
    print(f"  (iii) 黄道の同じ輪のラベル {zx:+.4f}   (iv) 薬学の同じ段の薬草のラベル {px:+.4f}", flush=True)
    print(f"  (d) ヴォイニッチ B の (ii) {res['B']:+.4f} と 黄道のラベル {zx:+.4f} の比 {max(res['B'], zx) / max(1e-9, min(res['B'], zx)):.2f}", flush=True)

    print("=== N220 VTN に表の持ち越し（偶数番目の頁と比べる）===", flush=True)
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))

    class VTNcarry(r68.VTN):
        def __init__(self, *a_, **k_):
            super().__init__(*a_, **k_)
            self.first6 = {u: list(H)[:6] for u, H in self.homo.items()}
            self.t, self.n = 0, 0

        def key(self, u):
            if self.n % 9 == 0:
                if self.rng.random() >= 0.7:
                    self.t = self.rng.randrange(6)
            self.n += 1
            if self.rng.random() < 0.6 and u in self.first6 and len(self.first6[u]) > self.t:
                k = self.first6[u][self.t]
                self.homo[u][k] += 1
                return k
            return super().key(u)
    r68.show("VTN・持ち越しなし", VT1, ref_e)
    r68.show("VTN・表の持ち越しあり", r68.make_text(VTNcarry, stream, cae, r68.para_lengths(Fo), len(ew)), ref_e)


if __name__ == "__main__":
    main(sys.argv[1])

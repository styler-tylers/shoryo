#!/usr/bin/env python3
"""nēvo による解析 第 7 巡: N18（語の端の区別を保つ表記 E7）・N19（第 17 回の数え直し）・N20（言語 B の段落の境目）。

    python3 voynich/nevo_round7.py <Caesar> <Descartes>
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
import line_unit  # noqa: E402
import null_generator  # noqa: E402
import nevo_round6  # noqa: E402
import scripts_compare as scmp  # noqa: E402
import self_citation as sc  # noqa: E402
import syllable_code_tests as sct  # noqa: E402
import unit_entropy  # noqa: E402
from line_grammar import fisher  # noqa: E402
from nevo_round6b import adjacency  # noqa: E402

INIT, FINAL = "mnopqrst", "567890"


def make_e7(words):
    ini = Counter(re.match(r"[^aeiouy]*", w).group(0) for w in words)
    fin = Counter(w[len("".join(re.findall(r"[^aeiouy]*[aeiouy]+", w))):] for w in words)
    fin.pop("", None)
    ti = {c: INIT[i] for i, (c, _) in enumerate(ini.most_common(7))}
    tf = {c: FINAL[i] for i, (c, _) in enumerate(fin.most_common(5))}

    def enc(word):
        parts = re.findall(r"[^aeiouy]*[aeiouy]+", word)
        tail = word[len("".join(parts)):]
        out, prev_g = [], 0
        for k, p in enumerate(parts):
            m = re.match(r"([^aeiouy]*)([aeiouy]+)", p)
            n = scmp._h("n" + m.group(2), 6)
            g = (n // 2 + prev_g) % 3
            if k == 0:
                out.append(ti.get(m.group(1), INIT[7]))
            else:
                out.append(scmp.ONSET[g * 4 + scmp._h("o" + m.group(1), 4)])
            out.append(scmp.NUCLEUS[n])
            prev_g = n // 2
        if tail:
            out.append(tf.get(tail, FINAL[5]))
        return "".join(out)

    return enc


def n18(paths, rng):
    print("=== N18 語の端の区別を保つ表記 E7 ===")
    nevo_round6.CLASSES = [scmp.ONSET, scmp.NUCLEUS, scmp.CODA, INIT, FINAL]
    for p in paths:
        lw = ["".join(w) for w in unit_entropy.latin_words(p)]
        enc = make_e7(lw)
        ws = [enc(w) for w in lw[:30000]]
        e = unit_entropy.entropies([list(w) for w in ws])
        v = null_generator.vocab_stats(ws)
        k, n = scmp.judge(e, v)
        print(f"-- (i) {p.stem} E7: 8 つの量 {k}/{n}（h1 {e['h1']:.2f} h2 {e['h2']:.2f} h2/h1 {e['h2/h1']:.2f} 語長 {e['語の長さ']:.2f}, "
              + ", ".join(f"{a} {b:.3f}" for a, b in v.items()) + "）")
        pages = line_unit.wrap(ws, 37)
        sc.CHAR_MODE = True
        sc.glyph_tuple.cache_clear()
        sc.distance.cache_clear()
        sct.measure("   T1〜T4", dict(pages), tuple, rng)
        adjacency(f"   {p.stem} E7 隣どうし", [["#"] + l + ["#"] for _, ls in pages for l in ls], rng)
        # (ii) N15 の S のモデルを E7 で
        half = len(lw) // 2
        it = iter([enc(w) for w in lw[:half]])
        edge = [enc(w) for w in lw[half:]]
        random.Random(5).shuffle(edge)
        et = iter(edge)
        mp = nevo_round6.build(lambda: next(it, None), lambda: next(et, None), 0.4, random.Random(11), 0.25, short=True)
        nevo_round6.row(f"(ii) {p.stem} S のモデル（E7）", mp, rng)
        adjacency(f"   {p.stem} S のモデル 隣どうし", [l for _, ls in mp for l in ls], rng)


def n19(rng):
    print("\n=== N19 第 17 回の数え直し（段落の始まり: (a) @、(b) <%> だけ、(c) それ以外）===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    for lang in ("A", "B"):
        L = [(ln, ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == lang]
        L = [(ln, ws) for ln, ws in L if len(ws) >= 3]
        kind = lambda ln: "a" if ln.position == "@" else ("b" if "<%>" in ln.raw else "c")  # noqa: E731
        not_first = set(w for _, ws in L for w in ws[1:])
        only = set(ws[0] for _, ws in L) - not_first
        cnt = {k: [0, 0] for k in "abc"}
        for ln, ws in L:
            cnt[kind(ln)][0] += ws[0] in only
            cnt[kind(ln)][1] += 1
        (a1, n1), (b1, nb), (c1, nc) = cnt["a"], cnt["b"], cnt["c"]
        print(f"言語 {lang} I1: (a) @ {a1}/{n1}（{a1 / max(1, n1):.0%}）  (b) <%> だけ {b1}/{nb}（{b1 / max(1, nb):.0%}）  "
              f"(c) それ以外 {c1}/{nc}（{c1 / nc:.0%}）  (b) 対 (c) p = {fisher(b1, nb - b1, c1, nc - c1):.3g}")
        mids_page = defaultdict(set)
        for ln, ws in L:
            mids_page[ln.page.name].update(ws[1:-1])
        pages = list(mids_page)
        for label, ks in (("段落の始まり (a)+(b)", "ab"), ("それ以外 (c)", "c")):
            items = [(ln.page.name, "".join(ivtff.glyphs(ws[0])[1:])) for ln, ws in L
                     if ws[0] in only and len(ivtff.glyphs(ws[0])) >= 3 and kind(ln) in ks]
            rate = lambda asg: sum(r in mids_page[asg[p]] for p, r in items) / len(items)  # noqa: E731
            obs = rate({p: p for p in pages})
            null, ge = [], 0
            for _ in range(2000):
                sh = pages[:]
                rng.shuffle(sh)
                r = rate(dict(zip(pages, sh)))
                null.append(r)
                ge += r >= obs
            print(f"   I3 {label}: {obs:.1%}（入れ替え {statistics.mean(null):.1%}）, p = {(ge + 1) / 2001:.4f}（{len(items)} 語）")


def n20(rng, runs=200):
    print("\n=== N20 段落の境目のつながりはどこから来るか ===")
    args = corpus.make_parser("").parse_args([])
    args.locus = "P"
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    g = lambda w: list(ivtff.glyphs(w))  # noqa: E731
    cls = lambda w: (GL.get(g(w)[0], "その他"))  # noqa: E731
    for lang in ("A", "B"):
        L = [(ln.page.name, ln.raw, ln.position, ivtff.words(ln.raw, opts)) for ln in lines if ln.page.get("L") == lang]
        L = [x for x in L if x[3]]
        starts = [("<%>" in raw) or pos == "@" for _, raw, pos, _ in L]
        pairs = []
        for i in range(1, len(L)):
            (p1, raw1, _, w1), (p2, _, _, w2) = L[i - 1], L[i]
            if p1 == p2 and (starts[i] or "<$>" in raw1):
                pairs.append((p2, "".join(g(w1[-1])[-2:]), w2[0]))
        heads = [(p, ws[0]) for i, (p, _, _, ws) in enumerate(L) if starts[i]]
        obs_pairs = [(a, "".join(g(b)[:2])) for _, a, b in pairs]
        obs_c = Counter(obs_pairs)
        exp_c = Counter()
        mi_cls_null = []
        for _ in range(runs):
            null = []
            for page, a, _ in pairs:
                while True:
                    q, h = rng.choice(heads)
                    if q != page:
                        break
                null.append((a, h))
            exp_c.update((a, "".join(g(h)[:2])) for a, h in null)
            mi_cls_null.append(line_unit.mi([(a, cls(h)) for a, h in null]))
        top = sorted(obs_c, key=lambda k: -(obs_c[k] - exp_c[k] / runs))[:10]
        print(f"言語 {lang}（{len(pairs)} 組）: 観測 − 期待 の大きい組: "
              + ", ".join(f"{a}→{b} {obs_c[(a, b)]}（{exp_c[(a, b)] / runs:.1f}）" for a, b in top))
        obs = line_unit.mi([(a, cls(b)) for _, a, b in pairs])
        m = statistics.mean(mi_cls_null)
        p = (sum(x >= obs for x in mi_cls_null) + 1) / (runs + 1)
        dist = Counter(cls(b) for _, _, b in pairs)
        print(f"   段落の最初の字形（{dict(dist)}）× 前の段落の語末: 観測 {obs:.3f}  基準 {m:.3f}  差 {obs - m:+.3f}  p = {p:.3g}")


GL = {"k": "k", "t": "t", "p": "p", "f": "f", "ckh": "k", "cth": "t", "cph": "p", "cfh": "f"}


def main() -> None:
    paths = [Path(x) for x in sys.argv[1:3]]
    rng = random.Random(2026)
    n18(paths, rng)
    n19(rng)
    n20(rng)


if __name__ == "__main__":
    main()

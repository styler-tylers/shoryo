#!/usr/bin/env python3
"""nēvo による解析 第 44 巡: N132（当時の外交暗号の形）・N133（処方集と比べる）。N134（図の比較）は目視でノートに記録。

    python3 voynich/nevo_round44.py n132 <Caesar>
    python3 voynich/nevo_round44.py n133 <Forme of Cury（Project Gutenberg 8102）>
"""

from __future__ import annotations

import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round42 import report  # noqa: E402


def nomenclator(words, rng):
    """上位 50 語は専用の 2 記号、他は文字ごと（母音は 3 つの記号から無作為）、語の 1 割に空文字。"""
    top = [w for w, _ in Counter(words).most_common(50)]
    letters = sorted(set("".join(words)))
    sym, k = {}, 0
    for ch in letters:
        n = 3 if ch in "aeiou" else 1
        sym[ch] = [f"L{k + i}" for i in range(n)]
        k += n
    codes, used = {}, set()
    for w in top:
        while True:
            c = (f"C{rng.randrange(12)}", f"C{rng.randrange(12)}")
            if c not in used:
                used.add(c)
                codes[w] = c
                break
    out = []
    for w in words:
        t = list(codes[w]) if w in codes else [rng.choice(sym[ch]) for ch in w]
        if rng.random() < 0.1:
            t.insert(rng.randrange(len(t) + 1), "N0")
        out.append(tuple(t))
    return out


def n132(caesar):
    V = voynich()
    rng = random.Random(2026)
    words = words_any(Path(caesar))
    ciph = nomenclator(words, random.Random(1))
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        c = report("Caesar（ラテン語）", dict(line_unit.wrap([tuple(w) for w in words[:cap]], 37)), ref, rng)
        # 幅は記号の数で数える（1 記号 ＝ 1 字）
        x = report("外交暗号の形", dict(line_unit.wrap(ciph[:cap], 37)), ref, rng)
        verdict = "構造類似（Caesar より 2 つ以上多い）" if x >= c + 2 else "棄却"
        print(f"  → 外交暗号 {x}、Caesar {c}: {verdict}", flush=True)


def cury_recipes(path):
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    t = t.split("*** END")[0]
    lines = t.splitlines()
    head = re.compile(r"^[A-Z][A-Z ,.'&\-\[\]0-9]*\.\s+[IVXL]+(\.[IVXL]+)*\.\s*$")
    recs, cur = [], None
    for ln in lines:
        if head.match(ln.strip()):
            if cur:
                recs.append(cur)
            cur = []
            continue
        if cur is None:
            continue
        if re.match(r"^\s*\[\d+\]", ln):  # 注
            if cur:
                recs.append(cur)
            cur = None
            continue
        cur.append(ln)
    if cur:
        recs.append(cur)
    out = []
    for r in recs:
        body = re.sub(r"\[\d+\]", " ", " ".join(r))
        ws = re.findall(r"[A-Za-zþÞ]+", body.lower())
        if len(ws) >= 3:
            out.append(ws)
    return out


def describe(name, paras, strip_first=False):
    lens = [len(p) for p in paras]
    q1, med, q3 = statistics.quantiles(lens, n=4)
    op = [p[0][1:] if strip_first and len(p[0]) > 1 else p[0] for p in paras]
    c = Counter(op)
    top, k = c.most_common(1)[0]
    once = sum(1 for w in op if c[w] == 1) / len(op)
    print(f"  {name:<30} 処方 {len(paras):>4}  語の数の中央値 {med:>4.0f}  ばらつき {(q3 - q1) / med:.2f}  "
          f"最も多い書き出し「{top}」{k / len(op):.0%}  1 度だけの書き出し {once:.0%}", flush=True)


def n133(cury):
    recs = cury_recipes(cury)
    describe("Forme of Cury（処方集）", recs)
    args = corpus.make_parser("").parse_args([])
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    def paras(pred):
        out, cur = [], None
        for ln in lines:
            if not (pred(ln) and ln.locus_class == "P"):
                continue
            if "<%>" in ln.raw or cur is None:
                if cur:
                    out.append(cur)
                cur = []
            cur += ivtff.words(ln.raw, opts)
            if "<$>" in ln.raw:
                out.append(cur)
                cur = None
        if cur:
            out.append(cur)
        return [p for p in out if p]
    for name, pred in (("レシピの部（T）", lambda ln: ln.page.get("Q") == "T"),
                       ("植物の部", lambda ln: ln.page.get("I") == "H"),
                       ("浴場の部", lambda ln: ln.page.get("I") == "B")):
        ps = paras(pred)
        describe(f"ヴォイニッチ {name}", ps)
        describe(f"ヴォイニッチ {name}・最初の字形を除く", ps, strip_first=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"n132": lambda: n132(a[1]), "n133": lambda: n133(a[1])}[a[0]]()

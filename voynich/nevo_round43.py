#!/usr/bin/env python3
"""nēvo による解析 第 43 巡（音楽の仮説の続き）: N129（定量記譜の形で書き直す）・N130（声部どうしの位置のそろい）。

    python3 voynich/nevo_round43.py n129 <MusicXML の場所> <Caesar>
    python3 voynich/nevo_round43.py n130 <MusicXML の場所>

MusicXML は music21 の公開の曲集（GitHub cuthbertLab/music21 の music21/corpus の trecento/・ciconia/・luca/）から取る。
"""

from __future__ import annotations

import math
import random
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round42 import report  # noqa: E402

STEPS = "CDEFGAB"


def dur_letter(q):
    for lim, ch in ((8, "X"), (4, "L"), (2, "B"), (1, "S"), (0.5, "M")):
        if q >= lim - 1e-9:
            return ch
    return "N"


def read_score(path):
    """[(声部, [(小節番号, [(長さ, 高さの段) または None（休符）])])]"""
    data = path.read_bytes()
    if path.suffix == ".mxl":
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith(".xml") and not n.startswith("META"))
            data = z.read(name)
    root = ET.fromstring(data)
    parts = []
    for part in root.findall("part"):
        div, bars = 1, []
        for i, m in enumerate(part.findall("measure")):
            d = m.find("attributes/divisions")
            if d is not None:
                div = int(float(d.text))
            notes = []
            for n in m.findall("note"):
                if n.find("chord") is not None or n.find("grace") is not None:
                    continue
                q = float(n.findtext("duration", "0")) / div
                if n.find("rest") is not None:
                    notes.append(None)
                    continue
                st, oc = n.findtext("pitch/step"), n.findtext("pitch/octave")
                if st is None or oc is None:
                    continue
                notes.append((q, int(oc) * 7 + STEPS.index(st)))
            bars.append((i, notes))
        parts.append(bars)
    return parts


def load(folder):
    return [read_score(p) for p in sorted(Path(folder).glob("*")) if p.suffix in (".xml", ".mxl")]


def to_lines(scores, form):
    lo = min(p for sc in scores for part in sc for _, ns in part for x in ns if x for p in [x[1]])
    pc = lambda v: chr(ord("a") + v - lo)  # noqa: E731
    lines = []
    for sc in scores:
        for part in sc:
            line, nbar = [], 0
            for _, ns in part:
                cur = []

                def flush():
                    if not cur:
                        return
                    if form == "M1":
                        w = "".join(dur_letter(q) + pc(v) for q, v in cur)
                    else:
                        w = dur_letter(cur[0][0]) + "".join(pc(v) for _, v in cur) + (dur_letter(cur[-1][0]) if len(cur) > 1 else "")
                    line.append(w)
                    cur.clear()
                for x in ns:
                    if x is None:
                        flush()
                        if line:
                            lines.append(list(line))
                            line.clear()
                            nbar = 0
                    else:
                        cur.append(x)
                flush()
                nbar += 1
                if nbar >= 10 and line:
                    lines.append(list(line))
                    line.clear()
                    nbar = 0
            if line:
                lines.append(list(line))
    return lines


def paged(lines, cap):
    out, n = [], 0
    for l in lines:
        if n >= cap:
            break
        out.append([tuple(w) for w in l])
        n += len(l)
    return {f"p{i // 25}": out[i:i + 25] for i in range(0, len(out), 25)}


def n129(folder, caesar):
    scores = load(folder)
    V = voynich()
    rng = random.Random(2026)
    cae = [tuple(w) for w in words_any(Path(caesar))]
    for form in ("M1", "M2"):
        ls = to_lines(scores, form)
        nw = sum(len(l) for l in ls)
        print(f"{form}: 曲 {len(scores)}、行 {len(ls)}、語 {nw}、語の種類 {len(Counter(w for l in ls for w in l))}、行あたり {nw / len(ls):.1f} 語", flush=True)
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）########", flush=True)
        c = report("Caesar（ラテン語）", dict(line_unit.wrap(cae[:cap], 37)), ref, rng)
        r = {}
        for form, label in (("M1", "M1 長さ＋高さ"), ("M2", "M2 端に長さ・芯に高さ")):
            r[form] = report(label, paged(to_lines(scores, form), cap), ref, rng)
        verdict = "棄却（自然言語より近くない）" if max(r.values()) <= c else ("構造類似（Caesar より 2 つ以上多い）" if max(r.values()) >= c + 2 else "どちらとも言えない")
        print(f"  → M1 {r['M1']}・M2 {r['M2']}、Caesar {c}: {verdict}", flush=True)


# ---------------------------------------------------------------- N130
def mi(pairs):
    n = len(pairs)
    if not n:
        return 0.0
    cxy, cx, cy = Counter(pairs), Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    return sum(c / n * math.log2(c * n / (cx[a] * cy[b])) for (a, b), c in cxy.items())


def align_stat(pairs_of_lines):
    al = [(a[k], b[k]) for a, b in pairs_of_lines for k in range(min(len(a), len(b)))]
    off = [(a[k], b[k + d]) for a, b in pairs_of_lines for d in (-2, 2) for k in range(len(a)) if 0 <= k + d < len(b)]
    return mi(al) - mi(off)


def align_z(pairs_of_lines, rng, runs=200):
    obs = align_stat(pairs_of_lines)
    nul = [align_stat([(a, rng.sample(b, len(b))) for a, b in pairs_of_lines]) for _ in range(runs)]
    m, sd = statistics.mean(nul), statistics.pstdev(nul)
    return obs, m, (obs - m) / sd if sd else float("nan"), len(pairs_of_lines)


def n130(folder):
    rng = random.Random(2026)
    scores = load(folder)
    pairs = []
    for sc in scores:
        if len(sc) < 2:
            continue
        top, bot = sc[0], sc[-1]
        feat = lambda ns: next(((v % 7) for x in ns if x for v in [x[1]]), None)  # noqa: E731
        fa = [feat(ns) for _, ns in top]
        fb = [feat(ns) for _, ns in bot]
        n = min(len(fa), len(fb))
        for s0 in range(0, n - 7, 8):
            a = [x for x in fa[s0:s0 + 8]]
            b = [x for x in fb[s0:s0 + 8]]
            if None in a or None in b:
                continue
            pairs.append((a, b))
    o, m, z, n = align_z(pairs, rng)
    print(f"  正の対照（同じ小節の上声と下声, 8 小節ずつ, 最初の音の音名）: そろい {o:+.4f}  かき混ぜ {m:+.4f}  z {z:+.1f}（組 {n}）  → {'通る' if z > 3 else '通らない'}", flush=True)
    V = voynich()
    for lang in ("A", "B"):
        lines = [[w[0] for w in l] for ls in V[lang][0].values() for l in ls]
        pp = [(a, b) for a, b in zip(lines, lines[1:]) if len(a) >= 4 and len(b) >= 4]
        o, m, z, n = align_z(pp, rng)
        print(f"  ヴォイニッチ {lang}（隣り合う行, 語の最初の字形）: そろい {o:+.4f}  かき混ぜ {m:+.4f}  z {z:+.1f}（組 {n}）", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"n129": lambda: n129(a[1], a[2]), "n130": lambda: n130(a[1])}[a[0]]()

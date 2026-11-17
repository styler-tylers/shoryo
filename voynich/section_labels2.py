#!/usr/bin/env python3
"""セクションの単位の絵と文章（第 19 回）。

S1 生物の人物のラベル（Ln）と管・池のラベル（Lt）の、本文との語彙の共有 / S2 共有される語の一覧 / S3 語頭の型

    python3 voynich/section_labels2.py
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

SECTIONS = {"H": "植物", "P": "薬学", "B": "生物", "S": "星", "A": "天文", "C": "宇宙", "Z": "黄道", "T": "文章"}


def main() -> None:
    rng = random.Random(2026)
    args = corpus.make_parser("").parse_args([])
    args.locus = None
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    labels = []  # (頁, セクション, 種類, 語)
    sec_tokens = defaultdict(list)
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        sec = ln.page.get("I")
        if ln.locus_class == "L":
            labels += [(ln.page.name, sec, ln.locus_type, w) for w in ws if len(ivtff.glyphs(w)) >= 3]
        elif ln.locus_class in ("P", "C", "R"):
            sec_tokens[sec] += [(ln.page.name, w) for w in ws]
    targets = sorted(s for s, t in sec_tokens.items() if len(t) >= 500)
    n = min(len(sec_tokens[s]) for s in targets)

    # 各ラベルの語の「自分のセクション − 他の平均」（50 回の平均）
    def share(page, sec, w, samples=50):
        acc = {s: 0.0 for s in targets}
        for s in targets:
            pool = [x for q, x in sec_tokens[s] if q != page]
            for _ in range(samples):
                acc[s] += (w in set(rng.sample(pool, min(n, len(pool))))) / samples
        others = [acc[s] for s in targets if s != sec]
        return acc[sec] - sum(others) / len(others), acc

    cache = {}
    rows = []
    for page, sec, typ, w in labels:
        if sec not in ("B", "Z", "C"):
            continue
        k = (page, sec, w)
        if k not in cache:
            cache[k] = share(page, sec, w)
        rows.append((page, sec, typ, w, cache[k][0], cache[k][1]))

    # S1
    bio = [(typ, d) for _, sec, typ, _, d, _ in rows if sec == "B" and typ in ("Ln", "Lt")]
    types = [t for t, _ in bio]
    vals = [d for _, d in bio]

    def diff(ts):
        a = [v for t, v in zip(ts, vals) if t == "Ln"]
        b = [v for t, v in zip(ts, vals) if t == "Lt"]
        return sum(a) / len(a) - sum(b) / len(b)

    obs = diff(types)
    ge = 0
    for _ in range(5000):
        sh = types[:]
        rng.shuffle(sh)
        ge += abs(diff(sh)) >= abs(obs)
    a = [v for t, v in bio if t == "Ln"]
    b = [v for t, v in bio if t == "Lt"]
    print(f"S1 生物: 人物のラベル（Ln, {len(a)} 語）{sum(a) / len(a):+.3f}、管・池のラベル（Lt, {len(b)} 語）{sum(b) / len(b):+.3f}、"
          f"差 {obs:+.3f}、p = {(ge + 1) / 5001:.4f}（両側）\n")

    # S2
    freq = {s: Counter(w for _, w in sec_tokens[s]) for s in targets}
    tot = {s: len(sec_tokens[s]) for s in targets}
    for sec in ("Z", "B", "C"):
        ws = Counter(w for _, s, _, w, _, _ in rows if s == sec)
        out = []
        for w in ws:
            own = freq[sec][w] / tot[sec] * 1000
            oth = sum(freq[s][w] for s in targets if s != sec) / sum(tot[s] for s in targets if s != sec) * 1000
            if freq[sec][w] >= 2:
                out.append(((own + 0.05) / (oth + 0.05), w, freq[sec][w], own, oth))
        out.sort(reverse=True)
        print(f"S2 {SECTIONS[sec]}: 本文に 2 回以上出るラベルの語 {len(out)}/{len(ws)} 種類。自分のセクションに偏る上位:")
        print("   " + ", ".join(f"{w}（本文 {c} 回, 1000 語あたり {o:.1f} 対 {t:.2f}）" for _, w, c, o, t in out[:15]))
        if sec == "B":
            for typ in ("Ln", "Lt"):
                tw = [w for _, s, ty, w, _, _ in rows if s == "B" and ty == typ and freq["B"][w] >= 2]
                print(f"   {typ}: " + ", ".join(sorted(set(tw))))

    # S3
    def head2(w):
        return "".join(ivtff.glyphs(w)[:2])
    shared = [w for _, s, _, w, d, _ in rows if d > 0.05]
    not_sh = [w for _, s, _, w, d, _ in rows if d <= 0.05]
    for name, ws in (("共有される（差 > 0.05）", shared), ("共有されない", not_sh)):
        c = Counter(head2(w) for w in ws)
        print(f"S3 {name} {len(ws)} 語: " + ", ".join(f"{k} {v / len(ws):.0%}" for k, v in c.most_common(6)))


if __name__ == "__main__":
    main()

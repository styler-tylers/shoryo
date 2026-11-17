#!/usr/bin/env python3
"""セクションごとの語彙とラベル（第 11 回）。

L1: ラベルの語は、自分のセクションの本文に、他のセクションの本文より出やすいか。
L2: セクションごとの特徴的な語（対数オッズ比, 弱い事前分布で補正）。
notes/2026-11-15 ヴォイニッチ手稿 セクションごとの語彙とラベル.md の事前の記録のとおり。

    python3 voynich/section_vocab.py
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

SECTIONS = {"H": "植物", "P": "薬学", "B": "生物", "S": "星", "A": "天文", "C": "宇宙", "Z": "黄道", "T": "文章"}


def load():
    args = corpus.make_parser("").parse_args([])
    args.locus = None
    _, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    labels = defaultdict(list)            # 頁 → ラベルの語
    text = defaultdict(list)              # 頁 → 本文の語
    meta = {}
    for ln in lines:
        meta.setdefault(ln.page.name, ln.page)
        ws = ivtff.words(ln.raw, opts)
        if ln.locus_class == "L":
            labels[ln.page.name] += [w for w in ws if len(ivtff.glyphs(w)) >= 3]
        elif ln.locus_class in ("P", "C", "R"):
            text[ln.page.name] += ws
    return labels, text, meta


def l1(labels, text, meta, rng, samples=50, trials=5000):
    sec_of = {p: meta[p].get("I") for p in meta}
    sec_tokens = defaultdict(list)  # セクション → [(頁, 語)]
    for p, ws in text.items():
        sec_tokens[sec_of[p]] += [(p, w) for w in ws]
    targets = sorted(s for s, t in sec_tokens.items() if len(t) >= 500)
    n = min(len(sec_tokens[s]) for s in targets)
    lab_pages = sorted(p for p in labels if labels[p] and sec_of[p] in targets)
    print(f"照合の相手のセクション: {', '.join(f'{SECTIONS[s]}（{len(sec_tokens[s])} 語）' for s in targets)}")
    print(f"抜き出す語数: {n}。ラベルのある頁: {len(lab_pages)} 頁、ラベルの語 {sum(len(labels[p]) for p in lab_pages)} 語")
    print("  ラベルの頁ごと: " + ", ".join(f"{SECTIONS[s]} {c}" for s, c in Counter(sec_of[p] for p in lab_pages).items()))

    # M[頁][セクション] = その頁のラベルの語ごとの「含まれる割合」（50 回の平均）。ラベルの頁自身の本文は除く
    M = {}
    for p in lab_pages:
        acc = {s: [0.0] * len(labels[p]) for s in targets}
        for s in targets:
            pool = [w for q, w in sec_tokens[s] if q != p]
            for _ in range(samples):
                vocab = set(rng.sample(pool, min(n, len(pool))))
                for i, w in enumerate(labels[p]):
                    acc[s][i] += (w in vocab) / samples
        M[p] = acc

    def stat(assign):
        diffs = []
        for p in lab_pages:
            own = assign[p]
            for i in range(len(labels[p])):
                o = M[p][own][i]
                others = [M[p][s][i] for s in targets if s != own]
                diffs.append(o - sum(others) / len(others))
        return sum(diffs) / len(diffs)

    obs_assign = {p: sec_of[p] for p in lab_pages}
    obs = stat(obs_assign)
    secs = [sec_of[p] for p in lab_pages]
    ge = 0
    for _ in range(trials):
        sh = secs[:]
        rng.shuffle(sh)
        ge += stat(dict(zip(lab_pages, sh))) >= obs
    p = (ge + 1) / (trials + 1)
    print(f"\nL1 自分のセクション − 他のセクションの平均: {obs:+.3f}、p = {p:.4f}（片側, {trials} 回）")
    print("セクションごと（自分 / 他の平均）:")
    for s in targets:
        ps = [q for q in lab_pages if sec_of[q] == s]
        if not ps:
            continue
        own = [M[q][s][i] for q in ps for i in range(len(labels[q]))]
        oth = [sum(M[q][t][i] for t in targets if t != s) / (len(targets) - 1) for q in ps for i in range(len(labels[q]))]
        best = Counter()
        for q in ps:
            for i in range(len(labels[q])):
                best[max(targets, key=lambda t: M[q][t][i])] += 1
        print(f"  {SECTIONS[s]:<4} ラベル {len(own):>4} 語  自分 {sum(own) / len(own):.3f} / 他 {sum(oth) / len(oth):.3f}"
              f"  いちばん含まれるセクション: " + ", ".join(f"{SECTIONS[t]} {c}" for t, c in best.most_common(3)))
    return obs, p, M, lab_pages, targets


def log_odds(counts: dict[str, Counter], top: int = 15, alpha: float = 0.01):
    """各群の特徴的な語（対数オッズ比の z 値。Monroe ら 2008 の informative Dirichlet prior の簡単な形）。"""
    total = Counter()
    for c in counts.values():
        total.update(c)
    a0 = alpha * sum(total.values())
    prior = {w: alpha * c for w, c in total.items()}
    out = {}
    for g, c in counts.items():
        rest = total - c
        n1, n2 = sum(c.values()), sum(rest.values())
        scores = []
        for w in total:
            y1, y2, aw = c[w], rest[w], prior[w]
            d = (math.log((y1 + aw) / (n1 + a0 - y1 - aw)) - math.log((y2 + aw) / (n2 + a0 - y2 - aw)))
            var = 1 / (y1 + aw) + 1 / (y2 + aw)
            scores.append((d / math.sqrt(var), w, y1))
        scores.sort(reverse=True)
        out[g] = scores[:top]
    return out


def main() -> None:
    rng = random.Random(2026)
    labels, text, meta = load()
    obs, p, M, lab_pages, targets = l1(labels, text, meta, rng)
    if p < 0.05:
        print("\nL1 が有意なので、言語ごとに同じ統計量（入れ替えなし, 記述）:")
        for lang in ("A", "B"):
            ps = [q for q in lab_pages if meta[q].get("L") == lang]
            d = []
            for q in ps:
                own = meta[q].get("I")
                for i in range(len(labels[q])):
                    d.append(M[q][own][i] - sum(M[q][t][i] for t in targets if t != own) / (len(targets) - 1))
            if d:
                print(f"  言語 {lang}: {len(ps)} 頁 {len(d)} 語  {sum(d) / len(d):+.3f}")

    print("\nL2 セクションごとの特徴的な語（段落・円形・放射状の本文）")
    for lang, secs in (("B", ("H", "B", "S")), ("A", ("H", "P"))):
        counts = defaultdict(Counter)
        for q, ws in text.items():
            if meta[q].get("L") == lang and meta[q].get("I") in secs:
                counts[meta[q].get("I")].update(ws)
        for g, rows in log_odds(counts).items():
            print(f"  言語 {lang}・{SECTIONS[g]}（{sum(counts[g].values())} 語）: "
                  + ", ".join(f"{w}({n})" for z, w, n in rows))


if __name__ == "__main__":
    main()

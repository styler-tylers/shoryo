#!/usr/bin/env python3
"""文字の単位の数え直しと情報量（第 12 回）。

U0 EVA の文字 / U1 字形 / U2 よく一緒に出る字形の組をまとめ直した単位 で、
h0, h1, h2（前の単位が分かったときの条件つきエントロピー）を測り、自然言語の文章と比べる。

    python3 voynich/unit_entropy.py --control <ラテン語などのテキスト …>
    python3 voynich/unit_entropy.py --stage2 <テキスト …>   # 書き方を変えた自然言語
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402

N_UNITS = 30000
SEP = "_"


def entropies(words: list[list[str]], n_units: int = N_UNITS):
    seq: list[str] = []
    for w in words:
        seq += w + [SEP]
        if len(seq) >= n_units:
            break
    seq = seq[:n_units]
    c1 = Counter(seq)
    n = len(seq)
    h0 = math.log2(len(c1))
    h1 = -sum(v / n * math.log2(v / n) for v in c1.values())
    c2 = Counter(zip(seq, seq[1:]))
    prev = Counter(seq[:-1])
    m = n - 1
    h2 = -sum(v / m * math.log2(v / prev[a]) for (a, b), v in c2.items())
    lens = [len(w) for w in words if w]
    return {"種類": len(c1), "h0": h0, "h1": h1, "h2": h2, "h2/h1": h2 / h1,
            "語の長さ": sum(lens) / len(lens), "単位数": n}


def merge_rules(words: list[list[str]], p_min: float = 0.7, n_min: int = 200):
    """「a の次が b である確率 ≥ p_min」かつ「組が n_min 回以上」の組を、無くなるまで順にまとめる。"""
    rules = []
    ws = [list(w) for w in words]
    while True:
        first = Counter()
        pair = Counter()
        for w in ws:
            for a, b in zip(w, w[1:]):
                first[a] += 1
                pair[(a, b)] += 1
        cand = [(n, a, b) for (a, b), n in pair.items() if n >= n_min and n / first[a] >= p_min]
        if not cand:
            return rules
        n, a, b = max(cand)
        rules.append((a, b, n / first[a], n))
        ws = [apply_one(w, a, b) for w in ws]


def apply_one(w: list[str], a: str, b: str) -> list[str]:
    out, i = [], 0
    while i < len(w):
        if i + 1 < len(w) and w[i] == a and w[i + 1] == b:
            out.append(a + "+" + b)
            i += 2
        else:
            out.append(w[i])
            i += 1
    return out


def apply_rules(w: list[str], rules) -> list[str]:
    for a, b, _, _ in rules:
        w = apply_one(w, a, b)
    return w


def latin_words(path: Path) -> list[list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*\* ?START.*?\*\*\*(.*)\*\*\* ?END", text, re.S)
    if m:
        text = m.group(1)
    text = text.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u"), ("ï", "i"), ("ë", "e")):
        text = text.replace(a, b)
    return [list(w) for w in re.findall(r"[a-z]+", text)]


def show(name, r):
    print(f"{name:<28}{r['種類']:>5}{r['h0']:>7.2f}{r['h1']:>7.2f}{r['h2']:>7.2f}{r['h2/h1']:>8.2f}{r['語の長さ']:>8.2f}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="文字の単位の数え直しと情報量")
    ap.add_argument("--control", nargs="*", type=Path, default=[])
    args = ap.parse_args(argv)
    base = corpus.make_parser("").parse_args([])
    base.locus = "P"
    _, lines = corpus.load_lines(base)
    opts = corpus.word_options(base)
    by_lang = {"A": [], "B": []}
    for ln in lines:
        if ln.page.get("L") in by_lang:
            by_lang[ln.page.get("L")] += ivtff.words(ln.raw, opts)
    allw = [list(ivtff.glyphs(w)) for L in by_lang.values() for w in L]
    rules = merge_rules(allw)
    print("U2 のまとめ直しの規則（順に適用）:")
    for a, b, p, n in rules:
        print(f"   {a} + {b} → 1 単位（a の次が b の確率 {p:.2f}, {n} 回）")
    print()
    print(f"{'文章':<28}{'種類':>5}{'h0':>7}{'h1':>7}{'h2':>7}{'h2/h1':>8}{'語の長さ':>6}")
    for L, ws in by_lang.items():
        show(f"ヴォイニッチ {L} U0 EVA の文字", entropies([list(w) for w in ws]))
        show(f"ヴォイニッチ {L} U1 字形", entropies([list(ivtff.glyphs(w)) for w in ws]))
        show(f"ヴォイニッチ {L} U2 まとめ直し", entropies([apply_rules(list(ivtff.glyphs(w)), rules) for w in ws]))
    print()
    res = []
    for path in args.control:
        r = entropies(latin_words(path))
        res.append(r)
        show(path.name, r)
    if res:
        print(f"\n自然言語の範囲: h2 {min(r['h2'] for r in res):.2f}〜{max(r['h2'] for r in res):.2f}、"
              f"h2/h1 {min(r['h2/h1'] for r in res):.2f}〜{max(r['h2/h1'] for r in res):.2f}")


if __name__ == "__main__" and "--stage2" not in sys.argv:
    main()


# ---------------------------------------------------------------------------
# 第 2 段階: 書き方を変えた自然言語（子音だけ / 音節 / 冗長な暗号）
# ---------------------------------------------------------------------------

VOWELS = set("aeiouy")


def consonants_only(words):
    out = [[c for c in w if c not in VOWELS] for w in words]
    return [w for w in out if w]


def syllables(words):
    out = []
    for w in words:
        s = "".join(w)
        parts = re.findall(r"[^aeiouy]*[aeiouy]+", s)
        tail = s[len("".join(parts)):]
        if parts and tail:
            parts[-1] += tail
        elif not parts:
            parts = [s]
        out.append(parts)
    return out


def verbose(words, seed: int = 2026, alphabet: str = "abcdefghijkl"):
    import random as _r
    rng = _r.Random(seed)
    letters = sorted({c for w in words for c in w})
    pairs = [a + b for a in alphabet for b in alphabet]
    rng.shuffle(pairs)
    code = dict(zip(letters, pairs))
    return [[ch for c in w for ch in code[c]] for w in words]


def stage2(paths) -> None:
    print(f"{'文章':<28}{'種類':>5}{'h0':>7}{'h1':>7}{'h2':>7}{'h2/h1':>8}{'語の長さ':>6}")
    for name, f in (("T1 子音だけ", consonants_only), ("T2 音節", syllables), ("T3 冗長な暗号", verbose)):
        rs = []
        for path in paths:
            r = entropies(f(latin_words(path)))
            rs.append(r)
            show(f"{name} {path.stem}", r)
        hits = sum(1 for r in rs if 1.83 <= r["h2"] <= 2.52 and 0.32 <= r["h2/h1"] <= 0.80
                   and 3.54 <= r["h1"] <= 4.19)
        print(f"   → h2・h2/h1・h1 がヴォイニッチの範囲（±0.2・±0.3）に入る言語: {hits}/{len(rs)}\n")


if __name__ == "__main__" and "--stage2" in sys.argv:
    i = sys.argv.index("--stage2")
    stage2([Path(p) for p in sys.argv[i + 1:]])

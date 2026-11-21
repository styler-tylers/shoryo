#!/usr/bin/env python3
"""nēvo による解析 第 47 巡: N139（意味のない文章を書き手ごとに）・N140（「語頭で変わる」形の対照）・N141（トリテミウスの暗号の変形）。

    python3 voynich/nevo_round47.py <texts の場所> <ポリグラフィア III の表 CSV> <意味のない文章の場所> <マザーグース pg10607> <EEBO-TCP A26563.xml> <Forme of Cury pg8102>
"""

from __future__ import annotations

import math
import os
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round46 import gibberish, p3_cipher, p3_table  # noqa: E402


# ---------------------------------------------------------------- m1
def edit_pos(a, b):
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        if len(d) != 1:
            return None
        i, n = d[0], len(a)
    else:
        s, t = (a, b) if len(a) < len(b) else (b, a)
        if len(t) - len(s) != 1:
            return None
        i = next((k for k in range(len(s)) if s[k] != t[k]), len(s))
        if t[:i] + t[i + 1:] != s:
            return None
        n = len(t)
    return "頭" if i == 0 else ("末" if i == n - 1 else "中")


def family(words):
    types = sorted({w for w in words if len(w) >= 3})
    by_len = {}
    for w in types:
        by_len.setdefault(len(w), []).append(w)
    c = Counter()
    for w in types:
        for L in (len(w), len(w) + 1):
            for v in by_len.get(L, []):
                if v <= w and L == len(w):
                    continue
                p = edit_pos(w, v)
                if p:
                    c[p] += 1
    n = sum(c.values())
    return (c["頭"] / n, c["中"] / n, c["末"] / n, n) if n else (float("nan"),) * 3 + (0,)


# ---------------------------------------------------------------- m2, m3
def lencorr(lines, rng, runs=50):
    def corr(ls):
        xs, ys = [], []
        for l in ls:
            L = [len(w) for w in l]
            xs += L[:-1]
            ys += L[1:]
        if len(xs) < 10:
            return float("nan")
        mx, my, sx, sy = statistics.mean(xs), statistics.mean(ys), statistics.pstdev(xs), statistics.pstdev(ys)
        return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs) / (sx * sy) if sx and sy else float("nan")
    o = corr(lines)
    return o - statistics.mean(corr([rng.sample(l, len(l)) for l in lines]) for _ in range(runs))


def repeat_ratio(lines):
    adj = far = na = nf = 0
    for i, l in enumerate(lines):
        if i:
            prev = set(lines[i - 1])
            adj += sum(w in prev for w in l)
            na += len(l)
        for j in range(len(lines)):
            if abs(i - j) >= 5:
                s = set(lines[j])
                far += sum(w in s for w in l)
                nf += len(l)
    return (adj / na) / (far / nf) if na and nf and far else float("nan")


def chunks(lines, size=270):
    out, cur, n = [], [], 0
    for l in lines:
        cur.append(l)
        n += len(l)
        if n >= size:
            out.append(cur)
            cur, n = [], 0
    return out


def crossing(pages, rng, runs=20):
    """行の最後の字 × 次の行の最初の字 − 同じ頁の別の行の最初の字（書き手・頁の違いを除く）"""
    def mi(pairs):
        n = len(pairs)
        cxy, cx, cy = Counter(pairs), Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
        return sum(c / n * math.log2(c * n / (cx[a] * cy[b])) for (a, b), c in cxy.items())
    obs, nul = [], [[] for _ in range(runs)]
    for ls in pages.values():
        ls = [l for l in ls if l]
        for i in range(len(ls) - 1):
            obs.append((ls[i][-1][-1], ls[i + 1][0][0]))
            for r in range(runs):
                j = rng.choice([k for k in range(len(ls)) if k != i + 1])
                nul[r].append((ls[i][-1][-1], ls[j][0][0]))
    return mi(obs) - statistics.mean(mi(x) for x in nul), len(obs)


def summary(vals):
    v = sorted(x for x in vals if x == x)
    if not v:
        return "—"
    q = lambda p: v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))]  # noqa: E731
    return f"{statistics.median(v):.2f}（{q(0.1):.2f}〜{q(0.9):.2f}, {len(v)}）"


def pct(vals, x):
    v = [y for y in vals if y == y]
    return sum(y <= x for y in v) / len(v) if v else float("nan")


def main(tdir, csv, gdir, goose, tcp, cury):
    rng = random.Random(2026)
    V = voynich()
    G = gibberish(gdir)
    cae = words_any(Path(tdir) / "pg218.txt")
    head, table = p3_table(csv)
    letters = [c for c in "".join(cae).replace("j", "i").replace("v", "u") if c in head]
    p2 = p3_cipher(letters[:60000], table, "P2", random.Random(1))
    lines_of = {
        "意味のない文章（38 人）": None,
        "ヴォイニッチ A": [l for ls in V["A"][0].values() for l in ls],
        "ヴォイニッチ B": [l for ls in V["B"][0].values() for l in ls],
        "Caesar": [l for _, ls in line_unit.wrap([tuple(w) for w in cae[:30000]], 37) for l in ls],
        "暗号 P2": [l for ls in p2.values() for l in ls],
    }
    print("=== N139 単位ごとの 3 つの量（中央値・10〜90% の幅・単位の数）===", flush=True)
    res = {}
    for name, L in lines_of.items():
        units = list(G.values()) if L is None else chunks(L)
        m = {"語頭": [], "語末": [], "長さの相関": [], "くり返し": []}
        for u in units:
            h, _, e, n = family([w for l in u for w in l])
            if n >= 5:
                m["語頭"].append(h)
                m["語末"].append(e)
            m["長さの相関"].append(lencorr(u, rng))
            m["くり返し"].append(repeat_ratio(u))
        res[name] = m
        print(f"  {name:<18} " + "  ".join(f"{k} {summary(v)}" for k, v in m.items()), flush=True)
    g = res["意味のない文章（38 人）"]
    for name in ("ヴォイニッチ A", "ヴォイニッチ B", "Caesar", "暗号 P2"):
        print(f"  {name} の中央値は、意味のない文章の分布の何 % の位置: " + "  ".join(
            f"{k} {pct(g[k], statistics.median([x for x in res[name][k] if x == x])):.0%}" for k in g), flush=True)
    print("=== N139 行をまたぐつながり（同じ文書・頁の別の行と比べる）===", flush=True)
    for name, P in (("意味のない文章（38 人）", G), ("ヴォイニッチ A", V["A"][0]), ("ヴォイニッチ B", V["B"][0]),
                    ("Caesar", dict(line_unit.wrap([tuple(w) for w in cae[:30000]], 37)))):
        v, n = crossing(P, rng)
        print(f"  {name:<18} {v:+.4f}（行の組 {n}）", flush=True)

    print("=== N140 語の家族の違いの場所（最初の 1 万語）===", flush=True)
    def eng_words(p):
        return words_any(Path(p))
    ref = set(eng_words(Path(tdir) / "pg49513.txt")) | set(eng_words(cury)) | set(eng_words(goose)) | set(cae) | set(words_any(Path(tdir) / "pg23306.txt"))
    t = open(tcp, encoding="utf-8").read()
    body = re.sub(r"<[^>]+>", " ", t[t.find("<text"):])
    body = re.sub(r"&[a-z]+;", " ", body)
    toks = re.findall(r"[A-Za-z]+", body)
    strange = [w.lower() for w in toks if len(w) >= 3 and w.lower() not in ref]
    print(f"  呪文の語: 書き起こしの語 {len(toks)} のうち参照の語彙に無い 3 字以上の語 {len(strange)}（種類 {len(set(strange))}）。多いもの: "
          + ", ".join(w for w, _ in Counter(strange).most_common(25)), flush=True)
    vw = lambda lang: [w for ls in V[lang][0].values() for l in ls for w in l]  # noqa: E731
    texts = [("ヴォイニッチ A", vw("A")), ("ヴォイニッチ B", vw("B")), ("意味のない文章（38 人）", [w for ls in G.values() for l in ls for w in l]),
             ("呪文の語（ヘプタメロンほか）", [tuple(w) for w in strange]), ("Caesar（ラテン語）", [tuple(w) for w in cae]),
             ("Dante（イタリア語）", [tuple(w) for w in words_any(Path(tdir) / "pg1012.txt")]),
             ("Culpeper（英語）", [tuple(w) for w in words_any(Path(tdir) / "pg49513.txt")]),
             ("マザーグース", [tuple(w) for w in words_any(Path(goose))]),
             ("暗号 P2", [w for ls in p2.values() for l in ls for w in l])]
    for name, ws in texts:
        h, m_, e, n = family(ws[:10000])
        print(f"  {name:<26} 語 {min(len(ws), 10000):>5}  組 {n:>5}  語頭 {h:.2f}  語中 {m_:.2f}  語末 {e:.2f}  {'語頭 ＞ 語末' if h > e else '語末 ≥ 語頭'}", flush=True)

    print("=== N141 トリテミウスの暗号の変形（語尾を前に出す）===", flush=True)
    flipped = []
    for row in table:
        ws = [row[c] for c in head]
        stem = os.path.commonprefix(ws)
        flipped.append({c: (row[c][len(stem):] + stem) if row[c][len(stem):] else row[c] for c in head})
    pf = p3_cipher(letters[:60000], flipped, "P2", random.Random(1))
    for name, P in (("暗号 P2（もと）", p2), ("暗号 P2（語尾を前に）", pf)):
        h, m_, e, n = family([w for ls in P.values() for l in ls for w in l][:10000])
        print(f"  {name:<20} 組 {n:>4}  語頭 {h:.2f}  語中 {m_:.2f}  語末 {e:.2f}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:7])

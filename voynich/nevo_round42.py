#!/usr/bin/env python3
"""nēvo による解析 第 42 巡（音楽の仮説）: N126（旋律をそのまま書いた文章と比べる）・N127（移高の跡）・N128（アイソリズムの周期）。

    python3 voynich/nevo_round42.py check                 # N127・N128 の作り物での確かめ
    python3 voynich/nevo_round42.py n126 <gabc の場所> <Caesar>
    python3 voynich/nevo_round42.py n127 <gabc の場所>
    python3 voynich/nevo_round42.py n128

gabc は GregoBase（https://gregobase.selapa.net/）の download.php?id=N&format=gabc&elem=1 から取る。
"""

from __future__ import annotations

import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round25 import TOL  # noqa: E402
from nevo_round34 import lastf  # noqa: E402

PITCH = "abcdefghijklm"
DIV = re.compile(r"^[,;:]+$")
GEN = ["h2", "V2", "V3", "V4", "歪度", "隣", "G1"]


# ---------------------------------------------------------------- 聖歌を文章にする
def chant_lines(folder):
    """gabc の楽譜を [行（語＝音の高さの文字列のリスト）] にする。"""
    lines = []
    for p in sorted(Path(folder).glob("*.gabc"), key=lambda q: int(q.stem)):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "%%" not in t:
            continue
        body = t.split("%%", 1)[1]
        body = re.sub(r"<[^>]*>", "", body)
        cur = []
        for g in re.findall(r"\(([^)]*)\)", body):
            g = re.sub(r"\[[^\]]*\]", "", g)
            if DIV.match(g.strip().replace("'", "").replace("_", "").replace("^", "")):
                if cur:
                    lines.append(cur)
                cur = []
                continue
            if re.match(r"^[cf]b?[1-4]$", g.strip()):
                continue
            w = "".join(ch.lower() for ch in g if ch.lower() in PITCH)
            if w:
                cur.append(w)
        if cur:
            lines.append(cur)
    return lines


def to_interval(lines):
    """各音を直前の音からの音程（−4〜＋4 を 9 種の文字）に置き換える。"""
    out, prev = [], None
    sym = "ABCDEFGHI"
    for l in lines:
        nl = []
        for w in l:
            s = ""
            for ch in w:
                v = PITCH.index(ch)
                d = 0 if prev is None else max(-4, min(4, v - prev))
                s += sym[d + 4]
                prev = v
            nl.append(s)
        out.append(nl)
    return out


def paged(lines, cap):
    words, out = 0, []
    for l in lines:
        if words >= cap:
            break
        out.append(tuple(tuple(w) for w in l) if False else [tuple(w) for w in l])
        words += len(l)
    return {f"p{i // 25}": out[i:i + 25] for i in range(0, len(out), 25)}


def report(name, P, ref, rng):
    m = measure(P, lastf(P), rng)
    ok = {k: abs(m[k] - ref[k]) <= TOL[k] for k in GEN}
    ok["またぐ"] = m["またぐ"] <= 0.03
    n = sum(ok.values())
    vals = "  ".join(f"{k} {m[k]:.2f}{'○' if ok[k] else '×'}" for k in GEN) + f"  またぐ {m['またぐ']:.3f}{'○' if ok['またぐ'] else '×'}"
    words = sum(len(l) for ls in P.values() for l in ls)
    print(f"  {name:<22}（{words} 語）{n}/8  {vals}", flush=True)
    return n


def n126(folder, caesar_path):
    V = voynich()
    rng = random.Random(2026)
    lines = chant_lines(folder)
    nw = sum(len(l) for l in lines)
    print(f"聖歌: 行 {len(lines)}、語（音節の音符の群）{nw}、語の種類 {len(Counter(w for l in lines for w in l))}、"
          f"行あたり {nw / len(lines):.1f} 語", flush=True)
    iv = to_interval(lines)
    cae = [tuple(w) for w in words_any(Path(caesar_path))]
    for lang in ("A", "B"):
        pt = V[lang][0]
        cap = sum(len(l) for ls in pt.values() for l in ls)
        ref = measure(pt, V[lang][2], rng)
        print(f"######## 言語 {lang}（{cap} 語）: " + "  ".join(f"{k} {ref[k]:.2f}" for k in GEN) + f"  またぐ {ref['またぐ']:.3f}", flush=True)
        c = report("Caesar（ラテン語）", dict(line_unit.wrap(cae[:cap], 37)), ref, rng)
        r1 = report("聖歌 R1 音の高さ", paged(lines, cap), ref, rng)
        r2 = report("聖歌 R2 音程", paged(iv, cap), ref, rng)
        verdict = "棄却（自然言語より近くない）" if r1 <= c and r2 <= c else ("構造類似（Caesar より 2 つ以上多い）" if max(r1, r2) >= c + 2 else "どちらとも言えない")
        print(f"  → 聖歌 R1 {r1}・R2 {r2}、Caesar {c}: {verdict}", flush=True)


# ---------------------------------------------------------------- N127 移高の跡
def subs_of(a, b):
    out = []
    for w in a:
        for v in b:
            if len(w) == len(v) and w != v:
                d = [(x, y) for x, y in zip(w, v) if x != y]
                if len(d) == 1:
                    out.append(d[0])
    return out


def transposition(pages, rng=None, runs=200):
    """隣の行の組で、同じ置き換えが 2 度以上出る組の割合（置き換えが 2 つ以上ある組のうち）。
    比べる相手: 全ての組の置き換えを、各組の数を保ったまま組の間で入れ替えたときの割合（runs 回の平均と標準偏差）。"""
    rng = rng or random.Random(7)
    groups = []
    for ls in pages.values():
        L = [l[1:-1] for l in ls if len(l) >= 3]
        for i in range(len(L) - 1):
            sub = subs_of(L[i], L[i + 1])
            if len(sub) >= 2:
                groups.append(sub)
    if not groups:
        return float("nan"), float("nan"), float("nan"), 0
    frac = lambda gs: sum(max(Counter(g).values()) >= 2 for g in gs) / len(gs)  # noqa: E731
    obs = frac(groups)
    pool = [x for g in groups for x in g]
    nul = []
    for _ in range(runs):
        rng.shuffle(pool)
        it = iter(pool)
        nul.append(frac([[next(it) for _ in g] for g in groups]))
    m, sd = statistics.mean(nul), statistics.pstdev(nul)
    return obs, m, (obs - m) / sd if sd else float("nan"), len(groups)


def show127(name, pages):
    obs, m, z, n = transposition(pages)
    print(f"  {name:<26} 同じ置き換えが 2 度以上 {obs:.3f}  入れ替えたとき {m:.3f}  比 {obs / m if m else float('nan'):.2f}  z {z:+.1f}（行の組 {n}）", flush=True)
    return obs / m if m else float("nan")


def synth_lines(rng, mode, pages=60, lpp=25, L=9, A="abcdefgh"):
    out = {}
    for p in range(pages):
        ls = []
        prev = None
        for _ in range(lpp):
            if prev is None or rng.random() < 0.3:
                l = [tuple(rng.choice(A) for _ in range(rng.randint(3, 6))) for _ in range(L)]
            else:
                if mode == "ばらばら":
                    l = []
                    for w in prev:
                        i = rng.randrange(len(w))
                        l.append(w[:i] + (rng.choice(A),) + w[i + 1:])
                else:
                    x = rng.choice(A)
                    y = rng.choice([c for c in A if c != x])
                    l = [tuple(y if c == x else c for c in w) for w in prev]
            ls.append(l)
            prev = l
        out[f"p{p}"] = ls
    return out


# ---------------------------------------------------------------- N128 周期
def lag_z(seqs, lags, rng, runs=200):
    def corr(ss, k):
        xs, ys = [], []
        for s in ss:
            xs += s[:-k]
            ys += s[k:]
        if len(xs) < 10:
            return float("nan")
        mx, my = statistics.mean(xs), statistics.mean(ys)
        sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
        return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs) / (sx * sy) if sx and sy else float("nan")
    out = []
    for k in lags:
        obs = corr(seqs, k)
        nul = [corr([rng.sample(s, len(s)) for s in seqs], k) for _ in range(runs)]
        m, sd = statistics.mean(nul), statistics.pstdev(nul)
        out.append((k, obs, (obs - m) / sd if sd else float("nan")))
    return out


def show128(name, seqs, lags, rng):
    r = lag_z(seqs, lags, rng)
    print(f"  {name:<30} " + "  ".join(f"間隔 {k}: {c:+.3f}（z {z:+.1f}）" for k, c, z in r), flush=True)
    return r


def synth_len(rng, periodic, n=1500, L=9):
    seqs = []
    for _ in range(n):
        if periodic:
            pat = [rng.randint(2, 8) for _ in range(3)]
            seqs.append([pat[i % 3] if rng.random() > 0.3 else rng.randint(2, 8) for i in range(L)])
        else:
            seqs.append([rng.randint(2, 8) for _ in range(L)])
    return seqs


def check():
    rng = random.Random(5)
    print("=== N127 作り物 ===", flush=True)
    a = show127("(a) 語ごとにばらばらに替える", synth_lines(random.Random(1), "ばらばら"))
    print(f"     → {'通る' if 0.8 <= a <= 1.25 else '通らない'}（0.8〜1.25）", flush=True)
    b = show127("(b) 行ごとに 1 つの置き換え", synth_lines(random.Random(2), "移高"))
    print(f"     → {'通る' if b >= 2 else '通らない'}（2 以上）", flush=True)
    print("=== N128 作り物 ===", flush=True)
    r = show128("(a) 長さを独立に選ぶ", synth_len(random.Random(3), False), (1, 2, 3, 4), rng)
    print(f"     → {'通る' if all(abs(z) < 3 for _, _, z in r) else '通らない'}（どの間隔も |z| < 3）", flush=True)
    r = show128("(b) 3 語ごとにくり返す", synth_len(random.Random(4), True), (1, 2, 3, 4), rng)
    print(f"     → {'通る' if r[2][2] > 5 else '通らない'}（間隔 3 の z > 5）", flush=True)


def n127(folder):
    V = voynich()
    for lang in ("A", "B"):
        show127(f"ヴォイニッチ {lang}", V[lang][0])
    show127("聖歌 R1 音の高さ", paged([[tuple(w) for w in l] for l in chant_lines(folder)], 10 ** 9))


def n128():
    V = voynich()
    rng = random.Random(2026)
    for lang in ("A", "B"):
        pt, last = V[lang][0], V[lang][2]
        lines = [l for ls in pt.values() for l in ls]
        show128(f"ヴォイニッチ {lang}・行の内側", [[len(w) for w in l[1:-1]] for l in lines if len(l) >= 6], (1, 2, 3, 4), rng)
        paras, cur = [], []
        for l, e in zip(lines, last):
            cur += [len(w) for w in l]
            if e:
                if len(cur) >= 10:
                    paras.append(cur)
                cur = []
        show128(f"ヴォイニッチ {lang}・段落", paras, (1, 2, 3, 4, 5, 6, 7, 8), rng)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"check": lambda: check(), "n126": lambda: n126(a[1], a[2]), "n127": lambda: n127(a[1]), "n128": lambda: n128()}[a[0]]()

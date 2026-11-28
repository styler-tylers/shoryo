#!/usr/bin/env python3
"""nēvo による解析 第 65 巡: N194（Naibbe 暗号の元の表）・N195（書くたびに変える暗号）・N196（語の切れ目を残す暗号）。

表は Greshko の補足資料（Zenodo 17219445, CC-BY 4.0）の `Naibbe Cipher.xlsx` から取り出した JSON を使う
（{"uni": {"unigram_<表>_<字>": 語}, "presuf": {"<表>_<字>_prefix|suffix": 字形の組}}）。

    python3 voynich/nevo_round65.py <texts の場所> <tables.json> <author_rows.json>
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ivtff  # noqa: E402
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import family  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round61 import rank  # noqa: E402
from nevo_round64 import Code2, units_of  # noqa: E402

TABLES = ["alpha", "beta1", "beta2", "beta3", "gamma1", "gamma2"]
CARDS = [28, 14, 11, 11, 7, 7]
P_UNI = 0.4722222222222222


def g(s):
    return tuple(ivtff.glyphs(s))


def naibbe_letters(path):
    s = "".join("".join(w) for w in unit_entropy.latin_words(path)).lower()
    s = s.replace("j", "i").replace("k", "c").replace("w", "v")
    return [c for c in s if c in "abcdefghilmnopqrstuvxyz"]


class Naibbe:
    def __init__(self, T):
        self.uni, self.ps = T["uni"], T["presuf"]
        self.dec_uni = {v: k.split("_")[2] for k, v in self.uni.items()}
        self.dec_pre = {v: k.split("_")[1] for k, v in self.ps.items() if k.endswith("_prefix")}
        self.dec_suf = {v: k.split("_")[1] for k, v in self.ps.items() if k.endswith("_suffix")}

    def encrypt(self, letters, rng, with_units=False):
        out, units, i = [], [], 0
        while i < len(letters):
            if i + 1 < len(letters) and rng.random() >= P_UNI:
                a, b = rng.choices(TABLES, CARDS, k=2)
                out.append(self.ps[f"{a}_{letters[i]}_prefix"] + self.ps[f"{b}_{letters[i + 1]}_suffix"])
                units.append(letters[i] + letters[i + 1])
                i += 2
            else:
                out.append(self.uni[f"unigram_{rng.choices(TABLES, CARDS)[0]}_{letters[i]}"])
                units.append(letters[i])
                i += 1
        return (out, units) if with_units else out

    def readings(self, w):
        """語 1 つの読み方の集合（単独の語として、語頭側 ＋ 語尾側として）"""
        r = set()
        if w in self.dec_uni:
            r.add(self.dec_uni[w])
        r |= {self.dec_pre[w[:i]] + self.dec_suf[w[i:]] for i in range(1, len(w)) if w[:i] in self.dec_pre and w[i:] in self.dec_suf}
        return r

    def decrypt(self, words):
        res, bad = [], 0
        for w in words:
            if w in self.dec_uni:
                res.append(self.dec_uni[w])
                continue
            cuts = {(self.dec_pre[w[:i]], self.dec_suf[w[i:]]) for i in range(1, len(w)) if w[:i] in self.dec_pre and w[i:] in self.dec_suf}
            if len(cuts) == 1:
                res += list(next(iter(cuts)))
            else:
                res += ["?", "?"]
                bad += 1
        return res, bad


def block(name, words, ref, vref_lines, lang):
    P = dict(line_unit.wrap([g(w) if isinstance(w, str) else w for w in words], 37))
    lines_ = [l for ls in P.values() for l in ls]
    ws = [w for l in lines_ for w in l]
    three(name, lines_)
    m = report(name, P, ref, random.Random(2026))
    f = family(ws)
    n, h, wd = endinfo(ws)
    FM = {pg: [(l, j == 0) for j, l in enumerate(ls)] for pg, ls in P.items()}
    mean_len = sum(len(w) for w in ws) / len(ws)
    print(f"    家族の場所 頭 {f[0]:.3f} 中 {f[1]:.2f} 末 {f[2]:.2f}  語末の欄の種類 {n}  語尾の幅 {wd:.2f}  語の種類 {len(set(ws))}"
          f"  語の長さの平均 {mean_len:.2f}  行をまたぐ量の順位 {rank(FM, random.Random(7), runs=100):.3f}", flush=True)
    return m


def mutate_code(cd, units, p, rng, alphabet, weights):
    out = cd.encrypt(units, rng)
    res = []
    for w in out:
        if rng.random() < p:
            h, m, e = split(w)
            k = list(h) + list(m)
            if k:
                i = rng.randrange(len(k))
                k[i] = rng.choices(alphabet, weights)[0]
                w = tuple(k) + tuple(e)
        res.append(w)
    return res


def decode_mut(cd, words, alphabet):
    ok = 0
    for w in words:
        h, m, e = split(w)
        k = tuple(h) + tuple(m)
        if k in cd.dec:
            ok += 1
            continue
        cands = {cd.dec[k[:i] + (a,) + k[i + 1:]] for i in range(len(k)) for a in alphabet if k[:i] + (a,) + k[i + 1:] in cd.dec}
        ok += len(cands) == 1
    return ok / len(words)


def main(tdir, tables, rows):
    T = Path(tdir)
    V = voynich()
    nb = Naibbe(json.load(open(tables)))
    R = json.load(open(rows))
    author = [r["corr"] for r in R if r["corr"] and r["corr"] not in ("XXXXX", "#N/A")]
    cae, des = naibbe_letters(T / "pg218.txt"), naibbe_letters(T / "pg23306.txt")
    refs = {lang: measure(V[lang][0], V[lang][2], random.Random(2026)) for lang in ("A", "B")}
    print("=== N194 Naibbe 暗号（元の表）===", flush=True)
    for lang in ("B", "A"):
        p_ = V[lang][0]
        cap = sum(len(l) for ls in p_.values() for l in ls)
        print(f"######## 言語 {lang}（{cap} 語）と比べる", flush=True)
        three(f"ヴォイニッチ {lang}", [l for ls in p_.values() for l in ls])
        vw = [w for ls in p_.values() for l in ls for w in l]
        f = family(vw)
        n, h, wd = endinfo(vw)
        print(f"    家族の場所 頭 {f[0]:.3f} 中 {f[1]:.2f} 末 {f[2]:.2f}  語末の欄の種類 {n}  語尾の幅 {wd:.2f}  語の種類 {len(set(vw))}  語の長さの平均 {sum(map(len, vw)) / len(vw):.2f}", flush=True)
        cw = nb.encrypt(cae, random.Random(1))[:cap]
        block("(i) 著者の暗号文", author[:cap], refs[lang], None, lang)
        block("(ii) Caesar", cw, refs[lang], None, lang)
        three("(iii) Descartes", [l for _, ls in line_unit.wrap([g(w) for w in nb.encrypt(des, random.Random(2))[:cap]], 37) for l in ls])
    ws_, us_ = nb.encrypt(cae, random.Random(1), with_units=True)
    ws_, us_ = ws_[:23091], us_[:23091]
    rd = [nb.readings(w) for w in ws_]
    uniq = sum(len(r) == 1 and u in r for r, u in zip(rd, us_))
    amb = sum(len(r) > 1 and u in r for r, u in zip(rd, us_))
    print(f"  読み戻し（Caesar, 23091 語, 1 語ずつ, 事後に直した測り方）: 読みが 1 つで正しい {uniq / len(ws_):.2%}  読みが 2 つ以上（正しい読みを含む）{amb / len(ws_):.2%}"
          f"  正しい読みを含まない {(len(ws_) - uniq - amb) / len(ws_):.2%}", flush=True)

    print("=== N195 書くたびに少し変える（表 2・言語 B）===", flush=True)
    p_ = V["B"][0]
    vw = [w for ls in p_.values() for l in ls for w in l]
    cap = len(vw)
    from nevo_round63 import letters_of
    cl = letters_of(T / "pg218.txt")
    cu = units_of(cl, random.Random(1))
    cd = Code2(vw, [u for u, _ in Counter(cu).most_common()])
    gl = Counter(x for w in vw for x in (lambda s: tuple(s[0]) + tuple(s[1]))(split(w)))
    alph, wts = zip(*gl.items())
    for p in (0.0, 0.1, 0.3):
        mw = mutate_code(cd, cu, p, random.Random(3), alph, wts)[:cap]
        print(f"  p={p}: 読み戻し {decode_mut(cd, mw, alph):.1%}", flush=True)
        block(f"表 2・p={p}", mw, refs["B"], None, "B")

    print("=== N196 語の切れ目を残す（表 2・言語 B）===", flush=True)
    words = [[c for c in "".join(w).lower().replace("j", "i").replace("v", "u") if "a" <= c <= "z"] for w in unit_entropy.latin_words(T / "pg218.txt")]
    rng = random.Random(5)
    out = []
    for w in words:
        if not w:
            continue
        us = units_of(w, rng)
        ks = []
        for u in us:
            t = rng.choices(range(6), [0.40, 0.15, 0.15, 0.10, 0.10, 0.10])[0]
            k = cd.table.get((t, u)) or cd.table[(t, u[0])] + cd.table[(t, u[1])]
            ks.append(k)
        last = ks[-1]
        ek, ev = zip(*cd.ends[last].items()) if last in cd.ends else ((tuple(),), (1,))
        out.append(tuple(x for k in ks for x in k) + rng.choices(ek, ev)[0])
        if len(out) >= cap:
            break
    # 事後の直し: 語が長く 1 行あたりの語が少ないため、8 つの量（report）は計算できない。予測に要る量だけを直接測る
    import null_generator
    v = null_generator.vocab_stats(["".join(w) for w in out])
    three("語の切れ目を残す", [l for _, ls in line_unit.wrap(out, 37) for l in ls])
    print(f"    V2 {v['V2 1回だけ']:.2f}  V3 {v['V3 Zipf']:.2f}  V4 {v['V4 Heaps']:.2f}  語の長さの平均 {sum(map(len, out)) / len(out):.2f}  語の種類 {len(set(out))}"
          f"（ヴォイニッチ B: V2 {refs['B']['V2']:.2f}  V3 {refs['B']['V3']:.2f}  V4 {refs['B']['V4']:.2f}）", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])

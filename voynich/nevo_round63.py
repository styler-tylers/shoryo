#!/usr/bin/env python3
"""nēvo による解析 第 63 巡: Naibbe 型の冗長な暗号（自作の表）。N187〜N190。

Greshko（2025）の Naibbe 暗号と同じ考え方（1・2 文字の単位に区切り直し、6 つの表から 1 つを引いて書く）で、
表はヴォイニッチの語の欄から自作する。Naibbe 暗号そのものではない。

    python3 voynich/nevo_round63.py <texts の場所>
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
import unit_entropy  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round21 import words_any  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import family  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round61 import rank  # noqa: E402

P_BIGRAM = 0.55
WEIGHTS = [0.40, 0.15, 0.15, 0.10, 0.10, 0.10]


def letters_of(path):
    s = "".join("".join(w) for w in unit_entropy.latin_words(path)).lower().replace("j", "i").replace("v", "u")
    return [c for c in s if "a" <= c <= "z"]


def halves(w):
    h, m, e = split(w)
    k = math.ceil(len(m) / 2)
    return tuple(h) + tuple(m[:k]), tuple(m[k:]) + tuple(e)


class Naibbe:
    def __init__(self, vwords, alphabet):
        pre, suf, uni = Counter(), Counter(), Counter(vwords)
        for w in vwords:
            a, b = halves(w)
            if a and b:
                pre[a] += 1
                suf[b] += 1
        n = len(alphabet) * 6
        self.pre_list = [x for x, _ in pre.most_common(n)]
        self.suf_list = [x for x, _ in suf.most_common(n)]
        ps, ss = set(self.pre_list), set(self.suf_list)

        def composable(w):
            return any(w[:i] in ps and w[i:] in ss for i in range(1, len(w)))
        self.uni_list = [x for x, _ in uni.most_common() if not composable(x)][:n]
        assert len(self.pre_list) == len(self.suf_list) == len(self.uni_list) == n, (len(self.pre_list), len(self.suf_list), len(self.uni_list))
        self.alphabet = alphabet
        self.uni = {(t, c): self.uni_list[r * 6 + t] for r, c in enumerate(alphabet) for t in range(6)}
        self.pre = {(t, c): self.pre_list[r * 6 + t] for r, c in enumerate(alphabet) for t in range(6)}
        self.suf = {(t, c): self.suf_list[r * 6 + t] for r, c in enumerate(alphabet) for t in range(6)}
        self.dec_uni = {v: k[1] for k, v in self.uni.items()}
        self.dec_pre = {v: k[1] for k, v in self.pre.items()}
        self.dec_suf = {v: k[1] for k, v in self.suf.items()}

    def encrypt(self, letters, rng):
        out, i = [], 0
        tables = list(range(6))
        while i < len(letters):
            if i + 1 < len(letters) and rng.random() < P_BIGRAM:
                t1, t2 = rng.choices(tables, WEIGHTS, k=2)
                out.append(self.pre[(t1, letters[i])] + self.suf[(t2, letters[i + 1])])
                i += 2
            else:
                out.append(self.uni[(rng.choices(tables, WEIGHTS)[0], letters[i])])
                i += 1
        return out

    def decrypt(self, words):
        res, bad = [], 0
        for w in words:
            if w in self.dec_uni:
                res.append(self.dec_uni[w])
                continue
            cuts = [(self.dec_pre[w[:i]], self.dec_suf[w[i:]]) for i in range(1, len(w)) if w[:i] in self.dec_pre and w[i:] in self.dec_suf]
            if len(cuts) == 1:
                res += list(cuts[0])
            else:
                res += ["?", "?"]
                bad += 1
        return res, bad


def agree(a, b):
    # 位置をそろえて比べる（失敗の語は 2 字ぶんの ? として数えるので、長さがずれることがある。ずれたら前から順に比べる）
    n = min(len(a), len(b))
    return sum(x == y for x, y in zip(a[:n], b[:n])) / len(b)


def main(tdir):
    T = Path(tdir)
    V = voynich()
    cae, des = letters_of(T / "pg218.txt"), letters_of(T / "pg23306.txt")
    alphabet = [c for c, _ in Counter(cae).most_common()]
    extra = Counter(c for c in des if c not in alphabet)
    des = [c for c in des if c in alphabet]  # 直し: Caesar の字の一覧に無い字（w など）は Descartes から除く
    print(f"Descartes から除いた字: {dict(extra)}", flush=True)
    print(f"平文 Caesar {len(cae)} 字、字の種類 {len(alphabet)}：{''.join(alphabet)}", flush=True)
    for lang in ("A", "B"):
        p_ = V[lang][0]
        vw = [w for ls in p_.values() for l in ls for w in l]
        cap = len(vw)
        ref = measure(p_, V[lang][2], random.Random(2026))
        nb = Naibbe(vw, alphabet)
        print(f"######## 言語 {lang} の表（{cap} 語）  単独の語の例: " + "、".join("".join(x) for x in nb.uni_list[:6])
              + "  語頭側: " + "、".join("".join(x) for x in nb.pre_list[:6]) + "  語尾側: " + "、".join("".join(x) for x in nb.suf_list[:6]), flush=True)
        cw = nb.encrypt(cae, random.Random(1))
        P = dict(line_unit.wrap(cw[:cap], 37))
        lines_ = [l for ls in P.values() for l in ls]
        ws = [w for l in lines_ for w in l]
        print("=== N187 3 つの性質と 8 つの量 ===", flush=True)
        three(f"ヴォイニッチ {lang}", [l for ls in p_.values() for l in ls])
        three(f"Naibbe 型（Caesar）", lines_)
        report("Naibbe 型（Caesar）", P, ref, random.Random(2026))
        print("=== N188 語の作り ===", flush=True)
        for name, x in ((f"ヴォイニッチ {lang}", vw), ("Naibbe 型", ws)):
            f = family(x)
            n, h, wd = endinfo(x)
            print(f"  {name:<14} 家族の場所 頭 {f[0]:.2f} 中 {f[1]:.2f} 末 {f[2]:.2f}  語末の欄の種類 {n}  エントロピー {h:.2f}  語尾の幅 {wd:.2f}  語の種類 {len(set(x))}", flush=True)
        print("=== N189 行・頁と、別の平文 ===", flush=True)
        FM = {pg: [(l, j == 0) for j, l in enumerate(ls)] for pg, ls in P.items()}
        print(f"  行をまたぐ量の順位 {rank(FM, random.Random(7)):.3f}", flush=True)
        dw = nb.encrypt(des, random.Random(2))
        three("Naibbe 型（Descartes, 同じ表）", [l for _, ls in line_unit.wrap(dw[:cap], 37) for l in ls])
        print("=== N190 読み戻し ===", flush=True)
        back, bad = nb.decrypt(cw[:cap])
        n_letters = sum(1 for _ in back)
        plain = cae[:n_letters]
        print(f"  語 {cap}  読み戻せなかった語 {bad}（{bad / cap:.1%}）  字の一致 {agree(back, plain):.1%}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

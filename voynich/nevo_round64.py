#!/usr/bin/env python3
"""nēvo による解析 第 64 巡: 冗長な暗号, 自作の表 2（N191〜N193）。

平文の 1・2 文字の単位を、ヴォイニッチの語頭 ＋ 芯の組 1 つで書き、語末の欄は情報を担わない印として
その組にヴォイニッチで付く語末の割合で選ぶ。表は 6 つ（同じ単位の別の書き方）。

    python3 voynich/nevo_round64.py <texts の場所>
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_unit  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round42 import report  # noqa: E402
from nevo_round47 import family  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round56 import endinfo  # noqa: E402
from nevo_round61 import rank  # noqa: E402
from nevo_round63 import P_BIGRAM, WEIGHTS, letters_of  # noqa: E402


def units_of(letters, rng):
    out, i = [], 0
    while i < len(letters):
        if i + 1 < len(letters) and rng.random() < P_BIGRAM:
            out.append(letters[i] + letters[i + 1])
            i += 2
        else:
            out.append(letters[i])
            i += 1
    return out


class Code2:
    def __init__(self, vwords, unit_rank):
        hc = Counter()
        self.ends = defaultdict(Counter)
        for w in vwords:
            h, m, e = split(w)
            k = tuple(h) + tuple(m)
            if not k:
                continue
            hc[k] += 1
            self.ends[k][tuple(e)] += 1
        inv = [k for k, _ in hc.most_common()]
        U = len(unit_rank)
        self.table = {}
        for t in range(6):
            for r, u in enumerate(unit_rank):
                j = t * U + r
                self.table[(t, u)] = inv[j] if j < len(inv) else self.table[(0, u)]
        self.dec = {}
        for (t, u), k in self.table.items():
            self.dec.setdefault(k, u)
        self.inv_size, self.U = len(inv), U

    def encrypt(self, units, rng):
        out = []
        for u in units:
            t = rng.choices(range(6), WEIGHTS)[0]
            k = self.table.get((t, u))
            if k is None:  # 順位表に無い単位（別の平文で出る）: 1 文字ずつに分けて書く
                for c in u:
                    out.append(self._word(self.table[(t, c)], rng))
                continue
            out.append(self._word(k, rng))
        return out

    def _word(self, k, rng):
        ek, ev = zip(*self.ends[k].items())
        return k + rng.choices(ek, ev)[0]

    def decrypt(self, words):
        res, bad = [], 0
        for w in words:
            h, m, e = split(w)
            k = tuple(h) + tuple(m)
            if k in self.dec:
                res.append(self.dec[k])
            else:
                res.append("?")
                bad += 1
        return res, bad


def main(tdir):
    T = Path(tdir)
    V = voynich()
    cae, des = letters_of(T / "pg218.txt"), letters_of(T / "pg23306.txt")
    alphabet = set(cae)
    des = [c for c in des if c in alphabet]
    cu = units_of(cae, random.Random(1))
    unit_rank = [u for u, _ in Counter(cu).most_common()]
    print(f"平文の単位の種類 {len(unit_rank)}（1 文字 {sum(len(u) == 1 for u in unit_rank)}・2 文字 {sum(len(u) == 2 for u in unit_rank)}）", flush=True)
    for lang in ("A", "B"):
        p_ = V[lang][0]
        vw = [w for ls in p_.values() for l in ls for w in l]
        cap = len(vw)
        ref = measure(p_, V[lang][2], random.Random(2026))
        cd = Code2(vw, unit_rank)
        print(f"######## 言語 {lang}（{cap} 語）  語頭 ＋ 芯の在庫 {cd.inv_size}、必要 {6 * cd.U}", flush=True)
        units = cu
        cw = cd.encrypt(units, random.Random(3))[:cap]
        P = dict(line_unit.wrap(cw, 37))
        lines_ = [l for ls in P.values() for l in ls]
        ws = [w for l in lines_ for w in l]
        print("=== N191 ===", flush=True)
        three(f"ヴォイニッチ {lang}", [l for ls in p_.values() for l in ls])
        three("表 2（Caesar）", lines_)
        report("表 2（Caesar）", P, ref, random.Random(2026))
        print("=== N192 ===", flush=True)
        for name, x in ((f"ヴォイニッチ {lang}", vw), ("表 2", ws)):
            f = family(x)
            n, h, wd = endinfo(x)
            print(f"  {name:<14} 家族の場所 頭 {f[0]:.3f} 中 {f[1]:.2f} 末 {f[2]:.2f}  語末の欄の種類 {n}  語尾の幅 {wd:.2f}  語の種類 {len(set(x))}", flush=True)
        vs = set(vw)
        print(f"  観察: 暗号の語のうちヴォイニッチにある語の種類 {sum(w in vs for w in ws) / len(ws):.1%}（語の数で）", flush=True)
        FM = {pg: [(l, j == 0) for j, l in enumerate(ls)] for pg, ls in P.items()}
        print(f"  （参考）行をまたぐ量の順位 {rank(FM, random.Random(7)):.3f}", flush=True)
        print("=== N193 ===", flush=True)
        back, bad = cd.decrypt(cw)
        plain = "".join(units)
        got = "".join(back)
        n = min(len(plain), len(got))
        ok = sum(a == b for a, b in zip(plain[:n], got[:n])) / n
        print(f"  読み戻せなかった語 {bad}（{bad / cap:.1%}）  字の一致（前から順に） {ok:.1%}", flush=True)
        du = units_of(des, random.Random(2))
        dw = cd.encrypt(du, random.Random(4))[:cap]
        three("表 2（Descartes, 同じ表）", [l for _, ls in line_unit.wrap(dw, 37) for l in ls])


if __name__ == "__main__":
    main(sys.argv[1])

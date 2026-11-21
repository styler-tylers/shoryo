#!/usr/bin/env python3
"""nēvo による解析 第 74 巡: N221（前の行の語の形を見て選ぶ暗号）・N222（隣の行の似かたの中身）。

    python3 voynich/nevo_round74.py <texts の場所>
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round47 import edit_pos  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round64 import units_of  # noqa: E402
from nevo_round69 import synth_words  # noqa: E402
from nevo_round70 import set_uni  # noqa: E402
from nevo_round71 import sim  # noqa: E402
from nevo_round73 import line_excess  # noqa: E402

WIDTH = 37


class VTNlook(r68.VTN):
    q = 0.0

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.prev, self.cur, self.n = [], [], 0

    def _place(self, w):
        add = len(w) + (1 if self.cur else 0)
        if self.cur and self.n + add > WIDTH:
            self.prev, self.cur, self.n = self.cur, [], 0
            add = len(w)
        self.cur.append(w)
        self.n += add

    def word(self, u):
        if self.prev and self.rng.random() < self.q:
            if len(u) == 2:
                cands = [(k + self.end(k), k) for k in self.homo[u]]
            else:
                cands = [(w, w) for w in self.uni[u]]
            best = max(cands, key=lambda c: max(sim(c[0], p) for p in self.prev))
            if len(u) == 2:
                self.homo[u][best[1]] += 1
            else:
                self.uni[u][best[1]] += 1
            w = best[0]
        else:
            w = super().word(u)
        self._place(w)
        return w


def nearest_kind(w, line):
    if w in line:
        return "同じ語"
    best = max(line, key=lambda v: sim(w, v))
    p = edit_pos(w, best)
    return {"頭": "1 か所（語頭）", "中": "1 か所（語中）", "末": "1 か所（語末）"}.get(p, "それ以外")


def main(tdir):
    T = Path(tdir)
    V = voynich()
    print("=== N222 隣の行の似かたの中身 ===", flush=True)
    kinds = ["同じ語", "1 か所（語頭）", "1 か所（語中）", "1 か所（語末）", "それ以外"]
    for lang in ("A", "B"):
        F = flagged(V, lang)
        adj, far = Counter(), Counter()
        rng = random.Random(3)
        for v in F.values():
            ls = [l for l, st in v if not st and l]
            for i in range(len(ls) - 1):
                for w in ls[i + 1]:
                    adj[nearest_kind(w, ls[i])] += 1
                fars = [j for j in range(len(ls)) if abs(j - (i + 1)) >= 3]
                if fars:
                    j = rng.choice(fars)
                    for w in ls[i + 1]:
                        far[nearest_kind(w, ls[j])] += 1
        na, nf = sum(adj.values()), sum(far.values())
        print(f"  言語 {lang}（隣 {na} 語・離れた行 {nf} 語）: " + "  ".join(f"{k} {adj[k] / na:.1%}/{far[k] / nf:.1%}（{(adj[k] / na - far[k] / nf) * 100:+.1f}）" for k in kinds), flush=True)

    print("=== N221 前の行の語の形を見て選ぶ暗号（偶数番目の頁と比べる）===", flush=True)
    p_ = V["B"][0]
    pages_ = list(p_)
    odd = {k: p_[k] for k in pages_[0::2]}
    even = {k: p_[k] for k in pages_[1::2]}
    ow = [w for ls in odd.values() for l in ls for w in l]
    ew = [w for ls in even.values() for l in ls for w in l]
    Fo = {k: v for k, v in flagged(V, "B").items() if k in odd}
    ref_e = measure(even, [x for k, x in zip([k for k, ls in p_.items() for _ in ls], V["B"][2]) if k in even], random.Random(2026))
    Fe = {pg: [l for l, st in v if not st] for pg, v in flagged(V, "B").items() if pg in even}
    ve = line_excess(Fe, random.Random(2))
    print(f"  ヴォイニッチ B・偶数番目の頁: 隣の行の余り {ve:+.4f}", flush=True)
    syn = Counter(synth_words(ow, 300000, random.Random(5)))
    bylen = defaultdict(list)
    for w, c in syn.most_common():
        bylen[len(w)].append(w)
    rank_len = [len(w) for w, _ in Counter(ow).most_common()]
    used = defaultdict(int)
    ordered = []
    for L_ in rank_len * 20:
        lst = bylen.get(L_)
        if lst and used[L_] < len(lst):
            ordered.append(lst[used[L_]])
            used[L_] += 1
        if len(ordered) >= 30000:
            break
    stream = [w for i, w in enumerate(ordered) for _ in range(max(1, 30000 // (i + 1)))]
    set_uni(0.75)
    cae = r68.letters_any(T / "pg218.txt")
    for q in (0.0, 0.3, 0.6):
        VTNlook.q = q
        P = r68.make_text(VTNlook, stream, cae, r68.para_lengths(Fo), len(ew))
        r68.show(f"VTN・前の行を見る q={q}", P, ref_e)
        pages = {k: v[1:] for k, v in P.items()}
        x = line_excess(pages, random.Random(2))
        ctrl = sorted(line_excess({k: random.Random(s).sample(v, len(v)) for k, v in pages.items()}, random.Random(2)) for s in range(20))
        print(f"    隣の行の余り {x:+.4f}（対照 {ctrl[1]:+.4f}〜{ctrl[18]:+.4f}）{'超える' if x > ctrl[18] else ''}", flush=True)
    # 読み戻し（q=0.6 で、書いた語と単位の組を作り直して確かめる）
    VTNlook.q = 0.6
    cu = units_of(cae, random.Random(1))
    rank_ = [u for u, _ in Counter(cu).most_common()]
    vt = VTNlook(stream, rank_, random.Random(3))
    ok = 0
    for u in cu[:len(ew)]:
        w = vt.word(u)
        if len(u) == 1:
            ok += vt.uowner.get(w) == u
        else:
            h, m, e = split(w)
            ok += vt.owner.get(tuple(h) + tuple(m)) == u
    print(f"  読み戻し（q=0.6, 段落の最初の行の規則を掛ける前の語で）{ok / len(ew):.1%}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env python3
"""nēvo による解析 第 75 巡: N224（前の行を見て選ぶ暗号の確かめ直し）・N225（言語 A）。

    python3 voynich/nevo_round75.py <texts の場所>
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nevo_round68 as r68  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
from nevo_round10 import measure, split  # noqa: E402
from nevo_round52 import three  # noqa: E402
from nevo_round59 import flagged  # noqa: E402
from nevo_round64 import units_of  # noqa: E402
from nevo_round69 import synth_words  # noqa: E402
from nevo_round70 import set_uni  # noqa: E402
from nevo_round73 import line_excess  # noqa: E402
from nevo_round74 import VTNlook  # noqa: E402


def stream_from(ow):
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
    return [w for i, w in enumerate(ordered) for _ in range(max(1, 30000 // (i + 1)))]


def run(name, V, lang, train_keys, test_keys, letters):
    p_ = V[lang][0]
    tr = {k: p_[k] for k in train_keys}
    te = {k: p_[k] for k in test_keys}
    tw = [w for ls in tr.values() for l in ls for w in l]
    ew = [w for ls in te.values() for l in ls for w in l]
    F = flagged(V, lang)
    Ft = {k: v for k, v in F.items() if k in tr}
    order = [k for k, ls in p_.items() for _ in ls]
    ref = measure(te, [x for k, x in zip(order, V[lang][2]) if k in te], random.Random(2026))
    print(f"######## {name}（作る側 {len(tw)} 語・比べる側 {len(ew)} 語）", flush=True)
    three("比べる側のヴォイニッチ", [l for ls in te.values() for l in ls])
    Fe = {pg: [l for l, st in v if not st] for pg, v in F.items() if pg in te}
    print(f"    ヴォイニッチの隣の行の余り {line_excess(Fe, random.Random(2)):+.4f}", flush=True)
    st = stream_from(tw)
    set_uni(0.75)
    VTNlook.q = 0.3
    P = r68.make_text(VTNlook, st, letters, r68.para_lengths(Ft), len(ew))
    r68.show("暗号（q = 0.3）", P, ref)
    pages = {k: v[1:] for k, v in P.items()}
    x = line_excess(pages, random.Random(2))
    ctrl = sorted(line_excess({k: random.Random(s).sample(v, len(v)) for k, v in pages.items()}, random.Random(2)) for s in range(20))
    print(f"    隣の行の余り {x:+.4f}（対照 {ctrl[1]:+.4f}〜{ctrl[18]:+.4f}）{'超える' if x > ctrl[18] else '超えない'}", flush=True)
    cu = units_of(letters, random.Random(1))
    vt = VTNlook(st, [u for u, _ in Counter(cu).most_common()], random.Random(3))
    ok = 0
    for u in cu[:len(ew)]:
        w = vt.word(u)
        if len(u) == 1:
            ok += vt.uowner.get(w) == u
        else:
            h, m, e = split(w)
            ok += vt.owner.get(tuple(h) + tuple(m)) == u
    print(f"    読み戻し {ok / len(ew):.1%}", flush=True)


def main(tdir):
    T = Path(tdir)
    V = voynich()
    kb = list(V["B"][0])
    ka = list(V["A"][0])
    print("=== N224 確かめ直し ===", flush=True)
    run("C1 Descartes・奇数 → 偶数", V, "B", kb[0::2], kb[1::2], r68.letters_any(T / "pg23306.txt"))
    run("C2 Dante・奇数 → 偶数", V, "B", kb[0::2], kb[1::2], r68.letters_any(T / "pg1012.txt"))
    h = len(kb) // 2
    run("C3 Caesar・前半 → 後半", V, "B", kb[:h], kb[h:], r68.letters_any(T / "pg218.txt"))
    print("=== N225 言語 A ===", flush=True)
    run("言語 A・Caesar・奇数 → 偶数", V, "A", ka[0::2], ka[1::2], r68.letters_any(T / "pg218.txt"))


if __name__ == "__main__":
    main(sys.argv[1])

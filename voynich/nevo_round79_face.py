#!/usr/bin/env python3
"""nēvo による解析 第 79 巡: N234（顔と髪型だけを見る目隠し判定 3）の答え合わせ。

    python3 voynich/nevo_round79_face.py <答えの表 json> <判定の json の場所>
"""
import glob, json, os, sys
from itertools import product


def mw_one_sided(a, b):
    """a が b より高い、の片側の Mann–Whitney（同順位は 0.5）。並べ替えで正確な p"""
    from itertools import combinations
    allv = a + b; n = len(a)
    def U(x, y):
        return sum((i > j) + 0.5 * (i == j) for i, j in product(x, y))
    u0 = U(a, b); cnt = tot = 0
    for idx in combinations(range(len(allv)), n):
        s = set(idx); x = [allv[i] for i in idx]; y = [allv[i] for i in range(len(allv)) if i not in s]
        tot += 1; cnt += U(x, y) >= u0 - 1e-9
    return u0, cnt / tot


def main(keyf, recdir):
    key = {k["id"]: k for k in json.load(open(keyf))}
    same, diff = [], []
    for fp in sorted(glob.glob(os.path.join(recdir, "*.json"))):
        d = json.load(open(fp)); d = d.get("data", d)
        k = key[os.path.basename(fp)[:-5]]
        sim = d.get("sim", "")
        v = int(sim) if sim.isdigit() else None
        print(f"  {k['id']} {k['kind']:<4} {k['word']:<7} {k['left']['page']}#{k['left']['num']:<3} {k['right']['page']}#{k['right']['num']:<3} 似かた {sim or '—'}  濃さ {d.get('ink')}  {d.get('note','')}")
        if v is not None:
            (same if k["kind"] == "same" else diff).append(v)
    print(f"同じ語 {len(same)} 組: {sorted(same)}  平均 {sum(same)/len(same):.2f}")
    print(f"違う語 {len(diff)} 組: {sorted(diff)}  平均 {sum(diff)/len(diff):.2f}")
    u, p = mw_one_sided(same, diff)
    print(f"Mann–Whitney（片側, 同じ語が高い） U {u}  正確な p {p:.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

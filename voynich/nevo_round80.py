#!/usr/bin/env python3
"""nēvo による解析 第 80 巡: N237（薬学の頁の目隠し判定）の答え合わせ。

    python3 voynich/nevo_round80.py <答えの表 json> <判定の json の場所>
"""
import glob, json, os, sys
from itertools import combinations, product


def U(x, y):
    return sum((i > j) + 0.5 * (i == j) for i, j in product(x, y))


def mw_one_sided(a, b):
    """a が b より高い、の片側の Mann–Whitney。並べ替えで正確な p"""
    allv = a + b; u0 = U(a, b); cnt = tot = 0
    for idx in combinations(range(len(allv)), len(a)):
        s = set(idx)
        tot += 1; cnt += U([allv[i] for i in idx], [allv[i] for i in range(len(allv)) if i not in s]) >= u0 - 1e-9
    return u0, cnt / tot


def main(keyf, recdir):
    key = {k["id"]: k for k in json.load(open(keyf))}
    same, diff, rows = [], [], []
    for fp in sorted(glob.glob(os.path.join(recdir, "*.json"))):
        d = json.load(open(fp)); d = d.get("data", d)
        k = key[os.path.basename(fp)[:-5]]
        sim = d.get("sim", ""); v = int(sim) if sim.isdigit() else None
        print(f"  {k['id']} {k['kind']:<4} {k['a']:<9}({k['a_word']}, {k['a_kind']}) {k['b']:<9}({k['b_word']}, {k['b_kind']})  似かた {sim}  {d.get('note','')}")
        if v is not None:
            (same if k["kind"] == "same" else diff).append(v)
            rows.append((k, v))
    print(f"同じ語 {len(same)} 組: {sorted(same)}  平均 {sum(same)/len(same):.2f}")
    print(f"違う語 {len(diff)} 組: {sorted(diff)}  平均 {sum(diff)/len(diff):.2f}")
    u, p = mw_one_sided(same, diff)
    print(f"Mann–Whitney（片側, 同じ語が高い） U {u}  正確な p {p:.4f}")
    s2 = [v for k, v in rows if k["kind"] == "same" and k["a_kind"] == k["b_kind"] == "植物"]
    d2 = [v for k, v in rows if k["kind"] == "diff" and k["a_kind"] == k["b_kind"] == "植物"]
    u, p = mw_one_sided(s2, d2)
    print(f"（参考）植物どうしの組だけ: 同じ語 {len(s2)} 組 平均 {sum(s2)/len(s2):.2f}、違う語 {len(d2)} 組 平均 {sum(d2)/len(d2):.2f}、p {p:.4f}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

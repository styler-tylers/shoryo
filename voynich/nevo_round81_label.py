#!/usr/bin/env python3
"""nēvo による解析 第 81 巡: N239（なぞり直しとラベル）。胸の濃さ（第 248 節）とラベルの濃さの、頁ごとに中心を引いた後の Spearman。

    python3 voynich/nevo_round81_label.py <黄道の画像の場所> voynich/data/breast_figures_round79.json <胸の記録の場所> <ラベルの記録の場所>
"""
import glob, json, os, random, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zodiac_geom import Panels  # noqa: E402


def rank(v):
    o = np.argsort(np.argsort(v)); return o.astype(float)


def main(imgdir, keyf, bdir, ldir):
    P = Panels(imgdir)
    key = {k["id"]: k for k in json.load(open(keyf))}
    rows = []
    for fp in sorted(glob.glob(os.path.join(ldir, "*.json"))):
        fid = os.path.basename(fp)[:-5]
        L = json.load(open(fp)); L = L.get("data", L)
        B = json.load(open(os.path.join(bdir, fid + ".json"))); B = B.get("data", B)
        k = key[fid]
        im = np.asarray(P.get(k["page"]).convert("L"), dtype=float)
        x0, y0, x1, y1 = k["box"]; w = x1 - x0
        base = np.percentile(im[max(0, y0):y1, max(0, x0):x1], 80); R = 0.03 * w

        def dark(pt):
            if not pt:
                return None
            cx, cy = x0 + pt[0] * w, y0 + pt[1] * w
            yy, xx = np.mgrid[int(cy - R):int(cy + R) + 1, int(cx - R):int(cx + R) + 1]
            m = (xx - cx) ** 2 + (yy - cy) ** 2 <= R * R
            v = np.sort(im[yy[m].clip(0, im.shape[0] - 1), xx[m].clip(0, im.shape[1] - 1)])
            return (base - v[: max(1, len(v) // 10)].mean()) / base
        lab = None if (L.get("noFig") or L.get("labelNA")) else dark(L.get("label"))
        br = [x for x in (dark(B.get("left")), dark(B.get("right"))) if x is not None] if not B.get("noFig") else []
        bmax = max(br) if br else None
        pg = "f72r" if k["page"].startswith("f72r") else k["page"]
        print(f"  {fid} {k['page']:<6} {' '.join(k['words']):<10} ラベル {'' if lab is None else f'{lab:.3f}':<6} 胸 {'' if bmax is None else f'{bmax:.3f}'}"
              f"{'  ラベルが見えない' if L.get('labelNA') else ''}{'  人物が見つからない' if L.get('noFig') else ''}")
        if lab is not None and bmax is not None:
            rows.append((pg, lab, bmax))
    print(f"ラベルと胸の両方がある人物 {len(rows)}")
    by = defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    xs, ys = [], []
    for pg, rs in by.items():
        if len(rs) < 2:
            continue
        a = rank(np.array([r[1] for r in rs])); b = rank(np.array([r[2] for r in rs]))
        xs += list(a - a.mean()); ys += list(b - b.mean())
        print(f"  {pg:<6} 人物 {len(rs)}  ラベルの濃さの平均 {np.mean([r[1] for r in rs]):.3f}  胸 {np.mean([r[2] for r in rs]):.3f}")
    xs, ys = np.array(xs), np.array(ys)
    rho = np.corrcoef(xs, ys)[0, 1]
    # 並べ替え: 頁の中で胸の順位をかき混ぜる
    rng = random.Random(2031); cnt = 0; N = 20000
    groups = [(pg, rs) for pg, rs in by.items() if len(rs) >= 2]
    for _ in range(N):
        yy = []
        for pg, rs in groups:
            b = rank(np.array([r[2] for r in rs])); b = list(b - b.mean()); rng.shuffle(b); yy += b
        cnt += abs(np.corrcoef(xs, yy)[0, 1]) >= abs(rho) - 1e-12
    print(f"頁ごとに中心を引いた Spearman ρ {rho:+.3f}（人物 {len(xs)}）  並べ替えの p（両側） {cnt / N:.3f}")
    allL = [r[1] for r in rows]; allB = [r[2] for r in rows]
    print(f"（参考）ラベルの濃さ 中央値 {np.median(allL):.3f}、胸の濃さ 中央値 {np.median(allB):.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:5])

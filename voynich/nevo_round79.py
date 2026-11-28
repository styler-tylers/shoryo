#!/usr/bin/env python3
"""nēvo による解析 第 79 巡: N235（右胸と左胸の濃さ）。

    python3 voynich/nevo_round79.py <黄道の画像の場所> <人物の表 json> <胸の記録の json の場所>
"""
import glob, json, math, os, random, statistics, sys
from collections import defaultdict
from math import comb
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zodiac_geom import Panels  # noqa: E402


def sign_p(k, n):
    """両側の符号検定"""
    if n == 0:
        return float("nan")
    t = sum(comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * t)


def main(imgdir, keyf, recdir):
    P = Panels(imgdir)
    key = {k["id"]: k for k in json.load(open(keyf))}
    rows = []
    for fp in sorted(glob.glob(os.path.join(recdir, "*.json"))):
        d = json.load(open(fp)); d = d.get("data", d)
        k = key[os.path.basename(fp)[:-5]]
        if d.get("noFig"):
            rows.append((k["id"], k["page"], None, None, "人物が見つからない")); continue
        im = np.asarray(P.get(k["page"]).convert("L"), dtype=float)
        x0, y0, x1, y1 = k["box"]
        w = x1 - x0
        box = im[max(0, y0):y1, max(0, x0):x1]
        B = np.percentile(box, 80)
        R = 0.03 * w
        def dark(pt):
            if not pt:
                return None
            cx, cy = x0 + pt[0] * w, y0 + pt[1] * w
            yy, xx = np.mgrid[int(cy - R):int(cy + R) + 1, int(cx - R):int(cx + R) + 1]
            m = (xx - cx) ** 2 + (yy - cy) ** 2 <= R * R
            vals = im[yy[m].clip(0, im.shape[0] - 1), xx[m].clip(0, im.shape[1] - 1)]
            q = np.sort(vals)[: max(1, len(vals) // 10)]
            return (B - q.mean()) / B
        rows.append((k["id"], k["page"], dark(d.get("left")), dark(d.get("right")), ""))
    both = [r for r in rows if r[2] is not None and r[3] is not None]
    print(f"記録 {len(rows)}、左右とも指した人物 {len(both)}、人物が見つからない {sum(r[4] != '' for r in rows)}、"
          f"片方だけ {sum((r[2] is None) != (r[3] is None) for r in rows)}")
    for r in rows:
        print(f"  {r[0]} {r[1]:<6} 画像の左 {'' if r[2] is None else f'{r[2]:.3f}'}  画像の右 {'' if r[3] is None else f'{r[3]:.3f}'}  {r[4]}")
    def summary(rs, label):
        L = sum(r[2] > r[3] for r in rs); Rr = sum(r[3] > r[2] for r in rs)
        diff = [r[2] - r[3] for r in rs]
        print(f"  {label:<16} 人物 {len(rs):>2}  画像の左が濃い {L}・右が濃い {Rr}  差（左 − 右）の中央値 {statistics.median(diff) if diff else float('nan'):+.3f}"
              f"  符号検定 p {sign_p(min(L, Rr), L + Rr):.3f}", flush=True)
        return L, Rr
    print("=== (a) 左右の偏り ===")
    summary(both, "全て")
    byp = defaultdict(list)
    for r in both:
        byp[r[1] if r[1] not in ("f72r1", "f72r2") else "f72r"].append(r)
    print("=== (b) 頁ごと ===")
    for pg in sorted(byp):
        summary(byp[pg], pg)


if __name__ == "__main__":
    main(*sys.argv[1:4])

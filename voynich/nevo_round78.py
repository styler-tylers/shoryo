#!/usr/bin/env python3
"""nēvo による解析 第 78 巡: N231（胸のインクの濃さを画素の値で測る）。

    python3 voynich/nevo_round78.py <黄道の画像の場所> <答えの表 json> <判定の json の場所>
"""
import glob, json, math, os, random, statistics, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zodiac_geom import GEOM, Panels, figures  # noqa: E402

SKIP = {"f72v3", "f72v2"}


def gray(im):
    return np.asarray(im.convert("L"), dtype=float)


def darkness(a):
    B = np.percentile(a, 80)
    return (B - np.percentile(a, 1)) / B


def main(imgdir, keyf, judged):
    P = Panels(imgdir)
    F = [f for f in figures() if f["clock"] and f["page"] in GEOM and f["page"] not in SKIP and f["ring"] in (0, 1, 2)]
    dpage, E = {}, {}
    for pg in sorted({f["page"] for f in F}):
        im = P.get(pg)
        W, H = im.size
        cx, cy, radii = GEOM[pg]
        R = 1.2 * radii[1] * W
        a = gray(im)
        yy, xx = np.mgrid[0:H, 0:W]
        mask = (xx - cx * W) ** 2 + (yy - cy * H) ** 2 <= R * R
        dpage[pg] = darkness(a[mask])
    for f in F:
        im, W, H, X0, Y0, rad, th = P.point(f)
        X, Y = X0 + rad * math.sin(th), Y0 - rad * math.cos(th)
        S = max(0.20 * W, 0.60 * rad) * 0.4   # 拡大図の中央の丸の範囲（拡大図の 0.4 倍の正方形）
        a = gray(im.crop((int(X - S / 2), int(Y - S / 2), int(X + S / 2), int(Y + S / 2))))
        E[(f["page"], f["num"])] = darkness(a) - dpage[f["page"]]
    print("=== 頁ごと ===")
    byp = defaultdict(list)
    for (pg, n), e in E.items():
        byp[pg].append(e)
    for pg in sorted(byp):
        print(f"  {pg:<6} d_頁 {dpage[pg]:.3f}  人物 {len(byp[pg])}  E の中央値 {statistics.median(byp[pg]):+.3f}", flush=True)
    # 確かめ: 研究者の判定
    key = {k["id"]: k for k in json.load(open(keyf))}
    rated = []
    for fpath in glob.glob(os.path.join(judged, "*.json")):
        d = json.load(open(fpath)); d = d.get("data", d)
        k = key[os.path.basename(fpath)[:-5]]
        for side, ink in zip(("left", "right"), d.get("ink", [])):
            fk = (k[side]["page"], k[side]["num"])
            if ink in ("dark", "same") and fk in E:
                rated.append((ink, E[fk], fk[0]))
    dk = [e for i, e, _ in rated if i == "dark"]
    sm = [e for i, e, _ in rated if i == "same"]
    obs = statistics.mean(dk) - statistics.mean(sm)
    allv = dk + sm
    rng = random.Random(2026)
    hit = 0
    for _ in range(5000):
        rng.shuffle(allv)
        hit += statistics.mean(allv[:len(dk)]) - statistics.mean(allv[len(dk):]) >= obs
    print(f"=== 確かめ: 研究者の判定との対応 ===\n  濃い {len(dk)} 人 E 平均 {statistics.mean(dk):+.3f}  輪郭と同じ {len(sm)} 人 E 平均 {statistics.mean(sm):+.3f}  差 {obs:+.3f}  p {hit / 5000:.4f}", flush=True)
    f73 = byp["f73r"]
    others = [e for pg, v in byp.items() if pg != "f73r" for e in v]
    print(f"=== (a) f73r の E の中央値 {statistics.median(f73):+.3f}  他の頁 {statistics.median(others):+.3f}  差 {statistics.median(f73) - statistics.median(others):+.3f}", flush=True)
    od = [v for pg, v in dpage.items() if pg != "f73r"]
    print(f"=== (b) f73r の d_頁 {dpage['f73r']:.3f}  他の頁の中央値 {statistics.median(od):.3f}  差 {dpage['f73r'] - statistics.median(od):+.3f}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])

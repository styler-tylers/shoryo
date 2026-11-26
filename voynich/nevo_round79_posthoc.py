"""第 79 巡の事後の対照: 押した点を上下にずらして左右を比べる。

    python3 voynich/nevo_round79_posthoc.py <黄道の画像の場所> <人物の表 json> <胸の記録の json の場所>
"""
import sys, glob, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from zodiac_geom import Panels
imgdir, keyf, recdir = sys.argv[1:4]
P = Panels(imgdir); key = {k["id"]: k for k in json.load(open(keyf))}
for dy in (0.08, 0.15, -0.10):
    L = R = 0
    for fp in sorted(glob.glob(os.path.join(recdir, "*.json"))):
        d = json.load(open(fp)); d = d.get("data", d)
        if d.get("noFig") or not d.get("left") or not d.get("right"): continue
        k = key[os.path.basename(fp)[:-5]]
        im = np.asarray(P.get(k["page"]).convert("L"), dtype=float)
        x0, y0, x1, y1 = k["box"]; w = x1 - x0
        B = np.percentile(im[max(0,y0):y1, max(0,x0):x1], 80); Rr = 0.03 * w
        def dark(pt):
            cx, cy = x0 + pt[0]*w, y0 + (pt[1]+dy)*w
            yy, xx = np.mgrid[int(cy-Rr):int(cy+Rr)+1, int(cx-Rr):int(cx+Rr)+1]
            m = (xx-cx)**2 + (yy-cy)**2 <= Rr*Rr
            v = np.sort(im[yy[m].clip(0,im.shape[0]-1), xx[m].clip(0,im.shape[1]-1)])
            return (B - v[:max(1,len(v)//10)].mean()) / B
        a, b = dark(d["left"]), dark(d["right"])
        L += a > b; R += b > a
    print(f"ずらし {dy:+.2f}: 画像の左が濃い {L}・右が濃い {R}")

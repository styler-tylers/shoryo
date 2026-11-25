"""「黄道人物の胸を指す」ページを作る（第 246 節 N235, 種 2028）。
    python3 voynich/build_breast_page.py <画像の場所> <出力 html> <template> <人物の表 json>
"""
import json, math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zodiac_geom import Panels, enc, figures  # noqa: E402

IMG, OUT, TPL, KEY = map(Path, sys.argv[1:5])
QUOTA = [({"f73r"}, 10), ({"f70v2"}, 6), ({"f72r1", "f72r2"}, 6), ({"f73v"}, 4), ({"f72v1"}, 4)]
rng = random.Random(2028)
F = [f for f in figures() if f["clock"] and f["ring"] in (1, 2)]
chosen = []
for pages, n in QUOTA:
    pool = [f for f in F if f["page"] in pages]
    chosen += rng.sample(pool, n)
rng.shuffle(chosen)
P = Panels(IMG)
data, key, imgs = [], [], {}
for i, f in enumerate(chosen, 1):
    im, W, H, X0, Y0, rad, th = P.point(f)
    X, Y = X0 + rad * math.sin(th), Y0 - rad * math.cos(th)
    S = max(0.22 * W, 0.65 * rad)
    box = (int(X - S / 2), int(Y - S / 2), int(X + S / 2), int(Y + S / 2))
    zm = im.crop(box).resize((640, 640))
    fid = f"f{i:02d}"
    imgs[fid] = enc(zm, 74)
    data.append(dict(id=fid, page=f["page"]))
    key.append(dict(id=fid, page=f["page"], num=f["num"], ring=f["ring"], clock=f["clock"], words=f["words"], box=box))
KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
OUT.write_text(TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data)).replace("__IMGS__", json.dumps(imgs)), encoding="utf-8")
print(len(data))

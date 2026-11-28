"""「薬学の頁の目隠し判定」のページを作る（第 256 節 N237 の事前の登録どおり, 種 2029）。

    python3 voynich/build_pharma_blind_page.py <Yale IIIF の画像の場所> voynich/notes/html/薬学ラベルの照合.html \\
        voynich/data/pharma_label_positions_round80.json voynich/data/pharma_label_judgments_round80.json \\
        voynich/notes/html/pharma_blind_template.html <出力 html> <答えの表 json>

物の中心: 植物のラベルは研究者が付けた青い点（第 255 節）、容器のラベル 2 か所は容器の中心（CONTAINER）。
拡大図の中の 16 か所のラベルの語は、まわりの羊皮紙の色で塗りつぶす。判定する物には青い点を付ける（研究者が前のページで付けた印と同じ形）。"""
import base64, io, json, random, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
IMG, LABHTML, POSF, JUDF, TPL, OUT, KEY = map(Path, sys.argv[1:8])
P = json.load(open(POSF)); J = json.load(open(JUDF))
DATA = json.loads(re.search(r"const DATA = (\[.*?\]);\nconst CHOICES", LABHTML.read_text(encoding="utf-8"), re.S).group(1))
CONTAINER = {"f88r.12": (0.155, 0.480), "f89v2.11": (0.155, 0.470)}   # 容器の中心（画像の割合）
objs = []
for g in DATA:
    for i in g["inst"]:
        p = P["pos"][i["loc"]]
        im = Image.open(IMG / f"{p['img']}.jpg"); W, H = im.size
        if i["loc"] in CONTAINER:
            cx, cy = CONTAINER[i["loc"]][0] * W, CONTAINER[i["loc"]][1] * H; kind = "容器"
        else:
            x0, y0, x1, y1 = i["box"]; pk = J[g["id"]]["picks"][i["loc"]]
            cx, cy = x0 + pk[0] * (x1 - x0), y0 + pk[1] * (y1 - y0); kind = "植物"
        objs.append(dict(loc=i["loc"], word=g["id"], page=i["page"], img=p["img"], cx=cx, cy=cy, kind=kind))
rng = random.Random(2029)
same = []
for w in dict.fromkeys(o["word"] for o in objs):
    inst = [o for o in objs if o["word"] == w]
    same += [(a, b) for k, a in enumerate(inst) for b in inst[k + 1:]]
assert len(same) == 11, len(same)
cand = [(a, b) for k, a in enumerate(objs) for b in objs[k + 1:] if a["word"] != b["word"] and a["page"] != b["page"]]
rng.shuffle(cand)
use = {}; diff = []
for a, b in cand:
    if use.get(a["loc"], 0) < 2 and use.get(b["loc"], 0) < 2:
        diff.append((a, b)); use[a["loc"]] = use.get(a["loc"], 0) + 1; use[b["loc"]] = use.get(b["loc"], 0) + 1
    if len(diff) == 11:
        break
pairs = [("same", a, b) for a, b in same] + [("diff", a, b) for a, b in diff]
rng.shuffle(pairs)
pairs = [(k, *((a, b) if rng.random() < 0.5 else (b, a))) for k, a, b in pairs]


def crop(o):
    im = Image.open(IMG / f"{o['img']}.jpg").convert("RGB"); W, H = im.size
    pw = P["page_frac"][o["img"]] * W
    S = int((0.46 if o["kind"] == "容器" else 0.36) * pw)
    x0 = int(min(max(o["cx"] - S / 2, 0), W - S)); y0 = int(min(max(o["cy"] - S / 2, 0), H - S))
    a = np.asarray(im).copy()
    for loc, q in P["pos"].items():               # 同じ画像の 16 か所のラベルを塗る
        if q["img"] != o["img"]:
            continue
        lx, ly = q["x"] * W, q["y"] * H; rw, rh = 0.06 * pw, 0.024 * pw
        ys, xs = np.ogrid[:H, :W]
        m = ((xs - lx) / rw) ** 2 + ((ys - ly) / rh) ** 2 <= 1
        ring = (((xs - lx) / (rw * 1.5)) ** 2 + ((ys - ly) / (rh * 1.8)) ** 2 <= 1) & ~m
        col = np.percentile(a[ring], 60, axis=0)
        a[m] = col
    im = Image.fromarray(a)
    z = im.crop((x0, y0, x0 + S, y0 + S)).resize((640, 640), Image.LANCZOS)
    d = ImageDraw.Draw(z); k = 640 / S; ex, ey = (o["cx"] - x0) * k, (o["cy"] - y0) * k
    d.ellipse([ex - 17, ey - 17, ex + 17, ey + 17], fill=(31, 95, 168), outline=(255, 255, 255), width=4)  # 判定する物の印
    buf = io.BytesIO(); z.save(buf, "JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


cache = {}
out, key = [], []
for n, (k, a, b) in enumerate(pairs, 1):
    pid = f"q{n:02d}"
    for o in (a, b):
        if o["loc"] not in cache:
            cache[o["loc"]] = crop(o)
    out.append(dict(id=pid, a=a["loc"], b=b["loc"]))
    key.append(dict(id=pid, kind=k, a=a["loc"], a_word=a["word"], a_kind=a["kind"], b=b["loc"], b_word=b["word"], b_kind=b["kind"]))
pub = [dict(id=p["id"], figs=[cache[p["a"]], cache[p["b"]]]) for p in out]
# 組の id から場所が分からないよう、ページには画像だけを入れる
OUT.write_text(TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(pub)), encoding="utf-8")
KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(pub), "組", sum(k == "same" for k, _, _ in pairs), "同じ語", OUT.stat().st_size)

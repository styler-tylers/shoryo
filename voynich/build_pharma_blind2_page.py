"""「薬学の目隠し判定 2（1 字違いのラベル）」のページを作る（第 259 節 N238 の事前の登録どおり）。

    python3 voynich/build_pharma_blind2_page.py <Yale IIIF の画像の場所> <答えの表 json（pharma_near_pairs.py が作る）> \\
        voynich/data/pharma_label_positions_round81.json voynich/data/pharma_label_positions_round80.json \\
        voynich/notes/html/pharma_blind_template.html <出力 html>

物の中心は positions の obj。拡大図の中の既知のラベル（第 80・81 巡の 40 か所）は羊皮紙の色で塗り、物には青い点を付ける。"""
import base64, io, json, sys
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
IMG, KEYF, POS81, POS80, TPL, OUT = map(Path, sys.argv[1:7])
P = json.load(open(POS81)); P80 = json.load(open(POS80))
PF = {**P80["page_frac"], **P["page_frac"]}
ALL = list(P80["pos"].values()) + list(P["pos"].values())
key = json.load(open(KEYF))


def crop(loc):
    o = P["pos"][loc]
    im = Image.open(IMG / f"{o['img']}.jpg").convert("RGB"); W, H = im.size
    pw = PF[o["img"]] * W; S = int(0.36 * pw)
    cx, cy = o["obj"][0] * W, o["obj"][1] * H
    x0 = int(min(max(cx - S / 2, 0), W - S)); y0 = int(min(max(cy - S / 2, 0), H - S))
    a = np.asarray(im).copy()
    ys, xs = np.ogrid[:H, :W]
    for q in ALL:
        if q["img"] != o["img"]:
            continue
        lx, ly = q["x"] * W, q["y"] * H; rw, rh = 0.06 * pw, 0.024 * pw
        if lx + rw < x0 or lx - rw > x0 + S or ly + rh < y0 or ly - rh > y0 + S:
            continue
        m = ((xs - lx) / rw) ** 2 + ((ys - ly) / rh) ** 2 <= 1
        ring = (((xs - lx) / (rw * 1.5)) ** 2 + ((ys - ly) / (rh * 1.8)) ** 2 <= 1) & ~m
        a[m] = np.percentile(a[ring], 60, axis=0)
    z = Image.fromarray(a).crop((x0, y0, x0 + S, y0 + S)).resize((640, 640), Image.LANCZOS)
    d = ImageDraw.Draw(z); k = 640 / S; ex, ey = (cx - x0) * k, (cy - y0) * k
    d.ellipse([ex - 17, ey - 17, ex + 17, ey + 17], fill=(31, 95, 168), outline=(255, 255, 255), width=4)
    buf = io.BytesIO(); z.save(buf, "JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


cache = {}
pub = []
for p in key:
    for l in (p["a"], p["b"]):
        if l not in cache:
            cache[l] = crop(l)
    pub.append(dict(id=p["id"], figs=[cache[p["a"]], cache[p["b"]]]))
html = TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(pub))
html = html.replace("<title>薬学の目隠し判定</title>", "<title>薬学の目隠し判定 2</title>").replace("<h1>薬学の目隠し判定</h1>", "<h1>薬学の目隠し判定 2</h1>")
html = html.replace("22 組並べました。組の中には、同じ語のラベルが付いた 2 つと、違う語のラベルが付いた 2 つが混ざっています。",
                    "24 組並べました。組の中には、よく似た語（1 字だけ違う語）のラベルが付いた 2 つと、かけ離れた語のラベルが付いた 2 つが混ざっています。")
html = html.replace("前の日に見た物も入っています。思い出せる組があっても、見た目だけで判定してください。", "前回とは別の物です。")
html = html.replace("/ 22 組を保存", "/ 24 組を保存").replace('collection("pharmablind")', 'collection("pharmablind2")').replace("（第 256 節）", "（第 259 節）")
OUT.write_text(html, encoding="utf-8")
print(len(pub), "組", OUT.stat().st_size)

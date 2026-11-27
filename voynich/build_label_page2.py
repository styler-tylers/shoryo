"""「薬学ラベルの照合」のページを作り直す（第 80 巡）: ラベルごとに拡大図（赤丸がラベル）と頁の中の場所の小図を並べる。

    python3 voynich/build_label_page2.py <Yale IIIF の画像の場所> voynich/notes voynich/data/pharma_label_positions_round80.json \\
        voynich/notes/html/label_template2.html voynich/notes/html/薬学ラベルの照合.html

画像は https://collections.library.yale.edu/iiif/2/<id>/full/2800,/0/default.jpg（2800 が大きすぎる画像は 2000）。
拡大図の枠（画像の画素）を DATA の box に残し、押した点を頁の画像の上に戻せるようにする。"""
import base64, csv, io, json, sys
from pathlib import Path
from PIL import Image, ImageDraw
IMG, NOTES, POSF, TPL, OUT = map(Path, sys.argv[1:6])
P = json.load(open(POSF))
rows = list(csv.DictReader(open(NOTES / "薬学ラベル対応表.csv", encoding="utf-8-sig")))
obs = {r["ロカス"]: r for r in csv.DictReader(open(NOTES / "pharma_label_observations.csv", encoding="utf-8-sig"))}
groups = [("otoky", ["otoky"]), ("otaly", ["otaly"]), ("otaldy", ["otaldy"]), ("okol", ["okol"]), ("otoldy", ["otoldy"]),
          ("otory", ["otory"]), ("okaiin", ["okaiin", "okaiin dan"])]


def b64(im, q=78):
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


data = []
for gid, labs in groups:
    inst = []
    for r in rows:
        if r["ラベル"] not in labs:
            continue
        p = P["pos"][r["ロカス"]]
        im = Image.open(IMG / f"{p['img']}.jpg").convert("RGB"); W, H = im.size
        pw = P["page_frac"][p["img"]] * W
        S = int(0.36 * pw); cx, cy = p["x"] * W, p["y"] * H
        x0 = int(min(max(cx - S / 2, 0), W - S)); y0 = int(min(max(cy - S * 0.30, 0), H - S))
        Z = 720; k = Z / S
        z = im.crop((x0, y0, x0 + S, y0 + S)).resize((Z, Z), Image.LANCZOS)
        d = ImageDraw.Draw(z)
        ex, ey = (cx - x0) * k, (cy - y0) * k; rw, rh = 0.055 * pw * k, 0.022 * pw * k
        d.ellipse([ex - rw, ey - rh, ex + rw, ey + rh], outline=(225, 20, 20), width=4)
        # 頁の中の場所: 1 頁ぶんを切り出して縮め、赤い枠
        px0 = int(min(max(cx - pw / 2, 0), W - pw)) if pw < W else 0
        ov = im.crop((px0, 0, int(px0 + pw), H)); s = 520 / ov.width
        ov = ov.resize((520, int(H * s)))
        ImageDraw.Draw(ov).rectangle([(x0 - px0) * s, y0 * s, (x0 - px0 + S) * s, (y0 + S) * s], outline=(225, 20, 20), width=4)
        o = obs.get(r["ロカス"], {})
        inst.append(dict(loc=r["ロカス"], page=r["頁"], dan=r["段"], order=r["段内の順"], kind=r["種類"], label=r["ラベル"],
                         obs=o.get("物の様子", ""), conf=p["conf"], img=p["img"], box=[x0, y0, x0 + S, y0 + S],
                         zoom=b64(z), over=b64(ov, 70)))
    data.append(dict(id=gid, labels=labs, inst=inst))
html = open(TPL, encoding="utf-8").read().replace("__DATA__", json.dumps(data, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print(len(html), [(d["id"], len(d["inst"])) for d in data])

"""「薬学ラベルの照合」のページを作る: python3 voynich/build_label_page.py <Yale IIIF の画像の場所> voynich/notes voynich/notes/html/薬学ラベルの照合.html voynich/notes/html/label_template.html
画像は https://collections.library.yale.edu/iiif/2/<id>/full/1400,/0/default.jpg（id は pageimg の表）。"""
import base64, csv, io, json, sys
from pathlib import Path
from PIL import Image
IMG = Path(sys.argv[1]); NOTES = Path(sys.argv[2]); OUT = Path(sys.argv[3])
rows = list(csv.DictReader(open(NOTES / "薬学ラベル対応表.csv", encoding="utf-8-sig")))
obs = {r["ロカス"]: r for r in csv.DictReader(open(NOTES / "pharma_label_observations.csv", encoding="utf-8-sig"))}
pageimg = {"f88r": ["1037112"], "f88v": ["1006233"], "f89r1": ["1006233"], "f89r2": ["1006233"], "f89v2": ["1006234", "1006235"],
           "f99r": ["1006246"], "f99v": ["1006247"], "f101v": ["1006250", "1006251"], "f102v2": ["1006252"]}
imgname = {"1037112": "88r", "1006233": "88v と 89r（折り込み）", "1006234": "89v（一部）", "1006235": "89v（一部）と 90r",
           "1006246": "99r", "1006247": "99v", "1006250": "101v（一部）", "1006251": "101v（一部）と 102r", "1006252": "102v（一部, f102v2 と判断）"}
groups = [("otoky", ["otoky"]), ("otaly", ["otaly"]), ("otaldy", ["otaldy"]), ("okol", ["okol"]), ("otoldy", ["otoldy"]),
          ("otory", ["otory"]), ("okaiin", ["okaiin", "okaiin dan"])]
data, used = [], set()
for gid, labs in groups:
    inst = []
    for r in rows:
        if r["ラベル"] in labs:
            o = obs.get(r["ロカス"], {})
            inst.append(dict(page=r["頁"], dan=r["段"], order=r["段内の順"], kind=r["種類"], label=r["ラベル"],
                             obs=o.get("物の様子", ""), where=o.get("ラベルの位置", ""), conf=o.get("確からしさ", ""),
                             imgs=pageimg.get(r["頁"], [])))
            used.update(pageimg.get(r["頁"], []))
    data.append(dict(id=gid, labels=labs, inst=inst))
b64 = {}
for i in sorted(used):
    im = Image.open(IMG / f"{i}.jpg").convert("RGB")
    im.thumbnail((1000, 1400))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=70, optimize=True)
    b64[i] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
tpl = open(Path(sys.argv[4]), encoding="utf-8").read()
html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__IMGS__", json.dumps(b64)).replace("__IMGNAME__", json.dumps(imgname, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print(len(html), [ (d["id"], len(d["inst"])) for d in data])

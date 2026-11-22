"""「黄道ラベルの照合」のページを作る: python3 voynich/build_zodiac_page.py <画像の場所> voynich/notes/html/黄道ラベルの照合.html voynich/notes/html/zodiac_template.html
画像は https://collections.library.yale.edu/iiif/2/<id>/full/<幅>,/0/default.jpg（1006203 は 3200、1006204 は 2400、他は 1600）。"""
import base64, io, json, re, sys
from collections import defaultdict
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus, ivtff  # noqa: E402
IMG, OUT, TPL = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HERE = Path(__file__).resolve().parent
# 頁 → (画像, 切り分け [左, 右] の割合, 説明)。分析補助の見立て（未確認）
PANEL = {"f70v2": ("1006200", (0, 1), "70v（一部）: 中心に 2 匹の魚 → 魚座"),
         "f70v1": ("1006201", (0, 1), "70v（一部）: 中心に山羊・羊 → 牡羊座（暗）"),
         "f71r": ("1006202", (0, 1), "71r"),
         "f71v": ("1006203", (0.00, 0.28), "71v と 72r の 1 面目（左端）"),
         "f72r1": ("1006203", (0.25, 0.50), "71v と 72r の 2 面目（赤い牛）"),
         "f72r2": ("1006203", (0.47, 0.70), "71v と 72r の 3 面目（中心に人物）"),
         "f72r3": ("1006203", (0.66, 1.00), "71v と 72r の 4 面目（右端, 赤い小さな生き物）"),
         "f72v3": ("1006204", (0.18, 0.61), "72v（一部）の左の面"),
         "f72v2": ("1006204", (0.57, 1.00), "72v（一部）の右の面（中心に青い衣の人物）"),
         "f72v1": ("1006205", (0, 1), "72v（一部）: 中心に天秤 → 天秤座"),
         "f73r": ("1006206", (0, 1), "73r"), "f73v": ("1006207", (0, 1), "73v")}
def name_of(pg):
    return PANEL[pg][2]


RING = {0: "最初の円形の文章より前（中心寄り）", 1: "外側の人物の輪", 2: "内側の人物の輪", 3: "3 つ目の円形の文章より後"}
WANT = ["oky", "otaly", "otal", "okeey", "okal", "okeody"]
a = corpus.make_parser("").parse_args([]); opts = corpus.word_options(a)
cur, zod, grp, inst = None, False, defaultdict(int), defaultdict(list)
for line in open(HERE / "data" / "ZL3b-n.txt", encoding="utf-8", errors="replace"):
    m = re.match(r"<(f\d+[rv]\d*)>\s+<!(.*)>", line)
    if m:
        cur, zod = m.group(1), "$I=Z" in m.group(2); continue
    m = re.match(r"<(f\d+[rv]\d*)\.(\d+),(.)(\w\w)>\s+(?:<!([0-9:]+)>)?(.*)", line)
    if not m or not cur or not zod:
        continue
    pg, n, _, typ, clk, txt = m.groups()
    if typ[0] in "CR":
        grp[pg] += 1
    if typ == "Lz":
        ws = ivtff.words(txt, opts)
        for w in ws:
            if w in WANT:
                inst[w].append(dict(page=pg, label=" ".join(ws), ring=grp[pg], clock=clk, imgs=[]))
# 円の中心（面の幅・高さに対する割合）と人物の輪の半径（面の幅に対する割合）。縮小画像に目盛りを入れて見積もった（推定）
GEOM = {"f70v2": (0.505, 0.47, {1: 0.29, 2: 0.19}), "f70v1": (0.545, 0.475, {1: 0.33, 2: 0.20}),
        "f71v": (0.53, 0.48, {1: 0.32, 2: 0.20}), "f72r1": (0.45, 0.475, {1: 0.35, 2: 0.20}),
        "f72r2": (0.46, 0.475, {0: 0.52, 1: 0.33, 2: 0.20}), "f72v3": (0.49, 0.465, {1: 0.42, 2: 0.26}),
        "f72v2": (0.47, 0.48, {1: 0.37, 2: 0.23}), "f72v1": (0.56, 0.46, {1: 0.31, 2: 0.18}),
        "f73r": (0.44, 0.46, {0: 0.45, 1: 0.315, 2: 0.18}), "f73v": (0.555, 0.46, {0: 0.44, 1: 0.31, 2: 0.17})}
import math
from PIL import ImageDraw


def enc(im):
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=66, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


panels = {}
for pg, (iid, (l, r), name) in PANEL.items():
    im = Image.open(IMG / f"{iid}.jpg").convert("RGB")
    W, H = im.size
    panels[pg] = im.crop((int(W * l), 0, int(W * r), H))
imgs, names = {}, {}
RED = (196, 30, 30)
for w_, lst in inst.items():
    for n_, x in enumerate(lst, 1):
        pg = x["page"]
        cx, cy, radii = GEOM[pg]
        im = panels[pg]
        W, H = im.size
        ring = x["ring"]
        rad = radii.get(ring, radii[1]) * W
        h, mm = map(int, x["clock"].split(":")) if x["clock"] else (0, 0)
        th = math.radians(((h % 12) + mm / 60) * 30)
        X0, Y0 = cx * W, cy * H
        X, Y = X0 + rad * math.sin(th), Y0 - rad * math.cos(th)
        ov = im.copy()
        d = ImageDraw.Draw(ov)
        lw = max(3, W // 250)
        Xe, Ye = X0 + (rad + 0.12 * W) * math.sin(th), Y0 - (rad + 0.12 * W) * math.cos(th)
        d.line([(X0, Y0), (Xe, Ye)], fill=RED, width=lw)
        R = 0.045 * W
        d.ellipse([X - R, Y - R, X + R, Y + R], outline=RED, width=lw * 2)
        ov.thumbnail((800, 1000))
        k1 = f"{w_}-{n_}-ov"
        imgs[k1] = enc(ov)
        names[k1] = f"全体図（{name_of(pg)}）。赤い線は円の中心からの向き、赤い丸が対象の人物のあたり（推定）"
        S = max(0.20 * W, 0.60 * rad)
        zm = im.crop((int(X - S / 2), int(Y - S / 2), int(X + S / 2), int(Y + S / 2)))
        zs = zm.size[0]
        zm = zm.resize((600, int(600 * zm.size[1] / max(1, zm.size[0]))))
        d = ImageDraw.Draw(zm)
        rr = 600 * 0.20
        d.ellipse([300 - rr, zm.size[1] / 2 - rr, 300 + rr, zm.size[1] / 2 + rr], outline=RED, width=4)
        k2 = f"{w_}-{n_}-zm"
        imgs[k2] = enc(zm)
        names[k2] = "拡大図。赤い丸の中の人物と、その横に書かれた語が対象（丸は推定の位置なので、少しずれることがある）"
        x["imgs"] = [k2, k1]
        x["loc"] = f"{n_} か所目: {pg}（{name_of(pg)}）・{RING.get(ring, '—')}・{x['clock'] or '—'} の向き"
data = [dict(id=w, labels=[w], inst=inst[w]) for w in WANT]
html = TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__IMGS__", json.dumps(imgs)).replace("__IMGNAME__", json.dumps(names, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print(len(html), [(d["id"], len(d["inst"])) for d in data])

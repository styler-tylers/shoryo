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
                inst[w].append(dict(page=pg, label=" ".join(ws), loc=f"{pg}・{RING.get(grp[pg], '—')}・時計の位置 {clk or '—'}（ZL の {pg}.{n}）", imgs=[pg]))
imgs = {}
for pg, (iid, (l, r), name) in PANEL.items():
    if not any(pg == x["page"] for v in inst.values() for x in v):
        continue
    im = Image.open(IMG / f"{iid}.jpg").convert("RGB")
    W, H = im.size
    im = im.crop((int(W * l), 0, int(W * r), H))
    im.thumbnail((1100, 1400))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=68, optimize=True)
    imgs[pg] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
names = {pg: v[2] for pg, v in PANEL.items()}
data = [dict(id=w, labels=[w], inst=inst[w]) for w in WANT]
html = TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__IMGS__", json.dumps(imgs)).replace("__IMGNAME__", json.dumps(names, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print(len(html), [(d["id"], len(d["inst"])) for d in data])

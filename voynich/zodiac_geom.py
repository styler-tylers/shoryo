"""黄道の頁の人物の位置（ZL の輪・時計の位置）と、頁の写真の切り分け・円の見積もり（推定）。
build_zodiac_page.py・build_blind_page.py が使う。"""
import base64, io, math, re
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageDraw
import corpus, ivtff

HERE = Path(__file__).resolve().parent
PANEL = {"f70v2": ("1006200", (0, 1), "70v（一部）: 魚座"), "f70v1": ("1006201", (0, 1), "70v（一部）: 牡羊座（暗）"),
         "f71r": ("1006202", (0, 1), "71r"), "f71v": ("1006203", (0.00, 0.28), "71v と 72r の 1 面目"),
         "f72r1": ("1006203", (0.25, 0.50), "71v と 72r の 2 面目"), "f72r2": ("1006203", (0.47, 0.70), "71v と 72r の 3 面目"),
         "f72r3": ("1006203", (0.66, 1.00), "71v と 72r の 4 面目"), "f72v3": ("1006204", (0.18, 0.61), "72v（一部）の左の面"),
         "f72v2": ("1006204", (0.57, 1.00), "72v（一部）の右の面"), "f72v1": ("1006205", (0, 1), "72v（一部）: 天秤座"),
         "f73r": ("1006206", (0, 1), "73r"), "f73v": ("1006207", (0, 1), "73v")}
GEOM = {"f70v2": (0.505, 0.47, {1: 0.29, 2: 0.19}), "f70v1": (0.545, 0.475, {1: 0.33, 2: 0.20}),
        "f71v": (0.53, 0.48, {1: 0.32, 2: 0.20}), "f72r1": (0.45, 0.475, {1: 0.35, 2: 0.20}),
        "f72r2": (0.46, 0.475, {0: 0.52, 1: 0.33, 2: 0.20}), "f72v3": (0.49, 0.465, {1: 0.42, 2: 0.26}),
        "f72v2": (0.47, 0.48, {1: 0.37, 2: 0.23}), "f72v1": (0.56, 0.46, {1: 0.31, 2: 0.18}),
        "f73r": (0.44, 0.46, {0: 0.45, 1: 0.315, 2: 0.18}), "f73v": (0.555, 0.46, {0: 0.44, 1: 0.31, 2: 0.17})}
RED = (196, 30, 30)


def figures():
    """[{page, num, ring, clock, words, hand}]（Lz のラベル）"""
    a = corpus.make_parser("").parse_args([])
    opts = corpus.word_options(a)
    cur, zod, hand = None, False, None
    grp = defaultdict(int)
    out = []
    for line in open(HERE / "data" / "ZL3b-n.txt", encoding="utf-8", errors="replace"):
        m = re.match(r"<(f\d+[rv]\d*)>\s+<!(.*)>", line)
        if m:
            cur, zod = m.group(1), "$I=Z" in m.group(2)
            hm = re.search(r"\$H=(\S+)", m.group(2))
            hand = hm.group(1) if hm else None
            continue
        m = re.match(r"<(f\d+[rv]\d*)\.(\d+),(.)(\w\w)>\s+(?:<!([0-9:]+)>)?(.*)", line)
        if not m or not cur or not zod:
            continue
        pg, n, _, typ, clk, txt = m.groups()
        if typ[0] in "CR":
            grp[pg] += 1
        if typ == "Lz":
            out.append(dict(page=pg, num=int(n), ring=grp[pg], clock=clk, words=ivtff.words(txt, opts), hand=hand))
    return out


def enc(im, q=66):
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


class Panels:
    def __init__(self, imgdir):
        self.d, self.cache = Path(imgdir), {}

    def get(self, pg):
        if pg not in self.cache:
            iid, (l, r), _ = PANEL[pg]
            im = Image.open(self.d / f"{iid}.jpg").convert("RGB")
            W, H = im.size
            self.cache[pg] = im.crop((int(W * l), 0, int(W * r), H))
        return self.cache[pg]

    def point(self, f):
        im = self.get(f["page"])
        W, H = im.size
        cx, cy, radii = GEOM[f["page"]]
        rad = radii.get(f["ring"], radii[1]) * W
        h, mm = map(int, f["clock"].split(":"))
        th = math.radians(((h % 12) + mm / 60) * 30)
        return im, W, H, cx * W, cy * H, rad, th

    def zoom(self, f, size=520):
        im, W, H, X0, Y0, rad, th = self.point(f)
        X, Y = X0 + rad * math.sin(th), Y0 - rad * math.cos(th)
        S = max(0.20 * W, 0.60 * rad)
        zm = im.crop((int(X - S / 2), int(Y - S / 2), int(X + S / 2), int(Y + S / 2))).resize((size, size))
        d = ImageDraw.Draw(zm)
        rr = size * 0.20
        d.ellipse([size / 2 - rr, size / 2 - rr, size / 2 + rr, size / 2 + rr], outline=RED, width=4)
        return enc(zm)

    def overview(self, f, maxw=700):
        im, W, H, X0, Y0, rad, th = self.point(f)
        X, Y = X0 + rad * math.sin(th), Y0 - rad * math.cos(th)
        ov = im.copy()
        d = ImageDraw.Draw(ov)
        lw = max(3, W // 250)
        d.line([(X0, Y0), (X0 + (rad + 0.12 * W) * math.sin(th), Y0 - (rad + 0.12 * W) * math.cos(th))], fill=RED, width=lw)
        R = 0.045 * W
        d.ellipse([X - R, Y - R, X + R, Y + R], outline=RED, width=lw * 2)
        ov.thumbnail((maxw, maxw * 1.3))
        return enc(ov, 60)

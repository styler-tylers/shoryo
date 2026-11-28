"""N252（第 287・289 節）: 升ごとのインクの濃さの余りを測り、なぞり直しの候補の升とふつうの升を選んで、目隠しの判定のページを作る。

    python3 voynich/build_retrace_page.py <IIIF の画像の場所（list.json と <id>.jpg）> voynich/notes/html/retrace_template.html <出力 html> <答えの表 json> <升の表 json>
"""
import base64, colorsys, io, json, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402

IMG, TPL, OUT, KEY, TILES = map(Path, sys.argv[1:6])


def text_pages():
    args = corpus.make_parser("").parse_args([]); args.locus = "P"
    _, lines = corpus.load_lines(args)
    c = Counter(ln.page.name for ln in lines)
    return {p for p, n in c.items() if n >= 10}


def tiles_of(path):
    im = Image.open(path).convert("RGB"); W, H = im.size
    a = np.asarray(im, float) / 255
    L = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    mx, mn = a.max(2), a.min(2); sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    parch = np.percentile(L, 80)
    ink = L < 0.75 * parch
    T = int(0.04 * W); out = []
    for y in range(0, H - T, T):
        for x in range(0, W - T, T):
            l = L[y:y + T, x:x + T]; k = ink[y:y + T, x:x + T]; f = k.mean()
            if f < 0.03 or f > 0.40 or np.percentile(l, 80) < 0.6 * parch:
                continue
            if (sat[y:y + T, x:x + T][k] > 0.4).mean() >= 0.30:
                continue
            v = np.sort(l[k]); dark = (parch - v[: max(1, len(v) // 10)].mean()) / parch
            out.append((x, y, T, float(dark)))
    return out, (W, H)


def main():
    lst = json.load(open(IMG / "list.json"))
    tp = text_pages()
    rows, sizes = [], {}
    for iid, lab in lst:
        if not re.fullmatch(r"\d+[rv]", lab):
            continue
        pg = "f" + lab
        if pg not in tp or not (IMG / f"{iid}.jpg").exists():
            continue
        ts, sizes[iid] = tiles_of(IMG / f"{iid}.jpg")
        if len(ts) < 20:
            continue
        med = float(np.median([t[3] for t in ts]))
        rows += [dict(page=pg, img=iid, x=x, y=y, T=T, dark=d, excess=d - med) for x, y, T, d in ts]
    TILES.write_text(json.dumps(rows), encoding="utf-8")
    ex = np.array([r["excess"] for r in rows]); thr = np.percentile(ex, 99)
    print(f"頁 {len({r['page'] for r in rows})}・升 {len(rows)}・上位 1% のしきい {thr:.3f}", flush=True)
    rng = random.Random(2042)
    def pick(pool, n):
        rng.shuffle(pool); per = defaultdict(int); out = []
        for r in pool:
            if per[r["page"]] < 2:
                out.append(r); per[r["page"]] += 1
            if len(out) == n:
                break
        return out
    cand = pick([r for r in rows if r["excess"] >= thr], 20)
    typ = pick([r for r in rows if abs(r["excess"]) <= 0.02], 20)
    items = [("cand", r) for r in cand] + [("typ", r) for r in typ]
    rng.shuffle(items)
    pub, key = [], []
    for n, (k, r) in enumerate(items, 1):
        im = Image.open(IMG / f"{r['img']}.jpg").convert("RGB"); T = r["T"]
        x0, y0 = r["x"] - T, r["y"] - T
        z = im.crop((x0, y0, x0 + 3 * T, y0 + 3 * T)).resize((540, 540), Image.LANCZOS)
        d = ImageDraw.Draw(z); d.rectangle([180, 180, 360, 360], outline=(31, 95, 168), width=3)
        buf = io.BytesIO(); z.save(buf, "JPEG", quality=82)
        tid = f"t{n:02d}"
        pub.append(dict(id=tid, img="data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()))
        key.append(dict(id=tid, kind=k, page=r["page"], img=r["img"], x=r["x"], y=r["y"], T=T, dark=round(r["dark"], 4), excess=round(r["excess"], 4)))
    KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text(TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(pub)), encoding="utf-8")
    print(len(pub), "升", OUT.stat().st_size)


if __name__ == "__main__":
    main()

"""「黄道の人物の目隠し判定」のページを作る（第 238 節の事前の登録どおりに組を選ぶ, 種 2026）。
    python3 voynich/build_blind_page.py <黄道の画像の場所> <出力 html> <template> <答えの表 json>"""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zodiac_geom import PANEL, Panels, figures  # noqa: E402

IMG, OUT, TPL, KEY = map(Path, sys.argv[1:5])
WORDS = ["oky", "otaly", "otal", "okeey", "okal", "okeody"]
SKIP = {"f72v3", "f72v2"}
rng = random.Random(2026)
F = [f for f in figures() if f["clock"] and f["page"] not in SKIP and f["page"] in PANEL]
pairs = []
for w in WORDS:
    inst = [f for f in F if w in f["words"]]
    cand = [(a, b) for i, a in enumerate(inst) for b in inst[i + 1:] if a["page"] != b["page"]]
    for a, b in rng.sample(cand, min(2, len(cand))):
        pairs.append(("same", w, a, b))
        pool_a = [f for f in F if f["page"] == a["page"] and w not in f["words"] and f["ring"] in (1, 2)]
        pool_b = [f for f in F if f["page"] == b["page"] and w not in f["words"] and f["ring"] in (1, 2)]
        x = rng.choice(pool_a)
        y = rng.choice([f for f in pool_b if not set(f["words"]) & set(x["words"])])
        pairs.append(("diff", w, x, y))
rng.shuffle(pairs)
P = Panels(IMG)
data, key, imgs = [], [], {}
for i, (kind, w, a, b) in enumerate(pairs, 1):
    if rng.random() < 0.5:
        a, b = b, a
    pid = f"p{i:02d}"
    figs = []
    for side, f in (("L", a), ("R", b)):
        k = f"{pid}{side}"
        imgs[k + "z"] = P.zoom(f)
        imgs[k + "o"] = P.overview(f)
        figs.append(dict(key=k, page=f["page"]))
    data.append(dict(id=pid, figs=figs))
    key.append(dict(id=pid, kind=kind, word=w, left=dict(page=a["page"], num=a["num"], ring=a["ring"], clock=a["clock"], words=a["words"], hand=a["hand"]),
                    right=dict(page=b["page"], num=b["num"], ring=b["ring"], clock=b["clock"], words=b["words"], hand=b["hand"])))
KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
html = TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data)).replace("__IMGS__", json.dumps(imgs))
OUT.write_text(html, encoding="utf-8")
print(len(html), len(data), sum(k["kind"] == "same" for k in key))

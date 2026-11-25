"""「黄道人物の目隠し判定 3（顔と髪型）」のページを作る（第 246 節の事前の登録どおり, 種 2028）。
    python3 voynich/build_face_page.py <画像の場所> <出力 html> <template> <答えの表 json> <前回の答えの表 json> ...
"""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zodiac_geom import PANEL, Panels, figures  # noqa: E402

IMG, OUT, TPL, KEY = map(Path, sys.argv[1:5])
PREVF = sys.argv[5:]
WORDS = ["oky", "otaly", "otal", "okeey", "okal", "okeody"]
SKIP = {"f72v3", "f72v2"}
FOCUS = {"f70v1", "f70v2"}
rng = random.Random(2028)
fz = lambda a, b: frozenset([(a["page"], a["num"]), (b["page"], b["num"])])  # noqa: E731
PREV = set()
for p in PREVF:
    for k in json.load(open(p)):
        PREV.add(frozenset([(k["left"]["page"], k["left"]["num"]), (k["right"]["page"], k["right"]["num"])]))
F = [f for f in figures() if f["clock"] and f["page"] not in SKIP and f["page"] in PANEL]
same = []
for w in WORDS:
    inst = [f for f in F if w in f["words"]]
    same += [(w, a, b) for i, a in enumerate(inst) for b in inst[i + 1:] if a["page"] != b["page"] and fz(a, b) not in PREV]
rng.shuffle(same)
same.sort(key=lambda x: not ({x[1]["page"], x[2]["page"]} <= FOCUS))  # f70v2・f70v1 の組を先に
same = same[:15]
used = set(PREV)
pairs = []
for w, a, b in same:
    used.add(fz(a, b))
    pairs.append(("same", w, a, b))
    pa = [f for f in F if f["page"] == a["page"] and w not in f["words"] and f["ring"] in (1, 2)]
    pb = [f for f in F if f["page"] == b["page"] and w not in f["words"] and f["ring"] in (1, 2)]
    for _ in range(500):
        x, y = rng.choice(pa), rng.choice(pb)
        if not set(x["words"]) & set(y["words"]) and fz(x, y) not in used:
            used.add(fz(x, y))
            pairs.append(("diff", w, x, y))
            break
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
    key.append(dict(id=pid, kind=kind, word=w, left=dict(page=a["page"], num=a["num"], ring=a["ring"], clock=a["clock"], words=a["words"]),
                    right=dict(page=b["page"], num=b["num"], ring=b["ring"], clock=b["clock"], words=b["words"])))
KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
OUT.write_text(TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data)).replace("__IMGS__", json.dumps(imgs)), encoding="utf-8")
print(len(pairs), sum(k["kind"] == "same" for k in key), sum({k["left"]["page"], k["right"]["page"]} <= FOCUS for k in key if k["kind"] == "same"))

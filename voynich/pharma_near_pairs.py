"""第 81 巡 N238 の組を選ぶ（第 259 節の事前の登録どおり, 種 2030）。答えの表は判定が済むまで出さない。

    python3 voynich/pharma_near_pairs.py <答えの表 json の出力先>
"""
import json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
U16 = {("f88r", "5"), ("f88r", "6"), ("f88r", "12"), ("f88r", "15"), ("f88v", "14"), ("f89r1", "4"), ("f89r1", "14"), ("f89v2", "11"),
       ("f99r", "14"), ("f99v", "2"), ("f99v", "6"), ("f99v", "9"), ("f101v", "2"), ("f101v", "10"), ("f102v2", "7"), ("f102v2", "8")}


def labels():
    L = []
    for line in open(HERE / "data" / "ZL3b-n.txt", encoding="utf-8", errors="ignore"):
        m = re.match(r"<(f(\d+)[rv]\d*)\.(\d+),[@+=]L(\w)>\s*(.*)", line)
        if not m:
            continue
        pg, num, loc, typ, txt = m.group(1), int(m.group(2)), m.group(3), m.group(4), m.group(5)
        txt = re.sub(r"<[^>]*>", "", txt); txt = re.sub(r"\{[^}]*\}", "", txt); txt = re.sub(r"\[([^:\]]*):[^\]]*\]", r"\1", txt)
        w = " ".join(txt.replace(",", " ").replace(".", " ").split())
        if 87 <= num <= 102 and " " not in w and "?" not in w:
            L.append((pg, loc, typ, w))
    return L


def ed(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p = d[:]; d[0] = i
        for j, cb in enumerate(b, 1):
            d[j] = min(p[j] + 1, d[j - 1] + 1, p[j - 1] + (ca != cb))
    return d[-1]


def main(keyout):
    L = labels()
    ok = lambda x: x[2] == "f" and len(x[3]) >= 4 and (x[0], x[1]) not in U16  # noqa: E731
    near = [(a, b) for i, a in enumerate(L) for b in L[i + 1:] if a[0] != b[0] and ok(a) and ok(b) and ed(a[3], b[3]) == 1]
    print("1 字違いの組", len(near))
    rng = random.Random(2030)
    rng.shuffle(near)
    used, sel = set(), []
    for a, b in near:
        if a[:2] in used or b[:2] in used:
            continue
        sel.append(("near", a, b)); used |= {a[:2], b[:2]}
        if len(sel) == 12:
            break
    pool = sorted({x for _, a, b in sel for x in (a, b)})
    far = [(a, b) for i, a in enumerate(pool) for b in pool[i + 1:] if a[0] != b[0] and ed(a[3], b[3]) >= 3]
    rng.shuffle(far)
    cnt, fsel = {}, []
    for a, b in far:
        if cnt.get(a[:2], 0) < 2 and cnt.get(b[:2], 0) < 2:
            fsel.append(("far", a, b)); cnt[a[:2]] = cnt.get(a[:2], 0) + 1; cnt[b[:2]] = cnt.get(b[:2], 0) + 1
        if len(fsel) == 12:
            break
    pairs = sel + fsel
    rng.shuffle(pairs)
    pairs = [(k, *((a, b) if rng.random() < 0.5 else (b, a))) for k, a, b in pairs]
    key = [dict(id=f"r{n:02d}", kind=k, a=f"{a[0]}.{a[1]}", a_word=a[3], b=f"{b[0]}.{b[1]}", b_word=b[3]) for n, (k, a, b) in enumerate(pairs, 1)]
    json.dump(key, open(keyout, "w"), ensure_ascii=False, indent=1)
    locs = sorted({x for p in key for x in (p["a"], p["b"])}, key=lambda s: (s.split(".")[0], int(s.split(".")[1])))
    words = {f"{x[0]}.{x[1]}": x[3] for x in L}
    print(len(pairs), "組", len(locs), "か所")
    for l in locs:
        print(" ", l, words[l])


if __name__ == "__main__":
    main(sys.argv[1])

"""「写本は医学・薬学の書物である」という見方から出てくる 3 つの予測を、転写データで確かめる。

  1. recipes  : レシピの部（星の段落, クワイア T）は処方集の形をしているか
                （段落の長さが短くそろっているか、段落頭に決まった語があるか）
  2. pharma   : 薬学の部のラベル（容器や植物片の名前）は、植物の部の本文に出てくるか
                （偶然より多く出てくるか、特定の頁に集中するか）
  3. zodiac   : 黄道の部の各宮の人物ラベルの数は 30（1 宮 = 30 度 / 30 日）か

使い方:
  python3 voynich/medical_tests.py            # 3 つすべて
  python3 voynich/medical_tests.py zodiac     # 1 つだけ
  python3 voynich/medical_tests.py --file IT2a-n.txt pharma
"""

from __future__ import annotations

import argparse
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

import corpus
import ivtff

# 黄道の部の頁と、そこに描かれた宮（ZL の頁の並び順）
ZODIAC_PAGES = [
    ("f70v2", "双魚宮"), ("f70v1", "白羊宮（暗）"), ("f71r", "白羊宮（明）"),
    ("f71v", "金牛宮（暗）"), ("f72r1", "金牛宮（明）"), ("f72r2", "双子宮"),
    ("f72r3", "巨蟹宮"), ("f72v3", "獅子宮"), ("f72v2", "処女宮"),
    ("f72v1", "天秤宮"), ("f73r", "天蠍宮"), ("f73v", "人馬宮"),
]
# 1 つの宮が 2 頁に分かれているもの
SPLIT_SIGNS = {"白羊宮": ("f70v1", "f71r"), "金牛宮": ("f71v", "f72r1")}


def single_word_labels(lines, pred, opts):
    """条件に合うラベル行のうち、1 語だけのラベルを集める。"""
    out = []
    for ln in lines:
        if pred(ln):
            ws = ivtff.words(ln.raw, opts)
            if len(ws) == 1:
                out.append(ws[0])
    return out


def paragraphs(lines, pred, opts):
    """段落記号 <%> <$> で段落に分け、語と行数を返す。"""
    paras, cur = [], None
    for ln in lines:
        if not (pred(ln) and ln.locus_class == "P"):
            continue
        if "<%>" in ln.raw or cur is None:
            if cur:
                paras.append(cur)
            cur = {"page": ln.page.name, "words": [], "lines": 0}
        cur["words"] += ivtff.words(ln.raw, opts)
        cur["lines"] += 1
        if "<$>" in ln.raw:
            paras.append(cur)
            cur = None
    if cur:
        paras.append(cur)
    return [p for p in paras if p["words"]]


# ---------------------------------------------------------------------------
# 1. レシピの部
# ---------------------------------------------------------------------------


def test_recipes(lines, opts):
    print("=" * 70)
    print("検証 1: レシピの部は処方集の形をしているか")
    print("=" * 70)
    groups = {
        "レシピ（星, Q=T）": lambda l: l.page.get("I") == "S" and l.page.get("Q") == "T",
        "植物（H）": lambda l: l.page.get("I") == "H",
        "浴場（B）": lambda l: l.page.get("I") == "B",
    }
    print(f"{'部':<14}{'段落':>5}{'語数中央値':>9}{'四分位':>10}{'ばらつき*':>9}{'行数中央値':>9}")
    result = {}
    for name, pred in groups.items():
        ps = paragraphs(lines, pred, opts)
        n = sorted(len(p["words"]) for p in ps)
        q1, med, q3 = n[len(n) // 4], st.median(n), n[3 * len(n) // 4]
        spread = (q3 - q1) / med
        print(f"{name:<14}{len(n):>5}{med:>9}{f'{q1}-{q3}':>10}{spread:>9.2f}"
              f"{st.median(p['lines'] for p in ps):>9}")
        result[name] = ps
    print("  * ばらつき = 四分位範囲 ÷ 中央値（小さいほど長さがそろっている）")

    print()
    for name, ps in result.items():
        first = Counter(p["words"][0] for p in ps)
        once = sum(1 for c in first.values() if c == 1) / len(ps)
        heads = Counter(ivtff.glyphs(p["words"][0])[0] for p in ps)
        print(f"{name} 段落頭の語: 一度しか出ない語の割合 {once:.0%}、"
              f"多い語 {first.most_common(4)}")
        print(f"    段落頭の語の最初の字形: {heads.most_common(5)}")
    recipes = result["レシピ（星, Q=T）"]
    print()
    print("レシピの部: 段落の行数の分布", sorted(Counter(p["lines"] for p in recipes).items()))
    print("レシピの部: 頁ごとの段落数", dict(Counter(p["page"] for p in recipes)))


# ---------------------------------------------------------------------------
# 2. 薬学の部のラベル
# ---------------------------------------------------------------------------


def test_pharma(lines, opts, trials=200, seed=1):
    print("=" * 70)
    print("検証 2: 薬学の部のラベルは植物の部の本文に出てくるか")
    print("=" * 70)
    labels = single_word_labels(
        lines, lambda l: l.page.get("I") == "P" and l.locus_class == "L", opts)
    types = sorted(set(labels))

    herb_pages = defaultdict(Counter)
    for ln in lines:
        if ln.page.get("I") == "H" and ln.locus_class == "P":
            herb_pages[ln.page.name].update(ivtff.words(ln.raw, opts))
    herb = Counter()
    for c in herb_pages.values():
        herb.update(c)

    found = [w for w in types if herb[w] > 0]
    rate = len(found) / len(types)

    # 対照: 浴場・星の部の本文の語から、同じ長さの語を無作為に選んだ場合
    pool = Counter()
    for ln in lines:
        if ln.page.get("I") in ("B", "S") and ln.locus_class == "P":
            pool.update(ivtff.words(ln.raw, opts))
    by_len = defaultdict(list)
    for w in pool:
        by_len[len(w)].append(w)
    rng = random.Random(seed)
    rates = []
    for _ in range(trials):
        sample = [rng.choice(by_len[len(w)]) for w in types if by_len[len(w)]]
        rates.append(sum(1 for w in sample if herb[w] > 0) / len(sample))
    rates.sort()
    lo, hi = rates[int(trials * 0.05)], rates[int(trials * 0.95)]

    zodiac = sorted(set(single_word_labels(
        lines, lambda l: l.page.get("I") == "Z" and l.locus_type == "Lz", opts)))
    zrate = sum(1 for w in zodiac if herb[w] > 0) / len(zodiac)

    print(f"薬学の部の 1 語ラベル: {len(labels)} 個（異なり {len(types)}）")
    print(f"植物の部の本文に出てくるラベル: {len(found)} / {len(types)} = {rate:.1%}")
    print(f"  対照 1（浴場・星の本文の語、長さをそろえて無作為に {trials} 回）: "
          f"平均 {st.mean(rates):.1%}（90% の範囲 {lo:.1%}〜{hi:.1%}）")
    print(f"  対照 2（黄道の部のラベル {len(zodiac)} 語）: {zrate:.1%}")

    # 集中度: 植物名なら、その植物の頁に集中して出るはず
    total = sum(herb.values())
    sizes = [sum(c.values()) for c in herb_pages.values()]

    def concentration(w):
        f = herb[w]
        observed = sum(1 for c in herb_pages.values() if c[w] > 0)
        expected = sum(1 - (1 - s / total) ** f for s in sizes)
        return observed / expected

    lab = [concentration(w) for w in found if herb[w] >= 3]
    allw = [concentration(w) for w, f in herb.items() if f >= 3]
    print("頁への集中度（出てくる頁の数 ÷ 無作為に散らばった場合の頁の数。1 より小さいほど集中）:")
    print(f"  植物の部に 3 回以上出るラベル（{len(lab)} 語）: 中央値 {st.median(lab):.2f}")
    print(f"  植物の部に 3 回以上出る語すべて（{len(allw)} 語）: 中央値 {st.median(allw):.2f}")


# ---------------------------------------------------------------------------
# 3. 黄道の部
# ---------------------------------------------------------------------------


def test_zodiac(lines, opts):
    print("=" * 70)
    print("検証 3: 黄道の各宮のラベルの数は 30 か")
    print("=" * 70)
    counts = {}
    for page, sign in ZODIAC_PAGES:
        page_lines = [l for l in lines if l.page.name == page]
        n = sum(1 for l in page_lines if l.locus_type == "Lz")
        rings = []
        for l in page_lines:
            if l.locus_class == "C":
                rings.append(0)
            elif l.locus_type == "Lz" and rings:
                rings[-1] += 1
        counts[page] = n
        print(f"{page:<6} {sign:<8} ラベル {n:>3}   円環ごと（外から） {[r for r in rings if r]}")
    print()
    print("1 つの宮が 2 頁に分かれているもの:")
    for sign, (a, b) in SPLIT_SIGNS.items():
        print(f"  {sign}: {counts[a]} + {counts[b]} = {counts[a] + counts[b]}")
    per_sign = [counts[p] for p, s in ZODIAC_PAGES if "（" not in s]
    per_sign += [counts[a] + counts[b] for a, b in SPLIT_SIGNS.values()]
    print(f"10 宮のラベル数: {sorted(per_sign)}（30 の宮: {sum(1 for n in per_sign if n == 30)} / 10）")

    labels = single_word_labels(
        lines, lambda l: l.page.get("I") == "Z" and l.locus_type == "Lz", opts)
    starts = Counter("".join(ivtff.glyphs(w)[:2]) for w in labels)
    print(f"ラベルの最初の 2 字形（{len(labels)} 語）: {starts.most_common(6)}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("test", nargs="*", choices=["recipes", "pharma", "zodiac"],
                   help="実行する検証（省略時はすべて）")
    p.add_argument("--file", type=Path, default=corpus.DEFAULT_FILE,
                   help="IVTFF 転写ファイル（省略時は ZL3b-n.txt）")
    args = p.parse_args()
    lines = ivtff.parse_file(corpus.ensure_data(args.file))
    opts = ivtff.Options()
    tests = args.test or ["recipes", "pharma", "zodiac"]
    for name in tests:
        {"recipes": test_recipes, "pharma": test_pharma, "zodiac": test_zodiac}[name](lines, opts)
        print()


if __name__ == "__main__":
    main()

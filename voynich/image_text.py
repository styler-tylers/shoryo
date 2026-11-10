#!/usr/bin/env python3
"""ヴォイニッチ手稿 絵と文章の対応を調べるスクリプト（色の特徴による予備実験）。

仮説: 文章が同じ頁の絵を説明しているなら、絵の特徴が似た頁どうしは、文章の語彙も似ているはず。
（例: 青い花の植物の頁には「青」にあたる語が多い）

各頁の画像から、色の特徴（緑・青・赤・黄の顔料が頁に占める割合）を自動で測り、
  1. マンテル検定: 「色の似かた」と「語彙の似かた」の相関を、頁の組み合わせ全体で計算し、
     頁のラベルをランダムに入れ替えた場合と比べる。
     同じ二つ折り・同じクワイアの組（紙や顔料の束が同じで、文章も似やすい）を除いた場合も出す。
  2. 色と結びつく語: 色の多い頁と少ない頁で出方が違う語を G² で探し、
     頁のラベルを入れ替えたときの最大の G² と比べて、偶然でも出る程度かを判定する。

既定の対象は植物セクション（挿絵 H）の言語 A の頁。言語・セクションの違いは語彙を大きく変えるので、
同じグループの中で比べる（--language, --illustration で変更可）。

    python3 voynich/page_images.py                  # 先に全頁の画像を取得しておく
    python3 voynich/image_text.py
    python3 voynich/image_text.py --language B
    python3 voynich/image_text.py --features        # 頁ごとの色の特徴を表示

Pillow と numpy が必要。
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import page_images  # noqa: E402
import spread  # noqa: E402
import vocab_shift  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

COLORS = ["green", "blue", "red", "yellow"]
COLOR_JA = {"green": "緑", "blue": "青", "red": "赤", "yellow": "黄"}


# ---------------------------------------------------------------------------
# 色の特徴
# ---------------------------------------------------------------------------


def color_features(path: Path) -> dict[str, float]:
    """頁の画像で、各色の顔料が占める割合（背景の黒を除いた面積に対する割合）。

    HSV（Pillow の H は 0〜255）で判定する。羊皮紙は彩度が低く、インクの文字は細いので、
    彩度と明度の高い画素だけを顔料とみなす。境目は経験的に決めたもので、厳密な色分類ではない。
    """
    hsv = np.asarray(Image.open(path).convert("HSV"), dtype=np.int16)
    # 頁の縁（汚れ・黄ばみ・隣の頁の写り込み）を除くため、上下左右の 7% を切り落とす
    hh, ww = hsv.shape[:2]
    my, mx = int(hh * 0.07), int(ww * 0.07)
    hsv = hsv[my:hh - my, mx:ww - mx]
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    page = v >= 60  # 撮影の黒い背景を除く
    area = max(int(page.sum()), 1)
    cool = page & (s >= 45) & (v >= 70)  # 緑・青は羊皮紙と色相が離れているので淡い色も拾う
    warm = page & (s >= 90) & (v >= 70)
    masks = {
        "green": cool & (h >= 35) & (h < 120),
        "blue": cool & (h >= 120) & (h < 190),
        "red": warm & ((h < 11) | (h >= 235)),
        "yellow": page & (s >= 120) & (v >= 120) & (h >= 18) & (h < 35),
    }
    return {k: float(m.sum()) / area for k, m in masks.items()}


# ---------------------------------------------------------------------------
# 統計
# ---------------------------------------------------------------------------


def pair_values(units, text_sim, color_vecs, exclude) -> tuple[list[float], list[float], list[tuple]]:
    xs, ys, pairs = [], [], []
    n = len(units)
    for i in range(n):
        for j in range(i + 1, n):
            if exclude(units[i], units[j]):
                continue
            xs.append(text_sim[i][j])
            ys.append(-float(np.linalg.norm(color_vecs[i] - color_vecs[j])))
            pairs.append((i, j))
    return xs, ys, pairs


def pearson(xs, ys) -> float:
    x, y = np.asarray(xs), np.asarray(ys)
    if len(x) < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def mantel(units, text_sim, color_vecs, exclude, trials: int, rng: random.Random) -> tuple[float, float, int]:
    """語彙の類似度と色の類似度（色の特徴の距離の負）の相関と、頁を入れ替えた並べ替え検定の p 値。"""
    xs, ys, pairs = pair_values(units, text_sim, color_vecs, exclude)
    r = pearson(xs, ys)
    if math.isnan(r):
        return r, float("nan"), len(xs)
    x = np.asarray(xs)
    idx = list(range(len(units)))
    hits = 0
    for _ in range(trials):
        rng.shuffle(idx)
        y = [-float(np.linalg.norm(color_vecs[idx[i]] - color_vecs[idx[j]])) for i, j in pairs]
        if pearson(x, y) >= r:
            hits += 1
    return r, (hits + 1) / (trials + 1), len(xs)


def word_association(words_by_page: list[Counter], high: list[bool], min_count: int):
    """色の多い頁（high）に偏る語を G² で並べる。"""
    hi, lo = Counter(), Counter()
    for w, h in zip(words_by_page, high):
        (hi if h else lo).update(w)
    c, d = sum(hi.values()), sum(lo.values())
    return corpus.distinctive(hi, lo, c, d, min_count), c, d


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    p = corpus.make_parser("ヴォイニッチ手稿: 絵の色の特徴と文章の語彙の対応を調べる")
    p.add_argument("--width", type=int, default=500, help="使う画像の幅（page_images.py と同じ値, 既定: 500）")
    p.add_argument("--min-words", type=int, default=40, help="対象にする頁の最小語数（既定: 40）")
    p.add_argument("--trials", type=int, default=2000, help="並べ替え検定の回数（既定: 2000）")
    p.add_argument("--top", type=int, default=8, help="色ごとに表示する語の数（既定: 8）")
    p.add_argument("--features", action="store_true", help="頁ごとの色の特徴を表示する")
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args(argv)
    if args.locus is None:
        args.locus = "P"
    if args.illustration is None:
        args.illustration = "H"
    if args.language is None:
        args.language = "A"
    return args


def main(argv=None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(args.seed)

    manifest = spread.load_manifest()
    units, feats, missing = [], [], []
    for pt in vocab_shift.page_texts(lines, opts):
        if pt.size < args.min_words:
            continue
        label = spread.resolve_page(manifest, pt.name)
        if label != pt.name:  # 折り込み・2 頁まとめた画像は頁の範囲が分からないので除く
            continue
        img = page_images.image_path(label, args.width)
        if not img.exists():
            missing.append(pt.name)
            continue
        units.append(pt)
        feats.append(color_features(img))
    if missing:
        print(f"（画像が無い頁 {len(missing)} 件: 先に python3 voynich/page_images.py を実行してください）",
              file=sys.stderr)
    if len(units) < 10:
        sys.exit("対象の頁が少なすぎます。")

    print(f"転写ファイル: {path.name}")
    print(f"=== {corpus.filter_title(args)}: {len(units)} 頁（{args.min_words} 語以上, 画像あり）===\n")

    mat = np.array([[f[c] for c in COLORS] for f in feats])
    print("--- 色の特徴（顔料が頁に占める割合）---")
    print(f"{'':6}" + "".join(rjust(COLOR_JA[c], 8) for c in COLORS))
    for label, fn in (("平均", np.mean), ("中央値", np.median), ("最大", np.max)):
        print(ljust(label, 6) + "".join(f"{fn(mat[:, k]):>8.3%}" for k in range(len(COLORS))))
    print()
    if args.features:
        for pt, f in zip(units, feats):
            print(f"  {pt.name:<7}" + "".join(f"{f[c]:>8.3%}" for c in COLORS) + f"  {pt.size} 語")
        print()

    # 色の特徴を標準化（割合の大きさが色ごとに違うので、対数をとってから z 値に）
    logm = np.log(mat + 1e-4)
    z = (logm - logm.mean(axis=0)) / np.where(logm.std(axis=0) > 0, logm.std(axis=0), 1)
    text_sim = vocab_shift.similarity_matrix(corpus_features([pt.words for pt in units]))

    def none(a, b):
        return False

    def same_bifolio(a, b):
        return a.page.get("Q") == b.page.get("Q") and a.page.get("B") == b.page.get("B")

    def same_quire(a, b):
        return a.page.get("Q") == b.page.get("Q")

    print("--- マンテル検定: 色が似た頁どうしは、語彙も似ているか ---")
    print("r > 0 で p が小さければ、絵の色と文章の語彙に対応がある。\n")
    print(f"{ljust('対象の頁の組', 34)}  {rjust('組の数', 6)}  {rjust('r', 7)}  {rjust('p', 7)}")
    for label, ex in (("全ての組", none), ("同じ二つ折りの組を除く", same_bifolio),
                      ("同じクワイアの組を除く", same_quire)):
        r, p, n = mantel(units, text_sim, z, ex, args.trials, rng)
        print(f"{ljust(label, 34)}  {n:>6}  {r:>7.3f}  {p:>7.4f}")
    print()

    print("--- 色と結びつく語（色の多い上位 1/4 の頁 対 それ以外）---")
    print("「偶然の最大」= 頁を入れ替えたときに出る最大の G² の 95% 点。これを超える語だけが偶然では説明しにくい。\n")
    words = [pt.words for pt in units]
    for k, c in enumerate(COLORS):
        cut = np.quantile(mat[:, k], 0.75)
        high = [bool(x >= cut and x > 0) for x in mat[:, k]]
        if sum(high) < 3:
            continue
        rows, a_tot, b_tot = word_association(words, high, args.min_count)
        null_max = []
        for _ in range(min(args.trials, 500)):
            sh = high[:]
            rng.shuffle(sh)
            r_, _, _ = word_association(words, sh, args.min_count)
            null_max.append(r_[0][0] if r_ else 0.0)
        null_max.sort()
        thr = null_max[int(len(null_max) * 0.95) - 1] if null_max else float("inf")
        print(f"[{COLOR_JA[c]}] 多い頁 {sum(high)} / {len(high)}（{a_tot} 語）、偶然の最大 G² ≈ {thr:.1f}")
        for g2, w, a, b in rows[:args.top]:
            mark = "★" if g2 > thr else " "
            print(f"  {mark} {w:<12} G² {g2:>6.1f}   多い頁 {a:>3}  他 {b:>3}")
        print()


def corpus_features(words_list: list[Counter]) -> list[Counter]:
    """頁の語彙の tf-idf（どの頁にも出る語を軽くする）。"""
    n = len(words_list)
    df = Counter()
    for w in words_list:
        df.update(w.keys())
    idf = {k: math.log(n / d) for k, d in df.items()}
    return [Counter({k: v * idf[k] for k, v in w.items() if idf[k] > 0}) for w in words_list]


if __name__ == "__main__":
    main()

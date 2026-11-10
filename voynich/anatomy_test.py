#!/usr/bin/env python3
"""植物＝解剖図仮説の検定（notes/植物＝解剖図仮説の分類案.md で事前に決めた手順）。

notes/anatomy_classification.csv の根の型（R1〜R7, R0）と葉の型（L1〜L5, L0）を読み、
言語 A・B それぞれの中で、頁の組の語彙の類似度（tf-idf のコサイン）を「同じ型の組」と「違う型の組」で比べる。
型のラベルを頁の間で入れ替える並べ替え検定で p 値を出す。同じ二つ折り・同じクワイアの組を除いた場合も出す。

  P1（根）: 同じ根の型の組は、違う型の組より語彙が似ている
  P2（葉）: 葉の型では P1 のような差が出ない（または根より小さい）

    python3 voynich/anatomy_test.py
    python3 voynich/anatomy_test.py --confirmed-only     # 確認者が Claude（未確認）以外の行だけ使う

R0・L0 の頁は、その型の検定から除く。標準ライブラリのみで動作する。
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import image_text  # noqa: E402
import ivtff  # noqa: E402
import vocab_shift  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

CLASS_FILE = Path(__file__).resolve().parent / "notes" / "anatomy_classification.csv"
UNCONFIRMED = "Claude（未確認）"


def load_classes(confirmed_only: bool) -> dict[str, dict[str, str]]:
    with open(CLASS_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if confirmed_only:
        rows = [r for r in rows if r.get("確認者", "").strip() not in ("", UNCONFIRMED)]
    return {r["頁"]: r for r in rows}


def same_vs_diff(labels: list[str], sim, exclude) -> tuple[float, float, int, int]:
    same, diff = [], []
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            if exclude(i, j):
                continue
            (same if labels[i] == labels[j] else diff).append(sim[i][j])
    if not same or not diff:
        return float("nan"), float("nan"), len(same), len(diff)
    return sum(same) / len(same), sum(diff) / len(diff), len(same), len(diff)


def permutation_test(labels, sim, exclude, trials: int, rng: random.Random):
    s, d, ns, nd = same_vs_diff(labels, sim, exclude)
    obs = s - d
    hits = 0
    shuffled = labels[:]
    for _ in range(trials):
        rng.shuffle(shuffled)
        s2, d2, _, _ = same_vs_diff(shuffled, sim, exclude)
        if s2 - d2 >= obs:
            hits += 1
    return s, d, ns, nd, (hits + 1) / (trials + 1)


def main(argv=None) -> None:
    p = corpus.make_parser("植物＝解剖図仮説の検定")
    p.add_argument("--trials", type=int, default=5000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--confirmed-only", action="store_true", help="研究者が確認した行だけ使う")
    args = p.parse_args(argv)
    if args.locus is None:
        args.locus = "P"
    if args.illustration is None:
        args.illustration = "H"
    classes = load_classes(args.confirmed_only)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    rng = random.Random(args.seed)
    texts = {pt.name: pt for pt in vocab_shift.page_texts(lines, opts)}

    print(f"転写ファイル: {path.name}、分類: {CLASS_FILE.name}（{len(classes)} 頁"
          f"{'、確認済みのみ' if args.confirmed_only else ''}）\n")
    unconfirmed = sum(1 for r in classes.values() if r.get("確認者", "").strip() in ("", UNCONFIRMED))
    if unconfirmed:
        print(f"注意: {unconfirmed} 頁の分類は未確認（分析補助の AI の下書き）です。\n")

    for lang in ("A", "B"):
        pages = [n for n in classes if n in texts and texts[n].page.get("L") == lang]
        if len(pages) < 6:
            continue
        print(f"=== 言語 {lang}: {len(pages)} 頁 ===")
        print(f"{ljust('', 20)}{rjust('同じ型', 8)}{rjust('違う型', 8)}{rjust('差', 7)}{rjust('組(同/違)', 12)}{rjust('p', 8)}")
        for kind, col, zero in (("根（P1）", "根", "R0"), ("葉（P2）", "葉", "L0")):
            use = [n for n in pages if classes[n][col] != zero]
            labels = [classes[n][col] for n in use]
            sim = vocab_shift.similarity_matrix(image_text.corpus_features([texts[n].words for n in use]))
            units = [texts[n] for n in use]

            def same_bifolio(i, j, u=units):
                a, b = u[i].page, u[j].page
                return a.get("Q") == b.get("Q") and a.get("B") == b.get("B")

            def same_quire(i, j, u=units):
                return u[i].page.get("Q") == u[j].page.get("Q")

            for label, ex in ((kind, lambda i, j: False), (f"{kind} 同じ二つ折りを除く", same_bifolio),
                              (f"{kind} 同じクワイアを除く", same_quire)):
                s, d, ns, nd, pv = permutation_test(labels, sim, ex, args.trials, rng)
                print(f"{ljust(label, 20)}{s:>8.3f}{d:>8.3f}{s - d:>7.3f}{ns:>6}/{nd:<5}{pv:>8.4f}")
        print()


if __name__ == "__main__":
    main()

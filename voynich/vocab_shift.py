#!/usr/bin/env python3
"""ヴォイニッチ手稿 語彙の移り変わり分析スクリプト。

ページごとの語彙（単語の頻度分布）を比べ、どのページ同士が似ているかを調べる。

  1. ページの関係ごとの類似度: 隣り合うページ、同じ二つ折り（bifolio）、同じクワイア、
     同じセクション、同じ言語などの組で、語彙の類似度の平均を比べる。
     隣り合うページの類似度は、ページ順をランダムに並べ替えた場合と比べて有意性を出す。
  2. グループ間の類似度行列: 挿絵種別（セクション）や言語どうしの平均類似度
  3. 局所的な語: 総出現数のわりに少数のページに集中している語（話題語の候補）
  4. （--similar 指定時）指定したページに語彙が最も似ているページ

類似度は、ページごとの単語の相対頻度ベクトルのコサイン類似度（0〜1）。
語は疎なので、--feature glyph2 で字形の 2-gram（語の中の隣り合う字形の組）も使える。

使い方の例:
    python3 voynich/vocab_shift.py
    python3 voynich/vocab_shift.py --by Q                 # クワイアどうしの類似度行列
    python3 voynich/vocab_shift.py --similar f1r
    python3 voynich/vocab_shift.py --feature glyph2 --matrix-csv voynich/out/sim.csv

標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import csv
import math
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
from corpus import ljust, rjust  # noqa: E402


# ---------------------------------------------------------------------------
# データ構造と集計
# ---------------------------------------------------------------------------


@dataclass
class PageText:
    page: ivtff.Page
    index: int  # 手稿内の順番（転写ファイルでの出現順 = 現在の綴じ順）
    words: Counter

    @property
    def name(self) -> str:
        return self.page.name

    @property
    def size(self) -> int:
        return sum(self.words.values())


def page_texts(lines: list[ivtff.Line], opts: ivtff.Options) -> list[PageText]:
    pages: dict[str, PageText] = {}
    for ln in lines:
        pt = pages.get(ln.page.name)
        if pt is None:
            pt = pages[ln.page.name] = PageText(ln.page, len(pages), Counter())
        pt.words.update(ivtff.words(ln.raw, opts))
    return list(pages.values())


def glyph_bigrams(words: Counter) -> Counter:
    """語の中で隣り合う字形の組（語頭・語末の境界 '#' を含む）を数える。"""
    out = Counter()
    for w, c in words.items():
        gs = ["#"] + ivtff.glyphs(w) + ["#"]
        for a, b in zip(gs, gs[1:]):
            out[f"{a}{b}"] += c
    return out


def cosine(a: Counter, b: Counter) -> float:
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b[k] for k, v in a.items() if k in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def similarity_matrix(features: list[Counter]) -> list[list[float]]:
    n = len(features)
    sim = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim[i][j] = sim[j][i] = cosine(features[i], features[j])
    return sim


def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


# ---------------------------------------------------------------------------
# 分析
# ---------------------------------------------------------------------------


def folio_number(page_name: str) -> str:
    """ページ名から葉（フォリオ）番号を取り出す。例: f86v3 -> 86, f1r -> 1。"""
    m = re.match(r"f(\d+)", page_name)
    return m.group(1) if m else page_name


_PLAIN_PAGE_RE = re.compile(r"^f(\d+)([rv])$")


def plain_side(page_name: str) -> tuple[int, str] | None:
    """折り込みでない頁の (葉番号, 'r' または 'v')。折り込みの頁（f67r1 など）は None。"""
    m = _PLAIN_PAGE_RE.match(page_name)
    return (int(m.group(1)), m.group(2)) if m else None


def is_current_facing(a: PageText, b: PageText) -> bool:
    """a と b が現在の綴じ順で見開き（ある葉の裏と、次の葉の表）になっているか。"""
    sa, sb = plain_side(a.name), plain_side(b.name)
    return (b.index == a.index + 1 and sa is not None and sb is not None
            and sa[1] == "v" and sb[1] == "r" and sa[0] != sb[0])


def is_conjoint(a: PageText, b: PageText) -> bool:
    """a と b が同じ二つ折りの中央見開き（前の葉の裏と後ろの葉の表, 例: f78v と f81r）か。"""
    sa, sb = plain_side(a.name), plain_side(b.name)
    if sa is None or sb is None or sa[0] == sb[0]:
        return False
    pa, pb = a.page, b.page
    if not (pa.get("Q") == pb.get("Q") != "?" and pa.get("B") == pb.get("B") != "?"):
        return False
    (first, s1), (second, s2) = sorted([sa, sb])
    return s1 == "v" and s2 == "r"


def relation_table(pages: list[PageText], sim: list[list[float]]) -> list[tuple[str, list[float]]]:
    """ページの組を関係ごとに分け、類似度のリストを返す。

    「隣接」は残ったページの並び（--min-words で除外したページを詰めた順）で隣り合う組。
    """
    n = len(pages)
    rel: dict[str, list[float]] = {}

    def add(key, v):
        rel.setdefault(key, []).append(v)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = pages[i].page, pages[j].page
            v = sim[i][j]
            adjacent = j == i + 1
            same_i = a.get("I") == b.get("I") != "?"
            add("全ての組", v)
            if adjacent:
                add("隣り合うページ", v)
            same_folio = folio_number(a.name) == folio_number(b.name)
            if same_folio:
                add("同じ葉の表と裏", v)
            if is_current_facing(pages[i], pages[j]):
                add("現在の見開き（葉の裏と次の葉の表）", v)
            if is_conjoint(pages[i], pages[j]):
                add("二つ折りの中央見開き（例: f78v と f81r）", v)
            if same_folio:
                pass
            elif a.get("Q") == b.get("Q") != "?" and a.get("B") == b.get("B") != "?":
                add("同じ二つ折りの別の葉", v)
            if a.get("Q") == b.get("Q") != "?":
                add("同じクワイア", v)
            if same_i:
                add("同じセクション（挿絵種別）", v)
                add("同じセクションで隣り合う" if adjacent else "同じセクションで隣り合わない", v)
            if a.get("L") == b.get("L") != "?":
                add("同じ言語 (A/B)", v)
            if a.get("H") == b.get("H") != "?":
                add("同じ筆写者", v)
            if a.get("L") in "AB" and b.get("L") in "AB" and a.get("L") != b.get("L"):
                add("言語が異なる (A と B)", v)
    order = ["全ての組", "隣り合うページ", "同じ葉の表と裏", "現在の見開き（葉の裏と次の葉の表）",
             "二つ折りの中央見開き（例: f78v と f81r）", "同じ二つ折りの別の葉", "同じクワイア",
             "同じセクション（挿絵種別）", "同じセクションで隣り合う", "同じセクションで隣り合わない",
             "同じ言語 (A/B)", "同じ筆写者", "言語が異なる (A と B)"]
    return [(k, rel[k]) for k in order if k in rel]


def mean_difference_test(a: list[float], b: list[float], trials: int, seed: int) -> float:
    """a の平均が b の平均より大きいかを、組のラベルを入れ替える並べ替え検定で調べる（片側 p 値）。"""
    observed = mean(a) - mean(b)
    pooled = a + b
    rng = random.Random(seed)
    hits = 0
    for _ in range(trials):
        rng.shuffle(pooled)
        if mean(pooled[:len(a)]) - mean(pooled[len(a):]) >= observed:
            hits += 1
    return (hits + 1) / (trials + 1)


def adjacency_test(sim: list[list[float]], trials: int, seed: int) -> tuple[float, float, float]:
    """隣り合うページの平均類似度を、ページ順をランダムに並べ替えた場合と比べる。

    戻り値: (実際の平均, 並べ替えたときの平均, 並べ替えで実際以上になった割合 = p 値)
    """
    n = len(sim)
    observed = mean(sim[i][i + 1] for i in range(n - 1))
    rng = random.Random(seed)
    order = list(range(n))
    shuffled_means = []
    hits = 0
    for _ in range(trials):
        rng.shuffle(order)
        m = mean(sim[order[i]][order[i + 1]] for i in range(n - 1))
        shuffled_means.append(m)
        if m >= observed:
            hits += 1
    return observed, mean(shuffled_means), (hits + 1) / (trials + 1)


def group_matrix(pages: list[PageText], sim: list[list[float]], key: str):
    groups: dict[str, list[int]] = {}
    for i, pt in enumerate(pages):
        groups.setdefault(pt.page.get(key), []).append(i)
    keys = sorted(groups)
    matrix = {}
    for a in keys:
        for b in keys:
            vals = [sim[i][j] for i in groups[a] for j in groups[b] if i != j]
            matrix[a, b] = mean(vals)
    return keys, groups, matrix


def burstiness(pages: list[PageText], min_count: int) -> list[tuple]:
    """語がページにどれだけ集中しているか。

    語がページの大きさに比例してランダムに散らばると仮定したときに出現が期待されるページ数と、
    実際に出現したページ数の比（小さいほど少数のページに集中している）を返す。
    """
    total = sum(pt.size for pt in pages)
    shares = [pt.size / total for pt in pages]
    counts = Counter()
    for pt in pages:
        counts.update(pt.words)
    rows = []
    for word, n in counts.items():
        if n < min_count:
            continue
        expected = sum(1 - (1 - p) ** n for p in shares)
        observed_pages = [(pt.words[word], pt) for pt in pages if word in pt.words]
        observed_pages.sort(key=lambda x: -x[0])
        rows.append((len(observed_pages) / expected, word, n, len(observed_pages),
                     expected, observed_pages))
    rows.sort(key=lambda r: r[0])
    return rows


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def print_relations(pages, sim, trials, seed) -> None:
    print("--- ページの関係ごとの語彙の類似度（コサイン類似度の平均）---")
    print(f"{ljust('関係', 30)}  {rjust('組の数', 7)}  {rjust('平均', 6)}")
    for label, vals in relation_table(pages, sim):
        print(f"{ljust(label, 30)}  {len(vals):>7}  {mean(vals):>6.3f}")
    print()
    rel = dict(relation_table(pages, sim))
    conj = rel.get("二つ折りの中央見開き（例: f78v と f81r）")
    facing = rel.get("現在の見開き（葉の裏と次の葉の表）")
    if conj and facing and trials:
        p = mean_difference_test(conj, facing, trials, seed)
        print(f"二つ折りの中央見開き（{mean(conj):.3f}）は現在の見開き（{mean(facing):.3f}）より似ている: "
              f"並べ替え検定 p = {p:.4f}")
        print("中央見開きの方が似ていれば、二つ折り 1 枚ずつを開いて読む作り（singulion）だった"
              "という仮説と整合する。\n")
    if len(pages) > 2 and trials:
        obs, shuffled, p = adjacency_test(sim, trials, seed)
        print(f"隣り合うページの平均類似度 {obs:.3f} に対し、ページ順をランダムに "
              f"{trials} 回並べ替えたときの平均は {shuffled:.3f}（p = {p:.4f}）。")
        print("p が小さいほど「隣り合うページの語彙が似ているのは偶然ではない」ことを示す。\n")


def print_group_matrix(pages, sim, key: str) -> None:
    keys, groups, matrix = group_matrix(pages, sim, key)
    var_name = ivtff.PAGE_VARIABLES[key]
    labels = {k: ("未指定" if k == "?" else k) for k in keys}
    print(f"--- {var_name} どうしの平均類似度（対角 = グループ内）---")
    if key == "I":
        print("  " + ", ".join(f"{k}: {v.split(' ')[0]}" for k, v in ivtff.ILLUSTRATION_TYPES.items()))
    cell = 7
    print(ljust("", 10) + "".join(rjust(labels[k], cell) for k in keys) + rjust("ページ", 8))
    for a in keys:
        row = ""
        for b in keys:
            v = matrix[a, b]
            row += rjust("-" if math.isnan(v) else f"{v:.3f}", cell)
        print(ljust(labels[a], 10) + row + f"{len(groups[a]):>8}")
    print()


def print_burstiness(pages, min_count: int, top: int) -> None:
    rows = burstiness(pages, min_count)[:top]
    print(f"--- 少数のページに集中している語（出現 {min_count} 回以上）---")
    print("集中度 = 実際に出現したページ数 / ランダムに散らばった場合に期待されるページ数")
    width = max([len(r[1]) for r in rows] + [6])
    print(f"{ljust('単語', width)}  {rjust('出現数', 6)}  {rjust('ページ数', 8)}  "
          f"{rjust('期待値', 6)}  {rjust('集中度', 6)}  多いページ（回数, セクション）")
    for ratio, word, n, n_pages, expected, observed in rows:
        top_pages = ", ".join(f"{pt.name}({c},{pt.page.get('I')})" for c, pt in observed[:4])
        print(f"{word:<{width}}  {n:>6}  {n_pages:>8}  {expected:>6.1f}  {ratio:>6.2f}  {top_pages}")
    print()


def print_similar(pages, sim, name: str, top: int) -> None:
    idx = next((i for i, pt in enumerate(pages) if pt.name == name), None)
    if idx is None:
        print(f"ページ {name} は対象に含まれていません（語数が --min-words 未満か、絞り込みで除外）。\n")
        return
    p = pages[idx].page
    print(f"--- {name} に語彙が似ているページ（{name}: セクション {p.get('I')}, "
          f"言語 {p.get('L')}, 筆写者 {p.get('H')}, クワイア {p.get('Q')}）---")
    ranked = sorted((sim[idx][j], j) for j in range(len(pages)) if j != idx)[::-1][:top]
    for v, j in ranked:
        q = pages[j].page
        print(f"  {pages[j].name:<7} {v:.3f}  セクション {q.get('I')}  言語 {q.get('L')}  "
              f"筆写者 {q.get('H')}  クワイア {q.get('Q')}  ({pages[j].size} 語)")
    print()


def write_matrix(path: Path, pages, sim) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "section", "language", "hand", "quire"] + [pt.name for pt in pages])
        for pt, row in zip(pages, sim):
            p = pt.page
            w.writerow([pt.name, p.get("I"), p.get("L"), p.get("H"), p.get("Q")]
                       + [f"{v:.4f}" for v in row])
    print(f"類似度行列を書き出しました: {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None):
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）の語彙の移り変わり分析")
    p.add_argument("--feature", choices=["words", "glyph2"], default="words",
                   help="類似度に使う特徴: words=単語, glyph2=字形の 2-gram（既定: words）")
    p.add_argument("--min-words", type=int, default=50,
                   help="分析に含めるページの最小語数（既定: 50）")
    p.add_argument("--top", type=int, default=20, help="各表に表示する件数（既定: 20）")
    p.add_argument("--burst-min", type=int, default=15,
                   help="集中度を計算する語の最小出現数（既定: 15）")
    p.add_argument("--similar", help="このページに似ているページを表示（例: f1r）")
    p.add_argument("--trials", type=int, default=2000,
                   help="隣接ページの並べ替え検定の回数（既定: 2000, 0 で省略）")
    p.add_argument("--seed", type=int, default=1, help="並べ替え検定の乱数の種（既定: 1）")
    p.add_argument("--matrix-csv", type=Path, help="ページ×ページの類似度行列を CSV に書き出す")
    args = p.parse_args(argv)
    if args.locus is None:
        args.locus = "P"
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)

    all_pages = page_texts(lines, opts)
    pages = [pt for pt in all_pages if pt.size >= args.min_words]
    if len(pages) < 2:
        sys.exit("比較できるページが 2 ページ未満です（--min-words を下げてください）。")
    features = [pt.words if args.feature == "words" else glyph_bigrams(pt.words) for pt in pages]
    sim = similarity_matrix(features)

    feature_name = "単語" if args.feature == "words" else "字形 2-gram"
    print(f"転写ファイル: {path.name}\n")
    print(f"=== {corpus.filter_title(args)}: 語数 {args.min_words} 以上のページ "
          f"{len(pages)}/{len(all_pages)}（特徴: {feature_name}）===\n")

    print_relations(pages, sim, args.trials, args.seed)
    for key in ([args.by] if args.by else ["I", "L"]):
        print_group_matrix(pages, sim, key)
    print_burstiness(pages, args.burst_min, args.top)
    if args.similar:
        print_similar(pages, sim, args.similar, args.top)
    if args.matrix_csv:
        write_matrix(args.matrix_csv, pages, sim)


if __name__ == "__main__":
    main()

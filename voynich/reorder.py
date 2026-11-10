#!/usr/bin/env python3
"""ヴォイニッチ手稿 元の並びの推定スクリプト（語彙の類似度による並べ替え）。

現在の綴じ順は元の並びと違う可能性が高い（notes/頁順の問題.md）。
そこで、語彙の似ている単位どうしが隣に来るような並び（隣どうしの類似度の合計が最大になる並び）を探し、
元の並びの候補として示す。

並べる単位は、綴じ直しても一体のまま残る**二つ折りの紙（bifolio）**が既定。
二つ折りの中の葉の順番（どちらの葉が前か）や、表と裏の向きまでは推定しない。

  1. 並びの良さの比較: 現在の並び・推定した並び・ランダムな並びで、隣どうしの平均類似度を比べる
  2. 推定した並び: 各単位の属性（セクション・言語・筆写者・現在のクワイア）と、
     隣との類似度、ブートストラップでの支持率（語をランダムに抜き直して何回同じ隣になったか）
  3. 現在の並びとの違い: 推定でも隣どうしになった現在の隣接の数

使い方の例:
    python3 voynich/reorder.py                            # 二つ折り単位、全体
    python3 voynich/reorder.py --within L                 # 言語 A / B それぞれの中で並べる
    python3 voynich/reorder.py --unit folio --language A  # 葉の単位で、言語 A の頁だけ
    python3 voynich/reorder.py --link f67r1:f68r1         # 絵がつながる頁を必ず隣にする

標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import itertools
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import vocab_shift  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

LINK_BONUS = 10.0  # --link で指定した組に足す類似度（必ず隣になるよう十分大きく）


# ---------------------------------------------------------------------------
# 単位
# ---------------------------------------------------------------------------


@dataclass
class Unit:
    """並べ替えの単位（二つ折り・葉・頁）。"""

    key: str  # 例: "A1"（クワイア A の二つ折り 1）, "f1"（葉）, "f1r"（頁）
    index: int  # 現在の並びでの順番
    pages: list[ivtff.Page] = field(default_factory=list)
    words: Counter = field(default_factory=Counter)

    @property
    def size(self) -> int:
        return sum(self.words.values())

    def attr(self, var: str) -> str:
        """単位内の頁の属性。頁によって違えば '/' でつなぐ。"""
        values = []
        for p in self.pages:
            v = p.get(var)
            if v not in values:
                values.append(v)
        return "/".join(values)

    def label(self) -> str:
        names = [p.name for p in self.pages]
        if len(names) <= 2:
            return " ".join(names)
        return f"{names[0]}…{names[-1]}"


def unit_key(page: ivtff.Page, unit: str) -> str:
    if unit == "page":
        return page.name
    if unit == "folio":
        return "f" + vocab_shift.folio_number(page.name)
    q, b = page.get("Q"), page.get("B")
    return f"{q}{b}" if q != "?" and b != "?" else "f" + vocab_shift.folio_number(page.name)


def build_units(lines: list[ivtff.Line], opts: ivtff.Options, unit: str) -> list[Unit]:
    units: dict[str, Unit] = {}
    for ln in lines:
        key = unit_key(ln.page, unit)
        u = units.get(key)
        if u is None:
            u = units[key] = Unit(key, len(units))
        if not u.pages or u.pages[-1].name != ln.page.name:
            if all(p.name != ln.page.name for p in u.pages):
                u.pages.append(ln.page)
        u.words.update(ivtff.words(ln.raw, opts))
    return list(units.values())


# ---------------------------------------------------------------------------
# 類似度
# ---------------------------------------------------------------------------


def features(units: list[Unit], kind: str, weight: str) -> list[Counter]:
    feats = [u.words if kind == "words" else vocab_shift.glyph_bigrams(u.words) for u in units]
    if weight == "tfidf":
        n = len(feats)
        df = Counter()
        for f in feats:
            df.update(f.keys())
        idf = {k: math.log(n / d) for k, d in df.items()}
        feats = [Counter({k: v * idf[k] for k, v in f.items() if idf[k] > 0}) for f in feats]
    return feats


def bootstrap_words(words: Counter, rng: random.Random) -> Counter:
    """語を同じ数だけ復元抽出し直す（ブートストラップ）。"""
    items = list(words.keys())
    weights = list(words.values())
    return Counter(rng.choices(items, weights=weights, k=sum(weights)))


# ---------------------------------------------------------------------------
# 並べ替え（隣どうしの類似度の合計を最大にする開いた経路）
# ---------------------------------------------------------------------------


def path_score(order: list[int], sim: list[list[float]]) -> float:
    return sum(sim[a][b] for a, b in zip(order, order[1:]))


def greedy_path(start: int, sim: list[list[float]]) -> list[int]:
    n = len(sim)
    order = [start]
    left = set(range(n)) - {start}
    while left:
        last = order[-1]
        nxt = max(left, key=lambda j: sim[last][j])
        order.append(nxt)
        left.remove(nxt)
    return order


def two_opt(order: list[int], sim: list[list[float]]) -> list[int]:
    """区間を反転して改善する 2-opt（開いた経路版）。改善が無くなるまで繰り返す。"""
    n = len(order)
    improved = True
    while improved:
        improved = False
        for i in range(n - 1):
            for j in range(i + 1, n):
                # order[i..j] を反転したときの増減（両端の辺だけが変わる）
                before = after = 0.0
                if i > 0:
                    before += sim[order[i - 1]][order[i]]
                    after += sim[order[i - 1]][order[j]]
                if j < n - 1:
                    before += sim[order[j]][order[j + 1]]
                    after += sim[order[i]][order[j + 1]]
                if after > before + 1e-12:
                    order[i:j + 1] = reversed(order[i:j + 1])
                    improved = True
    return order


def or_opt(order: list[int], sim: list[list[float]]) -> list[int]:
    """1〜3 個の連続した単位を別の位置へ移して改善する。"""
    improved = True
    while improved:
        improved = False
        base = path_score(order, sim)
        for seg in (1, 2, 3):
            for i in range(len(order) - seg + 1):
                piece = order[i:i + seg]
                rest = order[:i] + order[i + seg:]
                for j in range(len(rest) + 1):
                    for cand_piece in (piece, piece[::-1]):
                        cand = rest[:j] + cand_piece + rest[j:]
                        s = path_score(cand, sim)
                        if s > base + 1e-12:
                            order, base, improved = cand, s, True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
    return order


def best_path(sim: list[list[float]], restarts: int, rng: random.Random) -> list[int]:
    n = len(sim)
    if n <= 2:
        return list(range(n))
    starts = list(range(n))
    rng.shuffle(starts)
    best, best_score = None, -math.inf
    for s in starts[:restarts]:
        order = or_opt(two_opt(greedy_path(s, sim), sim), sim)
        score = path_score(order, sim)
        if score > best_score:
            best, best_score = order, score
    return best


def orient(order: list[int]) -> list[int]:
    """現在の並びとなるべく同じ向きになるよう、必要なら経路を反転する。"""
    n = len(order)
    if n < 2:
        return order
    forward = sum((pos - n / 2) * (idx - n / 2) for pos, idx in enumerate(order))
    return order if forward >= 0 else order[::-1]


def adjacent_pairs(order: list[int]) -> set[frozenset]:
    return {frozenset(p) for p in zip(order, order[1:])}


# ---------------------------------------------------------------------------
# 分析と表示
# ---------------------------------------------------------------------------


def apply_links(sim: list[list[float]], units: list[Unit], links: list[tuple[str, str]]) -> list[str]:
    """--link の頁の組を含む単位どうしの類似度を大きくする。適用できなかった組を返す。"""
    where = {p.name: i for i, u in enumerate(units) for p in u.pages}
    failed = []
    for a, b in links:
        if a not in where or b not in where:
            failed.append(f"{a}:{b}（頁が対象外）")
            continue
        i, j = where[a], where[b]
        if i == j:
            failed.append(f"{a}:{b}（同じ単位の中）")
            continue
        sim[i][j] += LINK_BONUS
        sim[j][i] += LINK_BONUS
    return failed


@dataclass
class Result:
    units: list[Unit]
    sim: list[list[float]]  # --link の加算前の類似度（表示・評価用）
    linked: set  # --link で隣に固定した単位の組
    estimate: list[int]
    support: Counter  # frozenset((i, j)) -> 隣になったブートストラップ回数
    random_scores: list[float]


def compute(units: list[Unit], args, feature: str, weight: str) -> Result:
    rng = random.Random(args.seed)
    raw = vocab_shift.similarity_matrix(features(units, feature, weight))
    links = parse_links(args.link)
    sim = [row[:] for row in raw]
    apply_links(sim, units, links)
    linked = {frozenset((i, j)) for i in range(len(units)) for j in range(len(units))
              if i != j and sim[i][j] - raw[i][j] > LINK_BONUS / 2}
    estimate = orient(best_path(sim, args.restarts, rng))
    n_adj = len(units) - 1
    random_scores = []
    order = list(range(len(units)))
    for _ in range(args.random):
        rng.shuffle(order)
        random_scores.append(path_score(order, raw) / n_adj)
    # ブートストラップ: 語を抜き直して並べ替え、同じ隣どうしになった回数を数える
    support = Counter()
    for _ in range(args.bootstrap):
        boot_units = [Unit(u.key, u.index, u.pages, bootstrap_words(u.words, rng)) for u in units]
        bsim = vocab_shift.similarity_matrix(features(boot_units, feature, weight))
        apply_links(bsim, units, links)
        for pair in adjacent_pairs(best_path(bsim, max(1, args.restarts // 2), rng)):
            support[pair] += 1
    return Result(units, raw, linked, estimate, support, random_scores)


def parse_links(text: str | None) -> list[tuple[str, str]]:
    return [tuple(x.split(":", 1)) for x in (text or "").split(",") if ":" in x]


def select_units(units: list[Unit], min_words: int) -> list[Unit]:
    units = [u for u in units if u.size >= min_words]
    for i, u in enumerate(units):
        u.index = i
    return units


def print_result(r: Result, args) -> None:
    units, sim, estimate, support = r.units, r.sim, r.estimate, r.support
    n_adj = len(units) - 1
    current = list(range(len(units)))
    print("--- 並びの良さ（隣どうしの平均類似度）---")
    print(f"  現在の並び      : {path_score(current, sim) / n_adj:.3f}")
    print(f"  推定した並び    : {path_score(estimate, sim) / n_adj:.3f}")
    rs = sorted(r.random_scores)
    if rs:
        print(f"  ランダムな並び  : {sum(rs) / len(rs):.3f}（{len(rs)} 回の平均, 最大 {rs[-1]:.3f}）")
    kept = adjacent_pairs(current) & adjacent_pairs(estimate)
    print(f"  現在の隣どうしのうち、推定でも隣になったもの: {len(kept)}/{n_adj}\n")

    print("--- 推定した並び ---")
    print("支持率 = ブートストラップ（語を抜き直す）で、前の単位と隣になった割合。高いほど確か。")
    print("現在 = 現在の並びでの順番。★ = 現在の並びでも前の単位と隣どうし。🔗 = --link で固定。\n")
    print(f"{rjust('順', 3)}  {ljust('単位', 6)}  {ljust('頁', 18)}  {rjust('現在', 4)}  "
          f"{ljust('セクション', 10)}  {ljust('言語', 4)}  {ljust('筆写者', 6)}  {rjust('語数', 5)}  "
          f"{rjust('前との類似度', 12)}  {rjust('支持率', 6)}")
    for pos, idx in enumerate(estimate):
        u = units[idx]
        if pos == 0:
            sim_s, sup_s, mark = "", "", " "
        else:
            prev = estimate[pos - 1]
            link = "🔗" if frozenset((prev, idx)) in r.linked else ""
            sim_s = f"{sim[prev][idx]:.3f}{link}"
            sup_s = f"{support[frozenset((prev, idx))] / args.bootstrap:.0%}" if args.bootstrap else "-"
            mark = "★" if abs(prev - idx) == 1 else " "
        print(f"{pos + 1:>3}  {u.key:<6}  {u.label():<18}  {u.index + 1:>4}{mark} "
              f"{ljust(u.attr('I'), 10)}  {ljust(u.attr('L'), 4)}  {ljust(u.attr('H'), 6)}  "
              f"{u.size:>5}  {sim_s:>12}  {sup_s:>6}")
    print()

    if args.bootstrap:
        strong = [(support[frozenset((a, b))], a, b) for a, b in zip(estimate, estimate[1:])]
        strong = [x for x in strong if x[0] / args.bootstrap >= args.strong]
        print(f"--- 支持率 {args.strong:.0%} 以上の隣どうし（元の並びでも隣だった可能性が高い組）---")
        for c, a, b in strong:
            print(f"  {pair_text(units, a, b)}  {c / args.bootstrap:>5.0%}  （{distance_text(a, b)}）")
        print()


def pair_text(units: list[Unit], a: int, b: int) -> str:
    return f"{units[a].key:<5} {units[a].label():<18} — {units[b].key:<5} {units[b].label():<18}"


def distance_text(a: int, b: int) -> str:
    return "現在も隣" if abs(a - b) == 1 else f"現在は {abs(a - b)} 単位離れている"


CONSENSUS_SETTINGS = [("words", "tfidf"), ("words", "raw"), ("glyph2", "raw")]


def print_consensus(units: list[Unit], args) -> None:
    """複数の設定で並べ替え、支持率の高い隣どうしが設定をまたいで一致するかを見る。"""
    results = [compute(units, args, f, w) for f, w in CONSENSUS_SETTINGS]
    names = [f"{f}/{w}" for f, w in CONSENSUS_SETTINGS]
    rates: dict[frozenset, list[float]] = {}
    for k, r in enumerate(results):
        for pair, c in r.support.items():
            rates.setdefault(pair, [0.0] * len(results))[k] = c / args.bootstrap
    need = args.consensus_min
    rows = []
    for pair, rs in rates.items():
        n_strong = sum(1 for x in rs if x >= args.strong)
        if n_strong >= need:
            a, b = sorted(pair)
            rows.append((n_strong, sum(rs) / len(rs), a, b, rs))
    rows.sort(key=lambda x: (-x[0], -x[1], x[2]))
    print(f"--- 複数の設定で一致した隣どうし（{len(results)} 設定のうち {need} 以上で支持率 "
          f"{args.strong:.0%} 以上）---")
    print("設定: " + ", ".join(names) + "（各設定のブートストラップ支持率）\n")
    for n_strong, _, a, b, rs in rows:
        cells = " ".join(f"{x:>4.0%}" for x in rs)
        print(f"  {pair_text(units, a, b)}  {cells}  {n_strong}/{len(results)}  （{distance_text(a, b)}）")
    if not rows:
        print("  （該当なし）")
    print()


def analyse(title: str, units: list[Unit], args) -> None:
    units = select_units(units, args.min_words)
    print(f"=== {title}: {len(units)} 単位（{args.unit}, {args.min_words} 語以上）===\n")
    if len(units) < 4:
        print("単位が少なすぎるため並べ替えません（--min-words を下げてください）。\n")
        return
    for f in apply_links([[0.0] * len(units) for _ in units], units, parse_links(args.link)):
        print(f"  （--link を適用できません: {f}）")
    if args.consensus:
        print_consensus(units, args)
    else:
        print_result(compute(units, args, args.feature, args.weight), args)


# ---------------------------------------------------------------------------
# singulion モデル: 二つ折り 1 枚ずつを開いて読む作りでの総当たりの並べ替え
# ---------------------------------------------------------------------------
#
# Layfield & Davis (2026) は、各二つ折りを「前の葉の表・裏・後ろの葉の表・裏」の 4 頁として
# 順に読む作り（singulion）だったと推定した。この作りで二つ折り X の次に Y を綴じると、
# X の最後の頁（後ろの葉の裏）と Y の最初の頁（前の葉の表）が見開きになる。
# ここでは、その見開きの類似度の平均が最大になる二つ折りの並びを総当たりで探す。


@dataclass
class Sheet:
    """singulion として読む二つ折り 1 枚。"""

    key: str  # 例: "78|81"
    first: int  # 前の葉の番号
    second: int  # 後ろの葉の番号
    page_words: dict  # 頁名 -> Counter

    def page(self, which: str) -> str:
        return {"first_r": f"f{self.first}r", "first_v": f"f{self.first}v",
                "second_r": f"f{self.second}r", "second_v": f"f{self.second}v"}[which]


def build_sheets(lines: list[ivtff.Line], opts: ivtff.Options) -> tuple[list[Sheet], list[str]]:
    """二つ折りごとに Sheet を作る。2 枚の葉からなる通常の二つ折りだけを扱う。"""
    groups: dict[str, dict[str, Counter]] = {}
    order: list[str] = []
    for ln in lines:
        q, b = ln.page.get("Q"), ln.page.get("B")
        if q == "?" or b == "?":
            continue
        key = f"{q}{b}"
        if key not in groups:
            groups[key] = {}
            order.append(key)
        groups[key].setdefault(ln.page.name, Counter()).update(ivtff.words(ln.raw, opts))
    sheets, skipped = [], []
    for key in order:
        pages = groups[key]
        sides = [vocab_shift.plain_side(n) for n in pages]
        folios = sorted({s_[0] for s_ in sides if s_})
        if any(s_ is None for s_ in sides) or len(folios) != 2:
            skipped.append(f"{key}（{' '.join(pages)}）")
            continue
        sheets.append(Sheet(f"{folios[0]}|{folios[1]}", folios[0], folios[1], pages))
    return sheets, skipped


def transition_matrix(sheets: list[Sheet], weight: str) -> list[list[float]]:
    """T[i][j] = 二つ折り i の最後の頁と、二つ折り j の最初の頁の類似度（向きあり）。"""
    names, counters = [], []
    for sh in sheets:
        for pname, words in sh.page_words.items():
            names.append(pname)
            counters.append(words)
    feats = features([Unit(n, 0, [], c) for n, c in zip(names, counters)], "words", weight)
    vec = dict(zip(names, feats))
    empty = Counter()
    n = len(sheets)
    return [[vocab_shift.cosine(vec.get(sheets[i].page("second_v"), empty),
                                vec.get(sheets[j].page("first_r"), empty)) if i != j else 0.0
             for j in range(n)] for i in range(n)]


def sequence_score(order, trans) -> float:
    return sum(trans[a][b] for a, b in zip(order, order[1:])) / max(len(order) - 1, 1)


def print_singulion(title: str, lines: list[ivtff.Line], opts, args) -> None:
    sheets, skipped = build_sheets(lines, opts)
    print(f"=== {title}: singulion モデルでの総当たり（{len(sheets)} 枚）===")
    for sk in skipped:
        print(f"  （折り込み等のため対象外: {sk}）")
    n = len(sheets)
    if n < 3:
        print("二つ折りが 3 枚未満のため並べ替えません。\n")
        return
    if n > args.exact_max:
        print(f"二つ折りが {n} 枚あり、総当たり（{math.factorial(n):,} 通り）が多すぎます。"
              f"--quire などで絞ってください（上限 --exact-max {args.exact_max}）。\n")
        return
    trans = transition_matrix(sheets, args.weight)
    keys = [sh.key for sh in sheets]
    scored = sorted(((sequence_score(p, trans), p) for p in itertools.permutations(range(n))),
                    reverse=True)
    total = len(scored)

    def rank_of(order) -> int:
        s_ = sequence_score(order, trans)
        return 1 + sum(1 for sc, _ in scored if sc > s_ + 1e-12)

    def fmt(order) -> str:
        return ", ".join(keys[i] for i in order)

    print("見開きの類似度 = 二つ折りの最後の頁（後ろの葉の裏）と次の二つ折りの最初の頁（前の葉の表）の"
          "類似度の平均")
    print(f"全 {total:,} 通りの平均: {sum(sc for sc, _ in scored) / total:.3f}\n")
    current = list(range(n))
    print(f"  現在の並び（外側から内側）: {fmt(current)}")
    print(f"    見開きの類似度 {sequence_score(current, trans):.3f}、"
          f"{total:,} 通り中 {rank_of(current):,} 位\n")
    print(f"  上位 {args.top_orders} 通り:")
    for k, (sc, order) in enumerate(scored[:args.top_orders], 1):
        print(f"    {k:>2}. {sc:.3f}  {fmt(order)}")
    print()
    for spec in (args.order or []):
        wanted = [x.strip() for x in spec.split(",") if x.strip()]
        if sorted(wanted) != sorted(keys):
            continue  # 別のクワイア向けの指定
        order = [keys.index(x) for x in wanted]
        print(f"  指定した並び: {fmt(order)}")
        print(f"    見開きの類似度 {sequence_score(order, trans):.3f}、"
              f"{total:,} 通り中 {rank_of(order):,} 位")
    print()


def parse_args(argv: list[str] | None = None):
    p = corpus.make_parser("ヴォイニッチ手稿（ZL 転写, EVA）の元の並びの推定")
    p.add_argument("--unit", choices=["bifolio", "folio", "page"], default="bifolio",
                   help="並べる単位（既定: bifolio = 二つ折りの紙）")
    p.add_argument("--within", choices=list(ivtff.PAGE_VARIABLES),
                   help="この属性のグループごとに分けて並べる（例: L=言語, I=セクション）")
    p.add_argument("--feature", choices=["words", "glyph2"], default="words",
                   help="類似度に使う特徴（既定: words）")
    p.add_argument("--weight", choices=["raw", "tfidf"], default="tfidf",
                   help="特徴の重み（tfidf = どの単位にも出る語を軽くする, 既定: tfidf）")
    p.add_argument("--min-words", type=int, default=100,
                   help="並べる単位の最小語数（既定: 100）")
    p.add_argument("--link", help="必ず隣にする頁の組（例: f67r1:f68r1,f85r1:f86v4）")
    p.add_argument("--restarts", type=int, default=20, help="探索のやり直し回数（既定: 20）")
    p.add_argument("--bootstrap", type=int, default=30,
                   help="ブートストラップの回数（既定: 30, 0 で省略）")
    p.add_argument("--strong", type=float, default=0.7,
                   help="「確かな隣どうし」とみなす支持率（既定: 0.7）")
    p.add_argument("--random", type=int, default=1000,
                   help="比較用のランダムな並びの数（既定: 1000）")
    p.add_argument("--seed", type=int, default=1, help="乱数の種（既定: 1）")
    p.add_argument("--singulion", action="store_true",
                   help="二つ折り 1 枚ずつを開いて読む作りを仮定し、見開きの類似度で総当たりの並べ替えをする"
                        "（--quire で絞って使う。例: --quire M）")
    p.add_argument("--exact-max", type=int, default=8,
                   help="--singulion で総当たりする二つ折りの最大枚数（既定: 8）")
    p.add_argument("--top-orders", type=int, default=5, help="--singulion で表示する上位の数（既定: 5）")
    p.add_argument("--order", action="append",
                   help="--singulion で評価する並び（例: 77|82,78|81,75|84,76|83,79|80）。複数指定可")
    p.add_argument("--consensus", action="store_true",
                   help="3 つの設定（words/tfidf, words/raw, glyph2/raw）で並べ替え、一致した隣どうしを出す")
    p.add_argument("--consensus-min", type=int, default=2,
                   help="--consensus で、何設定以上で支持された組を出すか（既定: 2）")
    args = p.parse_args(argv)
    if args.locus is None:
        args.locus = "P"
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    path, lines = corpus.load_lines(args)
    opts = corpus.word_options(args)
    print(f"転写ファイル: {path.name}（特徴: {args.feature}, 重み: {args.weight}）\n")
    if args.singulion:
        groups_q: dict[str, list[ivtff.Line]] = {}
        for ln in lines:
            groups_q.setdefault(ln.page.get(args.within or "Q"), []).append(ln)
        for key in groups_q:
            print_singulion(corpus.group_label(args.within or "Q", key), groups_q[key], opts, args)
        return
    if args.within:
        groups: dict[str, list[ivtff.Line]] = {}
        for ln in lines:
            groups.setdefault(ln.page.get(args.within), []).append(ln)
        for key in sorted(groups):
            analyse(corpus.group_label(args.within, key),
                    build_units(groups[key], opts, args.unit), args)
    else:
        analyse(corpus.filter_title(args), build_units(lines, opts, args.unit), args)


if __name__ == "__main__":
    main()

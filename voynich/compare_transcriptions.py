#!/usr/bin/env python3
"""ヴォイニッチ手稿 転写の比較スクリプト。

これまでの分析（単語頻度・語頭語尾・行頭行末・語彙の移り変わり）の主な指標を、
複数の転写ファイルで同じ手順で計算して並べる。結果が特定の転写者の読みに依存していないか
（頑健性）を確かめるためのもの。

使い方の例:
    python3 voynich/compare_transcriptions.py                         # ZL と IT（高橋）を比較
    python3 voynich/compare_transcriptions.py ZL3b-n.txt IT2a-n.txt RF1b-e.txt

ファイル名だけを渡すと voynich/data/ から読み、無ければ voynich.nu から取得する。
標準ライブラリのみで動作する（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import affix  # noqa: E402
import corpus  # noqa: E402
import ivtff  # noqa: E402
import line_position  # noqa: E402
import vocab_shift  # noqa: E402
import word_freq  # noqa: E402
from corpus import ljust, rjust  # noqa: E402

DEFAULT_FILES = ["ZL3b-n.txt", "IT2a-n.txt"]
MISSING = "-"


def pct(a: float, b: float) -> str:
    return f"{a / b:.1%}" if b else MISSING


def share(counter: Counter, key: str) -> float:
    total = sum(counter.values())
    return counter[key] / total if total else 0.0


def metrics(path: Path, opts: ivtff.Options, trials: int) -> tuple[dict[str, str], Counter]:
    """1 つの転写ファイルについて主な指標を計算する。戻り値: (指標, 全体の単語頻度)"""
    lines = ivtff.parse_file(path)
    m: dict[str, str] = {}

    # --- 単語頻度（全テキスト）
    words = Counter()
    by_lang = {"A": Counter(), "B": Counter()}
    for ln in lines:
        ws = ivtff.words(ln.raw, opts)
        words.update(ws)
        if ln.page.get("L") in by_lang:
            by_lang[ln.page.get("L")].update(ws)
    s = word_freq.summary(words)
    m["頁数"] = str(len({ln.page.name for ln in lines}))
    m["総語数"] = f"{s['tokens']:,}"
    m["異なり語数"] = f"{s['types']:,}"
    m["Zipf 指数"] = f"{s['zipf']:.3f}"
    m["上位 5 語"] = " ".join(w for w, _ in words.most_common(5))

    # --- 語頭・語尾
    pos = affix.glyph_positions(words)
    for g, where in (("q", "語頭"), ("n", "語末"), ("m", "語末")):
        c = pos.get(g, Counter())
        m[f"`{g}` が{where}にある割合"] = pct(c[where], sum(c.values()))
    for lang in ("A", "B"):
        suf, _, _ = affix.affixes(by_lang[lang], 3, suffix=True)
        m[f"語尾 -edy の割合（言語 {lang}）"] = pct(suf["edy"], sum(by_lang[lang].values()))

    # --- 行頭・行末（段落テキスト）
    para = [ln for ln in lines if ln.locus_class == "P"]
    tls = line_position.text_lines(para, opts)
    lp = line_position.collect(tls)
    has_paragraphs = any(tl.paragraph_start for tl in tls)
    if has_paragraphs:
        pf = line_position.first_glyphs(lp.para_first)
        gallows = sum(c for g, c in pf.items() if g in line_position.GALLOWS)
        m["段落頭の語がガロウズで始まる割合"] = pct(gallows, sum(pf.values()))
        m["段落頭の語が p- で始まる割合"] = pct(pf["p"], sum(pf.values()))
        first = lp.line_first_other
        last = lp.line_last_other
    else:  # 段落記号の無い転写: 段落の区別をせずに全行の行頭・行末を使う
        m["段落頭の語がガロウズで始まる割合"] = MISSING
        m["段落頭の語が p- で始まる割合"] = MISSING
        first, last = lp.first, lp.last
    mid_first = line_position.first_glyphs(lp.middle)
    mid_last = line_position.last_glyphs(lp.middle)
    m["行頭の語が y- で始まる割合 / 行中"] = \
        f"{share(line_position.first_glyphs(first), 'y'):.1%} / {share(mid_first, 'y'):.1%}"
    m["行末の語が -m で終わる割合 / 行中"] = \
        f"{share(line_position.last_glyphs(last), 'm'):.1%} / {share(mid_last, 'm'):.1%}"

    # --- 語彙の移り変わり（段落テキスト, 50 語以上の頁）
    pages = [pt for pt in vocab_shift.page_texts(para, opts) if pt.size >= 50]
    sim = vocab_shift.similarity_matrix([pt.words for pt in pages])
    rel = dict(vocab_shift.relation_table(pages, sim))
    for key in ("全ての組", "言語が異なる (A と B)", "同じ言語 (A/B)", "隣り合うページ",
                "同じ二つ折りの別の葉", "同じ葉の表と裏"):
        vals = rel.get(key)
        m[f"類似度: {key}"] = f"{vocab_shift.mean(vals):.3f}" if vals else MISSING
    if trials:
        _, _, p = vocab_shift.adjacency_test(sim, trials, seed=1)
        m["隣接頁の並べ替え検定 p 値"] = f"{p:.4f}"
    return m, words


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="複数の転写ファイルで主な指標を比べる")
    p.add_argument("files", nargs="*", type=Path, default=[Path(f) for f in DEFAULT_FILES],
                   help="比べる転写ファイル（既定: " + " ".join(DEFAULT_FILES) + "）")
    p.add_argument("--trials", type=int, default=2000,
                   help="隣接頁の並べ替え検定の回数（既定: 2000, 0 で省略）")
    p.add_argument("--overlap-top", type=int, default=100,
                   help="上位語の一致を比べる語数（既定: 100）")
    args = p.parse_args(argv)

    opts = ivtff.Options()
    results = []
    for f in args.files:
        path = corpus.ensure_data(f)
        m, words = metrics(path, opts, args.trials)
        results.append((path.name, m, words))

    # 上位語の一致（1 つ目のファイルを基準に）
    base_top = {w for w, _ in results[0][2].most_common(args.overlap_top)}
    for name, m, words in results:
        top = {w for w, _ in words.most_common(args.overlap_top)}
        m[f"上位 {args.overlap_top} 語のうち {results[0][0]} と共通"] = str(len(top & base_top))

    keys = list(results[0][1])
    names = [name for name, _, _ in results]
    label_w = max(corpus.text_width(k) for k in keys) + 2
    col_w = max([corpus.text_width(v) for _, m, _ in results for v in m.values()]
                + [len(n) for n in names]) + 2
    print("各転写で同じ手順・同じ設定（既定の単語化）で計算した主な指標\n")
    for name in names:
        desc = corpus.KNOWN_FILES.get(name, "")
        print(f"  {name}: {desc}")
    print()
    print(ljust("指標", label_w) + "".join(rjust(n, col_w) for n in names))
    for k in keys:
        print(ljust(k, label_w) + "".join(rjust(m.get(k, MISSING), col_w) for _, m, _ in results))
    print()


if __name__ == "__main__":
    main()

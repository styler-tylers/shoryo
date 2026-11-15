#!/usr/bin/env python3
"""薬学セクションの「ラベル → 物」対応表の下書きを作る。

ZL 転写から薬学セクション（挿絵 P）のラベル（Lf 薬草のかけら・Lc 薬壺）を、頁・段・順番つきで書き出し、
画像で確かめた観察（notes/pharma_label_observations.csv）を突き合わせて
voynich/notes/薬学ラベル対応表.csv を作る。観察の無い行は空欄で、研究者が画像を見て埋める。

    python3 voynich/pharma_labels.py

列: 頁, 段, 段内の順, ロカス, 種類（薬草/薬壺）, ラベル, 他の頁にも出るか, IIIF の画像, 物の様子, ラベルの位置, 確からしさ, 確認者
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import spread  # noqa: E402

HERE = Path(__file__).resolve().parent
OBS = HERE / "notes" / "pharma_label_observations.csv"
OUT = HERE / "notes" / "薬学ラベル対応表.csv"

# Yale の画像のラベルが ZL の頁名と単純に対応しない頁（画像の文字と ZL のラベル順を照合して決めた）
IMAGE_OVERRIDE = {
    "f102v2": "f102v (part)",       # 小さな葉が 2 段に並ぶ頁
    "f102v1": "f102v (part) [2]",   # 根が 2 段に並ぶ頁
}


def rows_by_page(lines: list[ivtff.Line]):
    """頁ごとに、ラベルを段（本文や絵の行で区切られたまとまり）に分ける。"""
    pages: dict[str, list[list[ivtff.Line]]] = defaultdict(list)
    current: dict[str, list[ivtff.Line]] = {}
    for ln in lines:
        if ln.page.get("I") != "P":
            continue
        name = ln.page.name
        if ln.locus_type in ("Lf", "Lc"):
            current.setdefault(name, []).append(ln)
        elif current.get(name):
            pages[name].append(current.pop(name))
    for name, rest in current.items():
        if rest:
            pages[name].append(rest)
    return pages


def main() -> None:
    path = corpus.ensure_data(corpus.DEFAULT_FILE)
    lines = ivtff.parse_file(path)
    pages = rows_by_page(lines)
    manifest = spread.load_manifest()
    opts = ivtff.Options(drop_uncertain=False)

    count: dict[str, set] = defaultdict(set)
    for name, rows in pages.items():
        for row in rows:
            for ln in row:
                for w in ivtff.words(ln.raw, opts):
                    count[w].add(name)

    obs = {}
    if OBS.exists():
        with open(OBS, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                obs[r["ロカス"]] = r

    out_rows = []
    for name, rows in pages.items():
        image = IMAGE_OVERRIDE.get(name) or spread.resolve_page(manifest, name) or ""
        for k, row in enumerate(rows, 1):
            for j, ln in enumerate(row, 1):
                label = " ".join(ivtff.words(ln.raw, opts))
                others = sorted({p for w in label.split() for p in count[w]} - {name})
                o = obs.get(ln.id, {})
                out_rows.append({
                    "頁": name, "段": k, "段内の順": j, "ロカス": ln.id,
                    "種類": "薬壺" if ln.locus_type == "Lc" else "薬草",
                    "ラベル": label, "他の頁にも出る": " ".join(others),
                    "IIIF の画像": image.removeprefix("f") if image else "",
                    "物の様子": o.get("物の様子", ""), "ラベルの位置": o.get("ラベルの位置", ""),
                    "確からしさ": o.get("確からしさ", ""), "確認者": o.get("確認者", ""),
                })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    filled = sum(1 for r in out_rows if r["物の様子"])
    print(f"{OUT}: {len(out_rows)} 行（観察あり {filled} 行）")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ヴォイニッチ手稿 頁の左上の一覧画像（大きな頭文字を探すため）。

Layfield & Davis (2026) は、f76r と f105r が大きな「頭文字」で始まり、セクションの始まりを示すと指摘した。
転写ファイルには字の大きさが記録されていないので、各頁の左上（最初の行があるあたり）を
Yale の IIIF 画像から切り出し、頁名と最初の語（EVA）を添えて一覧画像（コンタクトシート）にまとめる。
一覧を目で見て、大きな頭文字の候補を探すためのもの。

    python3 voynich/initials.py                      # 段落テキストのある全頁
    python3 voynich/initials.py --quire T,M          # クワイアを絞る
    python3 voynich/initials.py --pages f76r,f105r --region 0,0,50,35

出力: voynich/out/initials/（各頁の切り出し crop_*.jpg と一覧 sheet_*.jpg）。Pillow が必要。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import ivtff  # noqa: E402
import spread  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "out" / "initials"


def first_paragraph_word(lines: list[ivtff.Line]) -> str:
    for ln in lines:
        if ln.locus_class == "P":
            ws = ivtff.words(ln.raw, ivtff.Options(drop_uncertain=False))
            if ws:
                return ws[0]
    return ""


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="頁の左上を切り出して一覧画像にする")
    p.add_argument("--file", type=Path, default=corpus.DEFAULT_FILE, help="転写ファイル（頁の選択と最初の語に使う）")
    p.add_argument("--quire", help="クワイア（カンマ区切り）")
    p.add_argument("--pages", help="頁（カンマ区切り）。指定すると --quire より優先")
    p.add_argument("--region", default="0,0,45,30",
                   help="切り出す範囲（頁に対する割合 %%: 左,上,幅,高さ。既定: 0,0,45,30）")
    p.add_argument("--width", type=int, default=360, help="切り出し画像の幅（既定: 360）")
    p.add_argument("--per-sheet", type=int, default=20, help="1 枚の一覧に並べる頁数（既定: 20）")
    p.add_argument("--cols", type=int, default=5, help="一覧の列数（既定: 5）")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    args = p.parse_args(argv)

    path = corpus.ensure_data(args.file)
    by_page: dict[str, list[ivtff.Line]] = {}
    for ln in ivtff.parse_file(path):
        by_page.setdefault(ln.page.name, []).append(ln)
    if args.pages:
        names = [x.strip() for x in args.pages.split(",") if x.strip()]
    else:
        quires = {q.strip() for q in args.quire.split(",")} if args.quire else None
        names = [n for n, ls in by_page.items()
                 if any(ln.locus_class == "P" for ln in ls)
                 and (quires is None or ls[0].page.get("Q") in quires)]

    pages = spread.load_manifest()
    args.out.mkdir(parents=True, exist_ok=True)
    crops = []
    for i, name in enumerate(names, 1):
        label = spread.resolve_page(pages, name)
        if label is None:
            print(f"  （IIIF に無い頁: {name}）", file=sys.stderr)
            continue
        if label != name:
            # 折り込みや 2 頁まとめた画像。同じ画像を指す頁は最初の 1 つだけ切り出す
            if any(c[3] == label for c in crops):
                continue
        dest = args.out / f"crop_{name}.jpg"
        if not dest.exists():
            img = spread.get_image(pages, name, f"pct:{args.region}", f"{args.width},")
            img.save(dest, quality=88)
        word = first_paragraph_word(by_page.get(name, []))
        crops.append((name, word, dest, label))
        print(f"  {i}/{len(names)} {name}", file=sys.stderr)

    # 一覧画像
    label_h = 22
    for s in range(0, len(crops), args.per_sheet):
        chunk = crops[s:s + args.per_sheet]
        ims = [Image.open(c[2]) for c in chunk]
        cell_w = args.width
        cell_h = max(im.height for im in ims) + label_h
        rows = (len(chunk) + args.cols - 1) // args.cols
        sheet = Image.new("RGB", (cell_w * args.cols, cell_h * rows), "white")
        draw = ImageDraw.Draw(sheet)
        for k, ((name, word, _, label), im) in enumerate(zip(chunk, ims)):
            x, y = (k % args.cols) * cell_w, (k // args.cols) * cell_h
            note = "" if label == name else f"  [画像: {label}]"
            draw.text((x + 4, y + 4), f"{name}  {word}{note}", fill="black")
            sheet.paste(im, (x, y + label_h))
        out = args.out / f"sheet_{s // args.per_sheet + 1:02d}_{chunk[0][0]}-{chunk[-1][0]}.jpg"
        sheet.save(out, quality=85)
        print(out)


if __name__ == "__main__":
    main()

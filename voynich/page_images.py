#!/usr/bin/env python3
"""ヴォイニッチ手稿の全頁の縮小画像を Yale の IIIF から取得して保存する。

    python3 voynich/page_images.py                # 幅 500 px で全 213 枚
    python3 voynich/page_images.py --width 800

保存先: voynich/data/pages/<IIIF のラベル>.jpg（リポジトリには含めない）。取得済みの画像は飛ばす。
画像: Yale University, Beinecke Rare Book and Manuscript Library, MS 408。Pillow が必要。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spread  # noqa: E402

PAGE_DIR = Path(__file__).resolve().parent / "data" / "pages"


def safe_name(label: str) -> str:
    return re.sub(r"[^\w.-]+", "_", label).strip("_")


def image_path(label: str, width: int) -> Path:
    return PAGE_DIR / f"w{width}" / f"{safe_name(label)}.jpg"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="全頁の縮小画像を取得する")
    p.add_argument("--width", type=int, default=500, help="画像の幅（既定: 500）")
    args = p.parse_args(argv)
    pages = spread.load_manifest()
    for i, label in enumerate(pages, 1):
        dest = image_path(label, args.width)
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        spread.get_image(pages, label, "full", f"{args.width},").save(dest, quality=90)
        print(f"{i}/{len(pages)} {label}", file=sys.stderr)
    print(f"保存先: {PAGE_DIR / f'w{args.width}'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ヴォイニッチ手稿 見開き画像の組み立てスクリプト。

Yale 大学図書館の IIIF 画像から 2 つの頁を取得し、左右に並べた「見開き」の画像と、
綴じ目の側だけを拡大して並べた画像を作る。綴じ目をまたぐ絵のつながりを目で確かめるためのもの。

    python3 voynich/spread.py f78v f81r                 # 二つ折りの中央見開き（singulion 仮説）
    python3 voynich/spread.py f78v f79r                 # 現在の綴じ順での見開き（比較用）
    python3 voynich/spread.py --conjoint                # 論文が挙げた 5 組をまとめて作る
    python3 voynich/spread.py --conjoint --compare      # 現在の見開きと並べた比較画像も作る

左に置く頁（ふつうは裏 v）の右端と、右に置く頁（ふつうは表 r）の左端が綴じ目の側。
出力先は voynich/out/spreads/（リポジトリには含めない）。Pillow が必要。
画像: Yale University, Beinecke Rare Book and Manuscript Library, MS 408
（https://collections.library.yale.edu/catalog/2002046）。
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow が必要です: pip install pillow")

MANIFEST_URL = "https://collections.library.yale.edu/manifests/2002046"
OUT_DIR = Path(__file__).resolve().parent / "out" / "spreads"
CACHE = Path(__file__).resolve().parent / "data" / "yale_manifest.json"

# Layfield & Davis (2026) が挙げた、綴じ目をまたぐ絵のある二つ折りの中央見開き
CONJOINT_EXAMPLES = [
    ("f78v", "f81r", "2 本の流れ"),
    ("f10v", "f15r", "飛び散った染み"),
    ("f33v", "f40r", "青い花びら"),
    ("f58v", "f65r", "緑の葉のかけら"),
    ("f76v", "f83r", "ニンフの右腕"),
]


def fetch(url: str, tries: int = 4) -> bytes:
    """画像サーバーが混んでいると 504 を返すことがあるので、間隔をあけて数回やり直す。"""
    req = urllib.request.Request(url, headers={"User-Agent": "voynich-analysis/1.0"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if attempt == tries - 1:
                sys.exit(f"エラー: 取得に失敗しました ({e}): {url}")
            wait = 5 * 2 ** attempt
            print(f"  取得に失敗（{e}）。{wait} 秒後にやり直します", file=sys.stderr)
            time.sleep(wait)
    raise AssertionError("unreachable")


def load_manifest() -> dict[str, tuple[str, int, int]]:
    """頁名（例: 'f78v'）-> (IIIF 画像サービスの URL, 幅, 高さ)"""
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"IIIF マニフェストを取得します: {MANIFEST_URL}", file=sys.stderr)
        CACHE.write_bytes(fetch(MANIFEST_URL))
    manifest = json.loads(CACHE.read_text(encoding="utf-8"))
    pages = {}
    for canvas in manifest["items"]:
        label = "".join(canvas.get("label", {}).get("none", []))
        body = canvas["items"][0]["items"][0]["body"]
        service = body["id"].split("/full/")[0]
        pages["f" + label] = (service, body["width"], body["height"])
    return pages


def page_order(pages) -> list[str]:
    return list(pages)  # マニフェストの順 = 現在の綴じ順


def current_neighbours(pages, left: str, right: str) -> tuple[str | None, str | None]:
    """現在の綴じ順で left の次の頁（left の現在の見開きの相手）と、right の前の頁を返す。"""
    order = page_order(pages)
    i, j = order.index(left), order.index(right)
    nxt = order[i + 1] if i + 1 < len(order) else None
    prv = order[j - 1] if j > 0 else None
    return nxt, prv


def make_comparison(pages, left: str, right: str, gutter_frac: float, out_dir: Path) -> Path | None:
    """[left | 現在の相手]、[left | right]、[現在の相手 | right] の綴じ目の拡大を横に並べる。"""
    nxt, prv = current_neighbours(pages, left, right)
    if nxt == right:
        print(f"  {left} と {right} は現在の綴じ順でも見開きのため、比較画像は作りません", file=sys.stderr)
        return None
    panels = []
    for a, b in ((left, nxt), (left, right), (prv, right)):
        if a and b:
            path = out_dir / f"gutter_{a}_{b}.jpg"
            if not path.exists():
                make_spread(pages, a, b, gutter_frac, out_dir)
            im = Image.open(path)
            h = 1100
            panels.append(im.resize((int(im.width * h / im.height), h)))
    out = panels[0]
    for im in panels[1:]:
        out = side_by_side(out, im, gap=30)
    path = out_dir / f"compare_{left}_{right}.jpg"
    out.save(path, quality=88)
    return path


def get_image(pages, name: str, region: str = "full", size: str = "900,") -> Image.Image:
    if name not in pages:
        sys.exit(f"頁 {name} が IIIF マニフェストに見つかりません。")
    service = pages[name][0]
    return Image.open(io.BytesIO(fetch(f"{service}/{region}/{size}/0/default.jpg"))).convert("RGB")


def side_by_side(left: Image.Image, right: Image.Image, gap: int = 0) -> Image.Image:
    h = max(left.height, right.height)
    out = Image.new("RGB", (left.width + right.width + gap, h), "black")
    out.paste(left, (0, 0))
    out.paste(right, (left.width + gap, 0))
    return out


def make_spread(pages, left: str, right: str, gutter_frac: float, out_dir: Path) -> list[Path]:
    """見開き全体と、綴じ目の側の拡大の 2 枚を作る。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    whole = side_by_side(get_image(pages, left), get_image(pages, right))
    p1 = out_dir / f"spread_{left}_{right}.jpg"
    whole.save(p1, quality=88)

    # 綴じ目の側: 左頁の右端と右頁の左端を、高さ全体で切り出す（原寸の 1/2）
    _, lw, lh = pages[left]
    _, rw, rh = pages[right]
    lx = int(lw * (1 - gutter_frac))
    lcrop = get_image(pages, left, f"{lx},0,{lw - lx},{lh}", f"{(lw - lx) // 2},")
    rcrop = get_image(pages, right, f"0,0,{int(rw * gutter_frac)},{rh}", f"{int(rw * gutter_frac) // 2},")
    p2 = out_dir / f"gutter_{left}_{right}.jpg"
    side_by_side(lcrop, rcrop, gap=12).save(p2, quality=90)
    return [p1, p2]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Yale の IIIF 画像から見開き画像を組み立てる")
    p.add_argument("pages", nargs="*", help="左の頁と右の頁（例: f78v f81r）")
    p.add_argument("--conjoint", action="store_true",
                   help="Layfield & Davis (2026) が挙げた綴じ目をまたぐ絵の 5 組をまとめて作る")
    p.add_argument("--gutter", type=float, default=0.25,
                   help="綴じ目の側として切り出す幅（頁幅に対する割合, 既定: 0.25）")
    p.add_argument("--out", type=Path, default=OUT_DIR, help="出力先（既定: voynich/out/spreads）")
    p.add_argument("--compare", action="store_true",
                   help="各組について [左頁 | 現在の相手] [左頁 | 右頁] [現在の相手 | 右頁] の"
                        "綴じ目の拡大を並べた比較画像（compare_*.jpg）も作る")
    args = p.parse_args(argv)

    pairs = []
    if args.conjoint:
        pairs += [(a, b) for a, b, _ in CONJOINT_EXAMPLES]
    if args.pages:
        if len(args.pages) % 2:
            p.error("頁は左・右の 2 つずつ指定してください")
        pairs += list(zip(args.pages[::2], args.pages[1::2]))
    if not pairs:
        p.error("頁の組か --conjoint を指定してください")

    pages = load_manifest()
    for left, right in pairs:
        for path in make_spread(pages, left, right, args.gutter, args.out):
            print(path)
        if args.compare:
            path = make_comparison(pages, left, right, args.gutter, args.out)
            if path:
                print(path)


if __name__ == "__main__":
    main()

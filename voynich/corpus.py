"""分析スクリプト共通の処理: 転写ファイルの取得、コマンドライン引数、絞り込み、統計、表示。"""

from __future__ import annotations

import argparse
import math
import sys
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

import ivtff

ZL_URL = "https://www.voynich.nu/data/ZL3b-n.txt"
DEFAULT_FILE = Path(__file__).resolve().parent / "data" / "ZL3b-n.txt"

GROUP_LABELS = {
    "L": {"A": "言語 A", "B": "言語 B"},
    "I": ivtff.ILLUSTRATION_TYPES,
}

_FILTER_KEYS = {"language": "L", "hand": "H", "illustration": "I", "quire": "Q"}


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------


def ensure_data(path: Path) -> Path:
    """転写ファイルが無ければ voynich.nu からダウンロードする。"""
    if path.exists():
        return path
    if path != DEFAULT_FILE:
        sys.exit(f"エラー: ファイルが見つかりません: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"転写ファイルをダウンロードします: {ZL_URL}", file=sys.stderr)
    req = urllib.request.Request(ZL_URL, headers={"User-Agent": "voynich-analysis/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:  # noqa: BLE001
        sys.exit(
            f"エラー: ダウンロードに失敗しました ({e})。\n"
            f"手動で {ZL_URL} を取得し {path} に置くか、--file で指定してください。"
        )
    path.write_bytes(data)
    return path


# ---------------------------------------------------------------------------
# コマンドライン引数
# ---------------------------------------------------------------------------


def make_parser(description: str) -> argparse.ArgumentParser:
    """ファイル指定・絞り込み・比較・単語化の共通オプションを備えたパーサを返す。"""
    p = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "挿絵種別 (--illustration / --by I):\n"
            + "\n".join(f"  {k}: {v}" for k, v in ivtff.ILLUSTRATION_TYPES.items())
            + "\nロカス種別 (--locus):\n"
            + "\n".join(f"  {k}: {v}" for k, v in ivtff.LOCUS_CLASSES.items())
        ),
    )
    p.add_argument("--file", type=Path, default=DEFAULT_FILE,
                   help="IVTFF 転写ファイル（省略時は ZL3b を自動ダウンロード）")

    f = p.add_argument_group("絞り込み（カンマ区切りで複数指定可）")
    f.add_argument("--language", help="Currier 言語（A, B）")
    f.add_argument("--hand", help="筆写者（1〜5）")
    f.add_argument("--illustration", help="挿絵種別（H, A, C, Z, B, P, S, T）")
    f.add_argument("--quire", help="クワイア（A〜T）")
    f.add_argument("--page", help="ページ（例: f1r,f1v）")
    f.add_argument("--locus", help="ロカス種別（P=段落, L=ラベル, C=円形, R=放射状）")

    g = p.add_argument_group("比較")
    g.add_argument("--by", choices=list(ivtff.PAGE_VARIABLES),
                   help="ページ属性でグループ分けして比較（例: L=言語, H=筆写者, I=挿絵）")
    g.add_argument("--min-count", type=int, default=5,
                   help="特徴の計算に使う最小出現数（既定: 5）")

    t = p.add_argument_group("単語化の設定")
    t.add_argument("--keep-uncertain", action="store_true",
                   help="判読不能文字 ? を含む単語も数える")
    t.add_argument("--drop-rare", action="store_true",
                   help="稀少文字 @nnn; を含む単語を除外する")
    t.add_argument("--comma-join", action="store_true",
                   help="カンマ（不確かなスペース）を区切りとみなさず連結する")
    t.add_argument("--alt", type=int, default=0,
                   help="異読 [a:o] のうち何番目を採用するか（0 始まり, 既定: 0）")
    return p


def _split(value: str | None) -> set[str] | None:
    return {v.strip() for v in value.split(",") if v.strip()} if value else None


def word_options(args: argparse.Namespace) -> ivtff.Options:
    return ivtff.Options(
        alternative=args.alt,
        comma_is_space=not args.comma_join,
        drop_uncertain=not args.keep_uncertain,
        drop_rare=args.drop_rare,
    )


def load_lines(args: argparse.Namespace) -> tuple[Path, list[ivtff.Line]]:
    """転写ファイルを読み込み、絞り込み条件に合う行だけを返す。"""
    path = ensure_data(args.file)
    page_filters = {var: _split(getattr(args, name)) for name, var in _FILTER_KEYS.items()}
    pages_wanted = _split(args.page)
    locus_wanted = _split(args.locus)

    def selected(line: ivtff.Line) -> bool:
        for key, allowed in page_filters.items():
            if allowed and line.page.get(key) not in allowed:
                return False
        if pages_wanted and line.page.name not in pages_wanted:
            return False
        if locus_wanted and line.locus_class not in locus_wanted:
            return False
        return True

    lines = [ln for ln in ivtff.parse_file(path) if selected(ln)]
    if not lines:
        sys.exit("条件に合う行がありません。")
    return path, lines


def filter_title(args: argparse.Namespace) -> str:
    filters = [f"{k}={getattr(args, k)}"
               for k in ("language", "hand", "illustration", "quire", "page", "locus")
               if getattr(args, k)]
    return "全体" + (f"（{', '.join(filters)}）" if filters else "")


def group_label(by: str, key: str) -> str:
    var_name = ivtff.PAGE_VARIABLES[by]
    if key == "?":
        return f"{var_name} = 未指定"
    return GROUP_LABELS.get(by, {}).get(key, f"{var_name} = {key}")


# ---------------------------------------------------------------------------
# 統計
# ---------------------------------------------------------------------------


def log_likelihood(a: int, b: int, c: int, d: int) -> float:
    """対数尤度比 G²。a: 対象群での出現数, b: 残りでの出現数, c/d: 各群の総数。

    対象群で相対的に多ければ正、少なければ負の値を返す。
    """
    e1 = c * (a + b) / (c + d)
    e2 = d * (a + b) / (c + d)
    g2 = 0.0
    if a:
        g2 += a * math.log(a / e1)
    if b:
        g2 += b * math.log(b / e2)
    g2 *= 2
    return g2 if a / c >= b / d else -g2


def distinctive(group: Counter, rest: Counter, c: int, d: int,
                min_count: int) -> list[tuple[float, str, int, int]]:
    """group で rest より多い項目を G² の降順で返す。c/d は各群の総数（単語数など）。"""
    scored = []
    for item in set(group) | set(rest):
        a, b = group[item], rest[item]
        if a + b < min_count:
            continue
        g2 = log_likelihood(a, b, c, d)
        if g2 > 0:
            scored.append((g2, item, a, b))
    scored.sort(reverse=True)
    return scored


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def text_width(text: str) -> int:
    """端末での表示幅（全角文字を 2 として数える）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def ljust(text: str, width: int) -> str:
    return text + " " * max(width - text_width(text), 0)


def rjust(text: str, width: int) -> str:
    return " " * max(width - text_width(text), 0) + text

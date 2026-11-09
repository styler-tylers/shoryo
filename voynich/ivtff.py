"""IVTFF 形式（Intermediate Voynich Transliteration File Format）のパーサ。

René Zandbergen の ZL 転写ファイル（ZL3b-n.txt など）を読み込み、
ページ属性（言語・筆写者・挿絵種別など）付きの行・単語に分解する。

標準ライブラリのみで動作する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

# ---------------------------------------------------------------------------
# ページ属性の意味（ZL ファイルのページヘッダ <! $X=... > に対応）
# ---------------------------------------------------------------------------

ILLUSTRATION_TYPES = {
    "A": "天文 (Astronomical)",
    "B": "生物・浴場 (Biological)",
    "C": "宇宙論 (Cosmological)",
    "H": "植物 (Herbal)",
    "P": "薬学 (Pharmaceutical)",
    "S": "星・レシピ (Stars)",
    "T": "テキストのみ (Text only)",
    "Z": "黄道十二宮 (Zodiac)",
}

PAGE_VARIABLES = {
    "Q": "クワイア (Quire)",
    "P": "クワイア内の位置 (Page in quire)",
    "F": "フォリオ (Folio in quire)",
    "B": "二つ折り (Bifolio in quire)",
    "I": "挿絵種別 (Illustration)",
    "L": "Currier 言語 (Language A/B)",
    "H": "筆写者 (Hand, Davis 分類)",
    "C": "Currier の筆写者 (Currier hand)",
    "X": "追加情報 (Extraneous writing)",
}

# 行ロカス種別の先頭文字
LOCUS_CLASSES = {
    "P": "段落テキスト (Paragraph)",
    "L": "ラベル (Label)",
    "C": "円形テキスト (Circular)",
    "R": "放射状テキスト (Radial)",
}

# ---------------------------------------------------------------------------
# データ構造
# ---------------------------------------------------------------------------


@dataclass
class Page:
    """1 ページ（フォリオの表または裏）。"""

    name: str  # 例: "f1r"
    variables: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str = "?") -> str:
        return self.variables.get(key, default)


@dataclass
class Line:
    """転写テキストの 1 行（IVTFF の 1 ロカス）。"""

    page: Page
    number: str  # 行番号（例: "1"）
    position: str  # ロカス位置記号（@ + * = & など）
    locus_type: str  # ロカス種別（例: "P0", "Lz", "Cc"）
    raw: str  # マークアップを含む生テキスト

    @property
    def locus_class(self) -> str:
        """ロカス種別の大分類（P/L/C/R）。"""
        return self.locus_type[:1]

    @property
    def id(self) -> str:
        return f"{self.page.name}.{self.number}"


@dataclass
class Options:
    """単語化の設定。"""

    # [a:o] のような異読のうち、どれを採用するか（0 = 最初の読み）
    alternative: int = 0
    # カンマ（不確かなスペース）を単語区切りとして扱うか
    comma_is_space: bool = True
    # ? を含む（判読不能文字を含む）単語を除外するか
    drop_uncertain: bool = True
    # @123; のような稀少文字を含む単語を除外するか
    drop_rare: bool = False


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

_PAGE_RE = re.compile(r"^<(f\d+[rv]\d*)>\s*(?:<!(.*)>)?\s*$")
_LOCUS_RE = re.compile(r"^<(f\d+[rv]\d*)\.(\w+),(.)(\w+)>\s*(.*)$")
_VAR_RE = re.compile(r"\$([A-Z])=([^\s>]+)")

_COMMENT_RE = re.compile(r"<![^>]*>")  # インラインコメント <!...>
_DRAWING_BREAK_RE = re.compile(r"<[-~]>")  # 挿絵による中断 <-> <~>
_OTHER_TAG_RE = re.compile(r"<[^>]*>")  # <%> <$> <@H=2> など
_ALTERNATIVE_RE = re.compile(r"\[([^\]]*)\]")  # 異読 [a:o]
_LIGATURE_RE = re.compile(r"\{([^}]*)\}")  # 合字 {ckh}
_RARE_RE = re.compile(r"@\d+;")  # 稀少文字 @185;


def parse(lines: Iterable[str]) -> Iterator[Line]:
    """IVTFF テキストの各行を解析し、転写行（Line）を順に返す。"""
    pages: dict[str, Page] = {}
    for text in lines:
        text = text.rstrip("\n")
        if not text or text.startswith("#"):
            continue

        m = _PAGE_RE.match(text)
        if m:
            name, header = m.group(1), m.group(2) or ""
            pages[name] = Page(name, dict(_VAR_RE.findall(header)))
            continue

        m = _LOCUS_RE.match(text)
        if m:
            name, number, position, locus_type, body = m.groups()
            page = pages.setdefault(name, Page(name))
            yield Line(page, number, position, locus_type, body)


def parse_file(path: str | Path) -> list[Line]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(parse(f))


def _choose_alternative(match: re.Match, index: int) -> str:
    options = match.group(1).split(":")
    return options[min(index, len(options) - 1)]


def clean(raw: str, opts: Options | None = None) -> str:
    """マークアップを除去し、単語区切りを '.' に統一したテキストを返す。"""
    opts = opts or Options()
    s = _COMMENT_RE.sub("", raw)
    s = _DRAWING_BREAK_RE.sub(".", s)
    s = _OTHER_TAG_RE.sub("", s)
    s = _ALTERNATIVE_RE.sub(lambda m: _choose_alternative(m, opts.alternative), s)
    s = _LIGATURE_RE.sub(r"\1", s)
    if opts.comma_is_space:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    return s


def words(raw: str, opts: Options | None = None) -> list[str]:
    """1 行の生テキストを単語リストに分解する。"""
    opts = opts or Options()
    result = []
    for w in clean(raw, opts).split("."):
        w = w.strip()
        if not w:
            continue
        if opts.drop_uncertain and "?" in w:
            continue
        if opts.drop_rare and _RARE_RE.search(w):
            continue
        result.append(w)
    return result

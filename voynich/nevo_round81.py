#!/usr/bin/env python3
"""nēvo による解析 第 81 巡: N240（平文ありの冗長な暗号に、ヘブライ語を平文として入れる）。

    python3 voynich/nevo_round81.py <Sefaria の JSON（創世記〜申命記）> ...

JSON は https://www.sefaria.org/api/v3/texts/<書名>?version=hebrew&return_format=text_only（リポジトリには入れない）。
作り方は第 75 巡の C1 と同じ（言語 B, 奇数番目の頁 → 偶数番目の頁, q = 0.3）。平文だけを入れ替える。"""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hebrew_compare import hebrew_words  # noqa: E402
from nevo_round9 import voynich  # noqa: E402
import nevo_round75 as r75  # noqa: E402

FINAL = str.maketrans("ךםןףץ", "כמנפצ")


def main(paths):
    ws = [w.translate(FINAL) for p in paths for w in hebrew_words(Path(p))]
    letters = [c for w in ws for c in w]
    cnt = Counter(letters)
    print(f"ヘブライ語: {len(ws)} 語・{len(letters)} 字・字の種類 {len(cnt)}（{''.join(sorted(cnt))}）", flush=True)
    V = voynich()
    kb = list(V["B"][0])
    r75.run("N240 ヘブライ語・奇数 → 偶数", V, "B", kb[0::2], kb[1::2], letters)


if __name__ == "__main__":
    main(sys.argv[1:])

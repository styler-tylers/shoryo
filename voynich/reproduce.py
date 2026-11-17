#!/usr/bin/env python3
"""主な検定を 1 つの入口から再現する。

    python3 voynich/reproduce.py list              # 一覧
    python3 voynich/reproduce.py fetch             # 比べる文章（Project Gutenberg）を voynich/data/texts に取ってくる
    python3 voynich/reproduce.py run <名前> [...]   # 実行（複数可）。all で全部（数時間かかる）

転写ファイル（ZL3b-n.txt ほか）は、各スクリプトが初回に voynich.nu から取ってきて voynich/data に置く。
結果の読み方は notes の「研究全体のまとめ（nēvo 第40巡まで）」と「nēvo Research Method による解析」の各節を参照。
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTS = HERE / "data" / "texts"
GUTENBERG = {"caesar": 218, "dante": 1012, "descartes": 23306, "culpeper": 49513, "welsh": 67424, "irish": 50913}
T = lambda k: str(TEXTS / f"pg{GUTENBERG[k]}.txt")  # noqa: E731

# 名前: (説明, 記録の節, 目安の時間, スクリプト, 引数)
TESTS = {
    "line":  ("行は意味の単位か（第 16 回）: 行をまたぐ語のつながり", "行は意味の単位か", "数分", "line_unit.py", lambda: [T("caesar")]),
    "exp13": ("暗号の研究 実験 12・13: 行ごとに語の並びを回すと行の独立が出る", "暗号の研究", "数分", "e6_rotation.py", lambda: [T("caesar")]),
    "n74":   ("平文あり・平文なしのモデルを 22 の量で採点（第 25 巡）", "§79 前後", "30 分", "nevo_round25.py", lambda: [T("caesar")]),
    "n81":   ("離れた頁どうしの語彙のまとまり（第 27 巡）", "§88 前後", "30 分", "nevo_round27.py", lambda: [T("caesar")]),
    "n87":   ("まとまりは綴じの単位に従う・好みの語の入れ替え（第 29 巡）", "§92〜94", "40 分", "nevo_round29.py", lambda: [T("caesar")]),
    "n88":   ("まとまりを担うのは語の芯（第 30 巡）", "§95〜97", "40 分", "nevo_round30.py", lambda: [T("caesar")]),
    "n95":   ("語頭・語末の割合とセクション・綴じ・書き手（第 32 巡）", "§102", "数分", "nevo_round32.py", lambda: ["n95"]),
    "n98":   ("行の位置ごとの字形の分布で語を選ぶ（第 33 巡）", "§105", "40 分", "nevo_round33.py", lambda: ["n98"]),
    "n103":  ("頁のまとまりが消える原因と直し方（第 35 巡）", "§111", "40 分", "nevo_round35.py", lambda: ["n103"]),
    "n104":  ("最良のモデルの採点（A 17・B 20）と、半分の頁での確かめ（第 35 巡）", "§111", "40 分", "nevo_round35.py", lambda: ["n104"]),
    "n107":  ("まだ見えていない芯を見積もりどおりに足す（第 36 巡）", "§114", "30 分", "nevo_round36.py", lambda: ["n107"]),
    "n113":  ("写しと、隣り合う語のつながり（第 38 巡）", "§120", "60 分", "nevo_round38.py", lambda: ["n113"]),
    "n117":  ("ラベルと本文（第 39 巡）", "§123", "1 分", "nevo_round39.py", lambda: ["labels"]),
    "n116":  ("1 つ飛びの語のつながり（古い指標）・隣の行の少し違う語・1 回だけの芯の近さ（第 39 巡）", "§123", "20 分", "nevo_round39.py",
              lambda: ["texts", T("caesar"), T("dante"), T("culpeper")]),
    "n118":  ("1 つ飛びの独立（直した測り方, 第 40 巡）", "§126", "20 分", "nevo_round40.py", lambda: ["n118", str(TEXTS), str(TEXTS)]),
    "n120":  ("行をまたぐ結び付き（第 40 巡）", "§126", "20 分", "nevo_round40.py", lambda: ["n120", str(TEXTS), str(TEXTS)]),
    "n122":  ("隣り合う語のつながりが、どの組で足りないか（第 41 巡）", "§130", "5 分", "nevo_round41.py", lambda: ["n122"]),
    "n123":  ("少し替えて写すの中身（第 41 巡）", "§130", "10 分", "nevo_round41.py", lambda: ["n123"]),
    "n124":  ("芯で綴じの中の並びを推定する（第 41 巡）", "§130", "1 分", "nevo_round41.py", lambda: ["n124"]),
}


MIRRORS = ("https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt", "https://gutenberg.pglaf.org/cache/epub/{n}/pg{n}.txt")


def fetch():
    TEXTS.mkdir(parents=True, exist_ok=True)
    for name, n in GUTENBERG.items():
        p = TEXTS / f"pg{n}.txt"
        if p.exists():
            print(f"あり: {name} {p}")
            continue
        for m in MIRRORS:
            url = m.format(n=n)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=60).read()
            except OSError as e:
                print(f"失敗: {name} {url}（{e}）")
                continue
            p.write_bytes(data)
            print(f"取得: {name} {url}（{len(data)} バイト）")
            break
        else:
            print(f"取れなかった: {name}。pg{n}.txt を手で {TEXTS} に置く")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for k, (desc, sec, t, script, _) in TESTS.items():
            print(f"{k:<6} {desc}\n       記録: {sec} ／ 目安: {t} ／ {script}")
    elif cmd == "fetch":
        fetch()
    elif cmd == "run":
        names = list(TESTS) if sys.argv[2:] == ["all"] else sys.argv[2:]
        for k in names:
            if k not in TESTS:
                sys.exit(f"知らない名前: {k}（list で一覧）")
            desc, _, _, script, args = TESTS[k]
            a = args()
            missing = [x for x in a if x.endswith(".txt") and not Path(x).exists()]
            if missing or (str(TEXTS) in a and not TEXTS.exists()):
                sys.exit(f"{k}: 比べる文章が無い。先に `python3 voynich/reproduce.py fetch` を実行する")
            print(f"######## {k}: {desc} ########", flush=True)
            subprocess.run([sys.executable, "-u", str(HERE / script), *a], check=True)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

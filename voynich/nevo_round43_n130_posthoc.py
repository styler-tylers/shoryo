#!/usr/bin/env python3
"""第 43 巡 N130 の事後の点検: 行の位置の型の効果を除く。
隣り合う行の同じ位置のそろいを、(i) 同じ頁の 10 行以上離れた行との同じ位置のそろい（同じ数の組を重ならずに取る）と比べる、(ii) 行の最初の 2 語と最後の語を除く。

    python3 voynich/nevo_round43_n130_posthoc.py
"""
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nevo_round9 import voynich  # noqa: E402
from nevo_round43 import align_stat  # noqa: E402


def run(trim):
    V = voynich()
    rng = random.Random(7)
    for lang in ("A", "B"):
        adj, far = [], []
        for ls in V[lang][0].values():
            L = [[w[0] for w in (l[2:-1] if trim else l)] for l in ls]
            L = [l for l in L if len(l) >= 4]
            for i in range(len(L) - 1):
                js = [j for j in range(len(L)) if abs(j - i) >= 10]
                if not js:
                    continue  # 離れた行のある行だけ（同じ頁・同じ行で比べる）
                adj.append((L[i], L[i + 1]))
                for j in rng.sample(js, min(3, len(js))):
                    far.append((L[i], L[j]))
        n = int(0.8 * min(len(adj), len(far)))
        # 両方から同じ数を重ならずに取る（200 回）。戻しながら引くと結び付きが上にずれるので使わない
        aa = [align_stat(rng.sample(adj, n)) for _ in range(200)]
        fs = [align_stat(rng.sample(far, n)) for _ in range(200)]
        ma, mf = statistics.mean(aa), statistics.mean(fs)
        sd = (statistics.pstdev(aa) ** 2 + statistics.pstdev(fs) ** 2) ** 0.5
        print(f"  ヴォイニッチ {lang}（{'最初の 2 語と最後の語を除く' if trim else 'そのまま'}）: 隣り合う行 {ma:+.4f}  離れた行 {mf:+.4f}  z {(ma - mf) / sd:+.1f}（組 {n} ずつ）", flush=True)


for t in (False, True):
    run(t)
